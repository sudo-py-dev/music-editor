from tools.enums import Messages
from tools.inline_keyboards import select_language_buttons
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ChatType
from pyrogram.handlers import MessageHandler
from pyrogram import filters
from tools.tools import with_language, is_admin_message
from tools.database import Chats


@with_language
async def start_handler(client: Client, message: Message, language: str):
    await message.reply(Messages(language=language).start.format(client.me.full_name))


@with_language
async def help_handler(_, message: Message, language: str):
    commands = Messages(language=language).commands
    commands_str = "\n".join([f"/{command} - {description}" for command, description in commands.items()])
    await message.reply(Messages(language=language).help.format(commands_str))


@is_admin_message()
@with_language
async def change_language_handler(_, message: Message, language: str):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        parts = message.text.split(" ")
        supported_langs = ", ".join(Messages().languages())
        if len(parts) != 2:
            error_msg = Messages(language=language).select_language_groups.format(supported_langs)
            await message.reply(error_msg)
            return
        new_lang = parts[1].strip()
        if new_lang not in Messages().languages():
            error_msg = Messages(language=language).language_not_supported.format(new_lang, supported_langs)
            await message.reply(error_msg)
            return

        Chats.update(chat_id=message.chat.id, language=new_lang)
        messages = Messages(language=new_lang)
        await message.reply(messages.language_set_groups.format(messages.language))
    else:
        await message.reply(Messages(language=language).select_language, reply_markup=select_language_buttons())


# Add more commands handlers here


commands_handlers = [
    MessageHandler(start_handler, filters.command("start") & filters.private),
    MessageHandler(help_handler, filters.command("help") & filters.private),
    MessageHandler(change_language_handler, filters.command("lang") & (filters.private | filters.group))
    # Add the commands functions with the filters here
]
