"""Parse recognized text to extract pressure and glucose values."""

import re
from dataclasses import dataclass


@dataclass
class PressureResult:
    systolic: int
    diastolic: int
    pulse: int | None = None


@dataclass
class PulseResult:
    value: int


@dataclass
class GlucoseResult:
    value: float


def parse_message(text: str) -> PressureResult | GlucoseResult | None:
    """Parse a text message and extract health readings.

    Supported formats:
        Давление 120 на 80
        Давление 120-80
        Давление 120/80
        Давление 120 80
        Давление 120/80 пульс 72
        Глюкоза 5.4
        Сахар 6,2
    """
    text = text.strip().lower()

    # Try pressure (before pulse, since pressure can contain pulse)
    pressure = _parse_pressure(text)
    if pressure:
        return pressure

    # Try pulse (standalone)
    pulse = _parse_pulse(text)
    if pulse:
        return pulse

    # Try glucose
    glucose = _parse_glucose(text)
    if glucose:
        return glucose

    return None


def _parse_pressure(text: str) -> PressureResult | None:
    pattern = (
        r"давлени[ея]\s+"
        r"(\d{2,3})\s*[-/наНА\s]+\s*(\d{2,3})"
        r"(?:\s+пульс\s+(\d{2,3}))?"
    )
    match = re.search(pattern, text)
    if not match:
        return None

    systolic = int(match.group(1))
    diastolic = int(match.group(2))
    pulse = int(match.group(3)) if match.group(3) else None

    if not (60 <= systolic <= 300 and 30 <= diastolic <= 200):
        return None
    if pulse is not None and not (30 <= pulse <= 250):
        return None

    return PressureResult(systolic=systolic, diastolic=diastolic, pulse=pulse)


def _parse_pulse(text: str) -> PulseResult | None:
    pattern = r"пульс\s+(\d{2,3})"
    match = re.search(pattern, text)
    if not match:
        return None

    # Don't match if this is part of a pressure reading
    if re.search(r"давлени[ея]", text):
        return None

    value = int(match.group(1))
    if not (30 <= value <= 250):
        return None

    return PulseResult(value=value)


def _parse_glucose(text: str) -> GlucoseResult | None:
    pattern = r"(?:глюкоз[аы]|сахар[а]?)\s+(\d{1,2}[.,]?\d*)"
    match = re.search(pattern, text)
    if not match:
        return None

    value_str = match.group(1).replace(",", ".")
    value = float(value_str)

    if not (1.0 <= value <= 40.0):
        return None

    return GlucoseResult(value=value)
