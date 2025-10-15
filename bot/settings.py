from pyrogram import filters
from pyrogram.types import Message
from database.database import Chats
from tools.inline_keyboards import bot_settings_buttons
from tools.enums import Messages
from pyrogram.handlers import MessageHandler
from database import BotSettings, Users
from tools.tools import (is_valid_chat_id, 
                         is_valid_user_id,
                         with_language,
                         owner_only,
                         wait_input_filter)


@owner_only
@with_language
async def bot_settings(_, message: Message, language: str):
    messages = Messages(language=language)
    bot_settings = await BotSettings.get_settings()
    buttons = bot_settings_buttons(bot_settings, language)
    await message.reply(messages.bot_settings, reply_markup=buttons)


@owner_only
@with_language
async def ban_user_or_chat(_, message: Message, language: str):
    messages = Messages(language=language)
    if is_valid_chat_id(message.text):
        chat = await Chats.get(chat_id=int(message.text))
        if chat and not chat.get("is_banned"):
            await Chats.update(chat_id=int(message.text), is_banned=True)
            await message.reply(messages.banid_success)
            await Users.update(user_id=message.from_user.id, wait_input=None)
            await message.delete()
            await bot_settings(_, message)
        elif chat and chat.get("is_banned"):
            await message.reply(messages.banid_chat_already_banned)
        else:
            await message.reply(messages.banid_chat_not_found)
    elif is_valid_user_id(message.text):
        user = await Users.get(user_id=int(message.text))
        if user and not user.get("is_banned"):
            await Users.update(user_id=int(message.text), is_banned=True)
            await message.reply(messages.banid_success)
            await Users.update(user_id=message.from_user.id, wait_input=None)
            await message.delete()
            await bot_settings(_, message)
        elif user and user.get("is_banned"):
            await message.reply(messages.banid_user_already_banned)
        else:
            await message.reply(messages.banid_user_not_found)
    elif message.text == "/cancel":
        await Users.update(user_id=message.from_user.id, wait_input=None)
        await message.delete()
        await bot_settings(_, message)
    else:
        await message.reply(messages.banid_invalid)


@owner_only
@with_language
async def unban_user_or_chat(_, message: Message, language: str):
    messages = Messages(language=language)
    if is_valid_chat_id(message.text):
        chat = await Chats.get(chat_id=int(message.text))
        if chat and chat.get("is_banned"):
            await Chats.update(chat_id=int(message.text), is_banned=False)
            await message.reply(messages.banid_success)
            await Users.update(user_id=message.from_user.id, wait_input=None)
            await message.delete()
            await bot_settings(_, message)
        elif chat and not chat.get("is_banned"):
            await message.reply(messages.unbanid_chat_not_banned)
        else:
            await message.reply(messages.unbanid_chat_not_found)
    elif is_valid_user_id(message.text):
        user = await Users.get(user_id=int(message.text))
        if user and user.get("is_banned"):
            await Users.update(user_id=int(message.text), is_banned=False)
            await message.reply(messages.unbanid_success)
            await Users.update(user_id=message.from_user.id, wait_input=None)
            await message.delete()
            await bot_settings(_, message)
        elif user and not user.get("is_banned"):
            await message.reply(messages.unbanid_user_not_banned)
        else:
            await message.reply(messages.unbanid_user_not_found)
    elif message.text == "/cancel":
        await Users.update(user_id=message.from_user.id, wait_input=None)
        await message.delete()
        await bot_settings(_, message)
    else:
        await message.reply(messages.unbanid_invalid)


settings_handlers = [MessageHandler(bot_settings, filters.command("admin")),
                     MessageHandler(ban_user_or_chat, filters.private & (filters.text | filters.command("cancel")) & wait_input_filter("banid")),
                     MessageHandler(unban_user_or_chat, filters.private & (filters.text | filters.command("cancel")) & wait_input_filter("unbanid"))]
