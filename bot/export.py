"""Export health data for a doctor as CSV and PDF."""

import csv
import io
import os
from fpdf import FPDF

from bot.database import get_pressure_history, get_glucose_history


def export_csv(user_id: int, days: int = 90) -> bytes | None:
    """Export pressure and glucose data as CSV bytes."""
    pressures = get_pressure_history(user_id, days)
    glucoses = get_glucose_history(user_id, days)

    if not pressures and not glucoses:
        return None

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Тип", "Дата/Время", "Значение 1", "Значение 2", "Пульс"])

    for r in pressures:
        writer.writerow([
            "Давление",
            r.timestamp.strftime("%d.%m.%Y %H:%M"),
            r.systolic,
            r.diastolic,
            r.pulse or "",
        ])

    for r in glucoses:
        writer.writerow([
            "Глюкоза",
            r.timestamp.strftime("%d.%m.%Y %H:%M"),
            r.value,
            "",
            "",
        ])

    return output.getvalue().encode("utf-8-sig")


def export_pdf(user_id: int, days: int = 90) -> bytes | None:
    """Export pressure and glucose data as PDF bytes."""
    pressures = get_pressure_history(user_id, days)
    glucoses = get_glucose_history(user_id, days)

    if not pressures and not glucoses:
        return None

    font_dir = os.path.join(os.path.dirname(__file__), "fonts")
    pdf = FPDF()
    pdf.add_page()

    # Try to load a Unicode font; fall back to built-in if unavailable
    font_path = os.path.join(font_dir, "DejaVuSans.ttf")
    if os.path.exists(font_path):
        pdf.add_font("DejaVu", "", font_path, uni=True)
        pdf.set_font("DejaVu", size=14)
    else:
        pdf.add_font("DejaVu", "", os.path.join(font_dir, "DejaVuSans.ttf"), uni=True)
        pdf.set_font("DejaVu", size=14)

    pdf.cell(0, 10, "Дневник здоровья — отчёт для врача", ln=True, align="C")
    pdf.ln(5)

    if pressures:
        pdf.set_font_size(12)
        pdf.cell(0, 8, "Артериальное давление", ln=True)
        pdf.set_font_size(10)

        pdf.cell(50, 7, "Дата", border=1)
        pdf.cell(40, 7, "Сист.", border=1)
        pdf.cell(40, 7, "Диаст.", border=1)
        pdf.cell(40, 7, "Пульс", border=1)
        pdf.ln()

        for r in pressures:
            pdf.cell(50, 7, r.timestamp.strftime("%d.%m.%Y %H:%M"), border=1)
            pdf.cell(40, 7, str(r.systolic), border=1)
            pdf.cell(40, 7, str(r.diastolic), border=1)
            pdf.cell(40, 7, str(r.pulse) if r.pulse else "-", border=1)
            pdf.ln()

        pdf.ln(5)

    if glucoses:
        pdf.set_font_size(12)
        pdf.cell(0, 8, "Глюкоза крови", ln=True)
        pdf.set_font_size(10)

        pdf.cell(80, 7, "Дата", border=1)
        pdf.cell(60, 7, "Значение (ммоль/л)", border=1)
        pdf.ln()

        for r in glucoses:
            pdf.cell(80, 7, r.timestamp.strftime("%d.%m.%Y %H:%M"), border=1)
            pdf.cell(60, 7, f"{r.value:.1f}", border=1)
            pdf.ln()

    return bytes(pdf.output())
