import os
import re
from pydub import AudioSegment
from tools.logger import logger
from tools.enums import Messages
from pathlib import Path
from typing import Optional, Tuple


def parse_time(time_str: str) -> float:
    """
    Convert a flexible timestamp string into seconds (float).
    Supports:
        "90" -> 90
        "1:30" -> 90
        "01:02:03" -> 3723
        "1m30s", "1h2m3s"
        "1.5m" -> 90
    """
    if not time_str:
        raise ValueError("Empty time string")

    time_str = time_str.strip().lower()

    # 1️⃣ Pure number
    if re.fullmatch(r"\d+(\.\d+)?", time_str):
        return float(time_str)

    # 2️⃣ Symbolic format (e.g. 1h2m3s)
    match = re.findall(r"(\d+(?:\.\d+)?)([hms])", time_str)
    if match:
        total = 0.0
        for value, unit in match:
            value = float(value)
            if unit == "h":
                total += value * 3600
            elif unit == "m":
                total += value * 60
            elif unit == "s":
                total += value
        return total

    # 3️⃣ Colon format (HH:MM:SS, MM:SS)
    parts = [float(p) for p in time_str.split(":")]
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds

    raise ValueError(f"Unsupported time format: {time_str}")


def parse_cut_range(cut_str: str, language: str) -> tuple[float, float]:
    """
    Parse a cut range string into (start_seconds, end_seconds).
    
    Supported formats:
        "1:15-2:30"
        "75-150"
        "1m15s-2m30s"
        "00:01:15-00:02:30"
    
    Raises ValueError if invalid.
    """
    messages = Messages(language=language)
    if not cut_str:
        raise ValueError(messages.empty_cut)

    # Split by dash or similar separators
    parts = re.split(r"\s*[-–—]\s*", cut_str.strip())  # supports "-", "–", "—"
    if len(parts) != 2:
        raise ValueError(messages.invalid_cut_range.format(cut_str))

    start_str, end_str = parts
    start_sec = parse_time(start_str)
    end_sec = parse_time(end_str)

    if start_sec < 0 or end_sec < 0:
        raise ValueError(messages.error_negative_time)

    if start_sec >= end_sec:
        raise ValueError(messages.error_invalid_order)

    return start_sec, end_sec




def cut_audio(
    input_path: str,
    output_path: str,
    start_time: float | None = None,
    end_time: float | None = None,
    language: str = "he",
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
    genre: str | None = None,
    **kwargs  # Accept additional unused kwargs for backward compatibility
) -> tuple[bool, str]:
    """
    Cut or re-export an audio file between optional start and end times,
    and optionally embed metadata (title, artist, album, genre).

    Args:
        input_path: Path to the input audio file
        output_path: Path where to save the output file
        start_time: Start time in seconds (None for beginning)
        end_time: End time in seconds (None for end)
        language: Language for error messages
        title: Audio title metadata
        artist: Artist metadata
        album: Album metadata
        genre: Genre metadata
        **kwargs: Additional unused parameters for backward compatibility

    Returns:
        Tuple of (success: bool, message: str)
    """
    msg = Messages(language=language)

    try:
        # Load audio file
        audio = AudioSegment.from_file(input_path)
        duration_s = len(audio) / 1000.0

        # Default full range if not specified
        start_time = float(start_time) if start_time is not None else 0.0
        end_time = float(end_time) if end_time is not None else duration_s

        # --- Validation ---
        if start_time < 0 or end_time < 0:
            error_msg = msg.error_negative_time
            return False, error_msg

        if start_time >= end_time:
            error_msg = msg.error_invalid_order
            return False, error_msg

        if start_time > duration_s:
            error_msg = msg.error_start_beyond_length
            return False, error_msg

        if end_time > duration_s:
            end_time = duration_s  # truncate if needed

        # --- Perform cut ---
        start_ms = int(start_time * 1000)
        end_ms = int(end_time * 1000)
        cut_segment = audio[start_ms:end_ms]

        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

        # --- Prepare metadata tags ---
        tags = {}
        if title:
            tags["title"] = str(title)
        if artist:
            tags["artist"] = str(artist)
        if album:
            tags["album"] = str(album)
        if genre:
            tags["genre"] = str(genre)

        # --- Determine export format from output path ---
        file_ext = os.path.splitext(output_path)[1].lower()
        if not file_ext:
            output_path += ".mp3"
            file_format = "mp3"
        else:
            file_format = file_ext[1:]  # Remove the dot

        # Export cut (or full) audio with metadata
        cut_segment.export(output_path, format=file_format, tags=tags or None)

        # --- Success ---
        if start_time == 0 and end_time >= duration_s * 0.99:  # Allow small floating point differences
            success_msg = msg.audio_saved_message
        else:
            success_msg = msg.audio_cut_success
        return True, success_msg

    except Exception as e:
        logger.error(f"Error processing audio {input_path}: {str(e)}", exc_info=True)
        error_msg = f"{msg.error_cut_failed}: {str(e)}"
        return False, error_msg


def validate_audio_filename(filename: str, language: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and sanitize an audio filename.
    
    Args:
        filename: The input filename to validate
        
    Returns:
        Tuple of (is_valid: bool, sanitized_name: Optional[str], error: Optional[str])
    """
    # Check if filename is empty
    messages = Messages(language=language)
    if not filename or not filename.strip():
        return False, None, messages.error_empty_filename
    
    # Convert to string in case a Path object is passed
    filename = str(filename)
    
    # Basic length check
    if len(filename) > 100:  # Common filesystem limit
        return False, None, messages.error_filename_too_long
    
    # Check for null bytes
    if '\x00' in filename:
        return False, None, messages.error_invalid_character
    
    # Check for path traversal attempts
    if any(part in ('.', '..') for part in Path(filename).parts):
        return False, None, messages.error_path_traversal
    
    # Get the base name to prevent directory traversal
    basename = os.path.basename(filename)
    if basename != filename:
        return False, None, messages.error_directory_traversal
    
    # Split into name and extension
    name, ext = os.path.splitext(basename)
    
    # Check for valid audio extensions
    valid_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma'}
    ext_lower = ext.lower()
    if ext_lower not in valid_extensions:
        valid_exts = ', '.join(valid_extensions)
        return False, None, messages.error_invalid_audio_format.format(valid_exts)
    
    # Sanitize the filename (remove or replace problematic characters)
    # Allow alphanumeric, spaces, underscores, hyphens, and dots
    sanitized = re.sub(r'[^\w\s\-_.]', '_', name).strip()
    if not sanitized:  # If after sanitization we have nothing left
        return False, None, messages.error_invalid_filename
    
    # Reconstruct the full filename with sanitized name and original extension
    sanitized_filename = f"{sanitized}{ext_lower}"
    
    # Final check for any remaining path separators
    if os.path.sep in sanitized_filename or (os.path.altsep and os.path.altsep in sanitized_filename):
        return False, None, messages.error_invalid_filename
    
    return True, sanitized_filename, None