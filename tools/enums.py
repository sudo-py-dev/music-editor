import os
import json
from tools.logger import logger
from enum import Enum


def format_timestamp(seconds):
    """Convert seconds to hh:mm:ss or mm:ss format."""
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return "-"
    
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    else:
        return f"{minutes:02}:{seconds:02}"


def load_json(file_path: str) -> dict:
    try:
        if not os.path.exists(file_path):
            return {}
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {e}")
        return {}


messages = load_json("locales/messages.json")
privileges = load_json("locales/privileges.json")


class Messages:
    def __init__(self, language: str = "he"):
        self.language = language
        self.messages = dict(messages)

    def __getattr__(self, name):
        if self.language and name in self.messages.get(self.language, {}):
            return self.messages[self.language][name]
        else:
            # Fallback to English if the message doesn't exist in the current language
            if name in self.messages.get("en", {}):
                return self.messages["en"][name]
            else:
                return f"Message '{name}' not found"

    def __setattr__(self, name, value):
        if name == 'language' or name == 'messages':
            super().__setattr__(name, value)
        else:
            # Handle dynamic message setting
            if hasattr(self, 'language') and hasattr(self, 'messages') and self.language:
                if self.language in self.messages and name in self.messages[self.language]:
                    self.messages[self.language][name] = value
                elif self.language in self.messages:
                    self.messages[self.language][name] = value
                # Don't set as instance attribute for message keys

    def languages(self):
        """Return a list of all available language codes."""
        return list(self.messages.keys())
    
    def languages_names(self):
        """Return a list of all available language names."""
        return [self.messages[language]['language'] for language in self.messages]


class PrivilegesMessages:
    def __init__(self, language: str = "he"):
        self.language = language
        self.privileges = dict(privileges)

    def __getattr__(self, name):
        if self.language and name in self.privileges.get(self.language, {}):
            return self.privileges[self.language][name]
        else:
            # Fallback to English if the message doesn't exist in the current language
            if name in self.privileges.get("en", {}):
                return self.privileges["en"][name]
            else:
                return f"Privilege '{name}' not found"

    def __setattr__(self, name, value):
        if name == 'language' or name == 'privileges':
            super().__setattr__(name, value)
        else:
            # Handle dynamic message setting
            if hasattr(self, 'language') and hasattr(self, 'privileges') and self.language:
                if self.language in self.privileges and name in self.privileges[self.language]:
                    self.privileges[self.language][name] = value
                elif self.language in self.privileges:
                    self.privileges[self.language][name] = value
                # Don't set as instance attribute for message keys

    def exists_privilege(self, privilege: str) -> bool:
        return privilege in self.privileges.get(self.language, {})


class AccessPermission(Enum):
    """Enum for access permission."""
    ALLOW = 1
    """User has permission to perform the action."""
    DENY = 2
    """User does not have permission to perform the action."""
    NOT_ADMIN = 3
    """User is not an admin."""
    CHAT_NOT_FOUND = 4
    """Chat is not found."""
    BOT_NOT_ADMIN = 5
    """Bot is not an admin."""


def format_file_size(size_bytes, default="N/A"):
    """
    Format file size in bytes to human-readable format.
    
    Args:
        size_bytes: File size in bytes (int, float, or None)
        default: Default value to return if size is invalid
        
    Returns:
        str: Formatted file size (e.g., '1.5 MB') or default value
    """
    if size_bytes is None or not isinstance(size_bytes, (int, float)):
        return default
        
    if size_bytes == 0:
        return "0 B"
        
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    import math
    magnitude = int(math.floor(math.log(size_bytes, 1024)))
    magnitude = min(magnitude, len(units) - 1)
    value = size_bytes / (1024 ** magnitude)
    return f"{value:.1f} {units[magnitude]}"


def create_message_audio(audio_file: dict, language: str = "he") -> str:
    messages = Messages(language=language)
    file_name = audio_file.get("file_name")[:35] if audio_file.get("file_name") else messages.not_set
    title = audio_file.get("title") or messages.not_set
    mime_type = audio_file.get("mime_type") or messages.not_set
    
    # Handle file_date which could be a string or datetime object
    file_date = audio_file.get("file_date")
    if file_date:
        if hasattr(file_date, 'strftime'):
            file_date = file_date.strftime("%d/%m/%Y %H:%M:%S")
        elif not isinstance(file_date, str):
            file_date = str(file_date)
    else:
        file_date = messages.not_set
        
    file_size = format_file_size(audio_file.get("file_size"), messages.not_set)
    genre = audio_file.get("genre") or messages.not_set
    album = audio_file.get("album") or messages.not_set 
    artist = audio_file.get("artist") or messages.not_set
    image = messages.was_set if audio_file.get("image_id") else messages.not_set
    cut_start = format_timestamp(audio_file.get("cut_start"))
    cut_end = format_timestamp(audio_file.get("cut_end"))
    return messages.audio_saved_message.format(file_name=file_name,
                                               title=title,
                                               mime_type=mime_type,
                                               file_date=file_date,
                                               file_size=file_size,
                                               genre=genre,
                                               album=album,
                                               artist=artist,
                                               cut_start=cut_start,
                                               cut_end=cut_end,
                                               image=image)
    