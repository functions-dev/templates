"""SQLite database wrapper.

Provides a class for creating tables, inserting rows, querying data,
and inspecting schema. All operations go through a single SQLite file
on disk so data persists across restarts.
"""

import pysqlite3 as sqlite3

ALLOWED_TYPES = {"TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"}


def _quote_id(identifier: str) -> str:
    """Quote a SQL identifier to prevent injection."""
    return f'"{identifier.replace(chr(34), "")}"'


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def list_tables(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master"
            " WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            " ORDER BY name"
        ).fetchall()
        return [row["name"] for row in rows]

    def describe_table(self, table: str) -> list[dict]:
        rows = self.conn.execute(
            f"PRAGMA table_info({_quote_id(table)})"
        ).fetchall()
        return [
            {"name": r["name"], "type": r["type"], "notnull": bool(r["notnull"])}
            for r in rows
        ]

    def create_table(self, table: str, columns: dict[str, str]) -> str:
        for col_name, col_type in columns.items():
            if col_type.upper() not in ALLOWED_TYPES:
                raise ValueError(
                    f"Invalid column type '{col_type}' for '{col_name}'. "
                    f"Allowed: {', '.join(sorted(ALLOWED_TYPES))}"
                )
        cols = ", ".join(f"{_quote_id(k)} {v}" for k, v in columns.items())
        sql = f"CREATE TABLE IF NOT EXISTS {_quote_id(table)} (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})"
        self.conn.execute(sql)
        self.conn.commit()
        return f"Table '{table}' created with columns: {', '.join(columns.keys())}"

    def insert(self, table: str, data: dict) -> str:
        keys = list(data.keys())
        placeholders = ", ".join("?" for _ in keys)
        cols = ", ".join(_quote_id(k) for k in keys)
        sql = f"INSERT INTO {_quote_id(table)} ({cols}) VALUES ({placeholders})"
        cursor = self.conn.execute(sql, list(data.values()))
        self.conn.commit()
        return f"Inserted row {cursor.lastrowid} into '{table}'"

    def query(self, table: str, filters: dict | None = None, limit: int = 100) -> list[dict]:
        sql = f"SELECT * FROM {_quote_id(table)}"
        params: list = []
        if filters:
            clauses = [f"{_quote_id(k)} = ?" for k in filters]
            sql += " WHERE " + " AND ".join(clauses)
            params = list(filters.values())
        sql += " LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def delete(self, table: str, filters: dict[str, str]) -> str:
        if not filters:
            return "Error: at least one filter is required for delete"
        clauses = [f"{_quote_id(k)} = ?" for k in filters]
        sql = f"DELETE FROM {_quote_id(table)} WHERE " + " AND ".join(clauses)
        cursor = self.conn.execute(sql, list(filters.values()))
        self.conn.commit()
        return f"Deleted {cursor.rowcount} row(s) from '{table}'"
