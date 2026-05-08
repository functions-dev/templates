"""HTTP function with SQLite persistence.

A Knative Function that provides a REST API backed by a SQLite database.
Shows how to use persistent storage in a serverless function.

Endpoints:
    GET  /                          -> function info + list of tables
    GET  /tables                    -> list all tables
    POST /tables                    -> create a table
    GET  /tables/<name>             -> query rows (filter via query params)
    POST /tables/<name>             -> insert a row
    DELETE /tables/<name>           -> delete rows (filter via query params)
    GET  /tables/<name>/schema      -> column info for a table

Configuration (environment variables):
    SQLITE_DB_PATH -> path to SQLite database file (default: data.db)
"""

import json
import logging
from urllib.parse import unquote

from .database import Database


def new():
    """Entry point -- called once by the Knative Functions runtime."""
    return Function()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def send_json(send, body, status: int = 200) -> None:
    payload = json.dumps(body).encode()
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [[b"content-type", b"application/json"]],
    })
    await send({
        "type": "http.response.body",
        "body": payload,
    })


async def read_body(receive) -> bytes:
    body = b""
    while True:
        message = await receive()
        body += message.get("body", b"")
        if not message.get("more_body", False):
            break
    return body


def parse_path(path: str) -> tuple[str, str, str]:
    """Parse /tables/name/schema into ("tables", "name", "schema")."""
    parts = [p for p in path.strip("/").split("/") if p]
    while len(parts) < 3:
        parts.append("")
    return (parts[0], parts[1], parts[2])


# ---------------------------------------------------------------------------
# The Function
# ---------------------------------------------------------------------------

class Function:
    def __init__(self):
        self.db = None

    async def handle(self, scope, receive, send) -> None:
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        query_string = unquote(scope.get("query_string", b"").decode())
        resource, name, sub = parse_path(path)

        # GET / -> function info
        if path == "/" and method == "GET":
            return await send_json(send, {
                "name": "sqlite",
                "description": "HTTP function with SQLite database",
                "database": self.db.db_path,
                "tables": self.db.list_tables(),
                "endpoints": {
                    "GET /tables": "List all tables",
                    "POST /tables": "Create a table",
                    "GET /tables/<name>": "Query rows (?col=val to filter, ?limit=N)",
                    "POST /tables/<name>": "Insert a row",
                    "DELETE /tables/<name>": "Delete rows (?col=val to filter)",
                    "GET /tables/<name>/schema": "Column info for a table",
                },
            })

        if resource != "tables":
            return await send_json(send, {"error": "Not found"}, status=404)

        # GET /tables -> list tables
        if not name and method == "GET":
            return await send_json(send, {"tables": self.db.list_tables()})

        # POST /tables -> create table
        # Body: {"table": "tasks", "columns": {"title": "TEXT", "done": "INTEGER"}}
        if not name and method == "POST":
            raw = await read_body(receive)
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return await send_json(send, {"error": "Invalid JSON body"}, status=400)
            table = body.get("table", "")
            columns = body.get("columns", {})
            if not table or not columns:
                return await send_json(send, {
                    "error": "Required: {\"table\": \"name\", \"columns\": {\"col\": \"TYPE\"}}"
                }, status=400)
            try:
                result = self.db.create_table(table, columns)
                return await send_json(send, {"result": result}, status=201)
            except Exception as e:
                return await send_json(send, {"error": str(e)}, status=400)

        # GET /tables/<name>/schema -> column info
        if name and sub == "schema" and method == "GET":
            columns = self.db.describe_table(name)
            return await send_json(send, {"table": name, "columns": columns})

        if sub:
            return await send_json(send, {"error": "Not found"}, status=404)

        # GET /tables/<name> -> query rows
        # Filter via query params: ?done=0&priority=high (equality filters)
        # Special param: ?limit=N (default 100)
        if name and method == "GET":
            params = dict(p.split("=", 1) for p in query_string.split("&") if "=" in p)
            try:
                limit = int(params.pop("limit", "100"))
            except ValueError:
                return await send_json(send, {"error": "limit must be an integer"}, status=400)
            try:
                rows = self.db.query(name, filters=params or None, limit=limit)
                return await send_json(send, {
                    "table": name,
                    "count": len(rows),
                    "rows": rows,
                })
            except Exception as e:
                return await send_json(send, {"error": str(e)}, status=400)

        # POST /tables/<name> -> insert row
        # Body: {"title": "Fix bug", "done": 0}
        if name and method == "POST":
            raw = await read_body(receive)
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return await send_json(send, {"error": "Invalid JSON body"}, status=400)
            try:
                result = self.db.insert(name, body)
                return await send_json(send, {"result": result}, status=201)
            except Exception as e:
                return await send_json(send, {"error": str(e)}, status=400)

        # DELETE /tables/<name>?id=5 -> delete rows
        # Filter via query params (at least one required)
        if name and method == "DELETE":
            params = dict(p.split("=", 1) for p in query_string.split("&") if "=" in p)
            if not params:
                return await send_json(send, {
                    "error": "Required: filter params (e.g. ?id=5)"
                }, status=400)
            try:
                result = self.db.delete(name, params)
                return await send_json(send, {"result": result})
            except Exception as e:
                return await send_json(send, {"error": str(e)}, status=400)

        return await send_json(send, {"error": "Method not allowed"}, status=405)

    def start(self, cfg) -> None:
        db_path = cfg.get("SQLITE_DB_PATH", "data.db")
        self.db = Database(db_path)
        logging.info("SQLite function ready: database=%s", db_path)

    def stop(self) -> None:
        if self.db:
            self.db.close()
        logging.info("Function stopping")

    def alive(self) -> tuple:
        return True, "Alive"

    def ready(self) -> tuple:
        if self.db is None:
            return False, "Database not initialized"
        return True, "Ready"
