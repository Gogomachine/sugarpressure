"""Generate charts for pressure and glucose history."""

import io
import tempfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

from bot.database import get_pressure_history, get_pulse_history, get_glucose_history


def generate_pressure_chart(user_id: int, days: int = 30) -> bytes | None:
    """Generate a blood pressure chart and return PNG bytes."""
    readings = get_pressure_history(user_id, days)
    if not readings:
        return None

    dates = [r.timestamp for r in readings]
    systolic = [r.systolic for r in readings]
    diastolic = [r.diastolic for r in readings]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, systolic, "ro-", label="Систолическое", markersize=6)
    ax.plot(dates, diastolic, "bo-", label="Диастолическое", markersize=6)

    # Normal range bands
    ax.axhspan(90, 120, alpha=0.1, color="green", label="Норма сист.")
    ax.axhspan(60, 80, alpha=0.1, color="blue", label="Норма диаст.")

    ax.set_title(f"Артериальное давление (последние {days} дн.)")
    ax.set_ylabel("мм рт.ст.")
    ax.set_xlabel("Дата")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_pulse_chart(user_id: int, days: int = 30) -> bytes | None:
    """Generate a pulse chart and return PNG bytes."""
    readings = get_pulse_history(user_id, days)
    if not readings:
        return None

    dates = [r.timestamp for r in readings]
    values = [r.value for r in readings]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, values, "mo-", label="Пульс", markersize=6)

    # Normal range
    ax.axhspan(60, 100, alpha=0.1, color="green", label="Норма (60–100)")

    ax.set_title(f"Пульс (последние {days} дн.)")
    ax.set_ylabel("уд/мин")
    ax.set_xlabel("Дата")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_glucose_chart(user_id: int, days: int = 30) -> bytes | None:
    """Generate a glucose chart and return PNG bytes."""
    readings = get_glucose_history(user_id, days)
    if not readings:
        return None

    dates = [r.timestamp for r in readings]
    values = [r.value for r in readings]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, values, "go-", label="Глюкоза", markersize=6)

    # Normal range
    ax.axhspan(3.9, 5.5, alpha=0.15, color="green", label="Норма натощак")
    ax.axhline(y=7.0, color="red", linestyle="--", alpha=0.5, label="Порог (7.0)")

    ax.set_title(f"Уровень глюкозы (последние {days} дн.)")
    ax.set_ylabel("ммоль/л")
    ax.set_xlabel("Дата")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
