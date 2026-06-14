from optiflux.export.excel_exporter import export_solutions_to_excel_bytes
from optiflux.domain.models import Solution


def test_excel_export_bytes():
    b = export_solutions_to_excel_bytes([Solution(day="Lundi", routes=[], units={})])
    assert b[:2] == b"PK"
