import os
import json

import asyncio
import nest_asyncio
from dotenv import load_dotenv
import google.generativeai as genai

from .logger import logger
from .mcp_client import Client


# load .env and extract API key
load_dotenv("../.env")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

nest_asyncio.apply()


class Model:
    def __init__(self, bot_name, model_name: str = "gemini-1.5-flash") -> None:
        self.model_name = model_name
        self.mcp_client = Client()

        self.sys_instruction = (
            f"Your name is {bot_name}.\n"
            "You are now a Discord chat bot in a primarily Traditional Chinese Discord Server.\n"
            "MCP (Model Context Protocol) is a powerful protocol to make LLM able to interact with other tools.\n"
            "You are now a MCP client and able to access to MCP Servers.\n"
            f"Available MCP servers are: {', '.join(self.mcp_client.list_servers()) if self.mcp_client.list_servers() else 'None'}."
        )

        self.generation_config = {
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }

        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        self.tools = [self.list_tools, self.execute_tool]
        self.model = self.load_model()
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)

    def list_tools(self, server_name: str) -> str:
        """
        list all tools of a MCP server
        """
        loop = asyncio.get_event_loop()
        tools = loop.run_until_complete(self.mcp_client.list_tools(server_name))

        # convert to string
        res = ""
        for tool in tools:
            res += f"\n{tool.format_for_llm()}"
        return res

    def execute_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: str,
        retries: int,
        delay: float,
    ) -> str:
        """
        Execute a tool of a MCP server
        The "arguments" must be JSON string
        """
        arguments = json.loads(arguments)

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.mcp_client.execute_tool(
                server_name,
                tool_name,
                arguments,
                retries,
                delay,
            )
        )
        return str(result)

    def load_model(self) -> genai.GenerativeModel:
        return genai.GenerativeModel(
            model_name=self.model_name,
            safety_settings=self.safety_settings,
            generation_config=self.generation_config,
            system_instruction=self.sys_instruction,
            tools=self.tools,
        )

    def send_message(self, message):
        try:
            response = self.chat.send_message(message)
            logger.info("Responded from Gemini.")
            return response.text
        except Exception as e:
            logger.error(f"Gemini Error:\n\t{e}")
            return "Please try again later..."
