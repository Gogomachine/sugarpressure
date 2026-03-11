import io
import logging
import os
import tempfile
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from database import init_db, add_pressure, add_glucose, get_pressure_history, get_glucose_history, get_all_history
from parser import parse_message, PressureReading, GlucoseReading
from speech import transcribe, ogg_to_wav
from charts import pressure_chart, glucose_chart
from export import export_csv, export_pdf

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📊 Давление — график", "📊 Глюкоза — график"],
        ["📋 История", "📤 Выгрузка для врача"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для трекинга давления и сахара.\n\n"
        "Отправьте мне голосовое или текстовое сообщение:\n"
        '• "Давление 120 на 80" или "120-80"\n'
        '• "Глюкоза 5.4" или "Сахар 5,4"\n\n'
        "Команды:\n"
        "/history — последние записи\n"
        "/pressure — график давления\n"
        "/glucose — график глюкозы\n"
        "/export — выгрузка для врача (PDF + CSV)",
        reply_markup=MAIN_KEYBOARD,
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download voice message, transcribe, and parse."""
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        ogg_path = os.path.join(tmpdir, "voice.ogg")
        file = await voice.get_file()
        await file.download_to_drive(ogg_path)

        wav_path = ogg_to_wav(ogg_path)
        text = transcribe(wav_path)

    logger.info("Transcribed: %s", text)
    await update.message.reply_text(f'Распознано: "{text}"')
    await _process_text(update, text)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages."""
    text = update.message.text

    # Handle keyboard buttons
    if text == "📊 Давление — график":
        return await cmd_pressure(update, context)
    if text == "📊 Глюкоза — график":
        return await cmd_glucose(update, context)
    if text == "📋 История":
        return await cmd_history(update, context)
    if text == "📤 Выгрузка для врача":
        return await cmd_export(update, context)

    await _process_text(update, text)


async def _process_text(update: Update, text: str):
    """Parse text and save the measurement."""
    result = parse_message(text)
    user_id = update.effective_user.id

    if isinstance(result, PressureReading):
        add_pressure(user_id, result.systolic, result.diastolic)
        await update.message.reply_text(
            f"✅ Записано давление: {result.systolic}/{result.diastolic} мм рт. ст.",
            reply_markup=MAIN_KEYBOARD,
        )
    elif isinstance(result, GlucoseReading):
        add_glucose(user_id, result.value)
        await update.message.reply_text(
            f"✅ Записана глюкоза: {result.value} ммоль/л",
            reply_markup=MAIN_KEYBOARD,
        )
    else:
        await update.message.reply_text(
            "Не удалось распознать данные. Попробуйте:\n"
            '• "Давление 120 на 80"\n'
            '• "Глюкоза 5.4"',
            reply_markup=MAIN_KEYBOARD,
        )


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show last 30 days of records."""
    user_id = update.effective_user.id
    history = get_all_history(user_id, days=30)

    if not history:
        await update.message.reply_text("Нет записей за последние 30 дней.")
        return

    lines = []
    for r in history[-20:]:  # last 20 entries
        dt = r["recorded_at"][:16].replace("T", " ")
        if r["type"] == "pressure":
            lines.append(f"🩸 {dt} — {r['systolic']}/{r['diastolic']} мм рт.ст.")
        else:
            lines.append(f"🍬 {dt} — {r['glucose']} ммоль/л")

    text = "📋 Последние записи:\n\n" + "\n".join(lines)
    if len(history) > 20:
        text += f"\n\n... и ещё {len(history) - 20} записей"
    await update.message.reply_text(text, reply_markup=MAIN_KEYBOARD)


async def cmd_pressure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a pressure chart."""
    user_id = update.effective_user.id
    history = get_pressure_history(user_id, days=30)

    if len(history) < 2:
        await update.message.reply_text("Недостаточно данных для графика (нужно минимум 2 записи).")
        return

    png = pressure_chart(history)
    await update.message.reply_photo(
        photo=io.BytesIO(png),
        caption="📊 График давления за 30 дней",
        reply_markup=MAIN_KEYBOARD,
    )


async def cmd_glucose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a glucose chart."""
    user_id = update.effective_user.id
    history = get_glucose_history(user_id, days=30)

    if len(history) < 2:
        await update.message.reply_text("Недостаточно данных для графика (нужно минимум 2 записи).")
        return

    png = glucose_chart(history)
    await update.message.reply_photo(
        photo=io.BytesIO(png),
        caption="📊 График глюкозы за 30 дней",
        reply_markup=MAIN_KEYBOARD,
    )


async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export data as PDF and CSV for a doctor."""
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
    history = get_all_history(user_id, days=90)

    if not history:
        await update.message.reply_text("Нет записей за последние 90 дней.")
        return

    csv_bytes = export_csv(history)
    pdf_bytes = export_pdf(history, user_name=user_name)

    await update.message.reply_document(
        document=io.BytesIO(csv_bytes),
        filename="health_diary.csv",
        caption="📋 Дневник здоровья (CSV)",
    )
    await update.message.reply_document(
        document=io.BytesIO(pdf_bytes),
        filename="health_diary.pdf",
        caption="📋 Дневник здоровья (PDF) — для врача",
        reply_markup=MAIN_KEYBOARD,
    )


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Set TELEGRAM_BOT_TOKEN environment variable. "
            "Get a token from @BotFather in Telegram."
        )

    init_db()

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("pressure", cmd_pressure))
    app.add_handler(CommandHandler("glucose", cmd_glucose))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
