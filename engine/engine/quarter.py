"""P2-006: Resolve rolling contract quarters for a measurement date.

Under GCC April 2022, Quarter 1 is the three months immediately after the
contract base month. Later quarters continue in three-month windows for the
life of the contract and use plain ordinal labels (``Q1``, ``Q5``, ...).
"""
from __future__ import annotations

from datetime import date


def resolve_quarter(measurement_date: date, base_month: date) -> tuple[str, list[str]]:
    """
    Return (quarter_label, quarter_months).

    Dates in or before the base month have no PVC quarter and return an empty
    label and month list so the calculator can surface a validation error.
    """
    months_since_base = (
        (measurement_date.year - base_month.year) * 12
        + measurement_date.month
        - base_month.month
    )
    if months_since_base <= 0:
        return "", []

    quarter_number = ((months_since_base - 1) // 3) + 1
    quarter_start_offset = (quarter_number - 1) * 3 + 1
    base_month_index = base_month.year * 12 + base_month.month - 1

    quarter_months: list[str] = []
    for offset in range(quarter_start_offset, quarter_start_offset + 3):
        year, zero_based_month = divmod(base_month_index + offset, 12)
        quarter_months.append(f"{year}-{zero_based_month + 1:02d}")

    return f"Q{quarter_number}", quarter_months
