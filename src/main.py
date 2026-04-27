"""Main entry point for n8n Workflow Manager."""

import argparse
import asyncio
import logging
import sys

from .config import get_settings, validate_required
from .telegram_bot import run_bot
from .n8n_client import get_n8n_summary

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def check_env() -> bool:
    """Check that all required environment variables are set."""
    missing = validate_required()
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please set the following environment variables:")
        logger.error("  TELEGRAM_BOT_TOKEN")
        logger.error("  TELEGRAM_OWNER_CHAT_ID")
        logger.error("  N8N_API_KEY")
        logger.error("  N8N_BASE_URL")
        logger.error("  NVIDIA_API_KEY")
        return False
    return True


async def run_status_check() -> None:
    """Run a one-time status check and print the result."""
    try:
        summary = get_n8n_summary()
        print(summary)
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="n8n Workflow Manager")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["bot", "status"],
        default="bot",
        help="Mode to run: 'bot' for Telegram bot, 'status' for one-time status check",
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Check environment variables and exit",
    )

    args = parser.parse_args()

    if args.check_env:
        if check_env():
            logger.info("All required environment variables are set.")
            sys.exit(0)
        else:
            sys.exit(1)

    if args.mode == "status":
        asyncio.run(run_status_check())
    elif args.mode == "bot":
        if not check_env():
            logger.warning("Proceeding anyway with missing variables...")
        run_bot()


if __name__ == "__main__":
    main()