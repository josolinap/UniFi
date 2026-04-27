"""Thin Telegram notification helper (no polling — fire-and-forget)."""

import httpx
import logging

from .config import get_settings

logger = logging.getLogger(__name__)


async def send_telegram(text: str, parse_mode: str = "HTML") -> None:
    """Send a message to the owner's Telegram chat."""
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_owner_chat_id:
        logger.warning("Telegram credentials not set — skipping notification.")
        return

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_owner_chat_id,
        "text": text[:4096],
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")
