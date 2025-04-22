import os
import asyncio
import shutil
from typing import Any, Annotated
from pydantic.networks import AnyUrl, UrlConstraints
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .logger import logger


class Tool:
    """Represents a tool with its properties and formatting."""

    def __init__(
        self, name: str, description: str, input_schema: dict[str, Any]
    ) -> None:
        self.name: str = name
        self.description: str = description
        self.input_schema: dict[str, Any] = input_schema

    def __str__(self) -> str:
        """
        Format tool information for LLM.

        Returns:
            A formatted string describing the tool.
        """
        args_desc = []
        if "properties" in self.input_schema:
            for param_name, param_info in self.input_schema["properties"].items():
                arg_desc = (
                    f"- {param_name}: {param_info.get('description', 'No description')}"
                )
                if param_name in self.input_schema.get("required", []):
                    arg_desc += " (required)"
                args_desc.append(arg_desc)

        return (
            f"Tool: {self.name}\n"
            + f"Description: {self.description}\n"
            + f"Arguments:\n"
            + f"{chr(10).join(args_desc)}\n"
        )


class Resource:
    """Represents a resource with its properties and formatting."""

    def __init__(
        self,
        uri: AnyUrl | str,
        name: str,
        description: str | None = None,
        mimeType: str | None = None,
        size: int | None = None,
    ) -> None:
        self.uri = AnyUrl(uri)
        self.name: str = name
        self.description: str = description
        self.mimeType = mimeType
        self.size = size

    def __str__(self):
        return (
            f"Resource: {self.name}\n"
            + f"URI: {str(self.uri)}\n"
            + f"Description: {self.description}\n"
            + f"MIME Type: {self.mimeType}\n"
            + f"Size: {self.size}\n"
        )


class ServerConnection:
    """Manages MCP server connections and tool execution."""

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config: dict[str, Any] = config
        self.stdio_context: Any | None = None
        self.session: ClientSession | None = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack: AsyncExitStack = AsyncExitStack()

    async def initialize(self) -> None:
        """Initialize the server connection."""
        command = (
            shutil.which("npx")
            if self.config["command"] == "npx"
            else self.config["command"]
        )
        if command is None:
            raise ValueError("The command must be a valid string and cannot be None.")

        server_params = StdioServerParameters(
            command=command,
            args=self.config["args"],
            env=(
                {**os.environ, **self.config["env"]} if self.config.get("env") else None
            ),
        )
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.session = session
        except Exception as e:
            logger.error(f"Error initializing server {self.name}: {e}")
            await self.cleanup()
            raise

    async def list_tool(self):
        """List available tools from the server."""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        tools = []
        tools_response = await self.session.list_tools()
        for item in tools_response:
            if isinstance(item, tuple) and item[0] == "tools":
                for tool in item[1]:
                    tools.append(Tool(tool.name, tool.description, tool.inputSchema))
        return tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        retries: int = 2,
        delay: float = 1.0,
    ) -> Any:
        """Execute a tool with retry mechanism."""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        attempt = 0
        while attempt < retries:
            try:
                logger.info(f"Executing {tool_name}...")
                result = await self.session.call_tool(tool_name, arguments)
                return result

            except Exception as e:
                attempt += 1
                logger.warning(
                    f"Error executing tool: {e}. Attempt {attempt} of {retries}."
                )
                if attempt < retries:
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries reached. Failing.")
                    raise

    async def list_resources(self):
        """List available resources from the server."""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        resources = []
        resources_response = await self.session.list_resources()
        for item in resources_response:
            if isinstance(item, tuple) and item[0] == "resources":
                for resource in item[1]:
                    resources.append(
                        Resource(
                            resource.uri,
                            resource.name,
                            resource.description,
                            resource.mimeType,
                            resource.size,
                        )
                    )
        return resources

    async def read_resource(self, uri: AnyUrl | str):
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")
        uri = AnyUrl(uri)
        res = await self.session.read_resource(uri)
        return res

    async def cleanup(self) -> None:
        """Clean up server resources."""
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
                self.session = None
                self.stdio_context = None
            except Exception as e:
                logger.error(f"Error during cleanup of server {self.name}: {e}")
