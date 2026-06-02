"""Render an approved PVC run to a downloadable Excel workbook or PDF.

These are pure functions: they take the already-fetched run + component rows
(the same shapes `GET /api/pvc-runs/{id}` returns) and return file bytes. The
route layer owns tenant/status gating; this module owns formatting only.

Library choice (SH-P5-5/6): `openpyxl` (Excel) and `fpdf2` (PDF) are both
pure-Python with no native/system dependencies, so a clean checkout boots
from declared deps alone — a hard requirement on the Windows dev/test env
(WeasyPrint's GTK/Pango/Cairo stack is not pip-installable there). Column
order / submission-format parity is deferred to P8-REVIEW.
"""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from typing import Any

# Component table columns, in display order. Keys match the `pvc_components`
# rows returned by GET /api/pvc-runs/{id}.
_COMPONENT_COLUMNS: list[tuple[str, str]] = [
    ("category", "Category"),
    ("eligible_amount", "Eligible amount"),
    ("base_index", "Base index"),
    ("current_avg_index", "Current avg index"),
    ("weight", "Weight"),
    ("pvc_value", "PVC value"),
]


def _fmt(value: Any) -> str:
    """Render a cell value as a plain string, preserving Decimal precision."""
    if value is None:
        return ""
    return str(value)


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
        ("Approved by", _fmt(run.get("approved_by"))),
        ("Approved at", _fmt(run.get("approved_at"))),
    ]


def build_run_excel(run: dict[str, Any], components: list[dict[str, Any]]) -> bytes:
    """Return an .xlsx workbook for the run as bytes."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

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
    for col, (_, header) in enumerate(_COMPONENT_COLUMNS, start=1):
        ws.cell(row=header_row, column=col, value=header).font = bold
    row += 1

    for comp in components:
        for col, (key, _) in enumerate(_COMPONENT_COLUMNS, start=1):
            ws.cell(row=row, column=col, value=_fmt(comp.get(key)))
        row += 1

    ws.cell(row=row, column=1, value="Total PVC").font = bold
    ws.cell(row=row, column=len(_COMPONENT_COLUMNS), value=_fmt(_total_pvc(components))).font = bold

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


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
    for _, header in _COMPONENT_COLUMNS:
        pdf.cell(col_w, 7, header, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", size=9)
    for comp in components:
        for key, _ in _COMPONENT_COLUMNS:
            pdf.cell(col_w, 6, _fmt(comp.get(key)), border=1)
        pdf.ln()

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(col_w * (len(_COMPONENT_COLUMNS) - 1), 7, "Total PVC", border=1)
    pdf.cell(col_w, 7, _fmt(_total_pvc(components)), border=1)

    out = pdf.output()
    return bytes(out)
