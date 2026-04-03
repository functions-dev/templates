# pyright: reportUnknownMemberType=false
"""
E2E test for the mcp-ollama-rag template.

Connects to the running MCP server, exercises all tools, and validates responses.

Usage: python test_mcp_client.py <mcp-url>
       python test_mcp_client.py http://localhost:8080/mcp
"""
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, TextContent


def get_text(result: CallToolResult) -> str:
    """Extract text from the first content item of a tool result."""
    item = result.content[0]
    assert isinstance(item, TextContent), f"Expected TextContent, got {type(item)}"
    return item.text


async def run_tests(url: str):
    errors = []

    async with streamable_http_client(url) as streams:
        read_stream, write_stream = streams[0], streams[1]

        async with ClientSession(read_stream, write_stream) as sess:
            _ = await sess.initialize()

            # ── Test 1: list_models ──────────────────────────
            print("  [test] list_models...", end="", flush=True)
            result = await sess.call_tool(name="list_models", arguments={})
            if result.isError:
                errors.append(f"list_models returned error: {result.content}")
                print(" FAIL")
            else:
                print(result)
                print(" OK")

            # ── Test 2: embed_document ───────────────────────
            print("  [test] embed_document...", end="", flush=True)
            result = await sess.call_tool(
                name="embed_document",
                arguments={
                    "data": [
                        "https://raw.githubusercontent.com/knative/func/main/docs/function-templates/python.md",
                    ],
                },
            )
            if result.isError:
                errors.append(f"embed_document returned error: {result.content}")
                print(" FAIL")
            else:
                text = get_text(result)
                if "ok - Embedded" not in text:
                    errors.append(f"embed_document unexpected response: {text}")
                    print(f" FAIL ({text})")
                else:
                    print(f" OK ({text})")

            # ── Test 3: call_model (RAG query) ───────────────
            print("  [test] call_model...", end="", flush=True)
            result = await sess.call_tool(
                name="call_model",
                arguments={"prompt": "What is a Knative Function?"},
            )
            if result.isError:
                errors.append(f"call_model returned error: {result.content}")
                print(" FAIL")
            else:
                text = get_text(result)
                if len(text) < 50:
                    errors.append(f"call_model response too short: {text}")
                    print(f" FAIL (response too short: {len(text)} chars)")
                else:
                    print(f" OK ({len(text)} chars)")

    return errors


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <mcp-url>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"  Connecting to {url}")

    errors = asyncio.run(run_tests(url))

    if errors:
        print(f"\n  FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
