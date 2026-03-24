"""
Unit tests for the echo function. Verifies that GET echoes the query string
and POST echoes the request body.
"""
import pytest
from function import new

@pytest.mark.asyncio
async def test_get_echoes_query_string():
    f = new()

    sent_body = None

    async def send(message):
        nonlocal sent_body
        # capture the body (second send() call)
        if message.get('type') == 'http.response.body':
            sent_body = message.get('body')

    scope = {'method': 'GET', 'query_string': b'message=hello'}
    await f.handle(scope, None, send)

    assert sent_body == b'message=hello', f"Unexpected body: {sent_body}"


@pytest.mark.asyncio
async def test_post_echoes_request_body():
    f = new()

    sent_body = None

    async def send(message):
        nonlocal sent_body
        # capture the body (second send() call)
        if message.get('type') == 'http.response.body':
            sent_body = message.get('body')

    request_body = b'{"message":"Hello World"}'

    async def receive():
        return {'body': request_body, 'more_body': False}

    scope = {'method': 'POST'}
    await f.handle(scope, receive, send)

    assert sent_body == request_body, f"Unexpected body: {sent_body}"


@pytest.mark.asyncio
async def test_get_empty_query_string():
    f = new()

    sent_body = None

    async def send(message):
        nonlocal sent_body
        # capture the body (second send() call)
        if message.get('type') == 'http.response.body':
            sent_body = message.get('body')

    scope = {'method': 'GET'}
    await f.handle(scope, None, send)

    assert sent_body == b'', f"Unexpected body: {sent_body}"
