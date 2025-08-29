# Ollama-MCP Function with RAG

A Knative Function implementing a Model Context Protocol (MCP) server that
provides integration with Ollama for LLM interactions. This function
exposes Ollama capabilities through standardized MCP tools, enabling the
interaction with hosted language models.

The communication flow is as follows:
`MCP client -> MCP Server (Function) -> Ollama Server`

1) Setup `ollama` server (`ollama serve`)
2) Run your function (MCP server) (`func run`)
3) Connect using MCP client in `client/` dir (`python client.py`)

## Architecture

This project implements an ASGI-based Knative function with the following key
components:

### Core Components
- **Function Class**: Main ASGI application entry point (This is your base
Function)
- **MCPServer Class**: FastMCP-based server implementing HTTP-streamable MCP
protocol
- **MCP Tools**: Three primary tools for Ollama interaction:
  - `list_models`: Enumerate available models on the Ollama server
  - `pull_model`: Download and install new models
  - `call_model`: Send prompts to models and receive responses
  - `rag_document`: RAG a document - accepts urls or text (strings)


## Setup

### Prerequisites

- Python 3.9 or higher
- Ollama server running locally or accessible via network

### Local Development Setup

1. **Install dependencies & setup env**
    ```bash

    # optionally setup venv
    pythom -m venv venv
    source venv/bin/activate

    # and install deps
    pip install -e .
    ```

2. **Start Ollama server:**
    ```bash
    # Install Ollama (if not already installed)
    curl -fsSL https://ollama.com/install.sh | sh

    # Start Ollama service (in different terminal/ in bg)
    ollama serve

    # Pull a model (optional, can be done via MCP tool)
    ollama pull llama3.2:3b
    ```

Now you have a running Ollama Server

3. **Run the function:**
    ```bash
    # Using func CLI (build via host builder)
    func run --builder=host
    ```

Now you have a running MCP Server which has integration with ollama client tools
that will enable you to: embed some documents, pull a model available on the
ollama server and call the (now) specialized inference model with prompts.

4. **Run MCP client**
    ```bash
    # In client/ directory.
    # MODIFY THIS FILE
    # By default it RAGs a document and prompts asking about it
    python client.py
    ```

Now you've connected via MCP protocol to the running function, using an MCP client
which has embedded a document into vector space for RAG tooling and prompted the
model which can use the embeddings to answer your question (hopefuly) in a more
sophisticated manner.

### Deployment to cluster (not tested)

#### Knative Function Deployment

```bash
# Deploy to Knative cluster
func deploy

# Or build and deploy with custom image
func deploy --image your-registry/mcp-ollama-function
```

Here you would also need to ensure the access to the ollama server, using a pod
or portforwarding etc.

### Troubleshooting

**Connection Issues:**
- Ensure Ollama server is running and accessible
- Check firewall settings for port 11434 (Ollama default)
- Verify model availability with `ollama list`
- Confirm function is running on expected port (default: 8080)

