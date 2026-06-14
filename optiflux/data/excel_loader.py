from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pandas as pd

from optiflux.config.columns import REQUIRED_SHEETS
from optiflux.data.normalizer import NormalizationReport, normalize_dataframe
from optiflux.utils.matrix_utils import MatrixRepository, matrix_from_dataframe


@dataclass
class WorkbookData:
    raw_sheets: dict[str, pd.DataFrame]
    normalized_sheets: dict[str, pd.DataFrame]
    normalization_report: NormalizationReport
    matrices: MatrixRepository


def load_workbook(path_or_buffer, circulation_factor: float = 0.0) -> WorkbookData:
    xl = pd.ExcelFile(path_or_buffer)
    raw: dict[str, pd.DataFrame] = {}
    normalized: dict[str, pd.DataFrame] = {}
    report = NormalizationReport()

    for sheet in xl.sheet_names:
        df = pd.read_excel(path_or_buffer, sheet_name=sheet)
        raw[sheet] = df
        normalized[sheet] = normalize_dataframe(df, sheet, report)

    durations = matrix_from_dataframe(normalized.get("matrice Durée", pd.DataFrame())) if "matrice Durée" in normalized else {}
    distances = matrix_from_dataframe(normalized.get("matrice Dist", pd.DataFrame())) if "matrice Dist" in normalized else {}
    matrices = MatrixRepository(durations=durations, distances=distances, circulation_factor=circulation_factor)
    return WorkbookData(raw_sheets=raw, normalized_sheets=normalized, normalization_report=report, matrices=matrices)


def missing_sheets(workbook: WorkbookData) -> list[str]:
    return [s for s in REQUIRED_SHEETS if s not in workbook.normalized_sheets]
