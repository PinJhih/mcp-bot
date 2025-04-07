import os

from dotenv import load_dotenv
import google.generativeai as genai

from .logger import logger


# load .env and extract API key
load_dotenv("../.env")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)


class Model:
    def echo(self, message: str) -> dict[str, str]:
        """
        print the message
        """
        logger.info(message)
        return {"message": "OK!"}

    def __init__(self, bot_name, model_name: str = "gemini-1.5-flash") -> None:
        self.model_name = model_name

        self.sys_instruction = (
            f"Your name is {bot_name}"
            + "You are now a Discord chat bot in a primarily Traditional Chinese Discord Server."
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

        self.tools = [self.echo]
        self.model = self.load_model()
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)

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
