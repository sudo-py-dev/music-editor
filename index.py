import os
import asyncio
from dotenv import load_dotenv
from pyrogram import Client, idle
from tools.logger import logger
from database import create_tables, BotSettings
from tools.tools import register_handlers
from handlers import (
    commands_handlers,
    callback_query_handlers,
    message_handlers
)
from bot import settings_handlers, settings_callback_handlers


load_dotenv()


api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
token = os.getenv("BOT_TOKEN")
bot_client_name = os.getenv("BOT_CLIENT_NAME", "bot")
bot_owner_id = os.getenv("BOT_OWNER_ID")
skip_updates = os.getenv("SKIP_UPDATES", False)


if not api_id or not api_hash or not token or not bot_client_name:
    raise ValueError("API_ID, API_HASH, BOT_TOKEN, BOT_CLIENT_NAME must be set in the environment variables")


app = Client(bot_client_name, api_id=api_id, api_hash=api_hash, bot_token=token, skip_updates=skip_updates)


register_handlers(
    app,
    commands_handlers,
    callback_query_handlers,
    settings_handlers,
    settings_callback_handlers,
    message_handlers
)


async def main():
    try:
        # Initialize database first
        await create_tables()

        await app.start()
        me = await app.get_me()
        logger.info(f"Bot https://t.me/{me.username} is now running!")
        
        # Get bot settings
        bot_settings = await BotSettings.get_settings()
        OWNER_ID = int(os.getenv("BOT_OWNER_ID"))
        logger.success("Bot settings initialized successfully")
        if bot_settings.owner_id is None or bot_settings.owner_id != OWNER_ID:
            await BotSettings.update_settings(owner_id=OWNER_ID)
            try:
                name = await app.get_chat(OWNER_ID)
                await app.send_message(OWNER_ID, f"Bot owner ID updated and the new owner is {OWNER_ID} {name.full_name} successfully\nsend /admin to get bot admin panel")
                logger.success(f"Bot owner ID updated and the new owner is {OWNER_ID} {name.full_name} successfully")
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}", exc_info=True)


        await idle()
    except asyncio.CancelledError:
        logger.success("Bot is shutting down...")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
    finally:
        if app.is_connected:
            await app.stop()
            logger.success("Bot stopped successfully")


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot is shutting down...")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
