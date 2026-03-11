"""Entry point for the Health Diary Telegram bot."""

import logging
import os

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot.handlers import (
    cmd_start,
    cmd_help,
    cmd_history,
    cmd_chart,
    cmd_export,
    handle_text,
    handle_voice,
    handle_delete_callback,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN not set. "
            "Copy .env.example to .env and fill in your bot token."
        )

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("chart", cmd_chart))
    app.add_handler(CommandHandler("export", cmd_export))

    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_delete_callback, pattern=r"^del:"))

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
