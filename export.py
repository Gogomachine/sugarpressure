import csv
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def _register_font():
    """Try to register a Cyrillic-capable font."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    ]
    for path in font_paths:
        try:
            pdfmetrics.registerFont(TTFont("DejaVu", path))
            return "DejaVu"
        except Exception:
            continue
    return "Helvetica"


def export_csv(history: list[dict]) -> bytes:
    """Export measurement history as CSV bytes."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Дата", "Тип", "Систолическое", "Диастолическое", "Глюкоза"])

    for row in history:
        dt = row["recorded_at"]
        if row["type"] == "pressure":
            writer.writerow([dt, "Давление", row["systolic"], row["diastolic"], ""])
        else:
            writer.writerow([dt, "Глюкоза", "", "", row["glucose"]])

    return buf.getvalue().encode("utf-8-sig")


def export_pdf(history: list[dict], user_name: str = "") -> bytes:
    """Export measurement history as a PDF report for a doctor."""
    font_name = _register_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleRu", parent=styles["Title"], fontName=font_name, fontSize=16
    )
    normal_style = ParagraphStyle(
        "NormalRu", parent=styles["Normal"], fontName=font_name, fontSize=10
    )

    elements = []

    elements.append(Paragraph("Дневник здоровья", title_style))
    if user_name:
        elements.append(Paragraph(f"Пациент: {user_name}", normal_style))
    elements.append(Paragraph(
        f"Дата выгрузки: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style
    ))
    elements.append(Spacer(1, 10 * mm))

    # Pressure table
    pressure_data = [r for r in history if r["type"] == "pressure"]
    if pressure_data:
        elements.append(Paragraph("Артериальное давление", title_style))
        table_data = [["Дата", "Систолическое", "Диастолическое"]]
        for r in pressure_data:
            dt = datetime.fromisoformat(r["recorded_at"]).strftime("%d.%m.%Y %H:%M")
            table_data.append([dt, str(r["systolic"]), str(r["diastolic"])])
        table = Table(table_data, colWidths=[50 * mm, 40 * mm, 40 * mm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 8 * mm))

    # Glucose table
    glucose_data = [r for r in history if r["type"] == "glucose"]
    if glucose_data:
        elements.append(Paragraph("Уровень глюкозы", title_style))
        table_data = [["Дата", "Глюкоза (ммоль/л)"]]
        for r in glucose_data:
            dt = datetime.fromisoformat(r["recorded_at"]).strftime("%d.%m.%Y %H:%M")
            table_data.append([dt, str(r["glucose"])])
        table = Table(table_data, colWidths=[50 * mm, 50 * mm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#70AD47")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(table)

    doc.build(elements)
    buf.seek(0)
    return buf.read()
