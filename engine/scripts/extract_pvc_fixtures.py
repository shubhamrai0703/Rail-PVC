"""Extract auditable RailPVC engine fixtures from the five Banjara workbooks.

The workbook paths and source cells are intentionally declarative.  The files
under ``PVC/`` are read-only evidence; this script only writes JSON fixtures.
Run from ``engine/`` with ``uv run python scripts/extract_pvc_fixtures.py``.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = REPO_ROOT / "PVC"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "engine" / "tests" / "fixtures" / "real_tenders"

SERIES_COLUMNS = {
    "labour": "C",
    "plant_machinery": "D",
    "fuel": "E",
    "other_materials": "F",
    "cement": "G",
    "steel_tmt": "H",
    "steel_angles": "I",
    "steel_plates": "J",
    "steel_other_sections": "K",
}

BILL_AMOUNT_COLUMNS = {
    "on_account_amount": "D",
    "cement_amount": "E",
    "steel_tmt_amount": "F",
    "steel_angles_amount": "G",
    "steel_plates_amount": "H",
    "steel_other_amount": "I",
    "technical_withheld": "J",
}


@dataclass(frozen=True)
class IndexRows:
    sheet: str
    rows: tuple[int, ...]


@dataclass(frozen=True)
class BillSpec:
    filename: str
    label: str
    source_row: int
    calculation_sheet: str
    expected_cell: str
    summary_sheet: str
    summary_cell: str
    tolerance: str = "0.01"
    extra_cells: tuple[str, ...] = ()
    xfail_reason: str | None = None
    divergence: str | None = None
    amount_overrides: dict[str, str] = field(default_factory=dict)
    index_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    current_engine_total: str | None = None
    expected_validation_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkbookSpec:
    contract: str
    workbook: str
    base_month: date
    base_sheet: str
    base_row: int
    w_sheet: str
    index_rows: tuple[IndexRows, ...]
    bills: tuple[BillSpec, ...]
    formula_bucket_cells: dict[str, str] = field(default_factory=lambda: {
        "steel_angles_amount": "B10",
        "steel_plates_amount": "B15",
        "steel_other_amount": "B20",
    })


KU_FOLLOWUP = "KU-001 follow-up: rolling quarter resolution is correct; "

SPECS = (
    WorkbookSpec(
        contract="STC COP & Seating",
        workbook="COP & Seating/Banjara - STC COP - Apr 2022 GCC.xlsx",
        base_month=date(2023, 7, 1),
        base_sheet="Table 2",
        base_row=7,
        w_sheet="Table 4",
        index_rows=(
            IndexRows("Table 2", (9, 10, 11, 15, 16, 17, 21, 22, 23)),
            IndexRows("Table 3", (2, 3, 4, 8, 9, 10, 14, 15, 16, 20, 21, 22, 26, 27, 28, 32, 33, 34)),
        ),
        formula_bucket_cells={
            "steel_tmt_amount": "B10",
            "steel_angles_amount": "B15",
            "steel_plates_amount": "B20",
            "steel_other_amount": "B25",
        },
        bills=(
            BillSpec(
                "stc_cop_bill1_q3.json", "Bill 1 / Q3", 4, "Table 8", "L30", "Table 1", "C8",
                "0.15",
                xfail_reason=(
                    KU_FOLLOWUP + "the workbook hard-codes rounded quarter averages"
                ),
                divergence=(
                    "Table 8 hard-codes two-decimal quarter averages instead of deriving "
                    "them at full precision from the Index-sheet monthly observations. "
                    "The fixture preserves the source observations verbatim; resolving "
                    "the averaging-rule difference requires a separate domain decision."
                ),
                current_engine_total="-120665.56",
            ),
            BillSpec(
                "stc_cop_bill2_q4.json", "Bill 2 / Q4", 6, "Table 9", "L30", "Table 1", "C9",
                "0.15",
                xfail_reason=(
                    KU_FOLLOWUP + "the workbook hard-codes rounded quarter averages"
                ),
                divergence=(
                    "Table 9 hard-codes two-decimal quarter averages instead of deriving "
                    "them at full precision from the Index-sheet monthly observations. "
                    "The fixture preserves the source observations verbatim; resolving "
                    "the averaging-rule difference requires a separate domain decision."
                ),
                current_engine_total="-54130.40",
            ),
            BillSpec(
                "stc_cop_bill3_q7.json", "Bill 3 / Q7", 8, "Table 10 ", "L30", "Table 1", "C12",
                xfail_reason=KU_FOLLOWUP + "the workbook double-counts TMT in general W",
                divergence=(
                    "The general-W mismatch double-counts TMT because Table 10 also "
                    "calculates a TMT bucket. Table 10 also hard-codes two-decimal quarter "
                    "averages, and its angles average 59820 conflicts with the Index-sheet "
                    "average 59806.22. The fixture preserves the Index-sheet monthly "
                    "observations verbatim."
                ),
                current_engine_total="5230.05",
            ),
            BillSpec(
                "stc_cop_bill4_q9.json", "Bill 4 / Q9", 10, "Table 11", "L30", "Table 1", "C15",
                xfail_reason=KU_FOLLOWUP + "the workbook uses a hybrid steel-other amount",
                divergence=(
                    "The workbook total is a hybrid: Table 4!I10 subtracts 665094.334275 "
                    "from W, while Table 11!B25 calculates the steel-other bucket on "
                    "1978547.683065. The fixture uses the calculation-sheet bucket amount "
                    "in the payload and preserves both source values in this note."
                ),
                amount_overrides={"steel_other_amount": "B25"},
                current_engine_total="-156249.28",
            ),
        ),
    ),
    WorkbookSpec(
        contract="BCT-24-25-252",
        workbook="BCT-24-25-252/Banjara - COLABA BP 252 - Apr 2022 GCC.xlsx",
        base_month=date(2024, 12, 1),
        base_sheet="Index",
        base_row=2,
        w_sheet="Second Page",
        index_rows=(IndexRows("Index", (6, 7, 8, 13, 14, 15)),),
        bills=(
            BillSpec(
                "bct_2425_252_golden_bill1_q2.json", "Bill 1 / Q2", 4, "Bill- 1", "L25",
                "Front Page ", "C8",
                divergence=(
                    "Front Page !C8 links Bill- 1!L25 but is labelled second bill/Q4; "
                    "Front Page !C7 links Bill-2!L25 but is labelled first bill/Q2. "
                    "The calculation-sheet precedent and Second Page row identify this as Bill 1/Q2."
                ),
            ),
            BillSpec(
                "bct_2425_252_golden_bill2_q4.json", "Bill 2 / Q4", 6, "Bill-2", "L25",
                "Front Page ", "C7",
                xfail_reason=(
                    "KU-001 follow-up: this calendar-aligned Q4 disproves the predicted pass "
                    "because the workbook calculation sheet references Q2 averages; "
                    "quarter.py alone will not fix it"
                ),
                divergence=(
                    "Bill-2 is labelled Quarter 4 and measured 2025-11-04, but its D5:D24 "
                    "formulas reference Index row 9 (Quarter 2 averages) instead of row 16 "
                    "(Quarter 4). Front Page !C7/C8 also cross-wire the Bill-2/Bill- 1 "
                    "calculation links against the displayed first/second-bill labels. "
                    "The workbook total is preserved."
                ),
                current_engine_total="80905.45",
            ),
        ),
    ),
    WorkbookSpec(
        contract="BCT-24-25-183",
        workbook="BCT-24-25-183/Banjara - COLABA BP  183 - Apr 2022 GCC.xlsx",
        base_month=date(2024, 9, 1),
        base_sheet="Index 2",
        base_row=3,
        w_sheet="Second page",
        index_rows=(IndexRows("Index 2", (4, 5, 6, 8, 9, 10, 12, 13, 14)),),
        bills=(
            BillSpec(
                "bct_2425_183_bill1_q2.json", "Bill 1 / Q2", 4, "Bill 1", "L25",
                "Front Page ", "C6",
            ),
            BillSpec(
                "bct_2425_183_bill2_q3.json", "Bill 2 / Q3", 6, "Bill 2", "L25",
                "Front Page ", "C7",
                xfail_reason=(
                    "KU-001 follow-up: this calendar-aligned Q3 disproves the predicted pass "
                    "because the workbook keeps cement in general W and also calculates "
                    "cement separately; quarter.py alone will not fix it"
                ),
                divergence=(
                    "Bill 2 also calculates a separate cement component from Second page!E7, "
                    "so the general-W mismatch double-counts cement."
                ),
                current_engine_total="73710.18",
            ),
        ),
    ),
    WorkbookSpec(
        contract="BCT-23-24-296",
        workbook="BCT-23-24-296/Banjara - COLABA BP  296 - Apr 2022 GCC.xlsx",
        base_month=date(2024, 2, 1),
        base_sheet="Index (2)",
        base_row=3,
        w_sheet="Second page",
        index_rows=(IndexRows("Index (2)", (5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 19, 21, 22, 23)),),
        bills=(
            BillSpec(
                "bct_2324_296_bill1_q3.json", "Bill 1 / Q3", 4, "Bill 1", "L25",
                "Front Page ", "C6",
            ),
            BillSpec(
                "bct_2324_296_bill2_q4.json", "Bill 2 / Q4", 6, "Bill 2", "L25",
                "Front Page ", "C7",
            ),
            BillSpec(
                "bct_2324_296_bill3_q4.json", "Bill 3 / Q4", 8, "Bill 3", "L25",
                "Front Page ", "C8",
                divergence=(
                    "Second page!C8 labels the third bill Q5, while Front Page!B8 and "
                    "Bill 3!A2 label it Q4 and the calculation sheet uses Q4 averages."
                ),
            ),
        ),
    ),
    WorkbookSpec(
        contract="JRH (BCT-23-24-48)",
        workbook="JRH/New folder/Banjara - JRH - Apr 2022 GCC (4) (1).xlsx",
        base_month=date(2023, 5, 1),
        base_sheet="Index",
        base_row=6,
        w_sheet="Second page ",
        index_rows=(IndexRows("Index", (8, 9, 10, 12, 13, 14, 16, 17, 18, 20, 21, 22, 24, 25, 26, 28, 29, 30, 32, 33, 34, 36, 37, 38, 40, 41, 42, 44, 45, 46)),),
        bills=(
            BillSpec(
                "jrh_bct_2324_48_bill1_q4.json", "Bill 1 / Q4", 4, "1st bill", "L25",
                "Front page", "C9",
            ),
            BillSpec(
                "jrh_bct_2324_48_bill2_q6.json", "Bill 2 / Q6", 6, "2nd Bill", "L25",
                "Front page", "C11",
            ),
            BillSpec(
                "jrh_bct_2324_48_bill3_q7.json", "Bill 3 / Q7", 8, "3rd bill", "L25",
                "Front page", "C12",
                xfail_reason=KU_FOLLOWUP + "the workbook uses stale W inputs in general rows",
                divergence=(
                    "3rd bill!B5 uses derived W 6668663.099263423, while B6:B8 "
                    "hard-code stale W 6660973.25310658. The fixture keeps the "
                    "source-derived W and Index-sheet values."
                ),
                current_engine_total="168488.10",
            ),
            BillSpec(
                "jrh_bct_2324_48_bill4_q9.json", "Bill 4 / Q9", 10, "4th bill", "L25",
                "Front page", "C14",
                xfail_reason=KU_FOLLOWUP + "the workbook mixes W, steel amounts, and indices",
                divergence=(
                    "4th bill!B5 uses derived W 7741793.184496519, while B6:B8 "
                    "hard-code 7734810.34001062. Steel rows also mix source amounts "
                    "with stale amounts and use materials average 154.466666666667 "
                    "instead of the Index-sheet Q9 average 154.433333333333."
                ),
                current_engine_total="181375.32",
            ),
            BillSpec(
                "jrh_bct_2324_48_bill5_q10.json", "Bill 5 / Q10", 12, "5th bill", "L25",
                "Front page", "C15",
                extra_cells=("L13", "L14"),
                xfail_reason=KU_FOLLOWUP + "the workbook rounds steel sub-index inputs",
                divergence=(
                    "5th bill!A2 says Quarter 9, but Front page!B15, Second page !C12, "
                    "and the calculation formulas identify/use Quarter 10. Its steel "
                    "rows round labour 147.733333→147.73, plant 93.066667→93.1, and "
                    "materials 155.333333→155.33 while general rows use exact averages."
                ),
                current_engine_total="100982.68",
            ),
        ),
    ),
)


def _decimal(value: Any, *, source: str) -> Decimal:
    if value in (None, "", "-"):
        raise ValueError(f"{source} is blank; a cached numeric value is required")
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{source} is not numeric: {value!r}") from exc


def _decimal_text(value: Any, *, source: str) -> str:
    return str(_decimal(value, source=source))


def _optional_decimal(value: Any, *, source: str) -> Decimal:
    if value in (None, "", "-"):
        return Decimal("0")
    return _decimal(value, source=source)


def _month_key(value: Any, *, source: str) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m")
    if isinstance(value, str):
        cleaned = value.strip().replace("Setp-", "Sep-")
        try:
            return datetime.strptime(cleaned, "%b-%y").strftime("%Y-%m")
        except ValueError as exc:
            raise ValueError(f"{source} is not a month: {value!r}") from exc
    raise ValueError(f"{source} is not a month: {value!r}")


def _load_cached(path: Path) -> Workbook:
    try:
        return load_workbook(path, data_only=True, read_only=False)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"source workbook not found: {path}") from exc


def _extract_indices(workbook: Workbook, spec: WorkbookSpec) -> dict[str, dict[str, str]]:
    base_key = spec.base_month.strftime("%Y-%m")
    series: dict[str, dict[str, str]] = {name: {} for name in SERIES_COLUMNS}
    base = workbook[spec.base_sheet]
    for name, column in SERIES_COLUMNS.items():
        cell = f"{column}{spec.base_row}"
        series[name][base_key] = _decimal_text(base[cell].value, source=f"{spec.base_sheet}!{cell}")

    for source in spec.index_rows:
        sheet = workbook[source.sheet]
        for row in source.rows:
            month = _month_key(sheet[f"B{row}"].value, source=f"{source.sheet}!B{row}")
            for name, column in SERIES_COLUMNS.items():
                cell = f"{column}{row}"
                series[name][month] = _decimal_text(sheet[cell].value, source=f"{source.sheet}!{cell}")
    return series


def _extract_rules(workbook: Workbook, bill: BillSpec) -> dict[str, Any]:
    sheet = workbook[bill.calculation_sheet]
    weights = {
        "labour": _decimal_text(sheet["J5"].value, source=f"{bill.calculation_sheet}!J5"),
        "plant": _decimal_text(sheet["J6"].value, source=f"{bill.calculation_sheet}!J6"),
        "fuel": _decimal_text(sheet["J7"].value, source=f"{bill.calculation_sheet}!J7"),
        "materials": _decimal_text(sheet["J8"].value, source=f"{bill.calculation_sheet}!J8"),
    }
    steel_split = tuple(
        _decimal(sheet[f"J{row}"].value, source=f"{bill.calculation_sheet}!J{row}")
        for row in range(10, 15)
    )
    expected_split = tuple(Decimal(value) for value in ("0.1", "0.5", "0.1", "0.1", "0.05"))
    if steel_split != expected_split:
        raise ValueError(f"{bill.calculation_sheet} steel split changed: {steel_split}")
    return {
        "quarter_mode": "measurement_date",
        "component_weights": weights,
        "adjustable_fraction": _decimal_text(sheet["J9"].value, source=f"{bill.calculation_sheet}!J9"),
        "negative_pvc_policy": "allow",
        "rounding_mode": "round_2",
    }


def _join_notes(*notes: str | None) -> str | None:
    present = [note for note in notes if note]
    return " ".join(present) if present else None


def _extract_bill(workbook: Workbook, spec: WorkbookSpec, bill: BillSpec) -> tuple[dict[str, Any], str | None]:
    sheet = workbook[spec.w_sheet]
    row = bill.source_row

    def source(column: str) -> str:
        return f"{spec.w_sheet}!{column}{row}"

    amounts: dict[str, Decimal] = {}
    for name, column in BILL_AMOUNT_COLUMNS.items():
        parser = _decimal if name == "on_account_amount" else _optional_decimal
        amounts[name] = parser(sheet[f"{column}{row}"].value, source=source(column))
    for name, cell in bill.amount_overrides.items():
        amounts[name] = _decimal(
            workbook[bill.calculation_sheet][cell].value,
            source=f"{bill.calculation_sheet}!{cell}",
        )
    extra_values: list[Decimal] = []
    direct_extra = _optional_decimal(sheet[f"K{row}"].value, source=source("K"))
    if direct_extra:
        extra_values.append(direct_extra)
    for cell in bill.extra_cells:
        extra_values.append(_decimal(sheet[cell].value, source=f"{spec.w_sheet}!{cell}"))

    measurement = sheet[f"B{row}"].value
    if not isinstance(measurement, (date, datetime)):
        raise ValueError(f"{source('B')} is not a date: {measurement!r}")

    extracted = {
        **{name: str(value) for name, value in amounts.items()},
        "recoveries_affecting_pvc": "0",
        "extra_item_decisions": [
            {"item_id": f"workbook-extra-{index}", "amount": str(value), "eligible": False}
            for index, value in enumerate(extra_values, start=1)
        ],
        "carry_forwards": [],
        "measurement_date": measurement.date().isoformat() if isinstance(measurement, datetime) else measurement.isoformat(),
        "prior_negative_carry_forward": "0",
    }

    derived_w = amounts["on_account_amount"] - sum(
        (value for name, value in amounts.items() if name != "on_account_amount"), Decimal("0")
    ) - sum(extra_values, Decimal("0"))
    calc_sheet = workbook[bill.calculation_sheet]
    calc_w = _decimal(calc_sheet["B5"].value, source=f"{bill.calculation_sheet}!B5")
    automatic_notes: list[str] = []
    if abs(derived_w - calc_w) > Decimal("0.01"):
        automatic_notes.append(
            f"Source-row deductions derive W={derived_w}, but {bill.calculation_sheet}!B5 uses {calc_w}."
        )
    for amount_name, cell in spec.formula_bucket_cells.items():
        source_amount = amounts[amount_name]
        formula_amount = _optional_decimal(
            calc_sheet[cell].value,
            source=f"{bill.calculation_sheet}!{cell}",
        )
        if abs(source_amount - formula_amount) > Decimal("0.01"):
            automatic_notes.append(
                f"{amount_name} is {source_amount} in "
                f"{spec.w_sheet}!{BILL_AMOUNT_COLUMNS[amount_name]}{row} "
                f"but {bill.calculation_sheet}!{cell} uses {formula_amount}."
            )
    return extracted, _join_notes(bill.divergence, *automatic_notes)


def _build_fixture(
    workbook: Workbook,
    spec: WorkbookSpec,
    bill: BillSpec,
    indices: dict[str, dict[str, str]],
) -> dict[str, Any]:
    extracted_bill, divergence = _extract_bill(workbook, spec, bill)
    fixture_indices = {
        name: dict(values)
        for name, values in indices.items()
    }
    for series_name, overrides in bill.index_overrides.items():
        fixture_indices[series_name].update(overrides)

    expected_value = workbook[bill.calculation_sheet][bill.expected_cell].value
    expected_total = _decimal(
        expected_value,
        source=f"{bill.calculation_sheet}!{bill.expected_cell}",
    )
    summary_value = _decimal(
        workbook[bill.summary_sheet][bill.summary_cell].value,
        source=f"{bill.summary_sheet}!{bill.summary_cell}",
    )
    if summary_value != expected_total:
        raise ValueError(
            f"{bill.summary_sheet}!{bill.summary_cell}={summary_value} does not match "
            f"{bill.calculation_sheet}!{bill.expected_cell}={expected_total}"
        )
    expected = {
        "total_pvc": str(expected_total),
        "tolerance": bill.tolerance,
    }
    notes: dict[str, Any] = {
        "source_tender": spec.contract,
        "source_bill": bill.label,
        "source_workbook": spec.workbook,
        "source_cells": {
            "bill_payload": f"{spec.w_sheet}!B{bill.source_row}:K{bill.source_row}",
            "expected_total_pvc": f"{bill.calculation_sheet}!{bill.expected_cell}",
            "summary_total_pvc": f"{bill.summary_sheet}!{bill.summary_cell}",
            "rules": f"{bill.calculation_sheet}!J5:J14",
            "base_indices": f"{spec.base_sheet}!C{spec.base_row}:K{spec.base_row}",
        },
        "verified_against": (
            "workbook calculation and summary cached formula results, cross-checked by "
            "engine/scripts/extract_pvc_fixtures.py"
        ),
        "reconciliation_status": (
            "workbook_divergence" if divergence else "reconciles"
        ),
    }
    if bill.xfail_reason:
        notes["xfail_reason"] = bill.xfail_reason
    if bill.current_engine_total is not None:
        notes["current_engine_total"] = bill.current_engine_total
    if bill.expected_validation_errors:
        notes["expected_validation_errors"] = list(bill.expected_validation_errors)
    if Decimal(bill.tolerance) > Decimal("0.01"):
        notes["tolerance_reason"] = (
            "Workbook rounds individual formula lines to 2dp; 0.15 covers the verified paise residual."
        )
    if bill.amount_overrides:
        notes["source_cells"]["bill_amount_overrides"] = {
            name: f"{bill.calculation_sheet}!{cell}"
            for name, cell in bill.amount_overrides.items()
        }
    if bill.index_overrides:
        notes["source_cells"]["index_overrides"] = (
            "Values documented in notes.workbook_divergence and required by the workbook calculation sheet"
        )
    if divergence:
        notes["workbook_divergence"] = divergence
    return {
        "bill": extracted_bill,
        "indices": {
            "base_month": spec.base_month.isoformat(),
            "series": fixture_indices,
        },
        "rules": _extract_rules(workbook, bill),
        "expected": expected,
        "notes": notes,
    }


def _serialized(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def extract_all(source_root: Path, output_dir: Path, *, check: bool) -> int:
    mismatches: list[Path] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for spec in SPECS:
        workbook = _load_cached(source_root / spec.workbook)
        try:
            indices = _extract_indices(workbook, spec)
            for bill in spec.bills:
                payload = _build_fixture(workbook, spec, bill, indices)
                path = output_dir / bill.filename
                content = _serialized(payload)
                if check:
                    if not path.exists() or path.read_text() != content:
                        mismatches.append(path)
                else:
                    path.write_text(content)
        finally:
            workbook.close()
    if mismatches:
        print("Fixtures differ from workbook extraction:")
        for path in mismatches:
            print(f"- {path}")
        return 1
    fixture_count = sum(len(spec.bills) for spec in SPECS)
    print(f"{'Checked' if check else 'Wrote'} {fixture_count} fixtures")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true", help="fail if committed fixtures differ from extraction")
    args = parser.parse_args()
    return extract_all(args.source_root, args.output_dir, check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
