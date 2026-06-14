from __future__ import annotations
import re


def slug(value: str, max_len: int = 18) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", str(value).strip()).strip("-").upper()
    return value[:max_len] or "X"


def flow_id(row_idx: int, support: str, origin: str, destination: str) -> str:
    return f"F{row_idx:04d}_{slug(support,10)}_{slug(origin,10)}-VERS-{slug(destination,10)}"


def unit_id(flow_id_value: str, idx: int) -> str:
    return f"{flow_id_value}_U{idx:02d}"
