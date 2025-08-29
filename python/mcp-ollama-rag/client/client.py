import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import json

from mcp.types import CallToolResult

def unload_list_models(models: CallToolResult) -> list[str]:
    return [json.loads(item.text)["model"] for item in models.content if item.text.strip().startswith('{')] #pyright: ignore

async def main():
    # check your running Function MCP Server, it will output where its available
    # at during initialization.
    async with streamablehttp_client("http://localhost:8080/mcp") as streams:
        read_stream,write_stream = streams[0],streams[1]

        async with ClientSession(read_stream,write_stream) as sess:
            print("Initializing connection...",end="")
            await sess.initialize()
            print("done!\n")


            # embed some documents
            embed = await sess.call_tool(
                name="embed_document",
                arguments={
                    "data": [
                        "https://raw.githubusercontent.com/knative/func/main/docs/function-templates/python.md",
                        "https://context7.com/knative/docs/llms.txt?topic=functions",
                        ],
                    }
                )
            print(embed.content[0].text) # pyright: ignore[reportAttributeAccessIssue]
            print("-"*60)

            # prompt the inference model
            resp = await sess.call_tool(
                name="call_model",
                arguments={
                    "prompt": "What actually is a Knative Function?",
                }
            )
            print(resp.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
