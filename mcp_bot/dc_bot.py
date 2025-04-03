import os

import discord
from dotenv import load_dotenv

from .logger import logger
from .gemini_client import Model


load_dotenv("../.env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")


class DiscordBot:
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

        # initialize after DC client is ready
        self.model = None

    async def on_ready(self):
        logger.info(f"Logged in as {self.client.user.name} (ID: {self.client.user.id})")
        print("-" * 80)
        self.model = Model(self.client.user.name)

    async def on_message(self, message):
        # extract fields from message
        author = message.author
        channel = message.channel
        content = message.content

        # skip if bot is not mentioned in the message, or message is from bot
        if not self.client.user.mentioned_in(message) or author == self.client.user:
            return

        # logs the message
        log = f'From "{author}" in channel "{channel}"'
        logger.info(log)

        content = content.replace(f"<@{self.client.user.id}>", self.client.user.name)
        user_message = [f"From <@{author.id}> in {channel.id}\n{content}"]
        response = self.model.send_message(user_message)
        await message.channel.send(response)

    def run(self):
        self.client.run(DISCORD_TOKEN)
