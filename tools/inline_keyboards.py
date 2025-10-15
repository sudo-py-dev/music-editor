from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from tools.enums import Messages
from database import BotSettings


def select_language_buttons():
    messages = Messages()
    buttons = []
    row = []

    for i, lang in enumerate(messages.languages(), start=1):
        language_name = messages.languages_names()[i-1]
        row.append(InlineKeyboardButton(
            language_name,
            callback_data=f"lang:{lang}"
        ))
        if i % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(buttons)


def buttons_builder(name, data):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(name, callback_data=data)
            ]
        ]
    )


def bot_settings_buttons(bot_settings: BotSettings, language: str):
    messages = Messages(language=language)
    
    buttons = [
        # Statistics on its own row
        [InlineKeyboardButton(text=messages.statistics_button, callback_data="bot:statistics")],
        
        # Group settings
        [
            InlineKeyboardButton(
                text=messages.can_join_group_button.format("✅" if bot_settings.can_join_group else "❌"),
                callback_data="bot:can_join_group"
            ),
            InlineKeyboardButton(
                text=messages.can_join_channel_button.format("✅" if bot_settings.can_join_channel else "❌"),
                callback_data="bot:can_join_channel"
            )
        ],
        
        # Export buttons
        [
            InlineKeyboardButton(text=messages.export_users_button, callback_data="bot:users"),
            InlineKeyboardButton(text=messages.export_chats_button, callback_data="bot:chats")
        ],
        
        # Ban/Unban actions
        [
            InlineKeyboardButton(text=messages.banid_button, callback_data="bot:banid"),
            InlineKeyboardButton(text=messages.unbanid_button, callback_data="bot:unbanid")
        ]
    ]
    
    return InlineKeyboardMarkup(buttons)


def audio_edit_buttons(language: str, audio_id: int):
    messages = Messages(language=language)
    buttons = [
        [
            InlineKeyboardButton(messages.cut_button, callback_data=f"cut:{audio_id}"),
            InlineKeyboardButton(messages.image_button, callback_data=f"image:{audio_id}")
        ],
        [
            InlineKeyboardButton(messages.name_button, callback_data=f"name:{audio_id}"),
            InlineKeyboardButton(messages.title_button, callback_data=f"title:{audio_id}")
        ],
        [
            InlineKeyboardButton(messages.genre_button, callback_data=f"genre:{audio_id}")
        ],
        [
            InlineKeyboardButton(messages.album_button, callback_data=f"album:{audio_id}"),
            InlineKeyboardButton(messages.artist_button, callback_data=f"artist:{audio_id}")
        ],
        [
            InlineKeyboardButton(messages.done_button, callback_data=f"done:{audio_id}")
        ]
    ]
    return InlineKeyboardMarkup(buttons)