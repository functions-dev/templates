# Python HTTP Function — PDF Processing

A serverless function for processing PDF files. Upload a PDF and select an
operation via the `?op=` query parameter.

## Operations

| Operation | Description | Response |
|---|---|---|
| `extract-text` | Extract all text from PDF | JSON `{"text": "..."}` |
| `metadata` | Get page count, title, author, creator | JSON |
| `split` | Split into individual pages | ZIP of PDFs |
| `merge` | Combine multiple PDFs into one | PDF (send a ZIP of PDFs) |

## Usage

```console
# Extract text
curl -X POST --data-binary @doc.pdf "http://myfunction.example.com/?op=extract-text"

# Get metadata
curl -X POST --data-binary @doc.pdf "http://myfunction.example.com/?op=metadata"

# Split into pages
curl -X POST --data-binary @doc.pdf -o pages.zip "http://myfunction.example.com/?op=split"

# Merge (send a zip containing multiple PDFs)
curl -X POST --data-binary @bundle.zip -o merged.pdf "http://myfunction.example.com/?op=merge"
```

## Development

```console
pip install -e .
pytest tests/
```

For more, see [the complete documentation](https://github.com/knative/func/tree/main/docs)
