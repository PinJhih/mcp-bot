import os

import discord
from dotenv import load_dotenv

from .logger import logger
from .llm_client.open_router_client import OpenRouterChat


load_dotenv("../.env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")


class DiscordBot:
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

        self.chat = OpenRouterChat(
            api_key=OPEN_ROUTER_API_KEY,
            model="openai/gpt-3.5-turbo",
        )

    async def on_ready(self):
        await self.chat.mcp_client.start()
        logger.info(
            f"Logged in as {self.client.user.name} (ID: {self.client.user.id})\n"
            + "=" * 96
        )

    async def on_message(self, message):
        # extract fields from message
        author = message.author
        channel = message.channel
        content = message.content

        # skip if bot is not mentioned in the message, or message is from bot
        if not self.client.user.mentioned_in(message) or author == self.client.user:
            return

        log = f'From "{author}" in channel "{channel}"'
        logger.info(log)

        # content = content.replace(f"<@{self.client.user.id}>", self.client.user.name)
        # user_message = f"From <@{author.id}> in {channel.id}\n{content}"

        content = content.replace(f"<@{self.client.user.id}>", "")
        user_message = f"{content}"
        response = await self.chat.send_message(user_message)
        await message.channel.send(response)

    def run(self):
        self.client.run(DISCORD_TOKEN)
