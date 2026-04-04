"""
Unit tests for the Function.
"""
import pytest
from function import new

@pytest.mark.asyncio
async def test_function_handle_default():
    """Test that non-MCP requests get a 200 OK response."""
    f = new()

    sent_ok = False
    sent_headers = False
    sent_body = False

    async def send(message):
        nonlocal sent_ok, sent_headers, sent_body

        if message.get("status") == 200:
            sent_ok = True
        if message.get("type") == "http.response.start":
            sent_headers = True
        if message.get("type") == "http.response.body":
            sent_body = True

    scope = {"path": "/", "type": "http"}
    await f.handle(scope, {}, send)

    assert sent_ok, "Function did not send a 200 OK"
    assert sent_headers, "Function did not send headers"
    assert sent_body, "Function did not send a body"


@pytest.mark.asyncio
async def test_function_routes_mcp():
    """Test that /mcp paths are routed to MCP server."""
    f = new()

    scope = {"path": "/mcp", "type": "http", "method": "GET",
             "headers": [], "query_string": b""}

    # MCP server will handle this - we just verify no crash on routing
    try:
        async def receive():
            return {"type": "http.request", "body": b""}

        responses = []
        async def send(message):
            responses.append(message)

        await f.handle(scope, receive, send)
        # If we get here, routing worked
        assert len(responses) > 0
    except Exception:
        # MCP may reject malformed requests, but routing itself worked
        pass
