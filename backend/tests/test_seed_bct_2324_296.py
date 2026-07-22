"""Source reconciliation and safety coverage for the Ritesh contract seed."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "seeds" / "seed_bct_2324_296.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("seed_bct_2324_296_for_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_seed_requires_explicit_tenant(monkeypatch):
    module = _load_script()
    monkeypatch.delenv("SEED_TENANT_ID", raising=False)

    with pytest.raises(SystemExit, match="SEED_TENANT_ID is required"):
        module.resolve_tenant_id()


def test_source_bill_lines_reconcile_to_signed_gross_amounts():
    module = _load_script()
    totals = defaultdict(Decimal)
    for line in module.BILL_LINES:
        totals[line.bill_number] += line.amount_since_last.quantize(Decimal("0.0001"))

    assert totals == {
        1: Decimal("8811280.43"),
        2: Decimal("7319994.44"),
        3: Decimal("22091.28"),
    }
    assert totals == {bill.number: bill.gross_amount for bill in module.BILLS}


def test_bill_line_quantity_and_amount_progression_is_internally_consistent():
    module = _load_script()
    database_quantum = Decimal("0.0001")
    previous_quantity = defaultdict(Decimal)
    previous_amount = defaultdict(Decimal)

    for line in module.BILL_LINES:
        qty_up_to_last = line.qty_up_to_last.quantize(database_quantum)
        qty_since_last = line.qty_since_last.quantize(database_quantum)
        qty_up_to_date = line.qty_up_to_date.quantize(database_quantum)
        amount_up_to_last = line.amount_up_to_last.quantize(database_quantum)
        amount_since_last = line.amount_since_last.quantize(database_quantum)
        amount_up_to_date = line.amount_up_to_date.quantize(database_quantum)

        assert qty_up_to_last == previous_quantity[line.item_code]
        assert qty_up_to_date == qty_up_to_last + qty_since_last
        assert qty_since_last == (
            Decimal("1") if amount_since_last else Decimal("0")
        )
        assert amount_up_to_last == previous_amount[line.item_code]
        assert amount_up_to_date == amount_up_to_last + amount_since_last
        previous_quantity[line.item_code] = qty_up_to_date
        previous_amount[line.item_code] = amount_up_to_date


def test_pvc_buckets_are_derived_from_item_classification():
    module = _load_script()
    items = {item.code: item for item in module.ITEMS}
    derived = defaultdict(
        lambda: {
            "cement": Decimal("0"),
            "steel_angles": Decimal("0"),
            "steel_other": Decimal("0"),
            "technical_withheld": Decimal("0"),
        }
    )

    for line in module.BILL_LINES:
        item = items[line.item_code]
        if item.is_cement_item:
            derived[line.bill_number]["cement"] += line.amount_since_last
        if item.steel_subtype == "angles":
            derived[line.bill_number]["steel_angles"] += line.amount_since_last
        if item.steel_subtype == "other_sections":
            derived[line.bill_number]["steel_other"] += line.amount_since_last
        derived[line.bill_number]["technical_withheld"] += (
            line.special_condition_amount
        )

    quantum = Decimal("0.0001")
    assert {
        number: {bucket: amount.quantize(quantum) for bucket, amount in buckets.items()}
        for number, buckets in derived.items()
    } == {
        number: {bucket: amount.quantize(quantum) for bucket, amount in buckets.items()}
        for number, buckets in module.EXPECTED_BUCKETS.items()
    }


def test_source_recoveries_reconcile_to_signed_net_amounts():
    module = _load_script()
    recoveries = defaultdict(Decimal)
    for recovery in module.RECOVERIES:
        assert recovery.affects_pvc_base is False
        recoveries[recovery.bill_number] += recovery.amount

    assert recoveries == {
        1: Decimal("516559"),
        2: Decimal("452828"),
        3: Decimal("1881"),
    }
    assert {
        bill.number: bill.gross_amount - recoveries[bill.number]
        for bill in module.BILLS
    } == module.EXPECTED_NET_AMOUNTS


def test_fixture_buckets_and_pdf_dates_are_pinned():
    module = _load_script()

    assert module.BASE_MONTH.isoformat() == "2024-02-01"
    assert [bill.bill_date.isoformat() for bill in module.BILLS] == [
        "2024-09-18",
        "2025-02-15",
        "2025-03-21",
    ]
    assert [bill.measurement_date.isoformat() for bill in module.BILLS] == [
        "2024-09-17",
        "2025-02-15",
        "2025-03-20",
    ]
    assert module.EXPECTED_BUCKETS == {
        1: {
            "cement": Decimal("134635.71130340002"),
            "steel_angles": Decimal("96281.46738449999"),
            "steel_other": Decimal("90480.3894585"),
            "technical_withheld": Decimal("1249"),
        },
        2: {
            "cement": Decimal("67362.965069572"),
            "steel_angles": Decimal("0"),
            "steel_other": Decimal("143721.2815695"),
            "technical_withheld": Decimal("0"),
        },
        3: {
            "cement": Decimal("0"),
            "steel_angles": Decimal("0"),
            "steel_other": Decimal("0"),
            "technical_withheld": Decimal("0"),
        },
    }


def test_dry_run_flag_is_explicit(monkeypatch):
    module = _load_script()

    monkeypatch.delenv("SEED_DRY_RUN", raising=False)
    assert module.is_dry_run() is False
    monkeypatch.setenv("SEED_DRY_RUN", "1")
    assert module.is_dry_run() is True
    monkeypatch.setenv("SEED_DRY_RUN", "true")
    assert module.is_dry_run() is True
    monkeypatch.setenv("SEED_DRY_RUN", "yes")
    with pytest.raises(SystemExit, match="SEED_DRY_RUN"):
        module.is_dry_run()


def test_commit_mode_requires_exact_expected_database_host(monkeypatch):
    module = _load_script()
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://railpvc:secret@db.example.test:6543/railpvc",
    )
    monkeypatch.delenv("SEED_EXPECTED_DB_HOST", raising=False)

    assert module.resolve_database_destination(dry_run=True) == (
        "db.example.test",
        6543,
        "railpvc",
    )
    with pytest.raises(SystemExit, match="SEED_EXPECTED_DB_HOST is required"):
        module.resolve_database_destination(dry_run=False)

    monkeypatch.setenv("SEED_EXPECTED_DB_HOST", "wrong.example.test")
    with pytest.raises(SystemExit, match="does not match"):
        module.resolve_database_destination(dry_run=False)

    monkeypatch.setenv("SEED_EXPECTED_DB_HOST", "DB.EXAMPLE.TEST")
    assert module.resolve_database_destination(dry_run=False) == (
        "db.example.test",
        6543,
        "railpvc",
    )
