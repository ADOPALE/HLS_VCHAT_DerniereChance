from __future__ import annotations

from io import BytesIO
import pandas as pd
from optiflux.export.export_tables import all_export_tables


def export_solutions_to_excel_bytes(solutions, import_report=None, input_errors=None) -> bytes:
    output = BytesIO()
    tables = all_export_tables(solutions, import_report, input_errors)
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for sheet, df in tables.items():
            safe_sheet = sheet[:31]
            df.to_excel(writer, sheet_name=safe_sheet, index=False)
            workbook = writer.book
            worksheet = writer.sheets[safe_sheet]
            header_fmt = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
            for col_idx, col in enumerate(df.columns):
                worksheet.write(0, col_idx, col, header_fmt)
                width = min(max(len(str(col)) + 2, 12), 45)
                if not df.empty:
                    sample = df[col].astype(str).head(100).map(len).max()
                    width = min(max(width, int(sample) + 2), 60)
                worksheet.set_column(col_idx, col_idx, width)
            worksheet.freeze_panes(1, 0)
            if len(df) > 0 and len(df.columns) > 0:
                worksheet.autofilter(0, 0, len(df), len(df.columns)-1)
    return output.getvalue()


def save_excel(path: str, solutions, import_report=None, input_errors=None) -> None:
    with open(path, "wb") as f:
        f.write(export_solutions_to_excel_bytes(solutions, import_report, input_errors))
