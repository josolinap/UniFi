"""Telegram bot for UniFi Network Monitor with NVIDIA LLM."""

import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from .config import get_settings, validate_required
from .llm_client import NIMClient
from .unifi_client import get_network_summary

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

application: Optional[Application] = None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    welcome = """UniFi Network Monitor Bot

Commands:
/status - Network status
/ask - Ask about network
/chat - Chat with AI
/help - Show this help

Just send a message to chat with AI!"""
    await update.effective_message.reply_text(welcome)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await start_command(update, context)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    try:
        summary = get_network_summary()
        await update.effective_message.reply_text(summary, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.effective_message.reply_text(f"Error: {str(e)}")


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ask command."""
    msg = update.effective_message.text
    if msg == "/ask":
        await update.effective_message.reply_text("Usage: /ask [question]\n\nExample: /ask What devices are online?")
        return

    question = msg[5:].strip()
    if not question:
        await update.effective_message.reply_text("Please provide a question.")
        return

    await update.effective_message.reply_text("Thinking...")

    try:
        from .unifi_client import UniFiClient
        with UniFiClient() as client:
            network_data = client.get_all_sites_data()
        with NIMClient() as llm:
            response = llm.ask_about_network(question, network_data)
        await update.effective_message.reply_text(response.content)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.effective_message.reply_text(f"Error: {str(e)}")


async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chat command."""
    msg = update.effective_message.text
    if msg == "/chat":
        await update.effective_message.reply_text("Usage: /chat [message]\n\nExample: /chat Write a poem")
        return

    user_msg = msg[6:].strip()
    if not user_msg:
        await update.effective_message.reply_text("Please provide a message.")
        return

    await update.effective_message.reply_text("Thinking...")

    try:
        with NIMClient() as llm:
            response = llm.chat(user_msg)
        await update.effective_message.reply_text(response.content)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.effective_message.reply_text(f"Error: {str(e)}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages."""
    msg = update.effective_message.text
    if msg.startswith("/"):
        return

    await update.effective_message.reply_text("Thinking...")

    try:
        with NIMClient() as llm:
            response = llm.chat(msg)
        await update.effective_message.reply_text(response.content)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.effective_message.reply_text(f"Error: {str(e)}")


def create_bot() -> Application:
    """Create and configure the Telegram bot."""
    settings = get_settings()

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("chat", chat_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app


async def start_bot() -> None:
    """Start the bot."""
    app = create_bot()
    await app.run_polling(drop_pending_updates=True)
    logger.info("Bot stopped.")


def run_bot() -> None:
    """Run the bot."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(start_bot())


if __name__ == "__main__":
    run_bot()