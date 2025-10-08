from tools.database import Users, Chats, BotSettings
from pyrogram import filters
from tools.tools import with_language, owner_only
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import CallbackQuery
from tools.inline_keyboards import buttons_builder, bot_settings_buttons
from tools.logger import logger
from tools.enums import Messages


@owner_only
@with_language
async def bot_statistics(_, query: CallbackQuery, language: str):
    messages = Messages(language=language)
    users = Users().count()
    active_users = Users().count_by(is_active=True)
    chats = Chats().count()
    active_chats = Chats().count_by(is_active=True)
    back = buttons_builder(messages.back_button, data="bot:back")
    await query.edit_message_text(
                                  messages.statistics.format(users, active_users, chats, active_chats),
                                  reply_markup=back)


@owner_only
@with_language
async def update_bot_settings(_, query: CallbackQuery, language: str):
    parts = query.data.split(":")
    if len(parts) != 2:
        return

    key = parts[1]
    settings_options = ("can_join_group", "can_join_channel")
    if key not in settings_options:
        logger.error(f"Invalid setting key: {key} try to update bot settings")
        return

    BotSettings.switch_settings(key)
    messages = Messages(language=language)
    bot_settings = BotSettings.get_settings()
    await query.edit_message_text(messages.bot_settings, reply_markup=bot_settings_buttons(bot_settings, language))


@owner_only
@with_language
async def back(_, query: CallbackQuery, language: str):
    messages = Messages(language=language)
    bot_settings = BotSettings.get_settings()
    await query.edit_message_text(messages.bot_settings, reply_markup=bot_settings_buttons(bot_settings, language))


bot_settings_callback_handlers = [
    CallbackQueryHandler(bot_statistics, filters.regex("^bot:statistics$")),
    CallbackQueryHandler(back, filters.regex("^bot:back$")),
    CallbackQueryHandler(update_bot_settings, filters.regex("^bot:(can_join_group|can_join_channel)$"))
]
