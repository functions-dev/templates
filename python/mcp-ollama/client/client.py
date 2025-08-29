import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import pprint
import json

from mcp.types import CallToolResult

def unload_list_models(models: CallToolResult) -> list[str]:
    return [json.loads(item.text)["model"] for item in models.content if item.text.strip().startswith('{')]

async def main():
    # check your running Function MCP Server, it will output where its available
    # at during initialization.
    async with streamablehttp_client("http://localhost:8080/mcp") as streams:
        read_stream,write_stream = streams[0],streams[1]

        async with ClientSession(read_stream,write_stream) as sess:
            print("Initializing connection...",end="")
            await sess.initialize()
            print("done!\n")

            ### List all available tools
            #tools = await sess.list_tools()

            # List all available models
            #models = await sess.call_tool(
            #    name="list_models",
            #    )
            # extract model names from the response
            #models = unload_list_models(models)
            #print(f"list of models currently available: {models}")

            # create a request for the model
            response = await sess.call_tool(
                name="call_model",
                arguments={
                    "prompt":"How to properly tie a tie?",
                    "model":"llama3.2:3b",
                    }
                )
            print(response.content)

if __name__ == "__main__":
    asyncio.run(main())
