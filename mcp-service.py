import json
import asyncio
from typing import Dict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from mcp_client import MCPClient

def load_config(path:str):
    with open(path) as config_file:
        mcp_config = json.load(config_file)
        return mcp_config

mcp_config = load_config("./servers_config.json")

app = FastAPI()
mcp_client = MCPClient(mcp_config)

asyncio.create_task(mcp_client.start())


@app.get("/system_prompt")
async def get_system_prompt():
    # list all tools of each server
    mcp_tools = ""
    for server in mcp_client.list_servers():
        tools = f"Tools of MCP server '{server}':\n"
        for tool in await mcp_client.list_tools(server):
            tools += f"{tool}\n"
        mcp_tools += f"{tools}"

    system_prompt = (
        "You are a helpful assistant with access to MCP(Model Context Protocol) Servers."
        "MCP is a powerful protocol allows you to interact with other tools. MCP Servers provide different tools."
        "You can use the function execute_tool, with 'server name', 'tool name' and 'arguments', to access other tools."
        "Arguments must be a string in JSON format. After receiving a tool's response, transform the raw data into a natural, conversational response."
        f"Available MCP tools: {mcp_tools}"
    )
    return JSONResponse({"system_prompt": system_prompt})


@app.get("/tools/{server}")
async def get_tools(server: str):
    tools = await mcp_client.list_tools(server)
    tools = f"Tools of MCP server '{server}':\n"
    for tool in await mcp_client.list_tools(server):
        tools += f"{tool}\n"
    return JSONResponse({"tools": tools})


@app.post("/execute/{server}/{tool}")
async def execute_tool(server: str, tool: str, args: Dict):
    try:
        tool_result = await mcp_client.execute_tool(server, tool, args)
    except Exception as e:
        tool_result = f"Failed to execute the tool: {e}"
    return JSONResponse({"result": str(tool_result)})
