from __future__ import annotations

import pandas as pd
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizationReport:
    changes: list[dict[str, Any]] = field(default_factory=list)

    def add(self, sheet: str, row: int | None, column: str, old: Any, new: Any) -> None:
        if old != new:
            self.changes.append({"sheet": sheet, "row": row, "column": column, "old": old, "new": new})


def normalize_text(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        text = " ".join(text.split())
        return text
    return value


def normalize_bool(value: Any, default: bool = False) -> bool:
    if value is None or pd.isna(value):
        return default
    text = str(value).strip().upper()
    return text in {"OUI", "YES", "Y", "VRAI", "TRUE", "1"}


def normalize_sanitary(value: Any) -> str:
    text = str(value).strip().upper() if value is not None and not pd.isna(value) else ""
    if "SALE" in text:
        return "Sale"
    if "PROPRE" in text:
        return "Propre"
    return text.title() if text else ""


def normalize_exclusions(value: Any) -> set[str]:
    if value is None or pd.isna(value):
        return set()
    parts = [p.strip() for p in str(value).replace(";", ",").replace("/", ",").split(",")]
    return {normalize_sanitary(p) for p in parts if p.strip()}


def normalize_dataframe(df: pd.DataFrame, sheet: str, report: NormalizationReport) -> pd.DataFrame:
    out = df.copy()
    out.columns = [normalize_text(c) if isinstance(c, str) else c for c in out.columns]
    for col in out.columns:
        if out[col].dtype == "object":
            for idx, val in out[col].items():
                new = normalize_text(val)
                if new != val:
                    report.add(sheet, int(idx) + 2, str(col), val, new)
                    out.at[idx, col] = new
    return out
