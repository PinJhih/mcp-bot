import os

from dotenv import load_dotenv

from mcp_bot.dc_bot import DiscordBot

load_dotenv("../.env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    bot = DiscordBot(DISCORD_TOKEN)
    bot.run()
