"""
Comprehensive end-to-end test data for manual exercising of every built
RailPVC feature (GCC Clause 46A PVC billing OS).

Scenarios (see seeds/TEST_DATA.md for the full test matrix):
  A — Full happy-path contract (WR, inclusive, Active, pvc_applicable=TRUE):
        3 bills across Q2/Q3/Q4-2025, all item buckets, carry-forward,
        affects_pvc_base recovery, ExtraNS excluded, Approved PVC run
  B — Blocked-run contract: ExtraNS line with no decision → run blocks
  C1 — Negative-PVC, zero_floor policy (NER zone, Q4-2025, steel-heavy)
  C2 — Negative-PVC, allow policy  (NER zone, same bill → passes through)
  D — Supersede / approve / export (NR zone, Superseded + Approved run seeded)
  E — PVC-not-applicable contract (CR zone, pvc_applicable=FALSE)
  F — Draft / exclusive-GST contract (NCR zone, status Draft)
  G — Admin-user promotion in the test tenant
  H — Document-vault placeholder rows (one per document_type)

Run (Windows):
  PYTHONIOENCODING=utf-8 uv run python seeds/seed_test_data.py

Idempotent: re-running creates nothing, prints "skipped" for each row.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv

    import asyncpg
    from sqlalchemy.engine.url import make_url
except ModuleNotFoundError:
    if os.environ.get("RAILPVC_SEED_BACKEND_UV") != "1":
        env = os.environ.copy()
        env["RAILPVC_SEED_BACKEND_UV"] = "1"
        os.execvpe(
            "uv",
            ["uv", "--project", str(BACKEND_DIR), "run", "python", str(Path(__file__).resolve())],
            env,
        )
    raise

load_dotenv(BACKEND_DIR / ".env", override=True)

# Engine is an editable backend dependency — always importable here.
from engine.calculator import calculate_pvc
from engine.quarter import resolve_quarter
from engine.types import (
    BillPayload,
    CarryForwardPayload,
    ExtraItemDecision,
    IndexSnapshot,
    PVCRuleSet,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Default to a dedicated test tenant — NOT the demo tenant.
# Create this tenant first (log in once via Supabase to get it provisioned),
# then pass SEED_TENANT_ID=<uuid> or rely on this default.
TEST_TENANT_ID = os.environ.get(
    "SEED_TENANT_ID", "a0a0a0a0-1111-4000-8000-000000000001"
)

BASE_MONTH = date(2024, 12, 1)

INDEX_SERIES = (
    "labour", "plant_machinery", "fuel", "other_materials", "cement",
    "steel_tmt", "steel_angles", "steel_plates", "steel_other_sections",
)
RBI_SERIES = ("labour", "plant_machinery", "fuel", "other_materials", "cement")

# Months needing all 9 series (base + Q2-2025 + Q4-2025)
_FULL_MONTHS = [
    date(2024, 12, 1),
    date(2025, 4, 1), date(2025, 5, 1), date(2025, 6, 1),
    date(2025, 10, 1), date(2025, 11, 1), date(2025, 12, 1),
]
# Q3-2025 months — Contract A Bill 2 has zero steel; only RBI needed
_RBI_ONLY_MONTHS = [date(2025, 7, 1), date(2025, 8, 1), date(2025, 9, 1)]

STANDARD_WEIGHTS = {"labour": 0.20, "plant": 0.30, "fuel": 0.15, "materials": 0.20}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScheduleSeed:
    key: str
    name: str
    schedule_type: str
    bid_discount_pct: Decimal


@dataclass(frozen=True)
class ItemSeed:
    code: str
    schedule_key: str
    description: str
    unit: str
    original_qty: Decimal
    revised_qty: Decimal
    base_rate: Decimal
    agreement_rate: Decimal
    is_cement_item: bool = False
    steel_subtype: str | None = None


@dataclass(frozen=True)
class BillSeed:
    number: int
    bill_date: date
    measurement_date: date
    gross_amount: Decimal
    status: str


@dataclass(frozen=True)
class LineSeed:
    bill_number: int
    item_code: str
    qty_up_to_last: Decimal
    qty_since_last: Decimal
    qty_up_to_date: Decimal
    amount_up_to_last: Decimal
    amount_since_last: Decimal
    amount_up_to_date: Decimal
    special_condition_amount: Decimal = Decimal("0")


@dataclass(frozen=True)
class RecoverySeed:
    bill_number: int
    recovery_type: str
    amount: Decimal
    affects_pvc_base: bool = False


@dataclass(frozen=True)
class CarryFwdSeed:
    item_code: str
    source_bill_number: int
    target_bill_number: int
    recorded_qty: Decimal
    paid_qty_source: Decimal
    steel_subtype: str
    agreement_rate: Decimal


@dataclass(frozen=True)
class ExtraDecisionSeed:
    item_code: str
    eligible: bool | None
    notes: str


@dataclass(frozen=True)
class DocumentSeed:
    file_type: str
    storage_path: str
    original_filename: str


@dataclass
class ContractSpec:
    tender_number: str
    agreement_number: str
    loa_number: str
    loa_date: date
    contractor_name: str
    work_description: str
    contract_value: Decimal
    bid_amount: Decimal
    start_date: date
    completion_date: date
    base_month: date
    railway_zone: str
    gst_mode: str
    pvc_applicable: bool
    overall_rebate: Decimal
    status: str
    schedules: list[ScheduleSeed]
    items: list[ItemSeed]
    bills: list[BillSeed]
    lines: list[LineSeed]
    recoveries: list[RecoverySeed] = field(default_factory=list)
    carry_forwards: list[CarryFwdSeed] = field(default_factory=list)
    extra_decisions: list[ExtraDecisionSeed] = field(default_factory=list)
    documents: list[DocumentSeed] = field(default_factory=list)
    rule_set_override: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Scenario A — Full happy-path (WR, inclusive, Active, pvc_applicable=TRUE)
# ---------------------------------------------------------------------------
# Three bills across Q2/Q3/Q4-2025.
# Bill 2 has zero steel amounts so Q3-2025 (RBI-only) calculates cleanly.
# Bill 3 introduces steel plates and a carry-forward for angles from Bill 1.
# The ExtraNS lump-sum is excluded (decision=FALSE) in Bill 1 only.

_A_SCHED = [
    ScheduleSeed("DSR",    "Schedule A – DSR Items",       "DSR",    Decimal("-0.30")),
    ScheduleSeed("NS",     "Schedule B – NS Items",        "NS",     Decimal("-0.30")),
    ScheduleSeed("ExtraNS","Schedule C – Extra NS Items",  "ExtraNS",Decimal("0")),
]

_A_ITEMS = [
    ItemSeed("A-DSR-CEM","DSR","Cement concrete M15 in foundation",
             "Cum", Decimal("500"), Decimal("500"), Decimal("4000"), Decimal("2800"),
             is_cement_item=True),
    # revised_qty > original — exercises that UI display
    ItemSeed("A-DSR-PLN","DSR","Earthwork in excavation",
             "Cum", Decimal("1000"), Decimal("1200"), Decimal("600"), Decimal("420")),
    # revised_qty < original — exercises the other direction
    ItemSeed("A-DSR-TMT","DSR","TMT reinforcement bars Fe-500D",
             "Kg",  Decimal("10000"), Decimal("8000"), Decimal("75"), Decimal("52.50"),
             steel_subtype="tmt"),
    ItemSeed("A-NS-PLN","NS","Supply and fix vitrified tiles 600×600 mm",
             "Sqm", Decimal("300"), Decimal("300"), Decimal("1800"), Decimal("1260")),
    ItemSeed("A-NS-ANG","NS","Structural steel angles 75×75×6 ISA",
             "Kg",  Decimal("8000"), Decimal("8000"), Decimal("90"), Decimal("63"),
             steel_subtype="angles"),
    ItemSeed("A-NS-PLT","NS","Steel plates 10 mm IS 2062",
             "Kg",  Decimal("3000"), Decimal("3000"), Decimal("90"), Decimal("63"),
             steel_subtype="plates"),
    ItemSeed("A-NS-SEC","NS","Steel channel sections ISMC-150",
             "Kg",  Decimal("2000"), Decimal("2000"), Decimal("90"), Decimal("63"),
             steel_subtype="other_sections"),
    ItemSeed("A-ENS-LMP","ExtraNS","Extra NS – Project mobilization lump sum",
             "LS",  Decimal("1"), Decimal("1"), Decimal("1500000"), Decimal("1500000")),
]

_A_BILLS = [
    # Bill 1 → Q2-2025 (Apr-May-Jun) — all indices available
    BillSeed(1, date(2025, 4, 30), date(2025, 4, 20), Decimal("2202100"), "Approved"),
    # Bill 2 → Q3-2025 (Jul-Aug-Sep) — RBI only; steel amounts = 0 so JPC not needed
    BillSeed(2, date(2025, 7, 31), date(2025, 7, 20), Decimal("337400"),  "Imported"),
    # Bill 3 → Q4-2025 (Oct-Nov-Dec) — all indices available; plates introduced
    BillSeed(3, date(2025, 11, 30), date(2025, 11, 20), Decimal("361550"), "Draft"),
]

_D = Decimal
_A_LINES = [
    # Bill 1 — first bill, qty_up_to_last = 0 for all
    LineSeed(1,"A-DSR-CEM",_D("0"),_D("100"),_D("100"),_D("0"),_D("280000"),_D("280000")),
    LineSeed(1,"A-DSR-PLN",_D("0"),_D("200"),_D("200"),_D("0"),_D("84000"), _D("84000"),
             special_condition_amount=_D("5000")),  # display-only withheld
    LineSeed(1,"A-DSR-TMT",_D("0"),_D("2000"),_D("2000"),_D("0"),_D("105000"),_D("105000")),
    LineSeed(1,"A-NS-PLN", _D("0"),_D("80"),  _D("80"),  _D("0"),_D("100800"),_D("100800")),
    LineSeed(1,"A-NS-ANG", _D("0"),_D("1500"),_D("1500"),_D("0"),_D("94500"), _D("94500")),
    LineSeed(1,"A-NS-PLT", _D("0"),_D("0"),   _D("0"),   _D("0"),_D("0"),     _D("0")),
    LineSeed(1,"A-NS-SEC", _D("0"),_D("600"), _D("600"), _D("0"),_D("37800"), _D("37800")),
    LineSeed(1,"A-ENS-LMP",_D("0"),_D("1"),   _D("1"),   _D("0"),_D("1500000"),_D("1500000")),

    # Bill 2 — cement/plain work only; zero steel since_last (Q3-2025 clean calc)
    LineSeed(2,"A-DSR-CEM",_D("100"),_D("80"), _D("180"),_D("280000"),_D("224000"),_D("504000")),
    LineSeed(2,"A-DSR-PLN",_D("200"),_D("150"),_D("350"),_D("84000"), _D("63000"), _D("147000")),
    LineSeed(2,"A-DSR-TMT",_D("2000"),_D("0"),_D("2000"),_D("105000"),_D("0"),    _D("105000")),
    LineSeed(2,"A-NS-PLN", _D("80"),  _D("40"),_D("120"),_D("100800"),_D("50400"),_D("151200")),
    LineSeed(2,"A-NS-ANG", _D("1500"),_D("0"),_D("1500"),_D("94500"), _D("0"),    _D("94500")),
    LineSeed(2,"A-NS-PLT", _D("0"),   _D("0"),_D("0"),   _D("0"),     _D("0"),    _D("0")),
    LineSeed(2,"A-NS-SEC", _D("600"), _D("0"),_D("600"), _D("37800"), _D("0"),    _D("37800")),

    # Bill 3 — steel resumes; plates introduced; carry-forward for angles
    LineSeed(3,"A-DSR-CEM",_D("180"),_D("50"), _D("230"),_D("504000"),_D("140000"),_D("644000")),
    LineSeed(3,"A-DSR-PLN",_D("350"),_D("100"),_D("450"),_D("147000"),_D("42000"), _D("189000")),
    LineSeed(3,"A-DSR-TMT",_D("2000"),_D("1500"),_D("3500"),_D("105000"),_D("78750"),_D("183750")),
    LineSeed(3,"A-NS-PLN", _D("120"),_D("30"), _D("150"),_D("151200"),_D("37800"), _D("189000")),
    LineSeed(3,"A-NS-ANG", _D("1500"),_D("500"),_D("2000"),_D("94500"),_D("31500"), _D("126000")),
    LineSeed(3,"A-NS-PLT", _D("0"),   _D("300"),_D("300"),_D("0"),    _D("18900"), _D("18900")),
    LineSeed(3,"A-NS-SEC", _D("600"), _D("200"),_D("800"),_D("37800"), _D("12600"), _D("50400")),
]

_A_RECOVERIES = [
    RecoverySeed(1, "security_deposit", _D("100000"), False),
    RecoverySeed(1, "income_tax",       _D("50000"),  False),
    RecoverySeed(1, "water",            _D("15000"),  True),   # ← reduces PVC base (technical_withheld)
    RecoverySeed(2, "labour_cess",      _D("3374"),   False),
    RecoverySeed(2, "other",            _D("20000"),  True),   # ← reduces PVC base
    RecoverySeed(3, "security_deposit", _D("80000"),  False),
    RecoverySeed(3, "income_tax",       _D("40000"),  False),
]

# Carry-forward: angles from Bill 1 → Bill 3 (skip Bill 2, no steel that quarter)
_A_CARRY = [
    CarryFwdSeed(
        item_code="A-NS-ANG",
        source_bill_number=1, target_bill_number=3,
        recorded_qty=_D("1500"), paid_qty_source=_D("900"),
        steel_subtype="angles", agreement_rate=_D("63"),
    ),
]

_A_DECISIONS = [
    ExtraDecisionSeed("A-ENS-LMP", eligible=False,
                      notes="Mobilization lump-sum excluded from PVC per Clause 46A.5"),
]

_A_DOCS = [
    DocumentSeed("agreement",  "test-tenant/contracts/A/agreement.pdf",  "Contract_Agreement.pdf"),
    DocumentSeed("mb",         "test-tenant/contracts/A/mb1.pdf",         "MB1_Measurements.pdf"),
    DocumentSeed("bill",       "test-tenant/contracts/A/bill1.pdf",       "Running_Bill_1.pdf"),
    DocumentSeed("recovery",   "test-tenant/contracts/A/rec1.pdf",        "Recovery_Statement_1.pdf"),
    DocumentSeed("workbook",   "test-tenant/contracts/A/pvc_wb.xlsx",     "PVC_Workbook.xlsx"),
    DocumentSeed("other",      "test-tenant/contracts/A/site_photo.pdf",  "Site_Photo_Report.pdf"),
]

CONTRACT_A = ContractSpec(
    tender_number="TEST-A-WR-252",
    agreement_number="WR/TEST/Civil/2025/TEST-A",
    loa_number="TEST-WR-LOA-0001",
    loa_date=date(2025, 1, 15),
    contractor_name="TEST CONTRACTOR ALPHA PVT LTD",
    work_description="Test Contract A — full happy-path including all PVC buckets",
    contract_value=_D("5000000"),
    bid_amount=_D("4750000"),
    start_date=date(2025, 2, 1),
    completion_date=date(2026, 12, 31),
    base_month=BASE_MONTH,
    railway_zone="WR",
    gst_mode="inclusive",
    pvc_applicable=True,
    overall_rebate=_D("-0.02"),
    status="Active",
    schedules=_A_SCHED,
    items=_A_ITEMS,
    bills=_A_BILLS,
    lines=_A_LINES,
    recoveries=_A_RECOVERIES,
    carry_forwards=_A_CARRY,
    extra_decisions=_A_DECISIONS,
    documents=_A_DOCS,
)

# ---------------------------------------------------------------------------
# Scenario B — Blocked-run (identical skeleton, ExtraNS has NO decision row)
# ---------------------------------------------------------------------------

CONTRACT_B = ContractSpec(
    tender_number="TEST-B-WR-BLOCKED",
    agreement_number="WR/TEST/Civil/2025/TEST-B",
    loa_number="TEST-WR-LOA-0002",
    loa_date=date(2025, 1, 15),
    contractor_name="TEST CONTRACTOR BETA PVT LTD",
    work_description="Test Contract B — blocked PVC run (undecided ExtraNS)",
    contract_value=_D("3000000"),
    bid_amount=_D("2850000"),
    start_date=date(2025, 2, 1),
    completion_date=date(2026, 12, 31),
    base_month=BASE_MONTH,
    railway_zone="WR",
    gst_mode="inclusive",
    pvc_applicable=True,
    overall_rebate=_D("0"),
    status="Active",
    schedules=[
        ScheduleSeed("DSR",    "Schedule A – DSR",    "DSR",    _D("-0.30")),
        ScheduleSeed("NS",     "Schedule B – NS",     "NS",     _D("-0.30")),
        ScheduleSeed("ExtraNS","Schedule C – ExtraNS","ExtraNS",_D("0")),
    ],
    items=[
        ItemSeed("B-DSR-CEM","DSR","Cement plaster 12mm CM 1:4","Sqm",
                 _D("2000"),_D("2000"),_D("300"),_D("210"),is_cement_item=True),
        ItemSeed("B-NS-PLN","NS","UPVC windows with fittings","Sqm",
                 _D("400"),_D("400"),_D("3500"),_D("2450")),
        # ExtraNS item — deliberately has NO extra_item_decision (triggers block)
        ItemSeed("B-ENS-LMP","ExtraNS","Extra NS – Electrical fitments lump sum","LS",
                 _D("1"),_D("1"),_D("800000"),_D("800000")),
    ],
    bills=[
        BillSeed(1, date(2025, 5, 31), date(2025, 5, 20), _D("1430000"), "Imported"),
    ],
    lines=[
        LineSeed(1,"B-DSR-CEM",_D("0"),_D("800"),_D("800"),_D("0"),_D("168000"),_D("168000")),
        LineSeed(1,"B-NS-PLN", _D("0"),_D("180"),_D("180"),_D("0"),_D("441000"),_D("441000")),
        LineSeed(1,"B-ENS-LMP",_D("0"),_D("1"),  _D("1"),  _D("0"),_D("800000"),_D("800000")),
    ],
    recoveries=[
        RecoverySeed(1,"security_deposit",_D("50000"),False),
    ],
    # Intentionally NO extra_decisions → engine sees eligible=None → blocks
    extra_decisions=[],
)

# ---------------------------------------------------------------------------
# Scenario C — Negative-PVC pair (NER zone, Q4-2025, steel-heavy TMT)
# Steel TMT drops ~9.4% in Q4-2025 vs Dec-2024 base → total PVC is negative.
# ---------------------------------------------------------------------------

_C_SCHED = [
    ScheduleSeed("DSR","Schedule A – DSR","DSR",_D("-0.25")),
    ScheduleSeed("NS", "Schedule B – NS", "NS", _D("-0.25")),
]

_C_ITEMS = [
    # Large TMT quantity dominates; steel-TMT index fell in Q4-2025 → negative
    ItemSeed("C-DSR-TMT","DSR","TMT reinforcement bars Fe-500D, IS 1786","Kg",
             _D("100000"),_D("100000"),_D("70"),_D("52.50"),steel_subtype="tmt"),
    ItemSeed("C-DSR-PLN","DSR","Plain cement concrete PCC M10","Cum",
             _D("200"),_D("200"),_D("560"),_D("420")),
]

_C_BILLS = [
    BillSeed(1, date(2025, 10, 31), date(2025, 10, 15), _D("2121000"), "Imported"),
]

_C_LINES = [
    LineSeed(1,"C-DSR-TMT",_D("0"),_D("40000"),_D("40000"),_D("0"),_D("2100000"),_D("2100000")),
    LineSeed(1,"C-DSR-PLN",_D("0"),_D("50"),   _D("50"),   _D("0"),_D("21000"),  _D("21000")),
]

# C1: zero_floor — negative PVC is floored to 0
CONTRACT_C1 = ContractSpec(
    tender_number="TEST-C1-NER-FLOOR",
    agreement_number="NER/TEST/Civil/2025/TEST-C1",
    loa_number="TEST-NER-LOA-0003",
    loa_date=date(2025, 1, 20),
    contractor_name="TEST CONTRACTOR GAMMA PVT LTD",
    work_description="Test C1 — negative PVC, zero_floor policy",
    contract_value=_D("15000000"),
    bid_amount=_D("14250000"),
    start_date=date(2025, 2, 1),
    completion_date=date(2027, 1, 31),
    base_month=BASE_MONTH,
    railway_zone="NER",
    gst_mode="exclusive",
    pvc_applicable=True,
    overall_rebate=_D("0"),
    status="Active",
    schedules=_C_SCHED,
    items=_C_ITEMS,
    bills=_C_BILLS,
    lines=_C_LINES,
    recoveries=[RecoverySeed(1,"security_deposit",_D("200000"),False)],
    rule_set_override={"negative_pvc_policy": "zero_floor"},
)

# C2: allow — negative PVC passes through unchanged
CONTRACT_C2 = ContractSpec(
    tender_number="TEST-C2-NER-ALLOW",
    agreement_number="NER/TEST/Civil/2025/TEST-C2",
    loa_number="TEST-NER-LOA-0004",
    loa_date=date(2025, 1, 20),
    contractor_name="TEST CONTRACTOR DELTA PVT LTD",
    work_description="Test C2 — negative PVC, allow policy (passes through)",
    contract_value=_D("15000000"),
    bid_amount=_D("14250000"),
    start_date=date(2025, 2, 1),
    completion_date=date(2027, 1, 31),
    base_month=BASE_MONTH,
    railway_zone="NER",
    gst_mode="exclusive",
    pvc_applicable=True,
    overall_rebate=_D("0"),
    status="Active",
    schedules=_C_SCHED,
    items=_C_ITEMS,
    bills=_C_BILLS,
    lines=_C_LINES,
    recoveries=[RecoverySeed(1,"security_deposit",_D("200000"),False)],
    rule_set_override={"negative_pvc_policy": "allow"},
)

# ---------------------------------------------------------------------------
# Scenario D — Supersede / approve / export (NR zone)
# Seed one Superseded run + one Approved run for the same bill so the UI
# shows run history. Approved run enables export endpoint testing.
# ---------------------------------------------------------------------------

CONTRACT_D = ContractSpec(
    tender_number="TEST-D-NR-EXPORT",
    agreement_number="NR/TEST/Civil/2025/TEST-D",
    loa_number="TEST-NR-LOA-0005",
    loa_date=date(2025, 1, 25),
    contractor_name="TEST CONTRACTOR EPSILON PVT LTD",
    work_description="Test D — supersede/approve/export flow",
    contract_value=_D("2000000"),
    bid_amount=_D("1900000"),
    start_date=date(2025, 2, 1),
    completion_date=date(2026, 6, 30),
    base_month=BASE_MONTH,
    railway_zone="NR",
    gst_mode="inclusive",
    pvc_applicable=True,
    overall_rebate=_D("-0.01"),
    status="Active",
    schedules=[
        ScheduleSeed("DSR","Schedule A – DSR","DSR",_D("-0.30")),
        ScheduleSeed("NS", "Schedule B – NS", "NS", _D("-0.30")),
    ],
    items=[
        ItemSeed("D-DSR-CEM","DSR","Cement concrete M20 in columns","Cum",
                 _D("300"),_D("300"),_D("4000"),_D("2800"),is_cement_item=True),
        ItemSeed("D-NS-PLN","NS","Aluminium sliding windows with fittings","Sqm",
                 _D("200"),_D("200"),_D("1800"),_D("1260")),
    ],
    bills=[
        BillSeed(1, date(2025, 5, 31), date(2025, 5, 20), _D("686000"), "Approved"),
    ],
    lines=[
        LineSeed(1,"D-DSR-CEM",_D("0"),_D("200"),_D("200"),_D("0"),_D("560000"),_D("560000")),
        LineSeed(1,"D-NS-PLN", _D("0"),_D("100"),_D("100"),_D("0"),_D("126000"),_D("126000")),
    ],
    recoveries=[
        RecoverySeed(1,"security_deposit",_D("30000"),False),
        RecoverySeed(1,"income_tax",       _D("15000"),False),
    ],
)

# ---------------------------------------------------------------------------
# Scenario E — PVC not applicable (CR zone, pvc_applicable=FALSE)
# ---------------------------------------------------------------------------

CONTRACT_E = ContractSpec(
    tender_number="TEST-E-CR-NOPVC",
    agreement_number="CR/TEST/Civil/2025/TEST-E",
    loa_number="TEST-CR-LOA-0006",
    loa_date=date(2025, 2, 1),
    contractor_name="TEST CONTRACTOR ZETA PVT LTD",
    work_description="Test E — PVC not applicable (CR zone)",
    contract_value=_D("800000"),
    bid_amount=_D("760000"),
    start_date=date(2025, 3, 1),
    completion_date=date(2025, 12, 31),
    base_month=BASE_MONTH,
    railway_zone="CR",
    gst_mode="exclusive",
    pvc_applicable=False,
    overall_rebate=_D("0"),
    status="Active",
    schedules=[ScheduleSeed("DSR","Schedule A – DSR","DSR",_D("-0.20"))],
    items=[
        ItemSeed("E-DSR-PLN","DSR","Random rubble stone masonry","Cum",
                 _D("500"),_D("500"),_D("1200"),_D("960")),
    ],
    bills=[
        BillSeed(1, date(2025, 5, 31), date(2025, 5, 20), _D("192000"), "Imported"),
    ],
    lines=[
        LineSeed(1,"E-DSR-PLN",_D("0"),_D("200"),_D("200"),_D("0"),_D("192000"),_D("192000")),
    ],
)

# ---------------------------------------------------------------------------
# Scenario F — Draft / exclusive-GST contract (NCR zone, status Draft)
# ---------------------------------------------------------------------------

CONTRACT_F = ContractSpec(
    tender_number="TEST-F-NCR-DRAFT",
    agreement_number=None,
    loa_number=None,
    loa_date=None,
    contractor_name="TEST CONTRACTOR ETA PVT LTD",
    work_description="Test F — Draft exclusive-GST contract (NCR zone)",
    contract_value=_D("3500000"),
    bid_amount=_D("3325000"),
    start_date=None,
    completion_date=None,
    base_month=BASE_MONTH,
    railway_zone="NCR",
    gst_mode="exclusive",
    pvc_applicable=True,
    overall_rebate=_D("0"),
    status="Configured",
    schedules=[ScheduleSeed("DSR","Schedule A – DSR","DSR",_D("-0.28"))],
    items=[
        ItemSeed("F-DSR-CEM","DSR","RCC M25 in footings","Cum",
                 _D("400"),_D("400"),_D("6000"),_D("4320"),is_cement_item=True),
        ItemSeed("F-DSR-TMT","DSR","TMT bars Fe-500","Kg",
                 _D("20000"),_D("20000"),_D("80"),_D("57.6"),steel_subtype="tmt"),
    ],
    bills=[],
    lines=[],
)

ALL_CONTRACTS = [CONTRACT_A, CONTRACT_B, CONTRACT_C1, CONTRACT_C2,
                 CONTRACT_D, CONTRACT_E, CONTRACT_F]

# ---------------------------------------------------------------------------
# Expected W buckets for golden assertions
# Format: {(tender_number, bill_number): {bucket_key: Decimal}}
# technical_withheld = SUM(recoveries.amount WHERE affects_pvc_base=TRUE)
# extra_items = SUM(extra_item_decisions.amount WHERE eligible=FALSE)
# ---------------------------------------------------------------------------

EXPECTED_W: dict[tuple[str, int], dict[str, Decimal]] = {
    ("TEST-A-WR-252", 1): {
        "on_account":        _D("2202100"),
        "cement":            _D("280000"),
        "steel_angles":      _D("94500"),
        "steel_plates":      _D("0"),
        "steel_tmt":         _D("105000"),
        "steel_other":       _D("37800"),
        "technical_withheld":_D("15000"),  # water recovery affects_pvc_base=TRUE
        "extra_items":       _D("1500000"),
        "w":                 _D("169800"),
    },
    ("TEST-A-WR-252", 2): {
        "on_account":        _D("337400"),
        "cement":            _D("224000"),
        "steel_angles":      _D("0"),
        "steel_plates":      _D("0"),
        "steel_tmt":         _D("0"),
        "steel_other":       _D("0"),
        "technical_withheld":_D("20000"),  # other recovery affects_pvc_base=TRUE
        "extra_items":       _D("0"),
        "w":                 _D("93400"),
    },
    ("TEST-B-WR-BLOCKED", 1): {
        "on_account":        _D("1430000"),
        "cement":            _D("168000"),
        "steel_angles":      _D("0"),
        "steel_plates":      _D("0"),
        "steel_tmt":         _D("0"),
        "steel_other":       _D("0"),
        "technical_withheld":_D("0"),
        # extra_items can't be summed — no decision yet (that's the point)
        # validation checks only buckets that don't depend on decisions
        "extra_items":       _D("0"),  # placeholder; skip extra_items check for B
        "w":                 _D("0"),  # placeholder; skip W check for B
    },
    ("TEST-C1-NER-FLOOR", 1): {
        "on_account":        _D("2121000"),
        "cement":            _D("0"),
        "steel_angles":      _D("0"),
        "steel_plates":      _D("0"),
        "steel_tmt":         _D("2100000"),
        "steel_other":       _D("0"),
        "technical_withheld":_D("0"),
        "extra_items":       _D("0"),
        "w":                 _D("21000"),
    },
    ("TEST-D-NR-EXPORT", 1): {
        "on_account":        _D("686000"),
        "cement":            _D("560000"),
        "steel_angles":      _D("0"),
        "steel_plates":      _D("0"),
        "steel_tmt":         _D("0"),
        "steel_other":       _D("0"),
        "technical_withheld":_D("0"),
        "extra_items":       _D("0"),
        "w":                 _D("126000"),
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class Counts(dict):
    def add(self, key: str, created: bool) -> None:
        suffix = "created" if created else "skipped"
        self[f"{key}_{suffix}"] = self.get(f"{key}_{suffix}", 0) + 1


def _dec(v: Any) -> Decimal:
    return Decimal(str(v))


async def connect() -> asyncpg.Connection:
    raw = os.environ["DATABASE_URL"].strip()
    u = make_url(raw)
    try:
        return await asyncpg.connect(
            host=u.host, port=u.port, user=u.username,
            password=str(u.password), database=u.database,
        )
    except (asyncpg.PostgresError, OSError) as exc:
        raise SystemExit(
            f"Cannot connect via backend/.env DATABASE_URL. Postgres: {exc}"
        ) from exc


async def require_tenant(conn: asyncpg.Connection) -> None:
    row = await conn.fetchrow("SELECT id FROM tenants WHERE id = $1::uuid", TEST_TENANT_ID)
    if row is None:
        raise SystemExit(
            f"Tenant {TEST_TENANT_ID!r} not found.\n"
            "Log in once via the app to provision the test tenant, then re-run.\n"
            "Or set SEED_TENANT_ID=<your-tenant-uuid> in the environment."
        )


async def require_indices(conn: asyncpg.Connection) -> None:
    # Check all 9 series for base + Q2 + Q4 months
    rows = await conn.fetch(
        """
        SELECT s.name, o.month
        FROM index_series s
        JOIN index_observations o ON o.series_id = s.id
        WHERE s.name = ANY($1::text[]) AND o.month = ANY($2::date[])
        """,
        list(INDEX_SERIES), _FULL_MONTHS,
    )
    present_full = {(r["name"], r["month"]) for r in rows}
    missing_full = [
        (s, m) for s in INDEX_SERIES for m in _FULL_MONTHS
        if (s, m) not in present_full
    ]

    # Check only RBI series for Q3 months (JPC steel is None → OK for zero-steel bill)
    rows2 = await conn.fetch(
        """
        SELECT s.name, o.month
        FROM index_series s
        JOIN index_observations o ON o.series_id = s.id
        WHERE s.name = ANY($1::text[]) AND o.month = ANY($2::date[])
        """,
        list(RBI_SERIES), _RBI_ONLY_MONTHS,
    )
    present_rbi = {(r["name"], r["month"]) for r in rows2}
    missing_rbi = [
        (s, m) for s in RBI_SERIES for m in _RBI_ONLY_MONTHS
        if (s, m) not in present_rbi
    ]

    missing = missing_full + missing_rbi
    if missing:
        preview = ", ".join(f"{s}:{m:%Y-%m}" for s, m in missing[:10])
        more = f" ... +{len(missing)-10} more" if len(missing) > 10 else ""
        raise SystemExit(
            "Missing required index observations. Run first:\n"
            "  uv run python seeds/seed_indices.py\n"
            f"Missing: {preview}{more}"
        )


async def get_or_create_contract(conn: asyncpg.Connection, spec: ContractSpec) -> tuple[str, bool]:
    existing = await conn.fetchrow(
        "SELECT id::text AS id FROM contracts WHERE tenant_id=$1::uuid AND tender_number=$2",
        TEST_TENANT_ID, spec.tender_number,
    )
    if existing:
        return existing["id"], False

    row = await conn.fetchrow(
        """
        INSERT INTO contracts (
            tenant_id, tender_number, agreement_number, loa_number, loa_date,
            contractor_name, work_description, contract_value, bid_amount,
            start_date, completion_date, base_month, railway_zone, gst_mode,
            pvc_applicable, overall_rebate, status
        )
        VALUES (
            $1::uuid,$2,$3,$4,$5::date,$6,$7,$8,$9,
            $10::date,$11::date,$12::date,$13::railway_zone,$14::gst_mode,
            $15,$16,$17::contract_status
        )
        RETURNING id::text AS id
        """,
        TEST_TENANT_ID, spec.tender_number, spec.agreement_number,
        spec.loa_number, spec.loa_date, spec.contractor_name,
        spec.work_description, spec.contract_value, spec.bid_amount,
        spec.start_date, spec.completion_date, spec.base_month,
        spec.railway_zone, spec.gst_mode, spec.pvc_applicable,
        spec.overall_rebate, spec.status,
    )
    assert row is not None
    return row["id"], True


async def get_or_create_rule_set(
    conn: asyncpg.Connection, contract_id: str, override: dict | None
) -> tuple[str, bool]:
    policy = (override or {}).get("negative_pvc_policy", "zero_floor")
    row = await conn.fetchrow(
        """
        INSERT INTO pvc_rule_sets (
            contract_id, version, quarter_mode, component_weights,
            extra_item_policy, adjustable_fraction, rounding_mode, negative_pvc_policy
        )
        VALUES (
            $1::uuid, 1, 'measurement_date'::quarter_mode, $2::jsonb,
            'exclude_by_default'::extra_item_policy, 0.85,
            'round_2'::rounding_mode, $3::negative_pvc_policy
        )
        ON CONFLICT (contract_id, version) DO NOTHING
        RETURNING id::text AS id
        """,
        contract_id, json.dumps(STANDARD_WEIGHTS), policy,
    )
    if row:
        return row["id"], True
    existing = await conn.fetchrow(
        "SELECT id::text AS id FROM pvc_rule_sets WHERE contract_id=$1::uuid AND version=1",
        contract_id,
    )
    assert existing is not None
    return existing["id"], False


async def get_or_create_schedule(
    conn: asyncpg.Connection, contract_id: str, seed: ScheduleSeed
) -> tuple[str, bool]:
    existing = await conn.fetchrow(
        """
        SELECT id::text AS id FROM schedules
        WHERE contract_id=$1::uuid AND name=$2 AND schedule_type=$3::schedule_type
        """,
        contract_id, seed.name, seed.schedule_type,
    )
    if existing:
        return existing["id"], False
    row = await conn.fetchrow(
        """
        INSERT INTO schedules (contract_id, name, schedule_type, bid_discount_pct)
        VALUES ($1::uuid,$2,$3::schedule_type,$4) RETURNING id::text AS id
        """,
        contract_id, seed.name, seed.schedule_type, seed.bid_discount_pct,
    )
    assert row is not None
    return row["id"], True


async def get_or_create_item(
    conn: asyncpg.Connection, contract_id: str, schedule_id: str, seed: ItemSeed
) -> tuple[str, bool]:
    existing = await conn.fetchrow(
        "SELECT id::text AS id FROM contract_items WHERE contract_id=$1::uuid AND item_code=$2",
        contract_id, seed.code,
    )
    if existing:
        return existing["id"], False
    row = await conn.fetchrow(
        """
        INSERT INTO contract_items (
            contract_id, schedule_id, item_code, description, unit,
            original_qty, revised_qty, base_rate, agreement_rate,
            is_cement_item, steel_subtype
        )
        VALUES ($1::uuid,$2::uuid,$3,$4,$5,$6,$7,$8,$9,$10,$11::steel_subtype)
        RETURNING id::text AS id
        """,
        contract_id, schedule_id, seed.code, seed.description, seed.unit,
        seed.original_qty, seed.revised_qty, seed.base_rate, seed.agreement_rate,
        seed.is_cement_item, seed.steel_subtype,
    )
    assert row is not None
    return row["id"], True


async def get_or_create_bill(
    conn: asyncpg.Connection, contract_id: str, seed: BillSeed
) -> tuple[str, bool]:
    row = await conn.fetchrow(
        """
        INSERT INTO running_bills (
            contract_id, bill_number, bill_date, measurement_date,
            gross_amount, net_amount, status
        )
        VALUES ($1::uuid,$2,$3::date,$4::date,$5,NULL,$6::bill_status)
        ON CONFLICT (contract_id, bill_number) DO NOTHING
        RETURNING id::text AS id
        """,
        contract_id, seed.number, seed.bill_date,
        seed.measurement_date, seed.gross_amount, seed.status,
    )
    if row:
        return row["id"], True
    existing = await conn.fetchrow(
        "SELECT id::text AS id FROM running_bills WHERE contract_id=$1::uuid AND bill_number=$2",
        contract_id, seed.number,
    )
    assert existing is not None
    return existing["id"], False


async def insert_bill_line(
    conn: asyncpg.Connection, bill_id: str, item_id: str, seed: LineSeed
) -> bool:
    row = await conn.fetchrow(
        """
        INSERT INTO bill_lines (
            bill_id, item_id,
            qty_up_to_last, qty_since_last, qty_up_to_date,
            amount_up_to_last, amount_since_last, amount_up_to_date,
            special_condition_amount
        )
        VALUES ($1::uuid,$2::uuid,$3,$4,$5,$6,$7,$8,$9)
        ON CONFLICT (bill_id, item_id) DO NOTHING
        RETURNING id
        """,
        bill_id, item_id,
        seed.qty_up_to_last, seed.qty_since_last, seed.qty_up_to_date,
        seed.amount_up_to_last, seed.amount_since_last, seed.amount_up_to_date,
        seed.special_condition_amount,
    )
    return row is not None


async def insert_recovery(
    conn: asyncpg.Connection, bill_id: str, seed: RecoverySeed
) -> bool:
    existing = await conn.fetchrow(
        """
        SELECT id FROM recoveries
        WHERE bill_id=$1::uuid AND recovery_type=$2::recovery_type
          AND amount=$3 AND affects_pvc_base=$4
        """,
        bill_id, seed.recovery_type, seed.amount, seed.affects_pvc_base,
    )
    if existing:
        return False
    await conn.execute(
        """
        INSERT INTO recoveries (bill_id, recovery_type, amount, affects_pvc_base)
        VALUES ($1::uuid,$2::recovery_type,$3,$4)
        """,
        bill_id, seed.recovery_type, seed.amount, seed.affects_pvc_base,
    )
    return True


async def insert_extra_decision(
    conn: asyncpg.Connection, contract_id: str, item_id: str, seed: ExtraDecisionSeed
) -> bool:
    row = await conn.fetchrow(
        """
        INSERT INTO extra_item_decisions (
            contract_id, item_id, eligible, decided_by, decided_at, notes
        )
        VALUES ($1::uuid,$2::uuid,$3,'seed_test_data.py',NOW(),$4)
        ON CONFLICT (contract_id, item_id) DO NOTHING
        RETURNING id
        """,
        contract_id, item_id, seed.eligible, seed.notes,
    )
    return row is not None


async def insert_carry_forward(
    conn: asyncpg.Connection, contract_id: str, item_id: str,
    source_bill_id: str, target_bill_id: str, seed: CarryFwdSeed,
) -> bool:
    existing = await conn.fetchrow(
        """
        SELECT id FROM carry_forwards
        WHERE contract_id=$1::uuid AND item_id=$2::uuid
          AND source_bill_id=$3::uuid AND target_bill_id=$4::uuid
        """,
        contract_id, item_id, source_bill_id, target_bill_id,
    )
    if existing:
        return False
    paid_ratio = seed.paid_qty_source / seed.recorded_qty
    carry_qty  = seed.recorded_qty - seed.paid_qty_source
    await conn.execute(
        """
        INSERT INTO carry_forwards (
            contract_id, item_id, source_bill_id, target_bill_id,
            recorded_qty, paid_qty_source, paid_ratio, carry_qty, steel_subtype
        )
        VALUES ($1::uuid,$2::uuid,$3::uuid,$4::uuid,$5,$6,$7,$8,$9::steel_subtype)
        """,
        contract_id, item_id, source_bill_id, target_bill_id,
        seed.recorded_qty, seed.paid_qty_source, paid_ratio, carry_qty,
        seed.steel_subtype,
    )
    return True


async def insert_document(
    conn: asyncpg.Connection, contract_id: str, seed: DocumentSeed
) -> bool:
    existing = await conn.fetchrow(
        "SELECT id FROM documents WHERE contract_id=$1::uuid AND storage_path=$2",
        contract_id, seed.storage_path,
    )
    if existing:
        return False
    await conn.execute(
        """
        INSERT INTO documents (contract_id, file_type, storage_path, original_filename)
        VALUES ($1::uuid,$2::document_type,$3,$4)
        """,
        contract_id, seed.file_type, seed.storage_path, seed.original_filename,
    )
    return True


# ---------------------------------------------------------------------------
# Index snapshot + PVC run helpers
# ---------------------------------------------------------------------------

async def _build_index_snapshot(
    conn: asyncpg.Connection, base_month: date, measurement_date: date
) -> IndexSnapshot:
    _, qm_strs = resolve_quarter(measurement_date)
    qm_dates = [date(int(s[:4]), int(s[5:7]), 1) for s in qm_strs]
    all_months = [base_month] + qm_dates

    rows = await conn.fetch(
        """
        SELECT s.name AS series_name, o.month, o.value
        FROM index_observations o
        JOIN index_series s ON s.id = o.series_id
        WHERE o.month = ANY($1::date[])
        """,
        all_months,
    )
    series: dict[str, dict[str, Decimal]] = {}
    for r in rows:
        name = r["series_name"]
        key  = r["month"].strftime("%Y-%m")
        series.setdefault(name, {})[key] = _dec(r["value"])

    return IndexSnapshot(base_month=base_month, series=series)


async def _build_bill_payload(
    conn: asyncpg.Connection, bill_id: str, contract_id: str
) -> BillPayload:
    bill = await conn.fetchrow(
        "SELECT measurement_date, gross_amount FROM running_bills WHERE id=$1::uuid",
        bill_id,
    )
    assert bill is not None

    buckets = await conn.fetchrow(
        """
        SELECT
            COALESCE(SUM(CASE WHEN ci.is_cement_item THEN bl.amount_since_last END),0) AS cement,
            COALESCE(SUM(CASE WHEN ci.steel_subtype='angles' THEN bl.amount_since_last END),0) AS steel_angles,
            COALESCE(SUM(CASE WHEN ci.steel_subtype='plates' THEN bl.amount_since_last END),0) AS steel_plates,
            COALESCE(SUM(CASE WHEN ci.steel_subtype='tmt' THEN bl.amount_since_last END),0) AS steel_tmt,
            COALESCE(SUM(CASE WHEN ci.steel_subtype='other_sections' THEN bl.amount_since_last END),0) AS steel_other
        FROM bill_lines bl
        JOIN contract_items ci ON ci.id = bl.item_id
        WHERE bl.bill_id=$1::uuid AND ci.contract_id=$2::uuid
        """,
        bill_id, contract_id,
    )
    assert buckets is not None

    withheld_row = await conn.fetchrow(
        "SELECT COALESCE(SUM(amount),0) AS w FROM recoveries WHERE bill_id=$1::uuid AND affects_pvc_base=TRUE",
        bill_id,
    )
    technical_withheld = _dec(withheld_row["w"] or 0)

    # ExtraNS lines (drive from bill side, same logic as pvc_service P3-02)
    extra_rows = await conn.fetch(
        """
        SELECT bl.id::text AS bill_line_id, ci.id::text AS item_id, bl.amount_since_last AS amount
        FROM bill_lines bl
        JOIN contract_items ci ON ci.id = bl.item_id
        JOIN schedules s ON s.id = ci.schedule_id
        WHERE bl.bill_id=$1::uuid AND ci.contract_id=$2::uuid AND s.schedule_type='ExtraNS'
        """,
        bill_id, contract_id,
    )
    decision_rows = await conn.fetch(
        "SELECT item_id::text AS item_id, eligible FROM extra_item_decisions WHERE contract_id=$1::uuid",
        contract_id,
    )
    decisions = {r["item_id"]: r["eligible"] for r in decision_rows}
    extra_item_decisions = [
        ExtraItemDecision(
            item_id=r["item_id"],
            amount=_dec(r["amount"]),
            eligible=decisions.get(r["item_id"]),
            source_ref=r["bill_line_id"],
        )
        for r in extra_rows
    ]

    cf_rows = await conn.fetch(
        """
        SELECT cf.item_id::text AS item_id, cf.recorded_qty, cf.paid_qty_source,
               ci.steel_subtype, ci.agreement_rate AS rate, cf.id::text AS cf_id
        FROM carry_forwards cf
        JOIN contract_items ci ON ci.id = cf.item_id
        WHERE cf.target_bill_id=$1::uuid AND ci.contract_id=$2::uuid
        """,
        bill_id, contract_id,
    )
    carry_forwards = [
        CarryForwardPayload(
            item_id=r["item_id"],
            recorded_qty=_dec(r["recorded_qty"]),
            paid_qty_source=_dec(r["paid_qty_source"]),
            amount=_dec(r["recorded_qty"]) * _dec(r["rate"] or 0),
            steel_subtype=r["steel_subtype"],
            source_ref=r["cf_id"],
        )
        for r in cf_rows
    ]

    return BillPayload(
        on_account_amount=_dec(bill["gross_amount"] or 0),
        cement_amount=_dec(buckets["cement"]),
        steel_angles_amount=_dec(buckets["steel_angles"]),
        steel_plates_amount=_dec(buckets["steel_plates"]),
        steel_tmt_amount=_dec(buckets["steel_tmt"]),
        steel_other_amount=_dec(buckets["steel_other"]),
        technical_withheld=technical_withheld,
        extra_item_decisions=extra_item_decisions,
        carry_forwards=carry_forwards,
        measurement_date=bill["measurement_date"],
    )


async def _insert_pvc_run(
    conn: asyncpg.Connection,
    contract_id: str, bill_id: str, rule_set_id: str,
    bill_payload: BillPayload, snapshot: IndexSnapshot,
    result: Any, final_status: str,
) -> str:
    """Insert pvc_runs + pvc_components; return the new run_id."""
    run_row = await conn.fetchrow(
        """
        INSERT INTO pvc_runs (
            contract_id, bill_id, rule_set_id,
            index_snapshot, bill_snapshot, w_derivation, lines_snapshot,
            status, approved_by, approved_at,
            total_pvc, negative_carry_forward, quarter_used
        )
        VALUES (
            $1::uuid,$2::uuid,$3::uuid,
            $4::jsonb,$5::jsonb,$6::jsonb,NULL,
            $7::pvc_run_status,
            CASE WHEN $7='Approved' THEN 'seed_test_data.py' ELSE NULL END,
            CASE WHEN $7='Approved' THEN NOW() ELSE NULL END,
            $8,$9,$10
        )
        RETURNING id::text AS id
        """,
        contract_id, bill_id, rule_set_id,
        snapshot.model_dump_json(),
        bill_payload.model_dump_json(),
        result.w_derivation.model_dump_json(),
        final_status,
        str(result.total_pvc) if result.total_pvc is not None else None,
        str(result.negative_carry_forward),
        result.quarter_used,
    )
    assert run_row is not None
    run_id = run_row["id"]

    for comp in result.components:
        await conn.execute(
            """
            INSERT INTO pvc_components (
                run_id, category, eligible_amount,
                base_index, current_avg_index, weight, pvc_value
            )
            VALUES ($1::uuid,$2::pvc_category,$3,$4,$5,$6,$7)
            ON CONFLICT (run_id, category) DO NOTHING
            """,
            run_id, comp.category, comp.eligible_amount,
            comp.base_index, comp.current_avg_index, comp.weight, comp.pvc_value,
        )

    return run_id


async def compute_and_seed_pvc_run(
    conn: asyncpg.Connection,
    contract_id: str, bill_id: str, rule_set_id: str,
    base_month: date, measurement_date: date,
    negative_pvc_policy: str = "zero_floor",
    final_status: str = "Approved",
) -> tuple[str, Any, IndexSnapshot, BillPayload]:
    """Build payload, run engine, insert run. Returns (run_id, result, snapshot, payload)."""
    bill_payload = await _build_bill_payload(conn, bill_id, contract_id)
    snapshot = await _build_index_snapshot(conn, base_month, measurement_date)
    rules = PVCRuleSet(
        quarter_mode="measurement_date",
        component_weights={k: _dec(v) for k, v in STANDARD_WEIGHTS.items()},
        adjustable_fraction=_dec("0.85"),
        negative_pvc_policy=negative_pvc_policy,
        rounding_mode="round_2",
    )
    result = calculate_pvc(bill_payload, snapshot, rules)
    if result.validation_errors and final_status == "Approved":
        raise SystemExit(
            f"Engine validation failed for bill {bill_id}: {result.validation_errors}\n"
            "Check that all required index observations exist and decisions are correct."
        )
    run_id = await _insert_pvc_run(
        conn, contract_id, bill_id, rule_set_id,
        bill_payload, snapshot, result, final_status,
    )
    return run_id, result, snapshot, bill_payload


# ---------------------------------------------------------------------------
# W-derivation golden assertions
# ---------------------------------------------------------------------------

async def assert_w_buckets(
    conn: asyncpg.Connection,
    bill_id: str, contract_id: str, tender_number: str, bill_number: int,
) -> None:
    key = (tender_number, bill_number)
    if key not in EXPECTED_W:
        return  # no assertion defined for this bill (e.g. Bill 3 or Contract F)
    exp = EXPECTED_W[key]

    # Skip W-check for Contract B (no decision → W is meaningless)
    if tender_number == "TEST-B-WR-BLOCKED":
        return

    buckets = await conn.fetchrow(
        """
        SELECT
            COALESCE(SUM(CASE WHEN ci.is_cement_item THEN bl.amount_since_last END),0) AS cement,
            COALESCE(SUM(CASE WHEN ci.steel_subtype='angles' THEN bl.amount_since_last END),0) AS steel_angles,
            COALESCE(SUM(CASE WHEN ci.steel_subtype='plates' THEN bl.amount_since_last END),0) AS steel_plates,
            COALESCE(SUM(CASE WHEN ci.steel_subtype='tmt' THEN bl.amount_since_last END),0) AS steel_tmt,
            COALESCE(SUM(CASE WHEN ci.steel_subtype='other_sections' THEN bl.amount_since_last END),0) AS steel_other
        FROM bill_lines bl
        JOIN contract_items ci ON ci.id = bl.item_id
        WHERE bl.bill_id=$1::uuid AND ci.contract_id=$2::uuid
        """,
        bill_id, contract_id,
    )
    withheld_row = await conn.fetchrow(
        "SELECT COALESCE(SUM(amount),0) AS tw FROM recoveries WHERE bill_id=$1::uuid AND affects_pvc_base=TRUE",
        bill_id,
    )

    errors: list[str] = []
    for field_name in ("cement","steel_angles","steel_plates","steel_tmt","steel_other"):
        actual = _dec(buckets[field_name])
        expected = exp[field_name]
        if actual.quantize(_dec("0.01")) != expected:
            errors.append(f"  {field_name}: expected {expected}, got {actual}")

    tw_actual = _dec(withheld_row["tw"] or 0)
    if tw_actual.quantize(_dec("0.01")) != exp["technical_withheld"]:
        errors.append(f"  technical_withheld: expected {exp['technical_withheld']}, got {tw_actual}")

    if errors:
        joined = "\n".join(errors)
        raise RuntimeError(
            f"W-bucket reconciliation FAILED for {tender_number} Bill-{bill_number}:\n{joined}"
        )


# ---------------------------------------------------------------------------
# Admin user setup (Scenario G)
# ---------------------------------------------------------------------------

async def ensure_admin_user(conn: asyncpg.Connection) -> None:
    """Promote the first user in the test tenant to is_admin=TRUE if not already."""
    row = await conn.fetchrow(
        "SELECT id::text AS id, email, is_admin FROM users WHERE tenant_id=$1::uuid ORDER BY created_at LIMIT 1",
        TEST_TENANT_ID,
    )
    if row is None:
        print(
            "\n[G] No users found in the test tenant.\n"
            "   Log in via the app first to create the user row, then re-run this script.\n"
            "   After re-running, the first user will be promoted to is_admin=TRUE.\n"
            "   Required for: POST /api/indices/{series} (index admin endpoint)."
        )
        return

    if row["is_admin"]:
        print(f"  admin_user: skipped — {row['email']} already is_admin=TRUE")
        return

    await conn.execute(
        "UPDATE users SET is_admin=TRUE WHERE id=$1::uuid",
        row["id"],
    )
    print(f"  admin_user: promoted {row['email']} ({row['id']}) → is_admin=TRUE")


# ---------------------------------------------------------------------------
# Main seed
# ---------------------------------------------------------------------------

async def seed_contract(
    conn: asyncpg.Connection,
    spec: ContractSpec,
    counts: Counts,
    run_ids: dict[str, dict[str, str]],
) -> str:
    """Seed one contract and all its children. Returns the contract_id."""
    contract_id, created = await get_or_create_contract(conn, spec)
    counts.add("contract", created)
    status_str = "created" if created else "skipped"
    print(f"  contract: {status_str} {spec.tender_number} → {contract_id}")

    rule_set_id, created = await get_or_create_rule_set(conn, contract_id, spec.rule_set_override)
    counts.add("rule_set", created)

    schedule_ids: dict[str, str] = {}
    for sched in spec.schedules:
        sid, created = await get_or_create_schedule(conn, contract_id, sched)
        schedule_ids[sched.key] = sid
        counts.add("schedule", created)

    item_ids: dict[str, str] = {}
    for item in spec.items:
        iid, created = await get_or_create_item(conn, contract_id, schedule_ids[item.schedule_key], item)
        item_ids[item.code] = iid
        counts.add("item", created)

    bill_ids: dict[int, str] = {}
    for bill in spec.bills:
        bid, created = await get_or_create_bill(conn, contract_id, bill)
        bill_ids[bill.number] = bid
        counts.add("bill", created)

    for line in spec.lines:
        created = await insert_bill_line(conn, bill_ids[line.bill_number], item_ids[line.item_code], line)
        counts.add("bill_line", created)

    for rec in spec.recoveries:
        created = await insert_recovery(conn, bill_ids[rec.bill_number], rec)
        counts.add("recovery", created)

    for dec in spec.extra_decisions:
        created = await insert_extra_decision(conn, contract_id, item_ids[dec.item_code], dec)
        counts.add("extra_decision", created)

    for cf in spec.carry_forwards:
        created = await insert_carry_forward(
            conn, contract_id, item_ids[cf.item_code],
            bill_ids[cf.source_bill_number], bill_ids[cf.target_bill_number], cf,
        )
        counts.add("carry_forward", created)

    for doc in spec.documents:
        created = await insert_document(conn, contract_id, doc)
        counts.add("document", created)

    # W-bucket assertions for bills that have golden expectations
    for bill in spec.bills:
        await assert_w_buckets(conn, bill_ids[bill.number], contract_id, spec.tender_number, bill.number)

    # PVC run seeding
    bill_run_ids: dict[str, str] = {}
    run_ids[spec.tender_number] = bill_run_ids

    # --- Contract A: compute Approved run for Bill 1 (Q2-2025) ---
    if spec.tender_number == "TEST-A-WR-252" and 1 in bill_ids:
        existing_run = await conn.fetchrow(
            "SELECT id::text AS id FROM pvc_runs WHERE bill_id=$1::uuid AND status='Approved'",
            bill_ids[1],
        )
        if existing_run:
            bill_run_ids["bill1_approved"] = existing_run["id"]
            print(f"  pvc_run (A bill1 Approved): skipped {existing_run['id']}")
        else:
            run_id, result, _snap, _pl = await compute_and_seed_pvc_run(
                conn, contract_id, bill_ids[1], rule_set_id,
                spec.base_month, spec.bills[0].measurement_date,
                negative_pvc_policy="zero_floor", final_status="Approved",
            )
            bill_run_ids["bill1_approved"] = run_id
            print(f"  pvc_run (A bill1 Approved): created {run_id}  total_pvc={result.total_pvc}")

    # --- Contract C1/C2: compute Approved run for Bill 1 (Q4-2025) ---
    if spec.tender_number in ("TEST-C1-NER-FLOOR", "TEST-C2-NER-ALLOW") and 1 in bill_ids:
        policy = (spec.rule_set_override or {}).get("negative_pvc_policy", "zero_floor")
        existing_run = await conn.fetchrow(
            "SELECT id::text AS id FROM pvc_runs WHERE bill_id=$1::uuid AND status='Approved'",
            bill_ids[1],
        )
        if existing_run:
            bill_run_ids["bill1_approved"] = existing_run["id"]
            print(f"  pvc_run ({spec.tender_number} Approved): skipped {existing_run['id']}")
        else:
            run_id, result, _snap, _pl = await compute_and_seed_pvc_run(
                conn, contract_id, bill_ids[1], rule_set_id,
                spec.base_month, spec.bills[0].measurement_date,
                negative_pvc_policy=policy, final_status="Approved",
            )
            bill_run_ids["bill1_approved"] = run_id
            print(f"  pvc_run ({spec.tender_number} Approved): created {run_id}  "
                  f"total_pvc={result.total_pvc}  ncf={result.negative_carry_forward}")

    # --- Contract D: Superseded + Approved runs for Bill 1 ---
    if spec.tender_number == "TEST-D-NR-EXPORT" and 1 in bill_ids:
        existing_approved = await conn.fetchrow(
            "SELECT id::text AS id FROM pvc_runs WHERE bill_id=$1::uuid AND status='Approved'",
            bill_ids[1],
        )
        if existing_approved:
            bill_run_ids["bill1_approved"] = existing_approved["id"]
            print(f"  pvc_run (D Approved): skipped {existing_approved['id']}")
        else:
            # Compute once; reuse snapshot + payload for both Approved and Superseded rows.
            approved_id, result, snap_d, payload_d = await compute_and_seed_pvc_run(
                conn, contract_id, bill_ids[1], rule_set_id,
                spec.base_month, spec.bills[0].measurement_date,
                negative_pvc_policy="zero_floor", final_status="Approved",
            )
            bill_run_ids["bill1_approved"] = approved_id
            print(f"  pvc_run (D Approved): created {approved_id}  total_pvc={result.total_pvc}")

            # Insert Superseded run: same payload / same result, backdated 2 h to appear older.
            superseded_id = await conn.fetchval(
                """
                INSERT INTO pvc_runs (
                    contract_id, bill_id, rule_set_id,
                    index_snapshot, bill_snapshot, w_derivation, lines_snapshot,
                    status, superseded_by,
                    total_pvc, negative_carry_forward, quarter_used,
                    created_at
                )
                VALUES (
                    $1::uuid,$2::uuid,$3::uuid,
                    $4::jsonb,$5::jsonb,$6::jsonb,NULL,
                    'Superseded'::pvc_run_status,$7::uuid,
                    $8,$9,$10,
                    NOW() - INTERVAL '2 hours'
                )
                RETURNING id::text
                """,
                contract_id, bill_ids[1], rule_set_id,
                snap_d.model_dump_json(),
                payload_d.model_dump_json(),
                result.w_derivation.model_dump_json(),
                approved_id,
                str(result.total_pvc) if result.total_pvc is not None else None,
                str(result.negative_carry_forward),
                result.quarter_used,
            )
            bill_run_ids["bill1_superseded"] = superseded_id
            print(f"  pvc_run (D Superseded): created {superseded_id}")

    return contract_id


async def seed() -> None:
    print(f"\nRailPVC Test Data Seed")
    print(f"Tenant: {TEST_TENANT_ID}")
    print(f"Base month: {BASE_MONTH:%Y-%m}\n")

    counts = Counts()
    conn = await connect()
    contract_ids: dict[str, str] = {}
    run_ids: dict[str, dict[str, str]] = {}

    try:
        await require_tenant(conn)
        await require_indices(conn)

        async with conn.transaction():
            for spec in ALL_CONTRACTS:
                cid = await seed_contract(conn, spec, counts, run_ids)
                contract_ids[spec.tender_number] = cid

            await ensure_admin_user(conn)

    finally:
        await conn.close()

    # Summary
    print("\n" + "="*60)
    print("SEED COMPLETE")
    print("="*60)
    for key in ("contract","rule_set","schedule","item","bill","bill_line",
                "recovery","extra_decision","carry_forward","document"):
        c = counts.get(f"{key}_created", 0)
        s = counts.get(f"{key}_skipped", 0)
        if c or s:
            print(f"  {key:20s}: {c} created, {s} skipped")

    print("\nContract IDs:")
    letters = {"TEST-A-WR-252":"A","TEST-B-WR-BLOCKED":"B",
               "TEST-C1-NER-FLOOR":"C1","TEST-C2-NER-ALLOW":"C2",
               "TEST-D-NR-EXPORT":"D","TEST-E-CR-NOPVC":"E","TEST-F-NCR-DRAFT":"F"}
    for tender, cid in contract_ids.items():
        ltr = letters.get(tender, "?")
        print(f"  [{ltr}] {tender}")
        print(f"      /contracts/{cid}")

    print("\nPVC Run IDs (for export / supersede testing):")
    for tender, rmap in run_ids.items():
        cid = contract_ids.get(tender, "?")
        for key, rid in rmap.items():
            print(f"  [{letters.get(tender,'?')}] {key}: /contracts/{cid}/pvc-runs/{rid}")

    print("\nNext steps:")
    print("  1. Open /contracts/<id> for each scenario above.")
    print("  2. See seeds/TEST_DATA.md for the full click-path test matrix.")
    print("  3. For Scenario G admin test: log in and navigate to /indices.")
    print("  4. For Scenario H doc vault: upload files at /contracts/A/documents.")
    print("  5. Teardown: DELETE FROM contracts WHERE tenant_id='%s';" % TEST_TENANT_ID)


if __name__ == "__main__":
    asyncio.run(seed())
