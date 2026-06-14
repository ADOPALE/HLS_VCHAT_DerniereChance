from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass
class MatrixRepository:
    durations: dict[tuple[str, str], float]
    distances: dict[tuple[str, str], float]
    circulation_factor: float = 0.0

    def duration(self, origin: str, destination: str) -> float:
        val = float(self.durations.get((origin, destination), 0.0))
        if val == 0:
            return 0.0
        return val * (1 + self.circulation_factor)

    def distance(self, origin: str, destination: str) -> float:
        return float(self.distances.get((origin, destination), 0.0))


def matrix_from_dataframe(df: pd.DataFrame) -> dict[tuple[str, str], float]:
    df = df.copy()
    if "Unnamed: 0" in df.columns:
        row_col = "Unnamed: 0"
    else:
        row_col = df.columns[0]
    cols = [str(c).strip() for c in df.columns]
    df.columns = cols
    row_col = str(row_col).strip()
    matrix: dict[tuple[str, str], float] = {}
    for _, row in df.iterrows():
        origin = str(row[row_col]).strip()
        if not origin or origin.lower() == "nan":
            continue
        for col in df.columns:
            if col == row_col:
                continue
            dest = str(col).strip()
            val = row[col]
            try:
                val = float(val) if pd.notna(val) else 0.0
            except Exception:
                val = 0.0
            matrix[(origin, dest)] = val
    return matrix
