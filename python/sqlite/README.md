# Python HTTP Function - SQLite Database

A Knative Function with a REST API backed by a SQLite database. Shows how
to use persistent storage in a serverless function — no external database
server needed.

## Quick Start

### 1. Create the function

```bash
func create myfunc \
  -r https://github.com/functions-dev/templates \
  -l python -t sqlite
cd myfunc
```

### 2. Run the function

```bash
func run --builder=host
```

### 3. Try it

```bash
# Function info
curl -s http://localhost:8080/ | jq .

# Create a table
curl -s -X POST http://localhost:8080/tables \
  -H "Content-Type: application/json" \
  -d '{"table": "tasks", "columns": {"title": "TEXT", "status": "TEXT", "priority": "TEXT"}}' | jq .

# Insert rows
curl -s -X POST http://localhost:8080/tables/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Fix login bug", "status": "open", "priority": "high"}' | jq .

curl -s -X POST http://localhost:8080/tables/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Update docs", "status": "open", "priority": "low"}' | jq .

# Query all rows
curl -s http://localhost:8080/tables/tasks | jq .

# Filter rows
curl -s 'http://localhost:8080/tables/tasks?priority=high' | jq .

# Delete a row
curl -s -X DELETE 'http://localhost:8080/tables/tasks?id=2' | jq .

# List all tables
curl -s http://localhost:8080/tables | jq .

# Table schema
curl -s http://localhost:8080/tables/tasks/schema | jq .
```

## Configuration

| Variable | Required | Description | Default |
|---|---|---|---|
| `SQLITE_DB_PATH` | No | Path to the SQLite database file | `data.db` |

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Function info and list of tables |
| GET | `/tables` | List all tables |
| POST | `/tables` | Create a table |
| GET | `/tables/<name>` | Query rows (`?col=val` to filter, `?limit=N`) |
| POST | `/tables/<name>` | Insert a row |
| DELETE | `/tables/<name>` | Delete rows (`?col=val` to filter, at least one required) |
| GET | `/tables/<name>/schema` | Column info for a table |

## Deploying to a Cluster

SQLite stores data inside the container — it's lost on restart unless you
mount a persistent volume.

Add to `func.yaml`:

```yaml
run:
  envs:
  - name: SQLITE_DB_PATH
    value: /data/data.db
  volumes:
  - persistentVolumeClaim:
      claimName: sqlite-data
    path: /data
```

## Development

```bash
pip install -e '.[dev]'
pytest tests/
```

For more, see [the complete documentation](https://github.com/knative/func/tree/main/docs)
