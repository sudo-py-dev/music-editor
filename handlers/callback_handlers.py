import os
from pyrogram.types import CallbackQuery
from tools.audio_utils import cut_audio
from tools.database import AudioFiles, Users
from tools.enums import Messages, create_message_audio
from pyrogram.handlers import CallbackQueryHandler
from pyrogram import filters, Client
from tools.database import Users
from tools.inline_keyboards import audio_edit_buttons, cancel_button
from tools.tools import with_language
from tools.logger import logger
import tempfile
from tools.image_utils import download_and_process_image, cleanup_temp_file
import shutil


async def select_language_handler(_, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    language = callback_query.data.split(":")[1]
    if language not in Messages().languages():
        supported_langs = ", ".join(Messages().languages())
        await callback_query.answer(Messages(language="en").language_not_supported.format(language, supported_langs))
        return

    if not Users.get(user_id=user_id):
        full_name = callback_query.from_user.full_name
        username = callback_query.from_user.username
        Users.create(user_id=user_id, full_name=full_name, username=username, language=language)
    else:
        Users.update(user_id=user_id, language=language)

    messages = Messages(language=language)
    language_name = messages.messages[language]['language']
    await callback_query.edit_message_text(messages.language_set.format(language_name))


@with_language
async def audio_edit_handler(client: Client, callback_query: CallbackQuery, language: str):
    user_id = callback_query.from_user.id
    messages = Messages(language=language)
    parts = callback_query.data.split(":")
    if len(parts) != 2:
        await callback_query.answer(messages.invalid_action)
        return

    action = parts[0]
    audio_id = int(parts[1])
    actions = ("image", "name", "cut", "genre", "album", "artist", "title", "date")
    if action in actions:
        Users.set_waiting_for(user_id=user_id, waiting_for=action, audio_id=audio_id, waiting_for_message_id=callback_query.message.id)
        if action == "image":
            await callback_query.edit_message_text(messages.waiting_for_image, reply_markup=cancel_button(audio_id, language))
        elif action == "name":
            await callback_query.edit_message_text(messages.waiting_for_name, reply_markup=cancel_button(audio_id, language))
        elif action == "title":
            await callback_query.edit_message_text(messages.waiting_for_title, reply_markup=cancel_button(audio_id, language))
        elif action == "cut":
            await callback_query.edit_message_text(messages.waiting_for_cut, reply_markup=cancel_button(audio_id, language))
        elif action == "genre":
            await callback_query.edit_message_text(messages.waiting_for_genre, reply_markup=cancel_button(audio_id, language))
        elif action == "album":
            await callback_query.edit_message_text(messages.waiting_for_album, reply_markup=cancel_button(audio_id, language))
        elif action == "artist":
            await callback_query.edit_message_text(messages.waiting_for_artist, reply_markup=cancel_button(audio_id, language))
        elif action == "title":
            await callback_query.edit_message_text(messages.waiting_for_title, reply_markup=cancel_button(audio_id, language))
        elif action == "date":
            await callback_query.edit_message_text(messages.waiting_for_date, reply_markup=cancel_button(audio_id, language))
    elif action == "cancel":
        Users.clear_waiting_for(user_id=user_id)
        audio = AudioFiles.get(user_id=user_id, audio_id=audio_id)
        if audio:
            keyboard = audio_edit_buttons(language=language, audio_id=audio_id)
            message_audio = create_message_audio(audio_file=audio, language=language)
            await callback_query.edit_message_text(message_audio, reply_markup=keyboard)
        else:
            await callback_query.answer(messages.audio_not_found)
    elif action == "done":
        Users.clear_waiting_for(user_id=user_id)
        audio = AudioFiles.get(user_id=user_id, audio_id=audio_id)
        if audio:
            file_id = audio.get("file_id")
            file_name = audio.get("file_name")
            title = audio.get("title")
            image_id = audio.get("image_id")
            genre = audio.get("genre")
            album = audio.get("album")
            artist = audio.get("artist")
            cut_start = audio.get("cut_start")
            cut_end = audio.get("cut_end")
            input_file = await client.download_media(file_id)
            image_file = None
            if image_id:
                image_file = await download_and_process_image(
                    client=client,
                    file_id=image_id,
                    max_size=(500, 500),
                    quality=85
                )
                if not image_file:
                    logger.warning(f"Failed to process image {image_id}, continuing without thumbnail")
            temp_dir = tempfile.mkdtemp(prefix=f"audio_edit_{audio_id}_")
            try:
                file_ext = os.path.splitext(file_name)[1].lower() or ".mp3"
                output_file = os.path.join(temp_dir, f"edited_{audio_id}{file_ext}")
                success, result = cut_audio(
                    input_path=input_file,
                    output_path=output_file,
                    start_time=cut_start,
                    end_time=cut_end,
                    language=language,
                    title=title,
                    genre=genre,
                    album=album,
                    artist=artist
                )
                
                if not success:
                    await callback_query.answer(result, show_alert=True)
                    return
                
                with open(output_file, 'rb') as audio_file:
                    await client.send_audio(
                        chat_id=user_id,
                        audio=audio_file,
                        thumb=image_file,
                        file_name=file_name,
                        title=title,
                        performer=artist,
                        duration=int((cut_end or 0) - (cut_start or 0))
                    )
                
                await callback_query.answer(messages.audio_processed_successfully)
                AudioFiles.delete(user_id=user_id, audio_id=audio_id)
                await callback_query.message.delete()

                
            except Exception as e:
                logger.error(f"Error processing audio: {e}", exc_info=True)
                await callback_query.answer(messages.error_processing_audio, show_alert=True)
                
            finally:
                for file_path in [input_file, output_file]:
                    if file_path and os.path.exists(file_path):
                        cleanup_temp_file(file_path)
                
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    logger.error(f"Error removing temporary directory {temp_dir}: {e}")
                
                if image_file:
                    cleanup_temp_file(image_file)
        else:
            await callback_query.answer(messages.audio_not_found)
    else:
        await callback_query.answer(messages.invalid_action)


callback_query_handlers = [
    CallbackQueryHandler(select_language_handler, filters.regex(r"lang:(\w{2})")),
    CallbackQueryHandler(audio_edit_handler, filters.regex(r"^\w+:(\d+)$"))
]
