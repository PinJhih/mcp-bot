import os
import asyncio
import json

from dotenv import load_dotenv

from mcp_client import llm_client

def load_config(path:str):
    with open(path) as config_file:
        mcp_config = json.load(config_file)
        return mcp_config

async def main_loop():
    load_dotenv("./.env")
    api_key = os.getenv("OPEN_ROUTER_API_KEY")
    model_name = "openai/gpt-3.5-turbo"
    mcp_config = load_config("./servers_config.json")

    llm_chat = llm_client.OpenAIChat(api_key, model_name, mcp_config)
    await llm_chat.start()

    while True:
        text = input("You: ")
        res = await llm_chat.send_message(text)

        print("\nModel:", res)
        print("=" * 32, "\n")


if __name__ == "__main__":
    asyncio.run(main_loop())
