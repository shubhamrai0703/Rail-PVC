"""P2-006: Quarter resolver — measurement_date → quarter label + month list.

Quarter convention (confirmed KU-001, WR zone):
  - Anchor: the "To" date of the measurement period, passed as measurement_date
  - Calendar quarters: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec
  - FY label: Indian FY (Apr Y → Mar Y+1), e.g. FY2025-26
  - Format: "Q2-FY2025-26"
"""
from __future__ import annotations

from datetime import date


def resolve_quarter(measurement_date: date) -> tuple[str, list[str]]:
    """
    Return (quarter_label, quarter_months).

    quarter_label: e.g. "Q2-FY2025-26"
    quarter_months: e.g. ["2025-04", "2025-05", "2025-06"]
    """
    q = (measurement_date.month - 1) // 3 + 1  # 1–4
    q_start_month = (q - 1) * 3 + 1

    # Indian FY: starts April. Months Apr-Dec belong to fy_start year;
    # Jan-Mar belong to fy_start = year - 1.
    fy_start = measurement_date.year if measurement_date.month >= 4 else measurement_date.year - 1
    fy_end_short = str(fy_start + 1)[2:]
    quarter_label = f"Q{q}-FY{fy_start}-{fy_end_short}"

    quarter_months = [
        f"{measurement_date.year}-{q_start_month + i:02d}" for i in range(3)
    ]

    return quarter_label, quarter_months
