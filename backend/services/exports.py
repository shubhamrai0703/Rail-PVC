"""Render an approved PVC run to a downloadable Excel workbook or PDF.

These are pure functions: they take the already-fetched run + component rows
(the same shapes `GET /api/pvc-runs/{id}` returns) and return file bytes. The
route layer owns tenant/status gating; this module owns formatting only.

Library choice (SH-P5-5/6): `openpyxl` (Excel) and `fpdf2` (PDF) are both
pure-Python with no native/system dependencies, so a clean checkout boots
from declared deps alone — a hard requirement on the Windows dev/test env
(WeasyPrint's GTK/Pango/Cairo stack is not pip-installable there).

Column order and headers follow the real Railway submission "Bill" sheet
(P8-REVIEW parity): amount, then average index of quarter, then base index,
then component weight, then PVC amount. Money/index/weight cells are written
as native numbers with submission-style number formats, and the Excel total
is a live =SUM() formula. Remaining parity gaps (multi-sheet audit trail,
steel sub-line decomposition, cover page) stay open under P8-REVIEW.
"""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import Any

# Component table columns, in submission-sheet display order. Keys match the
# `pvc_components` rows returned by GET /api/pvc-runs/{id}. The third field
# is the Excel number format ("" = text/label column).
_FMT_MONEY = "#,##0.00"
_FMT_INDEX = "0.00"
_FMT_WEIGHT = "0%"

_COMPONENT_COLUMNS: list[tuple[str, str, str]] = [
    ("category", "Category", ""),
    ("eligible_amount", 'Eligible amount "W"', _FMT_MONEY),
    ("current_avg_index", "Average index of quarter", _FMT_INDEX),
    ("base_index", "Base index", _FMT_INDEX),
    ("weight", "Component weight", _FMT_WEIGHT),
    ("pvc_value", "PVC amount", _FMT_MONEY),
]


def _fmt(value: Any) -> str:
    """Render a cell value as a plain string, preserving Decimal precision."""
    if value is None:
        return ""
    return str(value)


def _num(value: Any) -> Decimal | None:
    """Coerce a numeric cell value to Decimal (None passes through)."""
    if value is None:
        return None
    return Decimal(str(value))


def _total_pvc(components: list[dict[str, Any]]) -> Decimal:
    total = Decimal("0")
    for c in components:
        raw = c.get("pvc_value")
        if raw is not None:
            total += Decimal(str(raw))
    return total


def _summary_rows(run: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("Run ID", _fmt(run.get("id"))),
        ("Status", _fmt(run.get("status"))),
        ("Tender", _fmt(run.get("tender_number"))),
        ("Contractor", _fmt(run.get("contractor_name"))),
        ("Quarter", _fmt(run.get("quarter_used"))),
        ("Approved by", _fmt(run.get("approved_by"))),
        ("Approved at", _fmt(run.get("approved_at"))),
    ]


def build_run_excel(run: dict[str, Any], components: list[dict[str, Any]]) -> bytes:
    """Return an .xlsx workbook for the run as bytes."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "PVC Run"
    bold = Font(bold=True)

    ws["A1"] = "PVC Run Export"
    ws["A1"].font = Font(bold=True, size=14)

    row = 3
    for label, value in _summary_rows(run):
        ws.cell(row=row, column=1, value=label).font = bold
        ws.cell(row=row, column=2, value=value)
        row += 1

    row += 1
    header_row = row
    for col, (_, header, _numfmt) in enumerate(_COMPONENT_COLUMNS, start=1):
        ws.cell(row=header_row, column=col, value=header).font = bold
    row += 1

    first_data_row = row
    for comp in components:
        for col, (key, _, numfmt) in enumerate(_COMPONENT_COLUMNS, start=1):
            if numfmt:
                cell = ws.cell(row=row, column=col, value=_num(comp.get(key)))
                cell.number_format = numfmt
            else:
                ws.cell(row=row, column=col, value=_fmt(comp.get(key)))
        row += 1

    total_col = len(_COMPONENT_COLUMNS)
    ws.cell(row=row, column=1, value="Total PVC").font = bold
    if components:
        letter = get_column_letter(total_col)
        total_cell = ws.cell(
            row=row,
            column=total_col,
            value=f"=SUM({letter}{first_data_row}:{letter}{row - 1})",
        )
    else:
        total_cell = ws.cell(row=row, column=total_col, value=_num(Decimal("0")))
    total_cell.font = bold
    total_cell.number_format = _FMT_MONEY

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _pdf_cell_text(key: str, value: Any) -> str:
    """Format a component value for the PDF table (mirrors the Excel formats)."""
    if value is None:
        return ""
    if key == "weight":
        return f"{Decimal(str(value)) * 100:.0f}%"
    if key in ("eligible_amount", "pvc_value"):
        return f"{Decimal(str(value)):,.2f}"
    if key in ("base_index", "current_avg_index"):
        return f"{Decimal(str(value)):.2f}"
    return str(value)


def build_run_pdf(run: dict[str, Any], components: list[dict[str, Any]]) -> bytes:
    """Return a PDF report for the run as bytes."""
    from fpdf import FPDF

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "PVC Run Export", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", size=10)
    for label, value in _summary_rows(run):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(45, 6, f"{label}:")
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / len(_COMPONENT_COLUMNS)
    pdf.set_font("Helvetica", "B", 9)
    for _, header, _numfmt in _COMPONENT_COLUMNS:
        pdf.cell(col_w, 7, header, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", size=9)
    for comp in components:
        for key, _, _numfmt in _COMPONENT_COLUMNS:
            pdf.cell(col_w, 6, _pdf_cell_text(key, comp.get(key)), border=1)
        pdf.ln()

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(col_w * (len(_COMPONENT_COLUMNS) - 1), 7, "Total PVC", border=1)
    pdf.cell(col_w, 7, f"{_total_pvc(components):,.2f}", border=1)

    out = pdf.output()
    return bytes(out)
