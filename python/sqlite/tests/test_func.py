"""Tests for the sqlite template.

Tests both the database layer and the HTTP handler.
Each test gets a fresh temporary database via the configured_function fixture.
"""

import json

import pytest

from function import new


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class ResponseCapture:
    def __init__(self):
        self.status = None
        self.body = b""

    async def __call__(self, message):
        if message["type"] == "http.response.start":
            self.status = message["status"]
        elif message["type"] == "http.response.body":
            self.body += message.get("body", b"")

    @property
    def json(self) -> dict:
        return json.loads(self.body)


def make_scope(path="/", method="GET", query_string=""):
    return {
        "method": method,
        "path": path,
        "headers": [],
        "query_string": query_string.encode(),
    }


async def call(f, path="/", method="GET", body=None, query_string=""):
    resp = ResponseCapture()
    body_bytes = json.dumps(body).encode() if body else b""
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"body": body_bytes, "more_body": False}
        return {"body": b"", "more_body": False}

    await f.handle(make_scope(path, method, query_string), receive, resp)
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def configured_function(tmp_path):
    """Create a Function with a temporary SQLite database."""
    f = new()
    f.start({"SQLITE_DB_PATH": str(tmp_path / "test.db")})
    yield f
    f.stop()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_root_info(configured_function):
    resp = await call(configured_function, "/")
    assert resp.status == 200
    assert resp.json["name"] == "sqlite"
    assert "tables" in resp.json


@pytest.mark.asyncio(loop_scope="function")
async def test_list_tables_empty(configured_function):
    resp = await call(configured_function, "/tables")
    assert resp.status == 200
    assert resp.json["tables"] == []


@pytest.mark.asyncio(loop_scope="function")
async def test_create_table(configured_function):
    resp = await call(configured_function, "/tables", method="POST", body={
        "table": "tasks",
        "columns": {"title": "TEXT", "done": "INTEGER"},
    })
    assert resp.status == 201
    assert "tasks" in resp.json["result"]

    resp = await call(configured_function, "/tables")
    assert "tasks" in resp.json["tables"]


@pytest.mark.asyncio(loop_scope="function")
async def test_create_table_invalid_type(configured_function):
    resp = await call(configured_function, "/tables", method="POST", body={
        "table": "bad",
        "columns": {"name": "VARCHAR(255)"},
    })
    assert resp.status == 400
    assert "Invalid column type" in resp.json["error"]


@pytest.mark.asyncio(loop_scope="function")
async def test_insert_and_query(configured_function):
    await call(configured_function, "/tables", method="POST", body={
        "table": "notes",
        "columns": {"text": "TEXT"},
    })

    resp = await call(configured_function, "/tables/notes", method="POST", body={"text": "hello"})
    assert resp.status == 201

    resp = await call(configured_function, "/tables/notes")
    assert resp.status == 200
    assert resp.json["count"] == 1
    assert resp.json["rows"][0]["text"] == "hello"


@pytest.mark.asyncio(loop_scope="function")
async def test_query_with_filter(configured_function):
    await call(configured_function, "/tables", method="POST", body={
        "table": "tasks",
        "columns": {"title": "TEXT", "done": "INTEGER"},
    })
    await call(configured_function, "/tables/tasks", method="POST", body={"title": "a", "done": 0})
    await call(configured_function, "/tables/tasks", method="POST", body={"title": "b", "done": 1})
    await call(configured_function, "/tables/tasks", method="POST", body={"title": "c", "done": 0})

    resp = await call(configured_function, "/tables/tasks", query_string="done=0")
    assert resp.json["count"] == 2


@pytest.mark.asyncio(loop_scope="function")
async def test_delete(configured_function):
    await call(configured_function, "/tables", method="POST", body={
        "table": "items",
        "columns": {"name": "TEXT"},
    })
    await call(configured_function, "/tables/items", method="POST", body={"name": "keep"})
    await call(configured_function, "/tables/items", method="POST", body={"name": "remove"})

    resp = await call(configured_function, "/tables/items", method="DELETE", query_string="name=remove")
    assert resp.status == 200
    assert "1 row" in resp.json["result"]

    resp = await call(configured_function, "/tables/items")
    assert resp.json["count"] == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_requires_filter(configured_function):
    resp = await call(configured_function, "/tables/items", method="DELETE")
    assert resp.status == 400


@pytest.mark.asyncio(loop_scope="function")
async def test_create_table_missing_fields(configured_function):
    resp = await call(configured_function, "/tables", method="POST", body={"table": "x"})
    assert resp.status == 400


@pytest.mark.asyncio(loop_scope="function")
async def test_query_bad_limit(configured_function):
    await call(configured_function, "/tables", method="POST", body={
        "table": "items",
        "columns": {"name": "TEXT"},
    })
    resp = await call(configured_function, "/tables/items", query_string="limit=abc")
    assert resp.status == 400


@pytest.mark.asyncio(loop_scope="function")
async def test_not_found(configured_function):
    resp = await call(configured_function, "/unknown")
    assert resp.status == 404


@pytest.mark.asyncio(loop_scope="function")
async def test_schema(configured_function):
    await call(configured_function, "/tables", method="POST", body={
        "table": "tasks",
        "columns": {"title": "TEXT", "done": "INTEGER"},
    })
    resp = await call(configured_function, "/tables/tasks/schema")
    assert resp.status == 200
    assert resp.json["table"] == "tasks"
    col_names = [c["name"] for c in resp.json["columns"]]
    assert "id" in col_names
    assert "title" in col_names
    assert "done" in col_names


@pytest.mark.asyncio(loop_scope="function")
async def test_not_ready_before_start():
    f = new()
    ok, msg = f.ready()
    assert not ok
    assert "not initialized" in msg.lower()
