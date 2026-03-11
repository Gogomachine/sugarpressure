import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def pressure_chart(history: list[dict]) -> bytes:
    """Generate a pressure chart and return PNG bytes."""
    dates = [_parse_dt(r["recorded_at"]) for r in history]
    sys_vals = [r["systolic"] for r in history]
    dia_vals = [r["diastolic"] for r in history]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, sys_vals, "r-o", label="Систолическое", markersize=4)
    ax.plot(dates, dia_vals, "b-o", label="Диастолическое", markersize=4)

    ax.axhspan(90, 120, alpha=0.1, color="green", label="Норма сист.")
    ax.axhspan(60, 80, alpha=0.1, color="blue", label="Норма диаст.")

    ax.set_title("Артериальное давление")
    ax.set_ylabel("мм рт. ст.")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    fig.autofmt_xdate()
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def glucose_chart(history: list[dict]) -> bytes:
    """Generate a glucose chart and return PNG bytes."""
    dates = [_parse_dt(r["recorded_at"]) for r in history]
    values = [r["glucose"] for r in history]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, values, "g-o", label="Глюкоза", markersize=4)

    ax.axhspan(3.9, 5.5, alpha=0.1, color="green", label="Норма (натощак)")
    ax.axhline(y=7.0, color="red", linestyle="--", alpha=0.5, label="Порог диабета")

    ax.set_title("Уровень глюкозы")
    ax.set_ylabel("ммоль/л")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    fig.autofmt_xdate()
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
