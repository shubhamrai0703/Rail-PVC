"""
Seed one end-to-end BCT-24-25-252 demo billing cycle.

Creates, for the tenant explicitly supplied in SEED_TENANT_ID:
  - Contract BCT-24-25-252 / WR/BCT/Civil/2025/0059
  - PVC rule set version 1 matching the verified fixtures
  - DSR, NS, and ExtraNS schedules
  - BOQ items covering cement, steel angles, plates, other sections, TMT,
    ordinary DSR/NS work, and the excluded ExtraNS item NS-1
  - Two running bills, bill lines, recoveries, one steel carry-forward, and
    the extra-item decision needed to avoid an unintended blocked run

Primary sources:
  - engine/tests/fixtures/real_tenders/bct_2425_252_bill1_q2.json
  - engine/tests/fixtures/real_tenders/bct_2425_252_bill2_q4.json
  - IRL PVC calculation sample/Banjara - COLABA BP 252 - Apr 2022 GCC.xlsx
  - IRL PVC calculation sample/10.2 1st MB.xlsx
  - IRL PVC calculation sample/MB/*BILL*.pdf and *RECOVERIES*.pdf
  - REFERENCES/jpc_monthly_averages.csv

Run:
  uv run python seeds/seed_demo_contract.py

Idempotent:
  The script uses the same asyncpg + backend/.env DATABASE_URL pattern as
  seed_indices.py. Natural keys and existing UNIQUE constraints are checked
  before inserts, so re-running prints skipped rows and creates no duplicates.

Known calculation boundary:
  The fixture values are authoritative for bill headers and W buckets. Bill-2
  deliberately pins the engine-correct Q4-FY2025-26 result, while the workbook
  diverges by using Q2 indices and by using the JPC-published other-sections
  rate instead of GCC 46A.9's derived SL1+SL2+SL3 average.

  Current DB schema has no technical_withheld column. This seed records the
  fixture withheld amounts in bill_lines.special_condition_amount and validates
  those totals, but backend/services/pvc_service.py currently sends
  technical_withheld=0 to the engine.

  Current carry_forwards schema stores quantities, not a direct amount. The
  service reconstructs carry-forward amount as recorded_qty * agreement_rate.
  This seed stores the real 10.2 quantities/rate from the workbook for UI
  realism; the direct fixture carry amount remains in the fixture JSON.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

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
            [
                "uv",
                "--project",
                str(BACKEND_DIR),
                "run",
                "python",
                str(Path(__file__).resolve()),
            ],
            env,
        )
    raise

load_dotenv(BACKEND_DIR / ".env", override=False)


TENDER_NUMBER = "BCT-24-25-252"

INDEX_SERIES = (
    "labour",
    "plant_machinery",
    "fuel",
    "other_materials",
    "cement",
    "steel_tmt",
    "steel_angles",
    "steel_plates",
    "steel_other_sections",
)

BASE_MONTH = date(2024, 12, 1)


def quarter_months(measurement_date: date) -> tuple[date, ...]:
    """Calendar-quarter months the engine reads for a bill (see engine/engine/quarter.py)."""
    start_month = ((measurement_date.month - 1) // 3) * 3 + 1
    return tuple(date(measurement_date.year, start_month + i, 1) for i in range(3))

WORK_DESCRIPTION = (
    "Colaba-Badhwarpark-Repairs to change of officers quarter in connection "
    "to new occupation at Badhwar Park Railway officers colony."
)

RULE_WEIGHTS = {
    "labour": 0.20,
    "plant": 0.30,
    "fuel": 0.15,
    "materials": 0.20,
}


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
class BillLineSeed:
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


SCHEDULES = (
    ScheduleSeed("DSR", "Schedule A-All Items of DSR", "DSR", Decimal("-0.5858")),
    ScheduleSeed("NS", "Schedule B-All NS items", "NS", Decimal("-0.5858")),
    ScheduleSeed("ExtraNS", "Schedule C-Extra NS", "ExtraNS", Decimal("0")),
)

ITEMS = (
    ItemSeed(
        "6.4.2",
        "DSR",
        "Brick work with common burnt clay F.P.S. bricks of class designation 7.5 in superstructure.",
        "Cum",
        Decimal("13.9000"),
        Decimal("13.9000"),
        Decimal("6943.0000"),
        Decimal("2882.4394"),
        is_cement_item=True,
    ),
    ItemSeed(
        "8.2.2.1",
        "DSR",
        "Providing and fixing 18 mm thick gang saw cut mirror-polished granite stone slab.",
        "Sqm",
        Decimal("520.0000"),
        Decimal("520.0000"),
        Decimal("3456.0000"),
        Decimal("1432.5552"),
        is_cement_item=True,
    ),
    ItemSeed(
        "10.2",
        "DSR",
        "Structural steel work in single sections including angles, channels, joists and plates.",
        "Kg",
        Decimal("6172.5700"),
        Decimal("6172.5700"),
        Decimal("111.9500"),
        Decimal("40.5850"),
        steel_subtype="angles",
    ),
    ItemSeed(
        "10.2P",
        "DSR",
        "Plate component of DSR item 10.2 measured from the 1st MB steel bifurcation.",
        "Kg",
        Decimal("78.5000"),
        Decimal("78.5000"),
        Decimal("111.9500"),
        Decimal("40.5850"),
        steel_subtype="plates",
    ),
    ItemSeed(
        "9.48.2",
        "DSR",
        "Providing and fixing factory made pressed steel door frames.",
        "Kg",
        Decimal("455.3000"),
        Decimal("455.3000"),
        Decimal("197.7000"),
        Decimal("71.6710"),
        steel_subtype="other_sections",
    ),
    ItemSeed(
        "5.22A.6",
        "DSR",
        "Thermo-Mechanically Treated bars of grade Fe-500D or more.",
        "Kg",
        Decimal("1000.0000"),
        Decimal("1000.0000"),
        Decimal("155.8000"),
        Decimal("56.4795"),
        steel_subtype="tmt",
    ),
    ItemSeed(
        "11.41.2",
        "DSR",
        "Providing and laying vitrified floor tiles in different sizes with cement mortar.",
        "Sqm",
        Decimal("1800.0000"),
        Decimal("1800.0000"),
        Decimal("1698.0000"),
        Decimal("703.3716"),
        is_cement_item=True,
    ),
    ItemSeed(
        "NS-PLY-19",
        "NS",
        "Providing, cutting and fixing 19 mm thick waterproof marine plywood on existing frames.",
        "Sqm",
        Decimal("324.0000"),
        Decimal("325.0000"),
        Decimal("2689.0000"),
        Decimal("1371.3900"),
    ),
    ItemSeed(
        "NS-GLASS-12",
        "NS",
        "Supply and fixing 12 mm thick toughened etched glass with machine-polished edges.",
        "Sqm",
        Decimal("10.0000"),
        Decimal("10.0000"),
        Decimal("1980.0000"),
        Decimal("1009.8000"),
    ),
    ItemSeed(
        "NS-BASIN",
        "NS",
        "Supplying and fixing wash basin table top Admiral Collection or similar approved make.",
        "Each",
        Decimal("80.0000"),
        Decimal("95.0000"),
        Decimal("1731.0000"),
        Decimal("882.8100"),
    ),
    ItemSeed(
        "NS-1",
        "ExtraNS",
        "Extra NS item from Bill-1 fixture; excluded from PVC eligibility.",
        "Lump Sum",
        Decimal("1.0000"),
        Decimal("1.0000"),
        Decimal("1600000.0000"),
        Decimal("1600000.0000"),
    ),
)

BILLS = (
    BillSeed(1, date(2025, 6, 19), date(2025, 6, 18), Decimal("8903877.99"), "Imported"),
    BillSeed(2, date(2025, 11, 7), date(2025, 11, 4), Decimal("7250000.00"), "Imported"),
)

BILL_LINES = (
    BillLineSeed(1, "6.4.2", Decimal("0"), Decimal("1"), Decimal("1"), Decimal("0"), Decimal("300000.00"), Decimal("300000.00")),
    BillLineSeed(1, "10.2", Decimal("0"), Decimal("1"), Decimal("1"), Decimal("0"), Decimal("125000.00"), Decimal("125000.00")),
    BillLineSeed(1, "9.48.2", Decimal("0"), Decimal("1"), Decimal("1"), Decimal("0"), Decimal("450000.00"), Decimal("450000.00")),
    BillLineSeed(1, "NS-PLY-19", Decimal("0"), Decimal("1"), Decimal("1"), Decimal("0"), Decimal("6378877.99"), Decimal("6378877.99"), Decimal("50000.00")),
    BillLineSeed(1, "NS-1", Decimal("0"), Decimal("1"), Decimal("1"), Decimal("0"), Decimal("1600000.00"), Decimal("1600000.00")),
    BillLineSeed(2, "6.4.2", Decimal("1"), Decimal("1"), Decimal("2"), Decimal("300000.00"), Decimal("200000.00"), Decimal("500000.00")),
    BillLineSeed(2, "10.2", Decimal("1"), Decimal("1"), Decimal("2"), Decimal("125000.00"), Decimal("80000.00"), Decimal("205000.00")),
    BillLineSeed(2, "10.2P", Decimal("0"), Decimal("1"), Decimal("1"), Decimal("0"), Decimal("60000.00"), Decimal("60000.00")),
    BillLineSeed(2, "9.48.2", Decimal("1"), Decimal("1"), Decimal("2"), Decimal("450000.00"), Decimal("300000.00"), Decimal("750000.00")),
    BillLineSeed(2, "NS-PLY-19", Decimal("1"), Decimal("1"), Decimal("2"), Decimal("6378877.99"), Decimal("6570000.00"), Decimal("12948877.99"), Decimal("40000.00")),
)

REQUIRED_INDEX_MONTHS = tuple(
    sorted({BASE_MONTH, *(m for b in BILLS for m in quarter_months(b.measurement_date))})
)

RECOVERIES = (
    RecoverySeed(1, "security_deposit", Decimal("260768.00")),
    RecoverySeed(1, "water", Decimal("871.00")),
    RecoverySeed(1, "income_tax", Decimal("157727.00")),
    RecoverySeed(1, "labour_cess", Decimal("78863.00")),
    RecoverySeed(2, "security_deposit", Decimal("263514.00")),
    RecoverySeed(2, "water", Decimal("1999.00")),
    RecoverySeed(2, "income_tax", Decimal("114192.00")),
    RecoverySeed(2, "labour_cess", Decimal("57096.00")),
)

EXPECTED_BUCKETS = {
    1: {
        "cement": Decimal("300000.00"),
        "steel_angles": Decimal("125000.00"),
        "steel_plates": Decimal("0.00"),
        "steel_tmt": Decimal("0.00"),
        "steel_other": Decimal("450000.00"),
        "technical_withheld": Decimal("50000.00"),
    },
    2: {
        "cement": Decimal("200000.00"),
        "steel_angles": Decimal("80000.00"),
        "steel_plates": Decimal("60000.00"),
        "steel_tmt": Decimal("0.00"),
        "steel_other": Decimal("300000.00"),
        "technical_withheld": Decimal("40000.00"),
    },
}


class Counts(dict[str, int]):
    def add(self, key: str, created: bool) -> None:
        suffix = "created" if created else "skipped"
        self[f"{key}_{suffix}"] = self.get(f"{key}_{suffix}", 0) + 1


def money(value: Decimal) -> str:
    return f"{value:.2f}"


def resolve_tenant_id() -> str:
    tenant_id = os.environ.get("SEED_TENANT_ID", "").strip()
    if not tenant_id:
        raise SystemExit(
            "SEED_TENANT_ID is required; refusing to seed a default tenant"
        )
    return tenant_id


async def connect() -> asyncpg.Connection:
    raw = os.environ["DATABASE_URL"].strip()
    u = make_url(raw)
    try:
        return await asyncpg.connect(
            host=u.host,
            port=u.port,
            user=u.username,
            password=str(u.password),
            database=u.database,
        )
    except (asyncpg.PostgresError, OSError) as exc:
        raise SystemExit(
            "Could not connect using backend/.env DATABASE_URL. "
            f"Postgres reported: {exc}"
        ) from exc


async def require_tenant(conn: asyncpg.Connection, tenant_id: str) -> None:
    row = await conn.fetchrow("SELECT id FROM tenants WHERE id = $1::uuid", tenant_id)
    if row is None:
        raise SystemExit(
            f"Tenant {tenant_id} not found. Provision the tenant before seeding demo data."
        )


async def require_indices(conn: asyncpg.Connection) -> None:
    rows = await conn.fetch(
        """
        SELECT s.name, o.month
        FROM index_series s
        JOIN index_observations o ON o.series_id = s.id
        WHERE s.name = ANY($1::text[])
          AND o.month = ANY($2::date[])
        """,
        list(INDEX_SERIES),
        list(REQUIRED_INDEX_MONTHS),
    )
    present = {(r["name"], r["month"]) for r in rows}
    missing = [
        (series, month)
        for series in INDEX_SERIES
        for month in REQUIRED_INDEX_MONTHS
        if (series, month) not in present
    ]
    if missing:
        preview = ", ".join(f"{s}:{m:%Y-%m}" for s, m in missing[:12])
        more = "" if len(missing) <= 12 else f" ... +{len(missing) - 12} more"
        raise SystemExit(
            "Missing required index observations. Run first:\n"
            "  uv run python seeds/seed_indices.py\n"
            f"Missing: {preview}{more}"
        )


async def get_or_create_contract(
    conn: asyncpg.Connection,
    tenant_id: str,
) -> tuple[str, bool]:
    existing = await conn.fetchrow(
        """
        SELECT id::text AS id
        FROM contracts
        WHERE tenant_id = $1::uuid AND tender_number = $2
        """,
        tenant_id,
        TENDER_NUMBER,
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
            $1::uuid, $2, $3, $4, $5::date,
            $6, $7, $8, $9,
            $10::date, $11::date, $12::date, $13::railway_zone, $14::gst_mode,
            TRUE, $15, $16::contract_status
        )
        RETURNING id::text AS id
        """,
        tenant_id,
        TENDER_NUMBER,
        "WR/BCT/Civil/2025/0059",
        "00944450126035",
        date(2025, 3, 25),
        "BANJARA CONSTRUCTION CORPORATION",
        WORK_DESCRIPTION,
        Decimal("9569037.43"),
        Decimal("9305888.90"),
        date(2025, 3, 26),
        date(2026, 3, 25),
        BASE_MONTH,
        "WR",
        "inclusive",
        Decimal("-0.0275"),
        "Active",
    )
    assert row is not None
    return row["id"], True


async def get_or_create_rule_set(conn: asyncpg.Connection, contract_id: str) -> tuple[str, bool]:
    row = await conn.fetchrow(
        """
        INSERT INTO pvc_rule_sets (
            contract_id, version, quarter_mode, component_weights,
            extra_item_policy, adjustable_fraction, rounding_mode, negative_pvc_policy
        )
        VALUES (
            $1::uuid, 1, 'measurement_date'::quarter_mode, $2::jsonb,
            'exclude_by_default'::extra_item_policy, 0.85,
            'round_2'::rounding_mode, 'zero_floor'::negative_pvc_policy
        )
        ON CONFLICT (contract_id, version) DO NOTHING
        RETURNING id::text AS id
        """,
        contract_id,
        json.dumps(RULE_WEIGHTS),
    )
    if row:
        return row["id"], True
    existing = await conn.fetchrow(
        "SELECT id::text AS id FROM pvc_rule_sets WHERE contract_id = $1::uuid AND version = 1",
        contract_id,
    )
    assert existing is not None
    return existing["id"], False


async def get_or_create_schedule(
    conn: asyncpg.Connection, contract_id: str, seed: ScheduleSeed
) -> tuple[str, bool]:
    existing = await conn.fetchrow(
        """
        SELECT id::text AS id
        FROM schedules
        WHERE contract_id = $1::uuid AND name = $2 AND schedule_type = $3::schedule_type
        """,
        contract_id,
        seed.name,
        seed.schedule_type,
    )
    if existing:
        return existing["id"], False
    row = await conn.fetchrow(
        """
        INSERT INTO schedules (contract_id, name, schedule_type, bid_discount_pct)
        VALUES ($1::uuid, $2, $3::schedule_type, $4)
        RETURNING id::text AS id
        """,
        contract_id,
        seed.name,
        seed.schedule_type,
        seed.bid_discount_pct,
    )
    assert row is not None
    return row["id"], True


async def get_or_create_item(
    conn: asyncpg.Connection,
    contract_id: str,
    schedule_id: str,
    seed: ItemSeed,
) -> tuple[str, bool]:
    existing = await conn.fetchrow(
        """
        SELECT id::text AS id
        FROM contract_items
        WHERE contract_id = $1::uuid AND item_code = $2
        """,
        contract_id,
        seed.code,
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
        VALUES (
            $1::uuid, $2::uuid, $3, $4, $5,
            $6, $7, $8, $9,
            $10, $11::steel_subtype
        )
        RETURNING id::text AS id
        """,
        contract_id,
        schedule_id,
        seed.code,
        seed.description,
        seed.unit,
        seed.original_qty,
        seed.revised_qty,
        seed.base_rate,
        seed.agreement_rate,
        seed.is_cement_item,
        seed.steel_subtype,
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
        VALUES ($1::uuid, $2, $3::date, $4::date, $5, NULL, $6::bill_status)
        ON CONFLICT (contract_id, bill_number) DO NOTHING
        RETURNING id::text AS id
        """,
        contract_id,
        seed.number,
        seed.bill_date,
        seed.measurement_date,
        seed.gross_amount,
        seed.status,
    )
    if row:
        return row["id"], True
    existing = await conn.fetchrow(
        """
        SELECT id::text AS id
        FROM running_bills
        WHERE contract_id = $1::uuid AND bill_number = $2
        """,
        contract_id,
        seed.number,
    )
    assert existing is not None
    return existing["id"], False


async def insert_bill_line(
    conn: asyncpg.Connection, bill_id: str, item_id: str, seed: BillLineSeed
) -> bool:
    row = await conn.fetchrow(
        """
        INSERT INTO bill_lines (
            bill_id, item_id, qty_up_to_last, qty_since_last, qty_up_to_date,
            amount_up_to_last, amount_since_last, amount_up_to_date,
            special_condition_amount
        )
        VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (bill_id, item_id) DO NOTHING
        RETURNING id::text AS id
        """,
        bill_id,
        item_id,
        seed.qty_up_to_last,
        seed.qty_since_last,
        seed.qty_up_to_date,
        seed.amount_up_to_last,
        seed.amount_since_last,
        seed.amount_up_to_date,
        seed.special_condition_amount,
    )
    return row is not None


async def insert_recovery(conn: asyncpg.Connection, bill_id: str, seed: RecoverySeed) -> bool:
    existing = await conn.fetchrow(
        """
        SELECT id
        FROM recoveries
        WHERE bill_id = $1::uuid
          AND recovery_type = $2::recovery_type
          AND amount = $3
          AND affects_pvc_base = $4
        """,
        bill_id,
        seed.recovery_type,
        seed.amount,
        seed.affects_pvc_base,
    )
    if existing:
        return False
    await conn.execute(
        """
        INSERT INTO recoveries (bill_id, recovery_type, amount, affects_pvc_base)
        VALUES ($1::uuid, $2::recovery_type, $3, $4)
        """,
        bill_id,
        seed.recovery_type,
        seed.amount,
        seed.affects_pvc_base,
    )
    return True


async def insert_extra_item_decision(
    conn: asyncpg.Connection, contract_id: str, item_id: str
) -> bool:
    row = await conn.fetchrow(
        """
        INSERT INTO extra_item_decisions (
            contract_id, item_id, eligible, decided_by, decided_at, notes
        )
        VALUES (
            $1::uuid, $2::uuid, FALSE, 'seed_demo_contract.py', NOW(),
            'Matches Bill-1 fixture: NS-1 amount 1600000.00 is excluded from PVC.'
        )
        ON CONFLICT (contract_id, item_id) DO NOTHING
        RETURNING id::text AS id
        """,
        contract_id,
        item_id,
    )
    return row is not None


async def insert_carry_forward(
    conn: asyncpg.Connection,
    contract_id: str,
    item_id: str,
    source_bill_id: str,
    target_bill_id: str,
) -> bool:
    existing = await conn.fetchrow(
        """
        SELECT id
        FROM carry_forwards
        WHERE contract_id = $1::uuid
          AND item_id = $2::uuid
          AND source_bill_id = $3::uuid
          AND target_bill_id = $4::uuid
        """,
        contract_id,
        item_id,
        source_bill_id,
        target_bill_id,
    )
    if existing:
        return False
    recorded_qty = Decimal("6172.5700")
    paid_qty_source = Decimal("5600.0000")
    carry_qty = recorded_qty - paid_qty_source
    paid_ratio = paid_qty_source / recorded_qty
    await conn.execute(
        """
        INSERT INTO carry_forwards (
            contract_id, item_id, source_bill_id, target_bill_id,
            recorded_qty, paid_qty_source, paid_ratio, carry_qty, steel_subtype
        )
        VALUES (
            $1::uuid, $2::uuid, $3::uuid, $4::uuid,
            $5, $6, $7, $8, 'angles'::steel_subtype
        )
        """,
        contract_id,
        item_id,
        source_bill_id,
        target_bill_id,
        recorded_qty,
        paid_qty_source,
        paid_ratio,
        carry_qty,
    )
    return True


async def bucket_totals(conn: asyncpg.Connection, bill_id: str) -> dict[str, Decimal]:
    row = await conn.fetchrow(
        """
        SELECT
            COALESCE(SUM(CASE WHEN ci.is_cement_item THEN bl.amount_since_last END), 0) AS cement,
            COALESCE(SUM(CASE WHEN ci.steel_subtype = 'angles' THEN bl.amount_since_last END), 0) AS steel_angles,
            COALESCE(SUM(CASE WHEN ci.steel_subtype = 'plates' THEN bl.amount_since_last END), 0) AS steel_plates,
            COALESCE(SUM(CASE WHEN ci.steel_subtype = 'tmt' THEN bl.amount_since_last END), 0) AS steel_tmt,
            COALESCE(SUM(CASE WHEN ci.steel_subtype = 'other_sections' THEN bl.amount_since_last END), 0) AS steel_other,
            COALESCE(SUM(bl.special_condition_amount), 0) AS technical_withheld
        FROM bill_lines bl
        JOIN contract_items ci ON ci.id = bl.item_id
        WHERE bl.bill_id = $1::uuid
        """,
        bill_id,
    )
    assert row is not None
    return {k: Decimal(row[k]) for k in EXPECTED_BUCKETS[1]}


def assert_expected_buckets(bill_number: int, actual: dict[str, Decimal]) -> None:
    expected = EXPECTED_BUCKETS[bill_number]
    errors = []
    for key, expected_value in expected.items():
        if actual[key].quantize(Decimal("0.01")) != expected_value:
            errors.append(f"{key}: expected {money(expected_value)}, got {money(actual[key])}")
    if errors:
        joined = "; ".join(errors)
        raise RuntimeError(f"Bill-{bill_number} W-bucket reconciliation failed: {joined}")


async def seed() -> None:
    counts = Counts()
    tenant_id = resolve_tenant_id()
    conn = await connect()
    try:
        await require_tenant(conn, tenant_id)
        await require_indices(conn)

        async with conn.transaction():
            contract_id, created = await get_or_create_contract(conn, tenant_id)
            counts.add("contract", created)
            print(f"contract: {'created' if created else 'skipped'} {contract_id}")

            rule_set_id, created = await get_or_create_rule_set(conn, contract_id)
            counts.add("rule_set", created)
            print(f"rule_set: {'created' if created else 'skipped'} {rule_set_id}")

            schedule_ids: dict[str, str] = {}
            for schedule in SCHEDULES:
                schedule_id, created = await get_or_create_schedule(conn, contract_id, schedule)
                schedule_ids[schedule.key] = schedule_id
                counts.add("schedule", created)
                print(f"schedule: {'created' if created else 'skipped'} {schedule.name} -> {schedule_id}")

            item_ids: dict[str, str] = {}
            for item in ITEMS:
                item_id, created = await get_or_create_item(
                    conn, contract_id, schedule_ids[item.schedule_key], item
                )
                item_ids[item.code] = item_id
                counts.add("item", created)
            print(f"items: {counts.get('item_created', 0)} created, {counts.get('item_skipped', 0)} skipped")

            bill_ids: dict[int, str] = {}
            for bill in BILLS:
                bill_id, created = await get_or_create_bill(conn, contract_id, bill)
                bill_ids[bill.number] = bill_id
                counts.add("bill", created)
                print(f"bill {bill.number}: {'created' if created else 'skipped'} {bill_id}")

            for line in BILL_LINES:
                created = await insert_bill_line(
                    conn, bill_ids[line.bill_number], item_ids[line.item_code], line
                )
                counts.add("bill_line", created)

            for recovery in RECOVERIES:
                created = await insert_recovery(conn, bill_ids[recovery.bill_number], recovery)
                counts.add("recovery", created)

            created = await insert_extra_item_decision(conn, contract_id, item_ids["NS-1"])
            counts.add("extra_item_decision", created)

            created = await insert_carry_forward(
                conn, contract_id, item_ids["10.2"], bill_ids[1], bill_ids[2]
            )
            counts.add("carry_forward", created)

            for bill_number, bill_id in bill_ids.items():
                assert_expected_buckets(bill_number, await bucket_totals(conn, bill_id))

            item_count = await conn.fetchval(
                "SELECT COUNT(*) FROM contract_items WHERE contract_id = $1::uuid",
                contract_id,
            )
            recovery_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM recoveries r
                JOIN running_bills b ON b.id = r.bill_id
                WHERE b.contract_id = $1::uuid
                """,
                contract_id,
            )

        print("\nFinal summary")
        print(f"  contract_id: {contract_id}")
        print(f"  schedule_ids: {schedule_ids}")
        print(f"  item_count: {item_count}")
        print(f"  bill_ids: {bill_ids}")
        print(f"  recovery_count: {recovery_count}")
        print(f"  bill_lines: {counts.get('bill_line_created', 0)} created, {counts.get('bill_line_skipped', 0)} skipped")
        print(f"  recoveries: {counts.get('recovery_created', 0)} created, {counts.get('recovery_skipped', 0)} skipped")
        print(f"  extra_item_decisions: {counts.get('extra_item_decision_created', 0)} created, {counts.get('extra_item_decision_skipped', 0)} skipped")
        print(f"  carry_forwards: {counts.get('carry_forward_created', 0)} created, {counts.get('carry_forward_skipped', 0)} skipped")
        print(f"  view: /contracts/{contract_id}/bills")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
