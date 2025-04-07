import os
import json
import asyncio
from typing import Any

from .utils import ServerConnection
from ..logger import logger


CONFIG_PATH = os.path.dirname(__file__) + "/../../servers_config.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


class Client:
    def __init__(self):
        self.config = load_json(CONFIG_PATH)
        self.servers: dict[str, ServerConnection] = dict()

        for name, srv_config in self.config["mcpServers"].items():
            self.servers[name] = ServerConnection(name, srv_config)
        asyncio.create_task(self.start())

    def list_servers(self):
        return list(self.servers.keys())

    async def start(self):
        for server in self.servers.values():
            await server.initialize()

    async def list_tools(self, server_name):
        logger.info(f"MCP Client list tools of {server_name} MCP server")
        tool_list = await self.servers[server_name].list_tool()
        return tool_list

    async def execute_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
        retries: int = 2,
        delay: float = 1.0,
    ):
        logger.info(
            f"MCP Client execute {tool_name} of {server_name} MCP server with args {str(arguments)}"
        )
        result = await self.servers[server_name].execute_tool(
            tool_name, arguments, retries, delay
        )
        logger.info(f"Result: {str(result)}")
        return result

    async def clean_all(self):
        for server in self.servers.values():
            await server.cleanup()
