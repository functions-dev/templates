# Ollama-MCP Function

A Knative Function implementing a Model Context Protocol (MCP) server that
provides integration with Ollama for local LLM interactions. This function
exposes Ollama capabilities through standardized MCP tools, enabling the
interaction with locally hosted language models.

The communication flow is as follows:
`MCP client -> MCP Server (Function) -> Ollama Server`

1) Setup `ollama` server using `ollama serve`
2) Run your function (MCP server)
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

## Setup

### Prerequisites

- Python 3.9 or higher
- Ollama server running locally or accessible via network

### Local Development Setup

1. **Install dependencies & setup env**
    ```bash
    # (optional)
    # setup venv
    python -m venv venv
    # and run it
    source venv/bin/activate

    # install deps
    pip install -e .
    ```

2. **Start Ollama server:**
    ```bash
    # Install Ollama (if not already installed)
    curl -fsSL https://ollama.com/install.sh | sh

    # Start Ollama service (in bg or different terminal)
    ollama serve

    # Pull a model (optional, can be done via MCP tool)
    ollama pull llama3.2:3b
    ```

Now you have a running Ollama Server.

3. **Run the function locally:**
    ```bash
    # Using func CLI
    func run --builder=host
    ```

Now you have a running MCP Server which has access to the Ollama server.

4. **Run MCP client**
    ```bash
    # In client/ directory
    python client.py
    ```

Now you connect via MCP protocol to the running function, which will call a tool
`call_model` which will invoke a request from the LLM running on Ollama server.

Edit the `client/client.py` file to change any requests for the MCP server.
Edit the `function/func.py` file to edit the MCP server and its tools etc.

### Deployment to cluster (not tested)

#### Knative Function Deployment

```bash
# Deploy to cluster with Knative
func deploy

# Or build and deploy with custom image
func deploy --image your-registry/mcp-ollama-function
```

### Troubleshooting

**Connection Issues:**
- Ensure Ollama server is running and accessible
- Check firewall settings for port 11434 (Ollama default)
- Verify model availability with `ollama list`
- Confirm function is running on expected port (default: 8080)

**Performance Considerations:**
- Model loading time varies by size (3B models ~2-5s, 7B+ models 10-30s)
- Consider pre-loading frequently used models
- Monitor memory usage for large models

### Dependencies

- **mcp**: Model Context Protocol implementation
- **ollama**: Python client for Ollama API
- **httpx**: Async HTTP client for external requests
- **pytest/pytest-asyncio**: Testing framework with async support

