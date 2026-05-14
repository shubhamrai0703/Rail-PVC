"""Unit tests for P2-006: quarter resolver."""
from datetime import date

from engine.quarter import resolve_quarter


class TestQuarterResolver:
    def test_bct_bill1_jun_18_is_q2_fy2025_26(self):
        """BCT-24-25-252 Bill-1: measurement_date 2025-06-18 → Q2."""
        label, months = resolve_quarter(date(2025, 6, 18))
        assert label == "Q2-FY2025-26"
        assert months == ["2025-04", "2025-05", "2025-06"]

    def test_bct_bill2_nov_4_is_q4_fy2025_26(self):
        """BCT-24-25-252 Bill-2: measurement_date 2025-11-04 → Q4."""
        label, months = resolve_quarter(date(2025, 11, 4))
        assert label == "Q4-FY2025-26"
        assert months == ["2025-10", "2025-11", "2025-12"]

    def test_q1_calendar_jan_mar(self):
        label, months = resolve_quarter(date(2026, 2, 15))
        assert label == "Q1-FY2025-26"
        assert months == ["2026-01", "2026-02", "2026-03"]

    def test_q3_jul_sep(self):
        label, months = resolve_quarter(date(2025, 8, 20))
        assert label == "Q3-FY2025-26"
        assert months == ["2025-07", "2025-08", "2025-09"]

    def test_fy_boundary_apr_starts_new_fy(self):
        label, months = resolve_quarter(date(2026, 4, 1))
        assert label == "Q2-FY2026-27"
        assert months == ["2026-04", "2026-05", "2026-06"]

    def test_fy_boundary_mar_stays_in_prior_fy(self):
        label, months = resolve_quarter(date(2026, 3, 31))
        assert label == "Q1-FY2025-26"
        assert months == ["2026-01", "2026-02", "2026-03"]

    def test_dec_is_q4(self):
        label, months = resolve_quarter(date(2024, 12, 31))
        assert label == "Q4-FY2024-25"
        assert months == ["2024-10", "2024-11", "2024-12"]

    def test_quarter_months_always_3(self):
        for month in range(1, 13):
            _, months = resolve_quarter(date(2025, month, 15))
            assert len(months) == 3
