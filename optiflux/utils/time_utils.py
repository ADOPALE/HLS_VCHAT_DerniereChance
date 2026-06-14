from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any
import math
import pandas as pd


def parse_time_to_min(value: Any) -> int | None:
    """Convertit une heure Excel/pandas/texte en minutes depuis minuit."""
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.hour * 60 + value.minute
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    if isinstance(value, pd.Timestamp):
        return value.hour * 60 + value.minute
    if isinstance(value, (int, float)):
        # Excel time fraction, e.g. 0.25 = 06:00. Ignore naked values like 15 from obsolete columns.
        if 0 <= float(value) < 1:
            return int(round(float(value) * 24 * 60))
        if 0 <= float(value) <= 24 and float(value).is_integer():
            return int(value) * 60
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%H:%M:%S", "%H:%M", "%Hh%M", "%Hh"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.hour * 60 + dt.minute
        except ValueError:
            pass
    return None


def min_to_hhmm(minutes: int | float | None) -> str:
    if minutes is None or (isinstance(minutes, float) and math.isnan(minutes)):
        return ""
    minutes = int(round(minutes))
    minutes %= 24 * 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def duration_label(minutes: int | float | None) -> str:
    if minutes is None:
        return ""
    minutes = int(round(minutes))
    return f"{minutes // 60}h{minutes % 60:02d}"


def parse_duration_to_min(value: Any, default: int | None = None) -> int | None:
    parsed = parse_time_to_min(value)
    if parsed is not None:
        return parsed
    if value is None or pd.isna(value):
        return default
    text = str(value).strip().lower().replace(",", ".")
    if not text:
        return default
    if "h" in text:
        h, _, m = text.partition("h")
        try:
            return int(float(h) * 60 + (float(m) if m else 0))
        except ValueError:
            return default
    try:
        return int(float(text))
    except ValueError:
        return default
