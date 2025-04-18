import json
import asyncio

from openai import OpenAI

from .logger import logger
from . import MCPClient


class OpenAIChat:
    """
    A client for interacting with an LLM via the OpenAI API (OpenRouter).

    Manages a chat session and provides a send_message method.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        mcp_config_path: str,
        base_url: str = "https://openrouter.ai/api/v1",
        site_url=None,
        site_name=None,
    ):
        """
        Initializes the LLMClient.

        Args:
            api_key (str): The API key for OpenRouter.
            model (str): The LLM model to use.
            mcp_config_path (str): The path to the MCP config file (servers_config.json).
            base_url (str, optional): The base URL of the OpenRouter API. Defaults to "https://openrouter.ai/api/v1".
            site_url (str, optional): Your site URL for rankings on OpenRouter.ai. Defaults to None.
            site_name (str, optional): Your site title for rankings on OpenRouter.ai. Defaults to None.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.site_url = site_url
        self.site_name = site_name
        self.model = model
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

        self.system_prompt = (
            "You are a helpful assistant with access to MCP(Model Context Protocol) Servers."
            "MCP is a powerful protocol allows you to interact with other tools. MCP Servers provide different tools."
            "You can use the function execute_tool, with 'server name', 'tool name' and 'arguments', to access other tools."
            "After receiving a tool's response, transform the raw data into a natural, conversational response."
        )
        self.conversation_history = []

        self.mcp_client = MCPClient(mcp_config_path)
        self.mcp_functions = [
            {
                "type": "function",
                "function": {
                    "name": "execute_tool",
                    "description": "Execute a tool of a MCP server",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "server_name": {
                                "type": "string",
                                "description": "The name of MCP Server.",
                            },
                            "tool_name": {
                                "type": "string",
                                "description": "The name of the tool to call.",
                            },
                            "args": {
                                "type": "string",
                                "description": "The arguments of the tool in JSON string format.",
                            },
                        },
                        "required": ["server_name"],
                    },
                },
            },
        ]

        self.function_mapping = {
            "execute_tool": self.execute_tool,
        }

    async def start(self) -> None:
        """Initialize all MCP Server connections"""
        await self.mcp_client.start()

        # list all servers
        mcp_servers = self.mcp_client.list_servers()

        # list all tools of each server
        mcp_tools = ""
        for server in self.mcp_client.list_servers():
            tools = f"Tools of {server}:\n"
            for tool in await self.mcp_client.list_tools(server):
                tools += f"{tool}\n"
            mcp_tools += f"{tools}"

        self.conversation_history.append(
            {
                "role": "system",
                "content": f"{self.system_prompt}\nAvailable MCP servers: {str(mcp_servers)}\n{mcp_tools}",
            }
        )

    async def list_tools(self, server_name: str) -> str:
        tools = await self.mcp_client.list_tools(server_name)
        result = ""
        for tool in tools:
            result += f"\n{str(tool)}"
        return result

    async def execute_tool(self, server_name: str, tool_name: str, args: str) -> str:
        args = json.loads(args)
        result = await self.mcp_client.execute_tool(server_name, tool_name, args)
        return str(result)

    def _build_extra_headers(self):
        """Builds the extra headers for the API request."""
        extra_headers = {}
        if self.site_url is not None:
            extra_headers["HTTP-Referer"] = self.site_url
        if self.site_name is not None:
            extra_headers["X-Title"] = self.site_name
        return extra_headers

    async def send_message(self, content: str) -> str:
        """
        Sends a message to the LLM and returns the response.

        Args:
            content (str): The text content of the message.

        Returns:
            str: The response from the LLM.  Returns None if there's an error.
        """

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": content})

        try:
            completion_kwargs = {
                "extra_headers": self._build_extra_headers(),
                "extra_body": {},
                "model": self.model,
                "messages": self.conversation_history,
                "tools": self.mcp_functions,
                "tool_choice": "auto",
            }

            # send to model
            completion = self.client.chat.completions.create(**completion_kwargs)
            response_message = completion.choices[0].message

            if response_message.tool_calls is None:
                # no tool call, return model's message
                response_content = response_message.content

                # append model message to history
                self.conversation_history.append(response_message)
                return response_content
            else:
                tool_responses = []

                for tool_call in response_message.tool_calls:
                    # extract function name and args from model response
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    # try to call tool
                    function_to_call = self.function_mapping.get(function_name)
                    if function_to_call is None:
                        function_result = f"Error: Function {function_name} not found."
                    else:
                        logger.info(
                            f"Call function '{function_name}' with args {function_args}"
                        )
                        try:
                            function_result = await function_to_call(**function_args)
                            function_result = str(function_result)
                        except Exception as e:
                            function_result = (
                                f"Error calling function {function_name}: {e}"
                            )
                            logger.error(function_result)

                    # generate tool message
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": function_result,
                    }
                    tool_responses.append(tool_message)

                # append model and tool messages to history
                self.conversation_history.append(response_message)
                self.conversation_history.extend(tool_responses)

                # send tool messages to model
                second_completion = self.client.chat.completions.create(
                    extra_headers=self._build_extra_headers(),
                    extra_body={},
                    model=self.model,
                    messages=self.conversation_history,
                )

                response_content = second_completion.choices[0].message.content
                self.conversation_history.append(
                    {"role": "assistant", "content": response_content}
                )
                return response_content

        except Exception as e:
            logger.error(f"Error communicating with LLM: {e}")
            return None

    def get_conversation_history(self):
        """Returns the entire conversation history."""
        return self.conversation_history

    def clear_conversation_history(self):
        """Clears the conversation history."""
        self.conversation_history = []


class StreamingChat(OpenAIChat):
    def __init__(
        self,
        api_key,
        model,
        mcp_config_path,
        base_url="https://openrouter.ai/api/v1",
        site_url=None,
        site_name=None,
    ):
        super().__init__(api_key, model, mcp_config_path, base_url, site_url, site_name)
        self.system_prompt += (
            "If you want to use MCP tool, your response should start with <MCP_CALL>, and a JSON string in following format.\n"
            "{"
            '    "server": <server_name>,'
            '    "tool": <tool_name>,'
            '    "args": <JSON_string_args>'
            "}\n"
            "IMPORTANT: DO NOT contain any other message if you want to use other tool"
        )

    async def start(self):
        await self.mcp_client.start()

        mcp_tools = ""
        mcp_servers = self.mcp_client.list_servers()
        for server in self.mcp_client.list_servers():
            tools = f"Tools of {server}:\n"
            for tool in await self.mcp_client.list_tools(server):
                tools += f"{tool}\n"
            mcp_tools += f"{tools}"

        self.conversation_history.append(
            {
                "role": "system",
                "content": f"{self.system_prompt}\nAvailable MCP servers: {str(mcp_servers)}\n{mcp_tools}",
            }
        )

    async def send_message(self, content):
        """
        Sends a message to the LLM and receives the response in streaming mode.

        Args:
            content: The text content to send to the LLM.

        Yields:
            Each text fragment received from the LLM.

        Raises:
            Exception: Exceptions may be raised if the connection to the LLM fails or other errors occur.
                       Handle these exceptions appropriately on the calling side.
        """

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": content})

        try:
            completion_kwargs = {
                "extra_headers": self._build_extra_headers(),
                "extra_body": {},
                "model": self.model,
                "messages": self.conversation_history,
                "stream": True,
            }

            # send to model
            response = self.client.chat.completions.create(**completion_kwargs)
            full_content = ""

            for chunk in response:
                if chunk.choices:
                    content = chunk.choices[0].delta.content
                    if content is not None:
                        full_content += content
                        yield content
                        await asyncio.sleep(0) # force flush the buffer
            self.conversation_history.append(
                {"role": "assistant", "content": full_content}
            )

            if full_content.startswith("<MCP_CALL>"):
                req = json.loads(
                    full_content.replace("<MCP_CALL>", "").replace("</MCP_CALL>", "")
                )
                mcp_server = req["server"]
                mcp_tool = req["tool"]
                args = req["args"]

                # try mcp tool call
                try:
                    res = await self.mcp_client.execute_tool(mcp_server, mcp_tool, args)
                    self.conversation_history.append(
                        {"role": "user", "content": f"The tool result: {str(res)}"}
                    )
                    yield "</MCP_CALL>\n"
                except Exception as e:
                    self.conversation_history.append(
                        {"role": "tool", "content": f"Error: {e}"}
                    )

                # Send tool result to LLM
                second_res = self.client.chat.completions.create(
                    extra_headers=self._build_extra_headers(),
                    extra_body={},
                    model=self.model,
                    messages=self.conversation_history,
                    stream=True,
                )

                full_content = ""
                for chunk in second_res:
                    if chunk.choices:
                        content = chunk.choices[0].delta.content
                        if content is not None:
                            full_content += content
                            yield content
                            await asyncio.sleep(0) # force flush the buffer
                
                self.conversation_history.append(
                    {"role": "assistant", "content": full_content}
                )

        except Exception as e:
            logger.error(f"Error communicating with LLM: {e}")
            return
