"""
Enhanced logging configuration for the Telegram Bot with Rich formatting.

Features:
- Colorful console output with emojis
- Size-based file rotation
- Custom log levels (SUCCESS)
- Contextual logging
- Performance optimizations
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, Union

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Load environment variables
load_dotenv()

# Custom log levels
SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")

# Custom color theme for Rich with vibrant colors
CUSTOM_THEME = Theme({
    # Log levels
    "debug": "dim cyan",
    "info": "bold #34b7eb",  # Bright blue
    "success": "bold #2ecc71",  # Emerald green
    "warning": "bold #f39c12",  # Orange
    "error": "bold #e74c3c",  # Red
    "critical": "bold #9b59b6 on #ffeb3b",  # Purple with yellow background
    
    # UI elements
    "time": "#7f8c8d",  # Gray
    "path": "#3498db",  # Light blue
    "module": "#9b59b6",  # Purple
    "message": "#ecf0f1",  # Off-white
    "bracket": "#95a5a6",  # Light gray
    "thread": "#1abc9c",  # Turquoise
    "process": "#e67e22"  # Carrot orange
})

# Log directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class ContextFilter(logging.Filter):
    """Add contextual information to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add process and thread info
        record.process_name = f"{record.process}"
        record.thread_name = f"{record.threadName}"
        return True


class RichLogFormatter(logging.Formatter):
    """Custom formatter for Rich console output with emojis and colors."""
    
    LEVEL_EMOJIS: ClassVar[Dict[int, str]] = {
        logging.DEBUG: "🐛",
        logging.INFO: "ℹ️",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "🔥",
        SUCCESS: "✅"
    }
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, style: str = "%"):
        super().__init__(fmt, datefmt, style)
        self.console = Console(theme=CUSTOM_THEME, width=120)
    
    def format(self, record: logging.LogRecord) -> str:
        level_emoji = self.LEVEL_EMOJIS.get(record.levelno, "📝")
        level_name = record.levelname.lower()
        
        # Format the message with proper color handling
        message = record.msg % record.args if record.args and isinstance(record.msg, str) else record.msg
        
        # Add context if available
        context = getattr(record, 'context', {})
        if context:
            context_str = " ".join(f"[dim][{k}=[/][b]{v}[/][/dim]]" for k, v in context.items())
            message = f"{message} {context_str}"
        
        # Format the main message with proper color
        message = f"[message]{message}[/]"
        
        # Add source location if debug level
        if record.levelno <= logging.DEBUG:
            path = f"{record.pathname.split('/')[-1]}:{record.lineno}"
            message = f"[path]{path}[/] {message}"
        
        # Format timestamp with milliseconds
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        
        # Get level style
        if record.levelno >= logging.CRITICAL:
            level_style = "critical"
        elif record.levelno >= logging.ERROR:
            level_style = "error"
        elif record.levelno >= logging.WARNING:
            level_style = "warning"
        elif record.levelno == SUCCESS:
            level_style = "success"
        elif record.levelno >= logging.INFO:
            level_style = "info"
        else:
            level_style = "debug"
        
        # Format the final output with proper colors and alignment
        return (
            f"[time][dim]{timestamp}[/][/] "
            f"{level_emoji} "
            f"[{level_style}][b]{level_name.upper():^8}[/][/] "
            f"[module]{record.name}[/] {message}"
        )


def setup_logger(
    name: str = "telegram_bot",
    log_level: Optional[Union[str, int]] = None,
    log_file: Optional[Union[str, Path]] = None
) -> logging.Logger:
    """
    Set up and configure a logger with Rich console output and file logging.

    Args:
        name: Name of the logger
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) or level name as string
        log_file: Path to log file. If None, uses LOG_FILE env var or 'logs/bot.log'

    Returns:
        Configured logger instance with Rich formatting
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if logger is already configured
    if logger.handlers:
        return logger

    # Set log level
    if log_level is None:
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
    elif isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), logging.INFO)

    logger.setLevel(log_level)

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(process_name)s/%(thread_name)s - %(filename)s:%(lineno)d - %(message)s'
    )

    # File handler with rotation
    if log_file is None:
        log_file = Path(os.getenv("LOG_FILE", LOG_DIR / "bot.log"))
    
    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # File handler with size-based rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB per file
        backupCount=7,  # Keep up to 7 rotated files
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(ContextFilter())

    # Rich console handler
    rich_handler = RichHandler(
        console=Console(theme=CUSTOM_THEME, stderr=sys.stderr),
        show_time=False,  # We'll handle time in our formatter
        show_path=True,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        tracebacks_extra_lines=3,
        tracebacks_theme="monokai"
    )
    rich_handler.setLevel(log_level)
    rich_handler.setFormatter(RichLogFormatter())

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(rich_handler)

    # Disable propagation to avoid duplicate logs
    logger.propagate = False

    # Add custom log methods
    def success(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a success message (level SUCCESS)."""
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, msg, args, **kwargs)
    
    def with_context(self, **context: Any) -> logging.LoggerAdapter:
        """Add context to log messages."""
        return logging.LoggerAdapter(self, {'context': context})
    
    def log_performance(self, operation: str, start_time: float, **context: Any) -> None:
        """Log performance metrics for an operation."""
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        self.info(f"{operation} completed in {duration:.2f}ms", extra={'context': context})

    # Add type hints for the logger class methods
    logging.Logger.success = success  # type: ignore[method-assign]
    logging.Logger.with_context = with_context  # type: ignore[method-assign]
    logging.Logger.log_performance = log_performance  # type: ignore[method-assign]
    
    # Add SUCCESS level to the logger instance
    logger.success = success.__get__(logger, logging.Logger)
    logger.with_context = with_context.__get__(logger, logging.Logger)
    logger.log_performance = log_performance.__get__(logger, logging.Logger)
    
    # Ensure the logger is returned
    return logger


# Global logger instance
logger = setup_logger()

# Add some useful aliases
log = logger