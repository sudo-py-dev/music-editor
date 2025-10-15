import json
import tempfile
from datetime import datetime
from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import CallbackQuery
from database import Users, Chats, BotSettings
from tools.tools import with_language, owner_only
from tools.inline_keyboards import bot_settings_buttons, buttons_builder
from tools.enums import Messages


def _serialize_value(value):
    """Recursively serialize values to be JSON-compatible."""
    from datetime import datetime
    
    if isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    return value


@owner_only
@with_language
async def on_callback_settings(_, query: CallbackQuery, language: str):
    """Handle all bot-related callback queries.
    
    Args:
        _: Unused client parameter
        query: The callback query object
        language: User's language code
    """
    messages = Messages(language=language)
    data = query.data.split(":")
    
    if len(data) < 2:
        return
    
    action = data[1].strip()
    
    # Handle statistics
    if action == "statistics":
        users = await Users().count()
        active_users = await Users().count_by(is_active=True)
        chats = await Chats().count()
        active_chats = await Chats().count_by(is_active=True)
        
        back_button = buttons_builder(messages.back_button, "bot:back")
        
        text = messages.statistics.format(users, active_users, chats, active_chats)
        await query.edit_message_text(
            text,
            reply_markup=back_button
        )

    elif action in ("users", "chats"):
        await _export_data(query, messages, action)

    elif action in ("can_join_group", "can_join_channel", "back"):
        if action != "back":
            await BotSettings.switch_settings(action)
        await query.edit_message_text(
            messages.bot_settings,
            reply_markup=bot_settings_buttons(await BotSettings.get_settings(), language)
        )
    elif action == "banid":
        await Users.update(user_id=query.from_user.id, wait_input="banid")
        await query.edit_message_text(messages.send_banid)
    elif action == "unbanid":
        await Users.update(user_id=query.from_user.id, wait_input="unbanid")
        await query.edit_message_text(messages.send_unbanid)
        


async def _export_data(query: CallbackQuery, messages: Messages, data_type: str) -> None:
    """Export all users or chats as JSON and send as a document."""
    model = Users() if data_type == "users" else Chats()
    items = await model.get_all()
    if not items:
        await query.answer(messages.no_data_to_export, show_alert=True)
        return

    await query.answer(messages.exporting_data)
    data = _serialize_value(items)
    filename = f"{data_type}_export_{datetime.now():%Y%m%d_%H%M%S}.json"

    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".json", delete=True) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.seek(0)
        await query.message.reply_document(
            document=tmp.name,
            file_name=filename,
            caption=messages.export_success.format(data_type),
        )



settings_callback_handlers = [
    CallbackQueryHandler(
        on_callback_settings,
        filters.regex(r"^bot:(\w+)$")
    )
]
