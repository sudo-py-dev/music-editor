import re
from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.types import CallbackQuery, Message
from database import Chats, Users, AdminsPermissions, BotSettings
from tools.enums import AccessPermission
from tools.enums import Messages, PrivilegesMessages
from functools import wraps
from tools.logger import logger
from typing import Union
import os
from tools.inline_keyboards import select_language_buttons
from pyrogram.filters import create, Filter


def is_valid_chat_id(chat_id) -> bool:
    return bool(re.match(r"^-\d{5,32}$", str(chat_id)))


def is_valid_user_id(user_id) -> bool:
    return bool(re.match(r"^\d{1,32}$", str(user_id)))


def is_valid_username(username) -> bool:
    return bool(re.match(r"^@[a-zA-Z][a-zA-Z0-9_]{3,30}[a-zA-Z0-9]$", str(username)))


def is_admin_message(permission_require="can_restrict_members"):
    """
    Check if a message or callback query is from an admin of the chat and has the required permission.

    :param permission_require: Permission required (e.g., "can_restrict_members")
    :return: AccessPermission enum value
    """
    def function(func):
        @wraps(func)
        async def wrapper(client: Client, message: Message, *args, **kwargs):
            if not isinstance(message, Message):
                raise TypeError("Invalid Type, expected Message only")

            chat_type = message.chat.type

            if chat_type in [ChatType.PRIVATE, ChatType.CHANNEL]:
                return await func(client, message, *args, **kwargs)
            else:
                user_id = message.from_user.id
                chat_id = message.chat.id
                access = await AdminsPermissions.is_admin(client, chat_id, user_id, permission_require)
                if access == AccessPermission.ALLOW:
                    return await func(client, message, *args, **kwargs)
                elif access == AccessPermission.DENY:
                    chat = await Chats.get(chat_id=chat_id)
                    language = chat.get("language") or os.getenv("DEFAULT_LANGUAGE") or "he"
                    miss_permission = PrivilegesMessages(language=language).__getattr__(permission_require)
                    await message.reply(Messages(language=language).unauthorized_admin.format(miss_permission))
                    return
                elif access == AccessPermission.BOT_NOT_ADMIN:
                    chat = await Chats.get(chat_id=chat_id)
                    language = chat.get("language") or os.getenv("DEFAULT_LANGUAGE") or "he"
                    await message.reply(Messages(language=language).bot_not_admin)
                    return
                elif access == AccessPermission.CHAT_NOT_FOUND:
                    chat = await Chats.get(chat_id=chat_id)
                    language = chat.get("language") or os.getenv("DEFAULT_LANGUAGE") or "he"
                    await message.reply(Messages(language=language).chat_not_found)
                    return
                return
        return wrapper
    return function


def with_language(func):
    @wraps(func)
    async def wrapper(client: Client, msg: [Message, CallbackQuery], *args, **kwargs):
        if isinstance(msg, CallbackQuery):
            chat_type = msg.message.chat.type
        elif isinstance(msg, Message):
            chat_type = msg.chat.type
        else:
            raise ValueError("Invalid Object, expected Message or CallbackQuery only")

        default_language = os.getenv("DEFAULT_LANGUAGE") or "he"

        if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            chat_id = msg.chat.id
            chat = await Chats.get(chat_id=chat_id)
            if not chat:
                await Chats.create(chat_id=chat_id,
                             chat_type=chat_type,
                             chat_title=msg.chat.title)
                chat = await Chats.get(chat_id=chat_id)
            if isinstance(chat, dict) and chat.get("is_banned"):
                await msg.chat.leave()
                return
            language = chat.get("language") or default_language
        elif chat_type == ChatType.PRIVATE:
            user_id = msg.from_user.id
            user = await Users.get(user_id=user_id)
            if user is None:
                await Users.create(user_id=user_id,
                             username=msg.from_user.username,
                             full_name=msg.from_user.full_name,
                             is_active=True)
                user = await Users.get(user_id=user_id)
                await msg.reply(Messages(language=default_language).select_language,
                                reply_markup=select_language_buttons())
                return
            if isinstance(user, dict) and user.get("is_banned"):
                return
            language = user.get("language") or default_language
        else:
            raise TypeError("Invalid chat type only groups, supergroups or private allowd")
        try:
            return await func(client, msg, language, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in function {func.__name__} for user {msg.from_user.id}: {e}")
            return
    return wrapper


def chat_settings():
    def function(func):
        @wraps(func)
        async def wrapper(client: Client, msg_or_cq: [Message, CallbackQuery]):
            if isinstance(msg_or_cq, CallbackQuery):
                message = msg_or_cq.message
            elif not isinstance(msg_or_cq, Message):
                raise ValueError("Invalid Object, expected Message or CallbackQuery only")
            message = msg_or_cq
            if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
                logger.warning(f"wrapper work only in groups")
                return
            chat = await Chats.get(chat_id=message.chat.id)
            if not chat:
                chat = await Chats.create(chat_id=message.chat.id,
                                    chat_type=message.chat.type.value,
                                    chat_title=message.chat.title)
            try:
                return await func(client, msg_or_cq, chat)
            except Exception as e:
                logger.error(f"Error in function {func.__name__} for chat {message.chat.id}: {e}")
                return
        return wrapper
    return function


def owner_only(func):
    """Decorator to restrict access to the bot owner only"""
    @wraps(func)
    async def wrapper(client: Client, update: Union[Message, CallbackQuery], *args, **kwargs):
        try:
            user_id = update.from_user.id
            if "language" in kwargs.keys():
                language = kwargs.get("language")
            else:
                language = update.from_user.language_code or "en"

            if user_id != (await BotSettings.get_settings()).owner_id:
                if isinstance(update, CallbackQuery):
                    await update.answer(Messages(language=language).unauthorized_user, show_alert=True)
                return
            # Call the original function
            return await func(client, update, *args, **kwargs)

        except Exception as e:
            logger.error(f"Error in owner_only decorator: {e}")
            if isinstance(update, CallbackQuery):
                await update.answer(Messages(language=language).error_occurred, show_alert=True)
            return
    return wrapper


def register_handlers(app: Client, *handler_lists: list) -> None:
    """Register multiple lists of handlers with the client.
    
    Args:
        app: The Pyrogram Client instance
        *handler_lists: Variable number of handler lists to register
    """
    count_handlers = 0
    for handler_list in handler_lists:
        if not isinstance(handler_list, list):
            raise ValueError("All handler lists must be of type list")
        for handler in handler_list:
            app.add_handler(handler)
            count_handlers += 1
    logger.info(f"Registered {count_handlers} handlers")


def wait_input_filter(wait_input: str) -> Filter:
    """Filter to check if the bot is waiting for input from the user"""
    async def func(_, __, m: Message) -> bool:
        if m.chat.type == ChatType.PRIVATE:
            user = await Users().get(m.from_user.id)
            if not user:
                return False
            return user.get("wait_input") == wait_input
        return False
    return create(func=func, name=f"WaitInput_{wait_input}")
