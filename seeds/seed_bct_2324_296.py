"""Seed Ritesh's real BCT-23-24-296 contract into one explicit tenant.

The seed is intentionally contract-specific. It records the source contract header,
two accepted schedules, six auditable aggregate/steel items, three signed bills,
their signed recoveries, and the PVC rule set. It does not create PVC runs, upload
documents, or change global index observations.

Required:
  SEED_TENANT_ID=<verified tenant uuid>
  SEED_EXPECTED_DB_HOST=<DATABASE_URL host>  # commit mode only

Optional:
  SEED_DRY_RUN=1  # execute all inserts and validations, then roll back

Run from the repository root:
  uv run python seeds/seed_bct_2324_296.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import defaultdict
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


TENDER_NUMBER = "BCT-23-24-296"
AGREEMENT_NUMBER = "WR/BCT/Civil/2024/0109"
LOA_NUMBER = "00944450102350"
BASE_MONTH = date(2024, 2, 1)
WORK_DESCRIPTION = (
    "Colaba-Badhwarpark- Repairs to officers quarter in connection with change "
    "of occupation/vacation at Badhawarpark."
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
    status: str = "Imported"


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
    ScheduleSeed("DSR", "Schedule A-All DSR Items", "DSR", Decimal("-0.49")),
    ScheduleSeed(
        "NS",
        "Schedule B-All Non Scheduled items",
        "NS",
        Decimal("-0.44"),
    ),
)

ITEMS = (
    ItemSeed(
        "DSR-GENERAL",
        "DSR",
        "Aggregate of non-cement/non-steel Schedule A work from the signed bills.",
        "Lump Sum",
        Decimal("1"),
        Decimal("1"),
        Decimal("14162104.18"),
        Decimal("7222673.13"),
    ),
    ItemSeed(
        "NS-GENERAL",
        "NS",
        "Aggregate of Schedule B non-scheduled work from the signed bills.",
        "Lump Sum",
        Decimal("1"),
        Decimal("1"),
        Decimal("6485964.02"),
        Decimal("3632139.85"),
    ),
    ItemSeed(
        "CEMENT-AGG",
        "DSR",
        "Aggregate cement consumption for DSR items listed on the PVC workbook Cement sheet.",
        "Lump Sum",
        Decimal("1"),
        Decimal("1"),
        Decimal("1"),
        Decimal("1"),
        is_cement_item=True,
    ),
    ItemSeed(
        "10.1-ANGLES",
        "DSR",
        "Item 10.1 steel angle portion from the signed measurement books.",
        "Kg",
        Decimal("2254.31"),
        Decimal("2254.31"),
        Decimal("93.05"),
        Decimal("42.70995"),
        steel_subtype="angles",
    ),
    ItemSeed(
        "10.1-OTHER",
        "DSR",
        "Item 10.1 other-section steel portion from the signed measurement books.",
        "Kg",
        Decimal("1245.62"),
        Decimal("1245.62"),
        Decimal("93.05"),
        Decimal("42.70995"),
        steel_subtype="other_sections",
    ),
    ItemSeed(
        "9.48.2-OTHER",
        "DSR",
        "Item 9.48.2 other-section steel portion from the signed measurement books.",
        "Kg",
        Decimal("1994.63"),
        Decimal("1994.63"),
        Decimal("197.70"),
        Decimal("90.74430"),
        steel_subtype="other_sections",
    ),
)

BILLS = (
    BillSeed(1, date(2024, 9, 18), date(2024, 9, 17), Decimal("8811280.43")),
    BillSeed(2, date(2025, 2, 15), date(2025, 2, 15), Decimal("7319994.44")),
    BillSeed(3, date(2025, 3, 21), date(2025, 3, 20), Decimal("22091.28")),
)

# The two aggregate rows keep the signed Schedule A/B subtotals visible while
# the cement and steel rows preserve the workbook's PVC buckets. Bill 1's
# Rs.1,249 penalty/withheld amount is stored as special_condition_amount on the
# general DSR row and as a signed recovery below; it is not double-counted.
_SINCE_AMOUNTS = {
    1: {
        # Balancing amount at the database's NUMERIC(15,4) precision.
        "DSR-GENERAL": Decimal("5471871.6318"),
        "NS-GENERAL": Decimal("3018011.23"),
        "CEMENT-AGG": Decimal("134635.71130340002"),
        "10.1-ANGLES": Decimal("96281.46738449999"),
        "10.1-OTHER": Decimal("46241.6357655"),
        "9.48.2-OTHER": Decimal("44238.753693"),
    },
    2: {
        # Balancing amount at the database's NUMERIC(15,4) precision.
        "DSR-GENERAL": Decimal("5749321.7333"),
        "NS-GENERAL": Decimal("1359588.46"),
        "CEMENT-AGG": Decimal("67362.965069572"),
        "10.1-ANGLES": Decimal("0"),
        "10.1-OTHER": Decimal("6958.7321535"),
        "9.48.2-OTHER": Decimal("136762.549416"),
    },
    3: {
        "DSR-GENERAL": Decimal("4212"),
        "NS-GENERAL": Decimal("17879.28"),
        "CEMENT-AGG": Decimal("0"),
        "10.1-ANGLES": Decimal("0"),
        "10.1-OTHER": Decimal("0"),
        "9.48.2-OTHER": Decimal("0"),
    },
}


def _build_bill_lines() -> tuple[BillLineSeed, ...]:
    database_quantum = Decimal("0.0001")
    amount_cumulative = defaultdict(Decimal)
    quantity_cumulative = defaultdict(Decimal)
    rows: list[BillLineSeed] = []
    for bill in BILLS:
        for item in ITEMS:
            since = _SINCE_AMOUNTS[bill.number][item.code].quantize(database_quantum)
            amount_up_to_last = amount_cumulative[item.code]
            amount_up_to_date = amount_up_to_last + since
            qty_up_to_last = quantity_cumulative[item.code]
            qty_since_last = Decimal("1") if since else Decimal("0")
            qty_up_to_date = qty_up_to_last + qty_since_last
            rows.append(
                BillLineSeed(
                    bill.number,
                    item.code,
                    qty_up_to_last,
                    qty_since_last,
                    qty_up_to_date,
                    amount_up_to_last,
                    since,
                    amount_up_to_date,
                    Decimal("1249")
                    if bill.number == 1 and item.code == "DSR-GENERAL"
                    else Decimal("0"),
                )
            )
            amount_cumulative[item.code] = amount_up_to_date
            quantity_cumulative[item.code] = qty_up_to_date
    return tuple(rows)


BILL_LINES = _build_bill_lines()

RECOVERIES = (
    RecoverySeed(1, "labour_cess", Decimal("74672")),
    RecoverySeed(1, "security_deposit", Decimal("289441")),
    RecoverySeed(1, "water", Decimal("1853")),
    RecoverySeed(1, "other", Decimal("1249")),
    RecoverySeed(1, "income_tax", Decimal("149344")),
    RecoverySeed(2, "security_deposit", Decimal("265243")),
    RecoverySeed(2, "water", Decimal("1483")),
    RecoverySeed(2, "income_tax", Decimal("124068")),
    RecoverySeed(2, "labour_cess", Decimal("62034")),
    RecoverySeed(3, "water", Decimal("1320")),
    RecoverySeed(3, "income_tax", Decimal("374")),
    RecoverySeed(3, "labour_cess", Decimal("187")),
)

EXPECTED_NET_AMOUNTS = {
    1: Decimal("8294721.43"),
    2: Decimal("6867166.44"),
    3: Decimal("20210.28"),
}

EXPECTED_BUCKETS = {
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


class Counts(dict[str, int]):
    def add(self, key: str, created: bool) -> None:
        suffix = "created" if created else "skipped"
        self[f"{key}_{suffix}"] = self.get(f"{key}_{suffix}", 0) + 1


class DryRunRollback(RuntimeError):
    pass


def resolve_tenant_id() -> str:
    tenant_id = os.environ.get("SEED_TENANT_ID", "").strip()
    if not tenant_id:
        raise SystemExit("SEED_TENANT_ID is required; refusing to seed a default tenant")
    return tenant_id


def is_dry_run() -> bool:
    value = os.environ.get("SEED_DRY_RUN", "0").strip().lower()
    if value in {"0", "false"}:
        return False
    if value in {"1", "true"}:
        return True
    raise SystemExit("SEED_DRY_RUN must be one of: 0, 1, false, true")


def resolve_database_destination(dry_run: bool) -> tuple[str, int, str]:
    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if not raw_url:
        raise SystemExit("DATABASE_URL is required")
    url = make_url(raw_url)
    host = url.host or ""
    port = url.port or 5432
    database = url.database or ""
    if not host or not database:
        raise SystemExit("DATABASE_URL must include a database host and name")

    if not dry_run:
        expected_host = os.environ.get("SEED_EXPECTED_DB_HOST", "").strip()
        if not expected_host:
            raise SystemExit(
                "SEED_EXPECTED_DB_HOST is required in commit mode; refusing an "
                "unverified database destination"
            )
        if host.casefold() != expected_host.casefold():
            raise SystemExit(
                "DATABASE_URL host does not match SEED_EXPECTED_DB_HOST: "
                f"expected {expected_host}, got {host}"
            )
    return host, port, database


async def connect() -> asyncpg.Connection:
    url = make_url(os.environ["DATABASE_URL"].strip())
    try:
        return await asyncpg.connect(
            host=url.host,
            port=url.port,
            user=url.username,
            password=str(url.password),
            database=url.database,
        )
    except (asyncpg.PostgresError, OSError) as exc:
        raise SystemExit(f"Could not connect using backend/.env DATABASE_URL: {exc}") from exc


async def require_target_tenant(conn: asyncpg.Connection, tenant_id: str) -> None:
    row = await conn.fetchrow(
        """
        SELECT t.name, ti.consumed_at,
               EXISTS (
                   SELECT 1
                   FROM users u
                   WHERE u.tenant_id = t.id
                     AND lower(u.email) = 'claudebotkar@gmail.com'
                     AND u.supabase_auth_id IS NOT NULL
               ) AS has_active_user_mapping
        FROM tenants t
        JOIN tenant_invites ti ON ti.tenant_id = t.id
        WHERE t.id = $1::uuid
          AND lower(ti.email) = 'claudebotkar@gmail.com'
        FOR SHARE OF t, ti
        """,
        tenant_id,
    )
    if row is None:
        raise SystemExit(
            "SEED_TENANT_ID is not Ritesh's invited claudebotkar@gmail.com tenant"
        )
    if row["name"] != "BANJARA CONSTRUCTION CORPORATION- MUMBAI":
        raise SystemExit(f"Unexpected target tenant name: {row['name']}")
    if row["consumed_at"] is None:
        raise SystemExit("Ritesh's invite has not been consumed; refusing to seed")
    if not row["has_active_user_mapping"]:
        raise SystemExit(
            "Ritesh has no active claudebotkar@gmail.com user mapping in this tenant"
        )


async def get_or_create_contract(
    conn: asyncpg.Connection, tenant_id: str
) -> tuple[str, bool]:
    existing_rows = await conn.fetch(
        """
        SELECT id::text AS id
        FROM contracts
        WHERE tenant_id = $1::uuid AND tender_number = $2
        ORDER BY id
        """,
        tenant_id,
        TENDER_NUMBER,
    )
    if len(existing_rows) > 1:
        raise RuntimeError(
            f"duplicate existing contracts for tenant/tender: {tenant_id}/{TENDER_NUMBER}"
        )
    if existing_rows:
        return existing_rows[0]["id"], False
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
            $10::date, $11::date, $12::date, 'WR'::railway_zone, 'inclusive'::gst_mode,
            TRUE, 0, 'Completed'::contract_status
        )
        RETURNING id::text AS id
        """,
        tenant_id,
        TENDER_NUMBER,
        AGREEMENT_NUMBER,
        LOA_NUMBER,
        date(2024, 5, 3),
        "BANJARA CONSTRUCTION CORPORATION-MUMBAI",
        WORK_DESCRIPTION,
        Decimal("10854812.98"),
        Decimal("10854812.98"),
        date(2024, 5, 6),
        date(2025, 5, 3),
        BASE_MONTH,
    )
    assert row is not None
    return row["id"], True


async def get_or_create_rule_set(
    conn: asyncpg.Connection, contract_id: str
) -> tuple[str, bool]:
    row = await conn.fetchrow(
        """
        INSERT INTO pvc_rule_sets (
            contract_id, version, quarter_mode, component_weights,
            extra_item_policy, adjustable_fraction, rounding_mode,
            negative_pvc_policy, quarter_avg_precision
        )
        VALUES (
            $1::uuid, 1, 'measurement_date'::quarter_mode, $2::jsonb,
            'exclude_by_default'::extra_item_policy, 0.85,
            'round_2'::rounding_mode, 'allow'::negative_pvc_policy, 'full'
        )
        ON CONFLICT (contract_id, version) DO NOTHING
        RETURNING id::text AS id
        """,
        contract_id,
        json.dumps(RULE_WEIGHTS),
    )
    if row is not None:
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
        SELECT id::text AS id FROM schedules
        WHERE contract_id = $1::uuid AND name = $2
          AND schedule_type = $3::schedule_type
        """,
        contract_id,
        seed.name,
        seed.schedule_type,
    )
    if existing is not None:
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
        SELECT id::text AS id FROM contract_items
        WHERE contract_id = $1::uuid AND item_code = $2
        """,
        contract_id,
        seed.code,
    )
    if existing is not None:
        return existing["id"], False
    row = await conn.fetchrow(
        """
        INSERT INTO contract_items (
            contract_id, schedule_id, item_code, description, unit,
            original_qty, revised_qty, base_rate, agreement_rate,
            is_cement_item, steel_subtype
        )
        VALUES (
            $1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10,
            $11::steel_subtype
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
    if row is not None:
        return row["id"], True
    existing = await conn.fetchrow(
        """
        SELECT id::text AS id FROM running_bills
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
        ON CONFLICT (bill_id, item_id) DO UPDATE SET
            qty_up_to_last = EXCLUDED.qty_up_to_last,
            qty_since_last = EXCLUDED.qty_since_last,
            qty_up_to_date = EXCLUDED.qty_up_to_date,
            amount_up_to_last = EXCLUDED.amount_up_to_last,
            amount_since_last = EXCLUDED.amount_since_last,
            amount_up_to_date = EXCLUDED.amount_up_to_date,
            special_condition_amount = EXCLUDED.special_condition_amount
        RETURNING (xmax = 0) AS created
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
    assert row is not None
    return row["created"]


async def insert_recovery(
    conn: asyncpg.Connection, bill_id: str, seed: RecoverySeed
) -> bool:
    existing = await conn.fetchrow(
        """
        SELECT id FROM recoveries
        WHERE bill_id = $1::uuid AND recovery_type = $2::recovery_type
          AND amount = $3 AND affects_pvc_base = $4
        """,
        bill_id,
        seed.recovery_type,
        seed.amount,
        seed.affects_pvc_base,
    )
    if existing is not None:
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


async def verify_seed(conn: asyncpg.Connection, contract_id: str) -> dict[str, int]:
    header = await conn.fetchrow(
        """
        SELECT agreement_number, loa_number, loa_date, contract_value, bid_amount,
               start_date, completion_date, base_month, railway_zone::text AS railway_zone,
               gst_mode::text AS gst_mode, status::text AS status
        FROM contracts WHERE id = $1::uuid
        """,
        contract_id,
    )
    assert header is not None
    expected_header = {
        "agreement_number": AGREEMENT_NUMBER,
        "loa_number": LOA_NUMBER,
        "loa_date": date(2024, 5, 3),
        "contract_value": Decimal("10854812.98"),
        "bid_amount": Decimal("10854812.98"),
        "start_date": date(2024, 5, 6),
        "completion_date": date(2025, 5, 3),
        "base_month": BASE_MONTH,
        "railway_zone": "WR",
        "gst_mode": "inclusive",
        "status": "Completed",
    }
    for key, expected in expected_header.items():
        if header[key] != expected:
            raise RuntimeError(
                f"existing contract mismatch for {key}: expected {expected}, got {header[key]}"
            )

    rule_rows = await conn.fetch(
        """
        SELECT id::text AS id, contract_id::text AS contract_id, version,
               quarter_mode::text AS quarter_mode,
               component_weights::text AS component_weights,
               extra_item_policy::text AS extra_item_policy,
               adjustable_fraction, rounding_mode::text AS rounding_mode,
               negative_pvc_policy::text AS negative_pvc_policy,
               quarter_avg_precision, created_at
        FROM pvc_rule_sets
        WHERE contract_id = $1::uuid
        ORDER BY version
        """,
        contract_id,
    )
    if len(rule_rows) != 1:
        raise RuntimeError(
            f"expected exactly one PVC rule set, found {len(rule_rows)}"
        )
    rule = rule_rows[0]
    expected_rule = {
        "contract_id": contract_id,
        "version": 1,
        "quarter_mode": "measurement_date",
        "component_weights": RULE_WEIGHTS,
        "extra_item_policy": "exclude_by_default",
        "adjustable_fraction": Decimal("0.8500"),
        "rounding_mode": "round_2",
        "negative_pvc_policy": "allow",
        "quarter_avg_precision": "full",
    }
    for key, expected in expected_rule.items():
        actual = json.loads(rule[key]) if key == "component_weights" else rule[key]
        if actual != expected:
            raise RuntimeError(
                f"existing PVC rule-set mismatch for {key}: "
                f"expected {expected}, got {actual}"
            )
    if not rule["id"] or rule["created_at"] is None:
        raise RuntimeError("PVC rule set has invalid generated identity/audit fields")

    count_row = await conn.fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM schedules WHERE contract_id = $1::uuid) AS schedules,
            (SELECT COUNT(*) FROM contract_items WHERE contract_id = $1::uuid) AS items,
            (SELECT COUNT(*) FROM running_bills WHERE contract_id = $1::uuid) AS bills,
            (
                SELECT COUNT(*) FROM bill_lines bl
                JOIN running_bills b ON b.id = bl.bill_id
                WHERE b.contract_id = $1::uuid
            ) AS bill_lines,
            (
                SELECT COUNT(*) FROM recoveries r
                JOIN running_bills b ON b.id = r.bill_id
                WHERE b.contract_id = $1::uuid
            ) AS recoveries,
            (SELECT COUNT(*) FROM pvc_runs WHERE contract_id = $1::uuid) AS pvc_runs
        """,
        contract_id,
    )
    assert count_row is not None
    counts = dict(count_row)
    expected_counts = {
        "schedules": len(SCHEDULES),
        "items": len(ITEMS),
        "bills": len(BILLS),
        "bill_lines": len(BILL_LINES),
        "recoveries": len(RECOVERIES),
        "pvc_runs": 0,
    }
    if counts != expected_counts:
        raise RuntimeError(f"seed row-count mismatch: expected {expected_counts}, got {counts}")

    rows = await conn.fetch(
        """
        SELECT b.bill_number, b.bill_date, b.measurement_date, b.gross_amount,
               COALESCE(SUM(bl.amount_since_last), 0) AS line_total,
               COALESCE(SUM(CASE WHEN ci.is_cement_item THEN bl.amount_since_last END), 0) AS cement,
               COALESCE(SUM(CASE WHEN ci.steel_subtype = 'angles' THEN bl.amount_since_last END), 0) AS steel_angles,
               COALESCE(SUM(CASE WHEN ci.steel_subtype = 'other_sections' THEN bl.amount_since_last END), 0) AS steel_other,
               COALESCE(SUM(bl.special_condition_amount), 0) AS technical_withheld
        FROM running_bills b
        LEFT JOIN bill_lines bl ON bl.bill_id = b.id
        LEFT JOIN contract_items ci ON ci.id = bl.item_id
        WHERE b.contract_id = $1::uuid
        GROUP BY b.id
        ORDER BY b.bill_number
        """,
        contract_id,
    )
    by_number = {bill.number: bill for bill in BILLS}
    for row in rows:
        number = row["bill_number"]
        source = by_number[number]
        if (
            row["bill_date"] != source.bill_date
            or row["measurement_date"] != source.measurement_date
            or row["gross_amount"] != source.gross_amount
            or row["line_total"] != source.gross_amount
        ):
            raise RuntimeError(f"bill {number} header/line reconciliation failed")
        for bucket, expected in EXPECTED_BUCKETS[number].items():
            if row[bucket].quantize(Decimal("0.0001")) != expected.quantize(
                Decimal("0.0001")
            ):
                raise RuntimeError(
                    f"bill {number} {bucket} mismatch: expected {expected}, got {row[bucket]}"
                )

    line_rows = await conn.fetch(
        """
        SELECT b.bill_number, ci.item_code,
               bl.qty_up_to_last, bl.qty_since_last, bl.qty_up_to_date,
               bl.amount_up_to_last, bl.amount_since_last, bl.amount_up_to_date,
               bl.special_condition_amount
        FROM bill_lines bl
        JOIN running_bills b ON b.id = bl.bill_id
        JOIN contract_items ci ON ci.id = bl.item_id
        WHERE b.contract_id = $1::uuid
        ORDER BY b.bill_number, ci.item_code
        """,
        contract_id,
    )
    persisted_lines = {
        (row["bill_number"], row["item_code"]): row for row in line_rows
    }
    expected_lines = {
        (line.bill_number, line.item_code): line for line in BILL_LINES
    }
    if persisted_lines.keys() != expected_lines.keys():
        raise RuntimeError("persisted bill-line identities do not match the source seed")
    numeric_line_fields = (
        "qty_up_to_last",
        "qty_since_last",
        "qty_up_to_date",
        "amount_up_to_last",
        "amount_since_last",
        "amount_up_to_date",
        "special_condition_amount",
    )
    quantum = Decimal("0.0001")
    for identity, expected_line in expected_lines.items():
        persisted = persisted_lines[identity]
        for field in numeric_line_fields:
            expected = getattr(expected_line, field).quantize(quantum)
            actual = persisted[field].quantize(quantum)
            if actual != expected:
                raise RuntimeError(
                    f"bill line {identity} mismatch for {field}: "
                    f"expected {expected}, got {actual}"
                )

    recovery_rows = await conn.fetch(
        """
        SELECT b.bill_number, COALESCE(SUM(r.amount), 0) AS recovery_total
        FROM running_bills b
        LEFT JOIN recoveries r ON r.bill_id = b.id
        WHERE b.contract_id = $1::uuid
        GROUP BY b.id
        ORDER BY b.bill_number
        """,
        contract_id,
    )
    for row in recovery_rows:
        number = row["bill_number"]
        net = by_number[number].gross_amount - row["recovery_total"]
        if net != EXPECTED_NET_AMOUNTS[number]:
            raise RuntimeError(
                f"bill {number} signed net mismatch: expected {EXPECTED_NET_AMOUNTS[number]}, got {net}"
            )
    return counts


async def seed() -> None:
    tenant_id = resolve_tenant_id()
    dry_run = is_dry_run()
    db_host, db_port, db_name = resolve_database_destination(dry_run)
    print(f"DATABASE_DESTINATION={db_host}:{db_port}/{db_name}")
    conn = await connect()
    counts = Counts()
    contract_id = ""
    verified: dict[str, int] = {}
    try:
        try:
            async with conn.transaction():
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))",
                    f"{tenant_id}:{TENDER_NUMBER}",
                )
                await require_target_tenant(conn, tenant_id)
                contract_id, created = await get_or_create_contract(conn, tenant_id)
                counts.add("contract", created)

                _, created = await get_or_create_rule_set(conn, contract_id)
                counts.add("rule_set", created)

                schedule_ids: dict[str, str] = {}
                for schedule in SCHEDULES:
                    schedule_id, created = await get_or_create_schedule(
                        conn, contract_id, schedule
                    )
                    schedule_ids[schedule.key] = schedule_id
                    counts.add("schedule", created)

                item_ids: dict[str, str] = {}
                for item in ITEMS:
                    item_id, created = await get_or_create_item(
                        conn,
                        contract_id,
                        schedule_ids[item.schedule_key],
                        item,
                    )
                    item_ids[item.code] = item_id
                    counts.add("item", created)

                bill_ids: dict[int, str] = {}
                for bill in BILLS:
                    bill_id, created = await get_or_create_bill(conn, contract_id, bill)
                    bill_ids[bill.number] = bill_id
                    counts.add("bill", created)

                for line in BILL_LINES:
                    counts.add(
                        "bill_line",
                        await insert_bill_line(
                            conn,
                            bill_ids[line.bill_number],
                            item_ids[line.item_code],
                            line,
                        ),
                    )

                for recovery in RECOVERIES:
                    counts.add(
                        "recovery",
                        await insert_recovery(
                            conn, bill_ids[recovery.bill_number], recovery
                        ),
                    )

                verified = await verify_seed(conn, contract_id)
                if dry_run:
                    raise DryRunRollback()
        except DryRunRollback:
            pass
    finally:
        await conn.close()

    mode = "DRY RUN ROLLED BACK" if dry_run else "COMMITTED"
    print(mode)
    print(f"TENANT_ID={tenant_id}")
    print(f"CONTRACT_ID={contract_id}")
    print(f"created_or_skipped={dict(sorted(counts.items()))}")
    print(f"verified_counts={verified}")
    print(f"view=/contracts/{contract_id}/bills")


if __name__ == "__main__":
    asyncio.run(seed())
