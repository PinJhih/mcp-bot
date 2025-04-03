import discord

from .logger import logger


class DiscordBot:
    def __init__(self, token):
        intents = discord.Intents.default()
        intents.message_content = True

        self.client = discord.Client(intents=intents)
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

        self.token = token

    async def on_ready(self):
        logger.info(f"Logged in as {self.client.user.name} (ID: {self.client.user.id})")
        print("-" * 80)

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

        # TODO: send user message to model, and send response to Discord

    def run(self):
        self.client.run(self.token)
