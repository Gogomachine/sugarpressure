"""Export health data for a doctor as CSV and PDF."""

import csv
import io
import os
from datetime import timedelta
from fpdf import FPDF

from bot.database import get_pressure_history, get_pulse_history, get_glucose_history


# Normal ranges for color coding
SYSTOLIC_MAX = 130
DIASTOLIC_MAX = 85
PULSE_MIN = 60
PULSE_MAX = 90
GLUCOSE_MAX = 6.1

# Colors (R, G, B)
COLOR_NORMAL = (200, 240, 200)      # light green
COLOR_ELEVATED = (255, 200, 200)    # light red
COLOR_HEADER = (255, 255, 255)      # white (no fill for headers)


def export_csv(user_id: int, days: int = 90) -> bytes | None:
    """Export pressure, pulse and glucose data as CSV bytes."""
    pressures = get_pressure_history(user_id, days)
    pulses = get_pulse_history(user_id, days)
    glucoses = get_glucose_history(user_id, days)

    if not pressures and not pulses and not glucoses:
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

    for r in pulses:
        writer.writerow([
            "Пульс",
            r.timestamp.strftime("%d.%m.%Y %H:%M"),
            r.value,
            "",
            "",
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
    """Export pressure, pulse and glucose data as PDF bytes."""
    pressures = get_pressure_history(user_id, days)
    pulses = get_pulse_history(user_id, days)
    glucoses = get_glucose_history(user_id, days)

    if not pressures and not pulses and not glucoses:
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

    if pressures or pulses:
        # Merge pulse readings into pressure rows by matching timestamps (within 5 min)
        merged = []
        used_pulse_ids = set()

        for r in pressures:
            pulse_val = r.pulse
            if not pulse_val:
                # Try to find a standalone pulse reading close in time
                for p in pulses:
                    if p.id in used_pulse_ids:
                        continue
                    if abs((p.timestamp - r.timestamp).total_seconds()) <= 300:
                        pulse_val = p.value
                        used_pulse_ids.add(p.id)
                        break
            else:
                # Mark matching standalone pulse as used to avoid duplicates
                for p in pulses:
                    if p.id in used_pulse_ids:
                        continue
                    if abs((p.timestamp - r.timestamp).total_seconds()) <= 300:
                        used_pulse_ids.add(p.id)
                        break
            merged.append({
                "ts": r.timestamp,
                "sys": r.systolic,
                "dia": r.diastolic,
                "pulse": pulse_val,
            })

        # Add remaining standalone pulse readings as pulse-only rows
        for p in pulses:
            if p.id not in used_pulse_ids:
                merged.append({
                    "ts": p.timestamp,
                    "sys": None,
                    "dia": None,
                    "pulse": p.value,
                })

        merged.sort(key=lambda x: x["ts"])

        pdf.set_font_size(12)
        pdf.cell(0, 8, "Артериальное давление и пульс", ln=True)
        pdf.set_font_size(10)

        pdf.cell(50, 7, "Дата", border=1)
        pdf.cell(40, 7, "Сист.", border=1)
        pdf.cell(40, 7, "Диаст.", border=1)
        pdf.cell(40, 7, "Пульс", border=1)
        pdf.ln()

        for row in merged:
            pdf.cell(50, 7, row["ts"].strftime("%d.%m.%Y %H:%M"), border=1)

            # Systolic
            if row["sys"] is not None:
                color = COLOR_ELEVATED if row["sys"] > SYSTOLIC_MAX else COLOR_NORMAL
                pdf.set_fill_color(*color)
                pdf.cell(40, 7, str(row["sys"]), border=1, fill=True)
            else:
                pdf.cell(40, 7, "-", border=1)

            # Diastolic
            if row["dia"] is not None:
                color = COLOR_ELEVATED if row["dia"] > DIASTOLIC_MAX else COLOR_NORMAL
                pdf.set_fill_color(*color)
                pdf.cell(40, 7, str(row["dia"]), border=1, fill=True)
            else:
                pdf.cell(40, 7, "-", border=1)

            # Pulse
            if row["pulse"] is not None:
                color = COLOR_ELEVATED if row["pulse"] < PULSE_MIN or row["pulse"] > PULSE_MAX else COLOR_NORMAL
                pdf.set_fill_color(*color)
                pdf.cell(40, 7, str(row["pulse"]), border=1, fill=True)
            else:
                pdf.cell(40, 7, "-", border=1)

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
            color = COLOR_ELEVATED if r.value > GLUCOSE_MAX else COLOR_NORMAL
            pdf.set_fill_color(*color)
            pdf.cell(60, 7, f"{r.value:.1f}", border=1, fill=True)
            pdf.ln()

    return bytes(pdf.output())
