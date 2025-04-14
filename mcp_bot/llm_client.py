import json

from openai import OpenAI

from .logger import logger
from .mcp_client import MCPClient


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
            site_url (str, optional): Your site URL for rankings on openrouter.ai. Defaults to None.
            site_name (str, optional): Your site title for rankings on openrouter.ai. Defaults to None.
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

        # TODO: Initialize conversation history. (system instructions)
        self.conversation_history = []

        self.mcp_client = MCPClient(mcp_config_path)
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_tools",
                    "description": "List all tools of a MCP server",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "server_name": {
                                "type": "string",
                                "description": "The name of MCP Server.",
                            },
                        },
                        "required": ["server_name"],
                    },
                },
            },
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
            "list_tools": self.list_tools,
            "execute_tool": self.execute_tool,
        }

    async def start(self) -> None:
        # init all MCP Server connections
        await self.mcp_client.start()

        # list all servers and append to conversation history
        mcp_servers = self.mcp_client.list_servers()
        self.conversation_history.append(
            {
                "role": "system",
                "content": f"Available MCP servers: {str(mcp_servers)}",
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
                "tools": self.tools,
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
