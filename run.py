import os
import asyncio

from dotenv import load_dotenv

from mcp_bot.llm_client import open_router_client

async def main_loop():
    load_dotenv("./.env")
    api_key = os.getenv("OPEN_ROUTER_API_KEY")

    model_name = "openai/gpt-3.5-turbo"
    client = open_router_client.OpenRouterChat(api_key=api_key, model=model_name)

    await client.mcp_client.start()
    while True:
        text = input("You: ")
        res = await client.send_message(text)

        print("\nModel:", res)
        print("=" * 32, "\n")


if __name__ == "__main__":
    asyncio.run(main_loop())
