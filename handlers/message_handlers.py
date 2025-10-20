from pyrogram import Client, filters
from pyrogram.errors import MessageDeleteForbidden, MessageIdInvalid, MessageNotModified
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from database import AudioFiles, Users
from tools.inline_keyboards import audio_edit_buttons
from tools.tools import parse_date, with_language
from tools.enums import Messages, create_message_audio
from tools.audio_utils import parse_cut_range, validate_audio_filename
import os


@with_language
async def private_message_handler(client: Client, message: Message, language: str):
    user_id = message.from_user.id
    messages = Messages(language=language)
    user = await Users.get_waiting_for(user_id)
    if not user:
        await message.reply(messages.send_audio)
        return
    audio_id = user.get("audio_id")
    max_length = 64
    if (wait_for := user.get("wait_input")) and audio_id:
        if wait_for == "cut":
            if not message.text:
                await message.reply(messages.waiting_for_cut)
                await message.delete()
                return
            cat = message.text.strip()
            try:
                start_time, end_time = parse_cut_range(cat, language)
            except ValueError as e:
                await message.reply(str(e))
                await message.delete()
                return
            audio_file = await AudioFiles.update(user_id=user_id,
                                               audio_id=audio_id,
                                               cut_start=start_time,
                                               cut_end=end_time)
        elif wait_for == "name":
            if not message.text:
                await message.reply(messages.waiting_for_name)
                await message.delete()
                return
            name = message.text.strip()
            is_valid, sanitized_name, error = validate_audio_filename(name, language)
            if not is_valid:
                await message.reply(error)
                await message.delete()
                return
            audio_file = await AudioFiles.update(user_id=user_id,
                                           audio_id=audio_id,
                                           file_name=sanitized_name)
        elif wait_for == "image":
            if not message.photo or not message.photo.sizes:
                await message.reply(messages.waiting_for_image)
                await message.delete()
                return
            elif message.photo.sizes[-1].file_size > 5 * 1024 * 1024:
                await message.reply(messages.error_image_too_large)
                await message.delete()
                return
            image_id = message.photo.sizes[-1].file_id
            audio_file = await AudioFiles.update(user_id=user_id,
                                               audio_id=audio_id,
                                               image_id=image_id)
        elif wait_for == "genre":
            if not message.text:
                await message.reply(messages.waiting_for_genre)
                return
            
            genre = message.text.strip()
            if len(genre) > max_length:
                await message.reply(messages.error_genre_too_long)
                return
            audio_file = await AudioFiles.update(user_id=user_id,
                                           audio_id=audio_id,
                                           genre=genre)
        elif wait_for == "artist":
            if not message.text:
                await message.reply(messages.waiting_for_artist)
                return
            artist = message.text.strip()
            if len(artist) > max_length:
                await message.reply(messages.error_artist_too_long)
                return
            audio_file = await AudioFiles.update(user_id=user_id,
                                               audio_id=audio_id,
                                               artist=artist)
        elif wait_for == "album":
            if not message.text:
                await message.reply(messages.waiting_for_album)
                await message.delete()
                return
            album = message.text.strip()
            if len(album) > max_length:
                await message.reply(messages.error_album_too_long)
                await message.delete()
                return
            audio_file = await AudioFiles.update(user_id=user_id,
                                               audio_id=audio_id,
                                               album=album)
        elif wait_for == "title":
            if not message.text:
                await message.reply(messages.waiting_for_title)
                await message.delete()
                return
            title = message.text.strip()
            if len(title) > max_length:
                await message.reply(messages.error_title_too_long)
                await message.delete()
                return
            audio_file = await AudioFiles.update(user_id=user_id,
                                               audio_id=audio_id,
                                               title=title)
        elif wait_for == "date":
            if not message.text:
                await message.reply(messages.waiting_for_date)
                await message.delete()
                return
            date = message.text.strip()
            date = parse_date(date)
            if not date:
                await message.reply(messages.error_date_invalid)
                await message.delete()
                return
            audio_file = await AudioFiles.update(user_id=user_id,
                                               audio_id=audio_id,
                                               file_date=date)
        else:
            await message.reply(messages.invalid_action)
            await message.delete()
            return
        message_audio = create_message_audio(audio_file=audio_file, language=language)
        keyboard = audio_edit_buttons(language=language, audio_id=audio_id)
        try:
            await client.edit_message_text(chat_id=user_id,
                                           message_id=user.get("waiting_for_message_id"),
                                           text=message_audio,
                                           reply_markup=keyboard)
            await message.delete()
        except MessageIdInvalid:
            await message.reply(message_audio, reply_markup=keyboard)
            await message.delete()
        except MessageNotModified:
            await message.delete()
    else:
        await message.reply(messages.audio_not_found)
        try:
            await message.delete()
        except (MessageIdInvalid, MessageDeleteForbidden):
            pass


@with_language
async def audio_message_handler(_, message: Message, language: str):
    messages = Messages(language=language)
    user_id = message.from_user.id
    if message.audio:
        file_id = message.audio.file_id
        file_name = message.audio.file_name
        file_size = message.audio.file_size
        file_title = message.audio.title
        file_date = message.audio.date
        mime_type = message.audio.mime_type
    elif message.document and (message.document.mime_type == "audio/mpeg" or message.document.mime_type == "audio/mp3"):
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_size = message.document.file_size
        file_title = None
        file_date = message.document.date
        mime_type = message.document.mime_type
    elif message.voice:
        file_id = message.voice.file_id
        file_name = f"voice_{message.voice.file_id}.mp3"
        file_size = message.voice.file_size
        file_title = None
        file_date = message.voice.date
        mime_type = message.voice.mime_type
    else:
        await message.reply(messages.send_audio)
        return
    if file_size > int(os.getenv("MAX_AUDIO_SIZE", 40)) * 1024 * 1024:
        await message.reply(messages.error_audio_too_large.format(os.getenv("MAX_AUDIO_SIZE")))
        return
    audio_file = await AudioFiles.create(user_id=user_id,
                                         file_id=file_id,
                                         file_name=file_name,
                                         file_size=file_size,
                                         title=file_title,
                                         mime_type=mime_type,
                                         file_date=file_date)
    keyboard = audio_edit_buttons(language=language, audio_id=audio_file.get("audio_id"))
    message_audio = create_message_audio(audio_file=audio_file, language=language)
    await message.reply(message_audio, reply_markup=keyboard)


message_handlers = [MessageHandler(audio_message_handler, (filters.private & (filters.audio | filters.document | filters.voice))),
                    MessageHandler(private_message_handler, (filters.private & (filters.text | filters.photo)))]
