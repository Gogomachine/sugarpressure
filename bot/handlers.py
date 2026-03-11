"""Telegram bot command and message handlers."""

import logging
import os
import tempfile

from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.database import add_pressure, add_glucose, delete_reading, delete_all_readings, get_pressure_history, get_glucose_history
from bot.parser import parse_message, PressureResult, GlucoseResult
from bot.voice import transcribe_voice
from bot.charts import generate_pressure_chart, generate_glucose_chart
from bot.export import export_csv, export_pdf

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот-дневник здоровья.\n\n"
        "Отправьте мне голосовое или текстовое сообщение:\n"
        '  • "Давление 120/80"\n'
        '  • "Давление 130 на 85 пульс 72"\n'
        '  • "Глюкоза 5.4"\n'
        '  • "Сахар 6,2"\n\n'
        "Команды:\n"
        "/history — последние записи\n"
        "/chart — графики за 30 дней\n"
        "/export — выгрузка для врача (CSV + PDF)\n"
        "/help — справка"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Как пользоваться:\n\n"
        "1. Отправьте голосовое сообщение, например:\n"
        '   «Давление сто двадцать на восемьдесят»\n'
        '   «Глюкоза пять и четыре»\n\n'
        "2. Или напишите текстом:\n"
        '   «Давление 120/80»\n'
        '   «Сахар 5.4»\n\n'
        "Команды:\n"
        "/history [дней] — история записей (по умолчанию 30)\n"
        "/chart [дней] — графики (по умолчанию 30)\n"
        "/export [дней] — выгрузка CSV + PDF (по умолчанию 90)\n"
    )


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = 30
    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            pass

    user_id = update.effective_user.id
    pressures = get_pressure_history(user_id, days)
    glucoses = get_glucose_history(user_id, days)

    if not pressures and not glucoses:
        await update.message.reply_text(f"Нет записей за последние {days} дней.")
        return

    lines = [f"Записи за последние {days} дн.:\n"]

    if pressures:
        lines.append("Давление:")
        for r in pressures[-20:]:
            pulse_str = f", пульс {r.pulse}" if r.pulse else ""
            lines.append(
                f"  {r.timestamp.strftime('%d.%m %H:%M')} — {r.systolic}/{r.diastolic}{pulse_str}"
            )
        if len(pressures) > 20:
            lines.append(f"  ... и ещё {len(pressures) - 20} записей")

    if glucoses:
        lines.append("\nГлюкоза:")
        for r in glucoses[-20:]:
            lines.append(
                f"  {r.timestamp.strftime('%d.%m %H:%M')} — {r.value:.1f} ммоль/л"
            )
        if len(glucoses) > 20:
            lines.append(f"  ... и ещё {len(glucoses) - 20} записей")

    await update.message.reply_text("\n".join(lines))


async def cmd_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = 30
    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            pass

    user_id = update.effective_user.id
    sent = False

    pressure_png = generate_pressure_chart(user_id, days)
    if pressure_png:
        await update.message.reply_photo(photo=pressure_png, caption="Артериальное давление")
        sent = True

    glucose_png = generate_glucose_chart(user_id, days)
    if glucose_png:
        await update.message.reply_photo(photo=glucose_png, caption="Глюкоза крови")
        sent = True

    if not sent:
        await update.message.reply_text(f"Нет данных для графиков за последние {days} дней.")


async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = 90
    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            pass

    user_id = update.effective_user.id

    csv_data = export_csv(user_id, days)
    pdf_data = export_pdf(user_id, days)

    if not csv_data and not pdf_data:
        await update.message.reply_text(f"Нет данных для выгрузки за последние {days} дней.")
        return

    if csv_data:
        await update.message.reply_document(
            document=csv_data,
            filename=f"health_report_{days}d.csv",
            caption="Данные в формате CSV",
        )

    if pdf_data:
        await update.message.reply_document(
            document=pdf_data,
            filename=f"health_report_{days}d.pdf",
            caption="Отчёт для врача (PDF)",
        )


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Да, удалить всё", callback_data="clear:confirm"),
        InlineKeyboardButton("Отмена", callback_data="clear:cancel"),
    ]])
    await update.message.reply_text(
        "Вы уверены, что хотите удалить ВСЕ свои записи?\n"
        "Это действие необратимо.",
        reply_markup=keyboard,
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    text = update.message.text
    if not text:
        return

    result = parse_message(text)
    if result is None:
        await update.message.reply_text(
            "Не удалось распознать данные.\n"
            'Попробуйте: "Давление 120/80" или "Глюкоза 5.4"'
        )
        return

    await _save_result(update, result)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice messages — download, transcribe, parse."""
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    await update.message.reply_text("Распознаю голосовое сообщение...")

    file = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await file.download_to_drive(tmp_path)
        text = await transcribe_voice(tmp_path)
    finally:
        os.unlink(tmp_path)

    logger.info("Transcribed voice from user %s: %s", update.effective_user.id, text)
    await update.message.reply_text(f'Распознано: "{text}"')

    result = parse_message(text)
    if result is None:
        await update.message.reply_text(
            "Не удалось извлечь данные из распознанного текста.\n"
            "Попробуйте сказать чётче, например:\n"
            '«Давление сто двадцать на восемьдесят» или «Глюкоза пять и четыре»'
        )
        return

    await _save_result(update, result)


async def _save_result(update: Update, result):
    """Save a parsed result to the database and confirm to the user."""
    user_id = update.effective_user.id

    if isinstance(result, PressureResult):
        reading = add_pressure(user_id, result.systolic, result.diastolic, result.pulse)
        pulse_str = f", пульс {result.pulse}" if result.pulse else ""
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🗑 Удалить", callback_data=f"del:pressure:{reading.id}")
        ]])
        await update.message.reply_text(
            f"Записано давление: {result.systolic}/{result.diastolic}{pulse_str}\n"
            f"({reading.timestamp.strftime('%d.%m.%Y %H:%M')})",
            reply_markup=keyboard,
        )
    elif isinstance(result, GlucoseResult):
        reading = add_glucose(user_id, result.value)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🗑 Удалить", callback_data=f"del:glucose:{reading.id}")
        ]])
        await update.message.reply_text(
            f"Записана глюкоза: {result.value:.1f} ммоль/л\n"
            f"({reading.timestamp.strftime('%d.%m.%Y %H:%M')})",
            reply_markup=keyboard,
        )


async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button press to delete a reading."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("del:"):
        return

    _, reading_type, reading_id_str = data.split(":")
    user_id = update.effective_user.id

    if delete_reading(user_id, reading_type, int(reading_id_str)):
        await query.edit_message_text("Запись удалена.")
    else:
        await query.edit_message_text("Запись не найдена (возможно, уже удалена).")


async def handle_clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation/cancellation of clearing all records."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]
    if action == "confirm":
        count = delete_all_readings(update.effective_user.id)
        await query.edit_message_text(f"Удалено записей: {count}.")
    else:
        await query.edit_message_text("Отменено.")
