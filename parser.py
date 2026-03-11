import re
from dataclasses import dataclass


@dataclass
class PressureReading:
    systolic: int
    diastolic: int


@dataclass
class GlucoseReading:
    value: float


def parse_message(text: str) -> PressureReading | GlucoseReading | None:
    """Parse a text message and extract health metrics.

    Supported formats:
      Давление 120 на 80 / Давление 120-80 / Давление 120/80 / 120 на 80 / 120-80
      Глюкоза 5.4 / Сахар 5,4 / Глюкоза 5 4
    """
    text = text.lower().strip()

    # Pressure patterns
    pressure_patterns = [
        r"(?:давление\s+)?(\d{2,3})\s*(?:на|[-/])\s*(\d{2,3})",
    ]
    for pattern in pressure_patterns:
        m = re.search(pattern, text)
        if m:
            sys_val = int(m.group(1))
            dia_val = int(m.group(2))
            if 60 <= sys_val <= 300 and 30 <= dia_val <= 200:
                return PressureReading(systolic=sys_val, diastolic=dia_val)

    # Glucose patterns
    glucose_patterns = [
        r"(?:глюкоза|сахар|glucose)\s+(\d{1,2})[.,\s](\d{1,2})",
        r"(?:глюкоза|сахар|glucose)\s+(\d{1,2})",
    ]
    for pattern in glucose_patterns:
        m = re.search(pattern, text)
        if m:
            if m.lastindex == 2:
                value = float(f"{m.group(1)}.{m.group(2)}")
            else:
                value = float(m.group(1))
            if 1.0 <= value <= 40.0:
                return GlucoseReading(value=value)

    return None
