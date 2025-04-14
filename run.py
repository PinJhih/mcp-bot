import os
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from mcp_bot import llm_client


async def main_loop():
    load_dotenv("./.env")

    api_key = os.getenv("OPEN_ROUTER_API_KEY")
    model_name = "openai/gpt-3.5-turbo"
    mcp_config_path = Path("./servers_config.json").resolve()

    llm_chat = llm_client.OpenAIChat(api_key, model_name, mcp_config_path)
    await llm_chat.start()

    while True:
        text = input("You: ")
        res = await llm_chat.send_message(text)

        print("\nModel:", res)
        print("=" * 32, "\n")


if __name__ == "__main__":
    asyncio.run(main_loop())
