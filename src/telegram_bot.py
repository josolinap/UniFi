"""Telegram bot with commands for network monitoring and LLM interactions."""

import asyncio
import logging
import os
import re
from typing import Any, Optional

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .actions import ActionManager, ActionResult, ActionType, get_available_actions_text
from .config import get_settings, validate_required
from .llm_client import NIMClient, format_network_for_llm
from .unifi_client import UniFiClient, get_network_summary

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

application: Optional[Application] = None
action_manager: Optional[ActionManager] = None

OWNER_CHAT_ID = ""
REGISTERED_USERS: set[str] = set()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "An error occurred. Please try again.",
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    settings = get_settings()
    chat_id = str(update.effective_chat.id)
    owner_chat_id = settings.telegram_owner_chat_id

    REGISTERED_USERS.add(chat_id)

    welcome_text = """<b>Welcome to UniFi Network Monitor!</b>

This bot provides:
• Network status monitoring
• Device and client management
• Interactive Q&A with AI

<b>Commands:</b>
/status - Network status overview
/devices - List all devices
/clients - List connected clients
/alerts - Recent network alerts
/sites - List all sites
/ask - Ask a question about your network
/chat - Chat with AI (any topic)
/actions - Available network actions
/help - Show this help message

<b>Note:</b> You need to be the owner to execute actions.
"""
    await update.effective_message.reply_text(welcome_text, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await start_command(update, context)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    try:
        summary = get_network_summary()
        await update.effective_message.reply_text(summary, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        await update.effective_message.reply_text(
            f"Error fetching status: {str(e)}",
        )


async def sites_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sites command."""
    try:
        with UniFiClient() as client:
            sites = client.get_sites()

        if not sites:
            await update.effective_message.reply_text("No sites found.")
            return

        lines = ["<b>Your Sites</b>", ""]
        for site in sites:
            name = site.get("name", "Unknown")
            site_id = site.get("id") or site.get("_id", "N/A")
            desc = site.get("desc", "")
            lines.append(f"• <b>{name}</b> ({site_id})")
            if desc:
                lines.append(f"  {desc}")

        await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error fetching sites: {e}")
        await update.effective_message.reply_text(f"Error: {str(e)}")


async def devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /devices command."""
    try:
        with UniFiClient() as client:
            sites = client.get_sites()

        if not sites:
            await update.effective_message.reply_text("No sites found.")
            return

        for site in sites:
            site_id = site.get("id") or site.get("_id")
            site_name = site.get("name", "Unknown")

            if not site_id:
                continue

            with UniFiClient() as client:
                devices = client.get_site_devices(site_id)

            if not devices:
                continue

            lines = [f"<b>Devices - {site_name}</b>", ""]
            for device in devices:
                state = "🟢 Online" if device.is_online() else "🔴 Offline"
                lines.append(f"{state} {device.name}")
                lines.append(f"   {device.model} | {device.ip_address}")
                if device.channel:
                    lines.append(f"   Channel {device.channel}")

            lines.append("")
            await update.effective_message.reply_text(
                "\n".join(lines), parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error fetching devices: {e}")
        await update.effective_message.reply_text(f"Error: {str(e)}")


async def clients_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clients command."""
    try:
        with UniFiClient() as client:
            sites = client.get_sites()

        if not sites:
            await update.effective_message.reply_text("No sites found.")
            return

        total_clients = 0
        for site in sites:
            site_id = site.get("id") or site.get("_id")
            site_name = site.get("name", "Unknown")

            if not site_id:
                continue

            with UniFiClient() as client:
                clients = client.get_site_clients(site_id)

            if not clients:
                continue

            total_clients += len(clients)
            lines = [f"<b>Clients - {site_name}</b>", ""]
            for client_data in clients[:15]:
                name = client_data.get("name", "Unknown")
                mac = client_data.get("mac", "N/A")
                ip = client_data.get("ip", "N/A")
                wired = client_data.get("is_wired", False)
                icon = "🔌" if wired else "📶"
                lines.append(f"{icon} {name}")
                lines.append(f"   {mac} | {ip}")

            if len(clients) > 15:
                lines.append(f"... and {len(clients) - 15} more")

            lines.append("")
            await update.effective_message.reply_text(
                "\n".join(lines), parse_mode="HTML"
            )

        if total_clients == 0:
            await update.effective_message.reply_text("No connected clients.")

    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        await update.effective_message.reply_text(f"Error: {str(e)}")


async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /alerts command."""
    try:
        with UniFiClient() as client:
            sites = client.get_sites()

        if not sites:
            await update.effective_message.reply_text("No sites found.")
            return

        has_alerts = False
        for site in sites:
            site_id = site.get("id") or site.get("_id")
            site_name = site.get("name", "Unknown")

            if not site_id:
                continue

            with UniFiClient() as client:
                alerts = client.get_site_alerts(site_id)

            if not alerts:
                continue

            has_alerts = True
            lines = [f"<b>Recent Alerts - {site_name}</b>", ""]
            for alert in alerts[:10]:
                msg = alert.get("msg", alert.get("key", "Unknown"))
                time = alert.get("time", "")
                lines.append(f"• {msg}")
                if time:
                    lines.append(f"  {time}")

            lines.append("")
            await update.effective_message.reply_text(
                "\n".join(lines), parse_mode="HTML"
            )

        if not has_alerts:
            await update.effective_message.reply_text("No recent alerts.")

    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        await update.effective_message.reply_text(f"Error: {str(e)}")


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ask command - ask LLM about network."""
    message_text = update.effective_message.text

    if message_text == "/ask":
        await update.effective_message.reply_text(
            "<b>Ask about your network</b>\n\n"
            "Usage: /ask [your question]\n\n"
            "Examples:\n"
            "/ask Which AP has the most clients?\n"
            "/ask Show me offline devices\n"
            "/ask What is the total bandwidth?",
            parse_mode="HTML",
        )
        return

    question = message_text[5:].strip()
    if not question:
        await update.effective_message.reply_text("Please provide a question.")
        return

    await update.effective_message.reply_text("Thinking...", parse_mode="HTML")

    try:
        with UniFiClient() as client:
            network_data = client.get_all_sites_data()

        with NIMClient() as llm:
            response = llm.ask_about_network(question, network_data)

        await update.effective_message.reply_text(response.content)
    except Exception as e:
        logger.error(f"Error in ask command: {e}")
        await update.effective_message.reply_text(f"Error: {str(e)}")


async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chat command - general chat with LLM."""
    message_text = update.effective_message.text

    if message_text == "/chat":
        await update.effective_message.reply_text(
            "<b>Chat with AI</b>\n\n"
            "Usage: /chat [your message]\n\n"
            "Use this for general conversation or tasks.\n"
            "Example: /chat write a poem about networking",
            parse_mode="HTML",
        )
        return

    user_message = message_text[6:].strip()
    if not user_message:
        await update.effective_message.reply_text("Please provide a message.")
        return

    await update.effective_message.reply_text("Thinking...", parse_mode="HTML")

    try:
        with NIMClient() as llm:
            response = llm.chat(user_message)

        await update.effective_message.reply_text(response.content)
    except Exception as e:
        logger.error(f"Error in chat command: {e}")
        await update.effective_message.reply_text(f"Error: {str(e)}")


async def post_init(app: Application) -> None:
    """Post-initialization hook."""
    global application
    application = app


def create_bot() -> Application:
    """Create and configure the Telegram bot."""
    settings = get_settings()

    global application, action_manager
    action_manager = ActionManager()

    bot_app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .build()
    )

    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CommandHandler("status", status_command))
    bot_app.add_handler(CommandHandler("sites", sites_command))
    bot_app.add_handler(CommandHandler("devices", devices_command))
    bot_app.add_handler(CommandHandler("clients", clients_command))
    bot_app.add_handler(CommandHandler("alerts", alerts_command))
    bot_app.add_handler(CommandHandler("ask", ask_command))
    bot_app.add_handler(CommandHandler("chat", chat_command))
    bot_app.add_handler(CommandHandler("actions", actions_command))
    bot_app.add_handler(CommandHandler("restart", restart_command))
    bot_app.add_handler(CommandHandler("block", block_command))
    bot_app.add_handler(CommandHandler("unblock", unblock_command))
    bot_app.add_handler(CallbackQueryHandler(callback_query_handler))
    bot_app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )

    bot_app.add_error_handler(error_handler)

    bot = bot_app
    application = bot
    return bot


async def start_bot() -> None:
    """Start the bot."""
    missing = validate_required()
    if missing:
        logger.warning(f"Missing required settings: {missing}")

    bot = create_bot()
    await bot.run_polling(drop_pending_updates=True)


def run_bot() -> None:
    """Run the bot synchronously."""
    asyncio.run(start_bot())


if __name__ == "__main__":
    run_bot()