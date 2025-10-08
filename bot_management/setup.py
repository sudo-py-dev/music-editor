"""
Bot setup and initialization utilities.

This module provides functions for setting up and configuring the bot,
including owner configuration and related initialization tasks.
"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from tools.logger import logger
from tools.database import BotSettings
from tools.tools import is_valid_user_id


console = Console()


def setup_bot_owner() -> bool:
    """
    Configure the bot owner if not already set.

    Guides the user through the process of setting up
    the bot owner ID if it hasn't been configured yet.
    """
    bot_settings = BotSettings().get_settings()

    if bot_settings.owner_id:
        logger.info(f"Bot owner already configured with ID: {bot_settings.owner_id}")
        return True

    console.print(Panel.fit(
        Text("BOT OWNER SETUP", justify="center", style="bold cyan"),
        border_style="bright_blue",
        padding=(1, 2)
    ))

    console.print(
        "[yellow]No owner ID is currently configured for the bot.[/]\n"
        "The owner will have full control over the bot's administrative functions.\n"
    )

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        user_input = Prompt.ask(
            f"Please enter the owner's Telegram user ID "
            f"(attempt {attempt}/{max_attempts}, press [bold]Enter[/] to skip)",
            default="",
            show_default=False,
        ).strip()

        if not user_input:
            logger.warning("Owner ID setup was skipped.")
            console.print("[yellow]⚠️ Owner setup skipped.[/]")
            return False

        if not (user_input.isdigit() and is_valid_user_id(user_input)):
            logger.error("❌ Invalid user ID. Please enter a valid numeric Telegram user ID.")
            console.print("[red]❌ Invalid user ID. Please enter a valid numeric Telegram user ID.[/]")
            continue

        try:
            owner_id = int(user_input)
            BotSettings().update_settings(owner_id=owner_id)
            logger.info(f"✅ Successfully set owner ID to: {owner_id}")
            console.print(f"[green]✅ Successfully set owner ID to:[/] [bold]{owner_id}[/]")
            return True
        except Exception as exc:
            logger.error(f"❌ Error setting owner ID: {exc!r}")
            console.print(f"[red]❌ Error setting owner ID: {exc!r}[/]")

    logger.warning("❌ Failed to set owner ID after maximum retries.")
    console.print("[red]❌ Failed to set owner ID after maximum retries.[/]")
    return False
