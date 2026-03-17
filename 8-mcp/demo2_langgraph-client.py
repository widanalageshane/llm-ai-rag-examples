from typing import TypedDict, Annotated,  Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools


#llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash-lite')

class State(TypedDict):
    messages: Annotated[list, add_messages]

# MCP Server definition
mcp_server = StdioServerParameters(    
        command="python",
        args=["demo1_calculator.py"]
)

async def main():

    async with stdio_client(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            print("Initializing MCP Client...")
            await session.initialize()
            print("MCP Client initialized and connected to server.")
            tools = await load_mcp_tools(session)
            print(f"Loaded tools from MCP Server: {tools}")

            #llm_with_tools = llm.bind_tools(tools)


asyncio.run(main())


    