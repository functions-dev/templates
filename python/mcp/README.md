# Python MCP Function (HTTP)

Welcome to your new Python Function! This Function is an MCP server that
handles any HTTP requests with MCP requests at `/mcp`. The MCP is implemented
using [Python-SDK](https://github.com/modelcontextprotocol/python-sdk) library.

## Function

The main code lives in `function/func.py`.
The Function itself is ASGI compatible, implementing `handle(scope,receive,send)`
which is the entry for your function and all requests are handled here.

You can also use `start` and `stop` methods which are implemented and you can
see them in the bottom of the `function/func.py` file.

## Project Structure

```
├── function/
│   ├── __init__.py
│   └── func.py          # Main function code
├── client/
│   └── client.py        # Example MCP client
├── tests/
│   └── test_func.py     # simple HTTP test
└── pyproject.toml       # Project configuration
```

## MCP Server

The MCP server is implemented via a `MCPServer` class.
- Uses `FastMCP()` function from the Python SDK lib mentioned above
- Uses `streamable_http_app` transport which is a lower level function in the
Python-SDK library that is plugged in directly.
- Integrates with the Functions middleware without running its own server
- Routes all incoming MCP requests to the MCP handler

## MCP Client

Since we are using the Python-SDK library, in order to communicate easily
with the server we can use the Python-SDK Clients. You can refer to their
[client docs](https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#writing-mcp-clients)
for more information.

You can find an example implementation of a client in your function's `client/` directory.
Refer to [Testing section](#testing) for how to run clients.

## Deployment

Before running your Function, it is recommended to create a virtual environment
to isolate the project for easier dependency management.

Subsequently install necessary dependencies and you're all set up.

```bash
# Create the virtual env
python3 -m venv venv

# Optional: Activate the venv
source venv/bin/activate

# Install dependencies
pip install -e .
```

## Testing

Tests can be found in `tests/` directory with a simple test for HTTP requests
in `test_func.py`. To run tests:

```bash
# Install dependencies (if not already installed)
pip install -e .

# Run tests
pytest

# Run tests with verbose output
pytest -v
```

For testing the MCP functionality, you can use the included client at `client/client.py`:

```bash
# run your mcp server locally
func run --builder=host

# in different terminal: run mcp client
python client/client.py
```

## Contact and Docs

Please share your functions or ask us questions in our CNCF Slack
[Functions channel](https://cloud-native.slack.com/archives/C04LKEZUXEE)!

For more info about the Python Functions implementation itself, please visit
[python template docs](https://github.com/knative/func/blob/main/docs/function-templates/python.md)
and
[python default http template](https://github.com/knative/func/tree/main/templates/python/http)

For even more, see [the complete documentation](https://github.com/knative/func/tree/main/docs)
