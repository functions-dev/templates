# function/func.py

# Function as an MCP Server implementation
import logging
import uuid

from mcp.server.fastmcp import FastMCP
import ollama
import asyncio
import chromadb

from .parser import resolve_input, chunk_text

# Silence noisy library loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)

def new():
    """New is the only method that must be implemented by a Function.
    The instance returned can be of any name.
    """
    return Function()

class MCPServer:
    """
    MCP server that exposes a chat with an LLM model running on Ollama server
    as one of its tools.
    """

    def __init__(self):
        # Create FastMCP instance with stateless HTTP for Kubernetes deployment
        self.mcp = FastMCP("MCP-Ollama server", stateless_http=True)

        # Get the ASGI app from FastMCP
        self._app = self.mcp.streamable_http_app()

        self.client = ollama.Client()

        # init vector database
        self.dbClient = chromadb.Client()
        self.collection = self.dbClient.get_or_create_collection(
            name="my_collection"
        )
        # default embedding model
        self.embedding_model = "mxbai-embed-large"
        self._register_tools()

    def _register_tools(self):
        """Register MCP tools."""

        @self.mcp.tool()
        def list_models():
            """List all models currently available on the Ollama server"""
            try:
                models = self.client.list()
            except Exception as e:
                return f"Oops, failed to list models because: {str(e)}"
            return [model for model in models]

        default_embedding_model = self.embedding_model

        @self.mcp.tool()
        def embed_document(
            data: list[str], model: str = default_embedding_model
        ) -> str:
            """
            RAG (Retrieval-augmented generation) tool.
            Embeds documents provided in data. Each item can be a URL
            (fetched automatically) or a raw text string. Documents are
            chunked to fit the embedding model's context window.

            Args:
                data: List of URLs or text strings to embed.
                model: Embedding model to use. Example:
                    - mxbai-embed-large - default
            """
            all_chunks = []
            for item in data:
                content = resolve_input(item)
                chunks = chunk_text(content)
                all_chunks.extend(chunks)
                label = item[:60] + "..." if len(item) > 60 else item
                print(f"  Chunked '{label}' into {len(chunks)} chunks", flush=True)

            # Batch embed all chunks in one call for performance
            print(f"  Embedding {len(all_chunks)} chunks...", flush=True)
            response = ollama.embed(model=model, input=all_chunks)
            ids = [str(uuid.uuid4()) for _ in all_chunks]
            self.collection.add(
                ids=ids,
                embeddings=response["embeddings"],
                documents=all_chunks,
            )
            print("  Done.", flush=True)

            return (
                f"ok - Embedded {len(data)} document(s) "
                f"as {len(all_chunks)} chunks"
            )

        @self.mcp.tool()
        def pull_model(model: str) -> str:
            """Download and install an Ollama model into the running server"""
            try:
                _ = self.client.pull(model)
            except Exception as e:
                return f"Error occurred during pulling of a model: {str(e)}"
            return f"Success! model {model} is available"

        @self.mcp.tool()
        def call_model(
            prompt: str,
            model: str = "llama3.2:3b",
            embed_model: str = self.embedding_model,
        ) -> str:
            """Send a prompt to a model being served on ollama server.
            Uses RAG to find the most relevant embedded documents and
            includes them as context for the response."""
            try:
                # Embed the prompt for similarity search
                response = ollama.embed(model=embed_model, input=prompt)
                results = self.collection.query(
                    query_embeddings=response["embeddings"],
                    n_results=3,
                )
                context = "\n\n".join(results["documents"][0])

                output = ollama.generate(
                    model=model,
                    prompt=(
                        f"Using the following context:\n{context}\n\n"
                        f"Respond to: {prompt}"
                    ),
                )
            except Exception as e:
                return f"Error occurred during calling the model: {str(e)}"
            return output["response"]

    async def handle(self, scope, receive, send):
        """Handle ASGI requests - both lifespan and HTTP."""
        await self._app(scope, receive, send)


class Function:
    def __init__(self):
        """The init method is an optional method where initialization can be
        performed. See the start method for a startup hook which includes
        configuration.
        """
        self.mcp_server = MCPServer()
        self._mcp_initialized = False

    async def handle(self, scope, receive, send):
        """
        Main entry to your Function.
        This handles all the incoming requests.
        """

        # Initialize MCP server on first request
        if not self._mcp_initialized:
            await self._initialize_mcp()

        # Route MCP requests
        if scope.get("path", "").startswith("/mcp"):
            await self.mcp_server.handle(scope, receive, send)
            return

        # Default response for non-MCP requests
        await self._send_default_response(send)

    async def _initialize_mcp(self):
        """Initialize the MCP server by sending lifespan startup event."""
        lifespan_scope = {"type": "lifespan", "asgi": {"version": "3.0"}}
        startup_sent = False

        async def lifespan_receive():
            nonlocal startup_sent
            if not startup_sent:
                startup_sent = True
                return {"type": "lifespan.startup"}
            await asyncio.Event().wait()  # Wait forever for shutdown

        async def lifespan_send(message):
            if message["type"] == "lifespan.startup.complete":
                self._mcp_initialized = True
            elif message["type"] == "lifespan.startup.failed":
                logging.error(f"MCP startup failed: {message}")

        # Start lifespan in background
        asyncio.create_task(
            self.mcp_server.handle(
                lifespan_scope, lifespan_receive, lifespan_send
            )
        )

        # Brief wait for startup completion
        await asyncio.sleep(0.1)

    async def _send_default_response(self, send):
        """
        Send default OK response.
        This is for your non MCP requests if desired.
        """
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"OK",
            }
        )

    def start(self, cfg):
        logging.info("Function starting")

    def stop(self):
        logging.info("Function stopping")

    def alive(self):
        return True, "Alive"

    def ready(self):
        return True, "Ready"
