from tools.database import BotSettings
from tools.logger import logger
from pyrogram import Client
from dotenv import load_dotenv
import os
from handlers.command_handlers import commands_handlers
from handlers.callback_handlers import callback_query_handlers
from handlers.message_handlers import message_handlers
from bot_management.bot_settings import bot_handlers
from bot_management.callback_handlers import bot_settings_callback_handlers


load_dotenv()


api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
token = os.getenv("BOT_TOKEN")
bot_client_name = os.getenv("BOT_CLIENT_NAME")

if not api_id or not api_hash or not token or not bot_client_name:
    raise ValueError("API_ID, API_HASH, BOT_TOKEN, and BOT_CLIENT_NAME must be set in the environment variables")

app = Client(bot_client_name, api_id=api_id, api_hash=api_hash, bot_token=token)


# Commands handler
for handler in commands_handlers:
    app.add_handler(handler)

# Callback query handler
for handler in callback_query_handlers:
    app.add_handler(handler)

# Owner handlers
for handler in bot_handlers:
    app.add_handler(handler)

# Owner panel callback handlers
for handler in bot_settings_callback_handlers:
    app.add_handler(handler)

# Message handlers
for handler in message_handlers:
    app.add_handler(handler)

if os.getenv("OWNER_ID") != BotSettings.get_settings().owner_id:
    logger.info("Owner ID updated")
    BotSettings.update_settings(owner_id=os.getenv("OWNER_ID"))

# Run the bot
logger.info("Bot started successfully")
app.run()
logger.info("Bot stopped")
