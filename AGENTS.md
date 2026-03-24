# Function Templates — Agent Guide

## What Is This Repo?

Templates for [Knative Functions](https://github.com/knative/func). Users create
functions via `func create -r <this-repo> -l <language> -t <template>`.

```bash
# Example: create a Go function from the "hello" template
func create myfunc -r https://github.com/functions-dev/templates -l go -t hello
```

All files in a template directory are copied to the user's project (except `manifest.yaml`
which holds some metadata that the function will need and hidden files).

## Using Templates (This repository)

Templates are organized as `<language>/<template>/`. The `-l` flag matches the language
directory, the `-t` flag matches the template subdirectory:

```
go/hello/               →  func create -l go -t hello
python/echo/            →  func create -l python -t echo
rust/echo-cloudevents/  →  func create -l rust -t echo-cloudevents
```

### Template Index

Available in all languages (go, node, python, quarkus, rust, springboot, typescript):

| Template | Description |
|---|---|
| `hello` | Returns `{"message":"Hello <Language> World!"}`. Simplest starting point. |
| `echo` | Echoes back the request. GET returns query string, POST returns body. |
| `echo-cloudevents` | Receives a CloudEvent, echoes the data back as a new CloudEvent. |

Go-specific:

| Template | Description |
|---|---|
| `go/blog` | Hugo-powered blog served as static files. Requires `make` to build before use. |
| `go/splash` | Static splash page serving HTML, CSS, and PNG files. |

Python-specific:

| Template | Description |
|---|---|
| `python/pdf-processing` | PDF operations (extract text, metadata, split, merge) via HTTP. |
| `python/mcp` | MCP server exposing basic tools (hello, add_numbers) via Model Context Protocol. |
| `python/mcp-ollama` | Exposes Ollama LLM as MCP tools (list/pull/call models). Needs Ollama. |
| `python/mcp-ollama-rag` | RAG via MCP — combines Ollama with Chroma vector DB for document Q&A. Needs Ollama. |
| `python/ollama-client` | HTTP wrapper that forwards prompts to a local Ollama server. Needs Ollama. |
| `python/llamacpp` | Loads a Granite code model via llama.cpp for local text generation. |

For contributing to this repo, see [CONTRIBUTING.md](CONTRIBUTING.md).
