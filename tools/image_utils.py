import os
import tempfile
from typing import Tuple, Optional
from PIL import Image
from tools.logger import logger
from pyrogram import Client


async def download_and_process_image(client: Client, file_id: str, max_size: Tuple[int, int] = (500, 500), quality: int = 85) -> Optional[str]:
    """
    Download and process an image from Telegram.
    
    Args:
        client: Pyrogram client instance
        file_id: Telegram file ID of the image
        max_size: Maximum (width, height) for the output image
        quality: JPEG quality (1-100)
        
    Returns:
        Path to the processed temporary image file, or None if processing failed
    """
    temp_file = None
    original_path = None
    
    try:
        # Download the original image
        original_path = await client.download_media(file_id)
        if not original_path or not os.path.exists(original_path):
            logger.error(f"Failed to download image with file_id: {file_id}")
            return None

        # Create a temporary file for the processed image
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        temp_path = temp_file.name
        temp_file.close()  # Close the file so PIL can write to it
        
        # Process the image
        with Image.open(original_path) as img:
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Resize while maintaining aspect ratio
            img.thumbnail(max_size, Image.LANCZOS)
            
            # Save with specified quality
            img.save(temp_path, format='JPEG', quality=quality, optimize=True)
            
        logger.debug(f"Processed image saved to {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Error processing image {file_id}: {e}", exc_info=True)
        # Clean up in case of error
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.error(f"Error cleaning up temp file {temp_file.name}: {e}")
        return None
        
    finally:
        # Always clean up the original downloaded file
        if original_path and os.path.exists(original_path):
            try:
                os.unlink(original_path)
            except Exception as e:
                logger.error(f"Error cleaning up original file {original_path}: {e}")


def cleanup_temp_file(file_path: str) -> bool:
    """Safely remove a temporary file."""
    if not file_path or not os.path.exists(file_path):
        return False
    try:
        os.unlink(file_path)
        return True
    except Exception as e:
        logger.error(f"Error removing temp file {file_path}: {e}")
        return False
