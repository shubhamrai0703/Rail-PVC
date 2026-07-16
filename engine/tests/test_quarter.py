"""Unit tests for P2-006: rolling quarter resolver."""
from datetime import date

from engine.quarter import resolve_quarter


class TestQuarterResolver:
    def test_quarter_one_starts_in_month_after_base(self):
        label, months = resolve_quarter(date(2023, 8, 1), date(2023, 7, 1))
        assert label == "Q1"
        assert months == ["2023-08", "2023-09", "2023-10"]

    def test_measurement_on_last_month_of_quarter_stays_in_quarter(self):
        label, months = resolve_quarter(date(2023, 10, 31), date(2023, 7, 1))
        assert label == "Q1"
        assert months == ["2023-08", "2023-09", "2023-10"]

    def test_measurement_on_first_month_of_next_quarter_advances(self):
        label, months = resolve_quarter(date(2023, 11, 1), date(2023, 7, 1))
        assert label == "Q2"
        assert months == ["2023-11", "2023-12", "2024-01"]

    def test_quarter_window_wraps_across_december(self):
        label, months = resolve_quarter(date(2024, 1, 15), date(2023, 10, 1))
        assert label == "Q1"
        assert months == ["2023-11", "2023-12", "2024-01"]

    def test_contract_quarters_continue_past_q4(self):
        label, months = resolve_quarter(date(2025, 10, 30), date(2023, 5, 1))
        assert label == "Q10"
        assert months == ["2025-09", "2025-10", "2025-11"]

    def test_day_of_month_is_ignored_for_base_and_measurement(self):
        label, months = resolve_quarter(date(2024, 4, 30), date(2023, 7, 31))
        assert label == "Q3"
        assert months == ["2024-02", "2024-03", "2024-04"]

    def test_measurement_in_base_month_has_no_quarter(self):
        label, months = resolve_quarter(date(2023, 7, 31), date(2023, 7, 1))
        assert label == ""
        assert months == []

    def test_measurement_before_base_month_has_no_quarter(self):
        label, months = resolve_quarter(date(2023, 6, 30), date(2023, 7, 1))
        assert label == ""
        assert months == []
