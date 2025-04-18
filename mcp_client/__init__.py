import json
from typing import Any

from .utils import ServerConnection, Tool
from .logger import logger


def load_json(path):
    with open(path) as f:
        return json.load(f)


class MCPClient:
    def __init__(self, config_path: str):
        self.config = load_json(config_path)
        self.servers: dict[str, ServerConnection] = dict()

        for name, srv_config in self.config["mcpServers"].items():
            self.servers[name] = ServerConnection(name, srv_config)

    async def start(self):
        for server in self.servers.values():
            await server.initialize()

    def list_servers(self) -> list[str]:
        return list(self.servers.keys())

    async def list_tools(self, server_name: str) -> list[Tool]:
        logger.info(f"List tools of MCP server '{server_name}'.")
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
        result = await self.servers[server_name].execute_tool(
            tool_name, arguments, retries, delay
        )
        return result

    async def clean_all(self):
        for server in self.servers.values():
            await server.cleanup()
