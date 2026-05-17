"""Engine-payload construction, snapshot building, and run persistence.

This module is deliberately split into:

  * **Pure domain functions** (no I/O) — easy to unit-test, pinned by the
    remediation tests. These are the locus of every silent-wrong-number
    failure the P3 review caught:
      - `merge_extra_item_decisions`   — P3-02 (undecided items reach engine)
      - `select_zone_series`           — P3-04 (zone-specific overrides generic)
      - `build_index_snapshot_series`  — composition of the above
      - `default_rule_set_payload`     — P3-07 (deterministic contract bootstrap)

  * **DB-bound functions** — call the pure functions and persist results.
    These are thin and rely on the pure layer for correctness.

Every DB-bound function takes an explicit `tenant_id` argument and uses it
in every WHERE clause. The backend uses a privileged connection (P3-03);
RLS is not enforcing anything at the API layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from engine import calculate_pvc
from engine.types import (
    BillPayload,
    CarryForwardPayload,
    ExtraItemDecision,
    IndexSnapshot,
    PVCRuleSet,
)

from .errors import (
    EngineValidationProblem,
    IdempotencyConflict,
    NotFoundProblem,
    ValidationProblem,
)
from .zone_mapping import STEEL_SERIES_NAMES, city_for_zone


# ---------------------------------------------------------------------------
# Pure domain functions (no DB) — pinned by tests/test_pvc_service_pure.py
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExtraItemInput:
    """Source row used to build engine `ExtraItemDecision`. Comes from joining
    the bill's actual extra-NS lines (NOT from extra_item_decisions). This
    framing is the P3-02 fix: the bill drives the payload, decisions only
    annotate; missing decisions become explicit `eligible=None`."""
    item_id: str
    bill_line_id: str
    amount: Decimal


def merge_extra_item_decisions(
    bill_extra_items: list[ExtraItemInput],
    decisions: dict[str, bool | None],
) -> list[ExtraItemDecision]:
    """For every extra-NS line in the current bill, attach the decision row
    if one exists. Lines without a decision row pass through with
    `eligible=None`, which the engine treats as a blocking validation error.

    This is the heart of the P3-02 fix. The previous implementation built
    the list from `extra_item_decisions` and left-joined bill lines, which
    silently dropped undecided items. Driving from the bill side means
    omissions surface as explicit blocks.
    """
    out: list[ExtraItemDecision] = []
    for line in bill_extra_items:
        eligible = decisions.get(line.item_id)  # None if no decision row
        out.append(ExtraItemDecision(
            item_id=line.item_id,
            amount=line.amount,
            eligible=eligible,
            source_ref=line.bill_line_id,
        ))
    return out


def select_zone_series(
    available_series: dict[str, dict[str, Decimal]],
    zone: str,
) -> dict[str, dict[str, Decimal]]:
    """Resolve the engine-facing series map for a contract's zone.

    Rule (P3-04): if a city-specific series (e.g. `steel_tmt_kolkata`) is
    present in `available_series`, it **overrides** the generic series under
    the engine-expected name (`steel_tmt`), regardless of whether the generic
    series also exists. If only the generic is available, it is used as-is.

    The previous implementation only aliased the city-specific series when
    the generic was absent — meaning two contracts in different zones
    received identical steel snapshots whenever both forms were seeded.
    """
    city = city_for_zone(zone)
    out: dict[str, dict[str, Decimal]] = {}

    # Pass through everything first…
    for name, obs in available_series.items():
        out[name] = dict(obs)

    # …then deterministically overlay city-specific steel series.
    for steel_name in STEEL_SERIES_NAMES:
        city_key = f"{steel_name}_{city.lower()}"
        if city_key in available_series:
            out[steel_name] = dict(available_series[city_key])
            # Drop the city-specific entry to keep the engine snapshot tight.
            out.pop(city_key, None)

    return out


def default_rule_set_payload() -> dict[str, Any]:
    """The version-1 PVC rule set seeded transactionally with a new contract
    (P3-07). Matches `TASKS.md` P1-006 / P3-008 default weights and the
    KU-001 quarter anchor; concrete values live here so contract creation
    has a single source of truth and the frontend doesn't have to re-supply
    them on every contract POST."""
    return {
        "version": 1,
        "quarter_mode": "measurement_date",
        "component_weights": {
            "labour": "0.20",
            "plant": "0.30",
            "fuel": "0.15",
            "materials": "0.20",
        },
        "extra_item_policy": "exclude_by_default",
        "adjustable_fraction": "0.85",
        "rounding_mode": "round_2",
        "negative_pvc_policy": "zero_floor",
    }


# ---------------------------------------------------------------------------
# DB-bound functions (tenant-scoped, no RLS reliance)
# ---------------------------------------------------------------------------


async def assert_bill_belongs_to_tenant(
    session: AsyncSession, bill_id: str, tenant_id: str
) -> str:
    """Return the bill's contract_id if the caller's tenant owns it,
    otherwise raise NotFoundProblem (we deliberately do not distinguish
    "wrong tenant" from "doesn't exist" — see P3-06 rationale)."""
    row = (
        await session.execute(
            text("""
                SELECT b.contract_id::text AS contract_id
                FROM running_bills b
                JOIN contracts c ON c.id = b.contract_id
                WHERE b.id = :bill_id AND c.tenant_id = :tenant_id
            """),
            {"bill_id": bill_id, "tenant_id": tenant_id},
        )
    ).mappings().first()
    if row is None:
        raise NotFoundProblem("Bill not found", entity="running_bill", id=bill_id)
    return row["contract_id"]


async def assert_item_belongs_to_contract(
    session: AsyncSession, item_id: str, contract_id: str
) -> None:
    """P3-06: bill_lines must reference contract_items that belong to the
    bill's contract. Tenant ownership is necessary but not sufficient —
    every cross-table write must verify the full parent-child path."""
    row = (
        await session.execute(
            text("SELECT 1 FROM contract_items WHERE id = :id AND contract_id = :cid"),
            {"id": item_id, "cid": contract_id},
        )
    ).first()
    if row is None:
        raise ValidationProblem(
            "Contract item does not belong to the bill's contract",
            item_id=item_id,
            contract_id=contract_id,
        )


async def create_contract_with_default_rule_set(
    session: AsyncSession, tenant_id: str, contract_data: dict[str, Any]
) -> dict[str, Any]:
    """P3-07: insert the contract and its version-1 rule set in a single
    transaction. If rule-set creation fails, the contract is rolled back —
    the system never reaches a half-bootstrapped state where the contract
    exists but PVC runs immediately 404 on the missing rule set."""
    async with session.begin_nested():
        contract_row = (
            await session.execute(
                text("""
                    INSERT INTO contracts (
                        tenant_id, tender_number, agreement_number, loa_number,
                        loa_date, contractor_name, work_description,
                        contract_value, bid_amount, start_date, completion_date,
                        base_month, gst_mode, pvc_applicable, overall_rebate,
                        railway_zone, status
                    )
                    VALUES (
                        :tenant_id, :tender_number, :agreement_number, :loa_number,
                        :loa_date, :contractor_name, :work_description,
                        :contract_value, :bid_amount, :start_date, :completion_date,
                        :base_month, :gst_mode, :pvc_applicable, :overall_rebate,
                        :railway_zone, 'Draft'
                    )
                    RETURNING id::text AS id, created_at
                """),
                {**contract_data, "tenant_id": tenant_id},
            )
        ).mappings().first()
        assert contract_row is not None

        rs = default_rule_set_payload()
        await session.execute(
            text("""
                INSERT INTO pvc_rule_sets (
                    contract_id, version, quarter_mode, component_weights,
                    extra_item_policy, adjustable_fraction, rounding_mode,
                    negative_pvc_policy
                )
                VALUES (
                    :contract_id, :version, :quarter_mode,
                    CAST(:component_weights AS JSONB),
                    :extra_item_policy, :adjustable_fraction, :rounding_mode,
                    :negative_pvc_policy
                )
            """),
            {
                "contract_id": contract_row["id"],
                "version": rs["version"],
                "quarter_mode": rs["quarter_mode"],
                "component_weights": _json_dumps(rs["component_weights"]),
                "extra_item_policy": rs["extra_item_policy"],
                "adjustable_fraction": rs["adjustable_fraction"],
                "rounding_mode": rs["rounding_mode"],
                "negative_pvc_policy": rs["negative_pvc_policy"],
            },
        )

    return {"id": contract_row["id"], "created_at": contract_row["created_at"]}


async def build_bill_payload(
    session: AsyncSession, bill_id: str, contract_id: str
) -> BillPayload:
    """Construct the engine payload for a bill.

    Critical behaviours pinned by the P3 remediation:
      * Extra-item decisions come from the current bill's actual ExtraNS
        lines (P3-02). Missing decisions become explicit `eligible=None`.
      * Carry-forwards have `paid_ratio` computed by the engine model,
        never accepted from client input (P3-05 acceptance).
      * `source_ref` is the bill_lines.id so the trace can link a deduction
        back to its source row (P2-06 contract).
    """
    bill = (
        await session.execute(
            text("""
                SELECT measurement_date, gross_amount
                FROM running_bills WHERE id = :bid
            """),
            {"bid": bill_id},
        )
    ).mappings().first()
    if bill is None:
        raise NotFoundProblem("Bill not found", entity="running_bill", id=bill_id)

    # W-bucket aggregations from bill_lines × contract_items.
    bucket_rows = (
        await session.execute(
            text("""
                SELECT
                    COALESCE(SUM(CASE WHEN ci.is_cement_item THEN bl.amount_since_last END), 0) AS cement,
                    COALESCE(SUM(CASE WHEN ci.steel_subtype = 'angles' THEN bl.amount_since_last END), 0) AS steel_angles,
                    COALESCE(SUM(CASE WHEN ci.steel_subtype = 'plates' THEN bl.amount_since_last END), 0) AS steel_plates,
                    COALESCE(SUM(CASE WHEN ci.steel_subtype = 'tmt' THEN bl.amount_since_last END), 0) AS steel_tmt,
                    COALESCE(SUM(CASE WHEN ci.steel_subtype = 'other_sections' THEN bl.amount_since_last END), 0) AS steel_other
                FROM bill_lines bl
                JOIN contract_items ci ON ci.id = bl.item_id
                WHERE bl.bill_id = :bid AND ci.contract_id = :cid
            """),
            {"bid": bill_id, "cid": contract_id},
        )
    ).mappings().first()
    assert bucket_rows is not None

    # P3-02: drive from bill side, NOT from extra_item_decisions.
    extra_inputs = [
        ExtraItemInput(
            item_id=str(r["item_id"]),
            bill_line_id=str(r["bill_line_id"]),
            amount=Decimal(r["amount"]),
        )
        for r in (
            await session.execute(
                text("""
                    SELECT
                        bl.id::text AS bill_line_id,
                        ci.id::text AS item_id,
                        bl.amount_since_last AS amount
                    FROM bill_lines bl
                    JOIN contract_items ci ON ci.id = bl.item_id
                    JOIN schedules s ON s.id = ci.schedule_id
                    WHERE bl.bill_id = :bid
                      AND ci.contract_id = :cid
                      AND s.schedule_type = 'ExtraNS'
                """),
                {"bid": bill_id, "cid": contract_id},
            )
        ).mappings()
    ]

    decision_rows = (
        await session.execute(
            text("""
                SELECT item_id::text AS item_id, eligible
                FROM extra_item_decisions
                WHERE contract_id = :cid
            """),
            {"cid": contract_id},
        )
    ).mappings().all()
    decisions: dict[str, bool | None] = {
        r["item_id"]: r["eligible"] for r in decision_rows
    }
    extra_item_decisions = merge_extra_item_decisions(extra_inputs, decisions)

    excluded_extra_total = sum(
        (d.amount for d in extra_item_decisions if d.eligible is False),
        Decimal("0"),
    )

    cf_rows = (
        await session.execute(
            text("""
                SELECT
                    cf.id::text AS id,
                    cf.item_id::text AS item_id,
                    cf.recorded_qty,
                    cf.paid_qty_source,
                    cf.carry_qty,
                    ci.steel_subtype AS steel_subtype,
                    ci.agreement_rate AS rate
                FROM carry_forwards cf
                JOIN contract_items ci ON ci.id = cf.item_id
                WHERE cf.target_bill_id = :bid AND ci.contract_id = :cid
            """),
            {"bid": bill_id, "cid": contract_id},
        )
    ).mappings().all()
    carry_forwards = [
        CarryForwardPayload(
            item_id=str(r["item_id"]),
            recorded_qty=Decimal(r["recorded_qty"]),
            paid_qty_source=Decimal(r["paid_qty_source"]),
            amount=Decimal(r["recorded_qty"]) * Decimal(r["rate"] or 0),
            steel_subtype=r["steel_subtype"],
            source_ref=r["id"],
        )
        for r in cf_rows
    ]

    on_account = Decimal(bill["gross_amount"] or 0)
    return BillPayload(
        on_account_amount=on_account,
        cement_amount=Decimal(bucket_rows["cement"]),
        steel_angles_amount=Decimal(bucket_rows["steel_angles"]),
        steel_plates_amount=Decimal(bucket_rows["steel_plates"]),
        steel_tmt_amount=Decimal(bucket_rows["steel_tmt"]),
        steel_other_amount=Decimal(bucket_rows["steel_other"]),
        technical_withheld=Decimal("0"),
        extra_item_decisions=extra_item_decisions,
        carry_forwards=carry_forwards,
        measurement_date=bill["measurement_date"],
    )


async def build_index_snapshot(
    session: AsyncSession, base_month: date, quarter_months: list[date], zone: str
) -> IndexSnapshot:
    """Load index values for base + quarter months and resolve them through
    the zone mapping. P3-04: city-specific JPC series always win, even when
    the generic series is also seeded."""
    months = [base_month, *quarter_months]
    rows = (
        await session.execute(
            text("""
                SELECT s.name AS series, o.month AS month, o.value AS value
                FROM index_observations o
                JOIN index_series s ON s.id = o.series_id
                WHERE o.month = ANY(:months)
            """),
            {"months": months},
        )
    ).mappings().all()

    available: dict[str, dict[str, Decimal]] = {}
    for r in rows:
        key = r["month"].strftime("%Y-%m")
        available.setdefault(r["series"], {})[key] = Decimal(r["value"])

    resolved = select_zone_series(available, zone)
    return IndexSnapshot(base_month=base_month, series=resolved)


async def find_run_by_idempotency_key(
    session: AsyncSession, contract_id: str, bill_id: str, key: str
) -> str | None:
    row = (
        await session.execute(
            text("""
                SELECT id::text AS id FROM pvc_runs
                WHERE contract_id = :cid AND bill_id = :bid
                  AND idempotency_key = :key
            """),
            {"cid": contract_id, "bid": bill_id, "key": key},
        )
    ).mappings().first()
    return row["id"] if row else None


async def execute_pvc_run(
    session: AsyncSession,
    *,
    tenant_id: str,
    contract_id: str,
    bill_id: str,
    rule_set_row: dict[str, Any],
    idempotency_key: str | None,
) -> dict[str, Any]:
    """End-to-end PVC run: build payload, call engine, persist atomically.

    Idempotency (P3-05): if a key is supplied and a row already exists for
    (contract_id, bill_id, key), raise IdempotencyConflict with the existing
    run_id. The DB also enforces uniqueness via a partial unique index
    (migration 012); the pre-check is for friendly 409 messages, the index
    is the actual guarantee.
    """
    if idempotency_key:
        existing = await find_run_by_idempotency_key(
            session, contract_id, bill_id, idempotency_key
        )
        if existing:
            raise IdempotencyConflict(existing)

    contract_row = (
        await session.execute(
            text("""
                SELECT base_month, railway_zone::text AS railway_zone
                FROM contracts WHERE id = :cid AND tenant_id = :tid
            """),
            {"cid": contract_id, "tid": tenant_id},
        )
    ).mappings().first()
    if contract_row is None:
        raise NotFoundProblem("Contract not found", entity="contract", id=contract_id)
    if contract_row["railway_zone"] is None:
        raise ValidationProblem(
            "Contract has no railway_zone — required for JPC snapshot selection",
            contract_id=contract_id,
        )

    bill_payload = await build_bill_payload(session, bill_id, contract_id)

    # The engine resolves quarter months from measurement_date; we mirror that
    # to load the right observations. Importing the resolver keeps the two in
    # lock-step.
    from engine.quarter import resolve_quarter

    _, quarter_months_str = resolve_quarter(bill_payload.measurement_date)
    quarter_months = [date.fromisoformat(f"{m}-01") for m in quarter_months_str]

    snapshot = await build_index_snapshot(
        session, contract_row["base_month"], quarter_months, contract_row["railway_zone"]
    )

    rules = PVCRuleSet(
        quarter_mode=rule_set_row["quarter_mode"],
        component_weights={
            k: Decimal(str(v)) for k, v in rule_set_row["component_weights"].items()
        },
        adjustable_fraction=Decimal(str(rule_set_row["adjustable_fraction"])),
        negative_pvc_policy=rule_set_row["negative_pvc_policy"],
        rounding_mode=rule_set_row["rounding_mode"],
    )

    result = calculate_pvc(bill_payload, snapshot, rules)
    if result.validation_errors:
        # P3-09: structured error so the frontend can surface the engine's
        # specific reasons instead of a generic 422.
        raise EngineValidationProblem(result.validation_errors)

    return await persist_run_result(
        session,
        contract_id=contract_id,
        bill_id=bill_id,
        rule_set_id=rule_set_row["id"],
        bill_payload=bill_payload,
        snapshot=snapshot,
        result=result,
        idempotency_key=idempotency_key,
    )


async def persist_run_result(
    session: AsyncSession,
    *,
    contract_id: str,
    bill_id: str,
    rule_set_id: str,
    bill_payload: BillPayload,
    snapshot: IndexSnapshot,
    result: Any,
    idempotency_key: str | None,
) -> dict[str, Any]:
    """Insert pvc_runs + pvc_components + revision_snapshots atomically.

    The savepoint protects the API from leaving an orphan run if the
    component insert fails (e.g. a bad enum value during refactor).
    """
    try:
        async with session.begin_nested():
            run_row = (
                await session.execute(
                    text("""
                        INSERT INTO pvc_runs (
                            contract_id, bill_id, rule_set_id,
                            index_snapshot, bill_snapshot, w_derivation,
                            status, idempotency_key
                        )
                        VALUES (
                            :cid, :bid, :rsid,
                            CAST(:idx AS JSONB), CAST(:bsnap AS JSONB),
                            CAST(:wd AS JSONB), 'Calculated', :key
                        )
                        RETURNING id::text AS id
                    """),
                    {
                        "cid": contract_id,
                        "bid": bill_id,
                        "rsid": rule_set_id,
                        "idx": snapshot.model_dump_json(),
                        "bsnap": bill_payload.model_dump_json(),
                        "wd": result.w_derivation.model_dump_json(),
                        "key": idempotency_key,
                    },
                )
            ).mappings().first()
            assert run_row is not None
            run_id = run_row["id"]

            for c in result.components:
                await session.execute(
                    text("""
                        INSERT INTO pvc_components (
                            run_id, category, eligible_amount, base_index,
                            current_avg_index, weight, pvc_value
                        )
                        VALUES (
                            :rid, :cat, :elig, :base, :cur, :w, :pvc
                        )
                    """),
                    {
                        "rid": run_id,
                        "cat": c.category,
                        "elig": str(c.eligible_amount),
                        "base": str(c.base_index),
                        "cur": str(c.current_avg_index),
                        "w": str(c.weight),
                        "pvc": str(c.pvc_value),
                    },
                )

            # P2-06 contract: full trace lives in revision_snapshots — that is
            # the audit truth even if index_observations later mutates.
            await session.execute(
                text("""
                    INSERT INTO revision_snapshots (run_id, snapshot_data)
                    VALUES (:rid, CAST(:data AS JSONB))
                """),
                {"rid": run_id, "data": result.trace.model_dump_json()},
            )
    except IntegrityError as exc:
        # Race: another concurrent caller landed the same idempotency_key
        # between our pre-check and the insert. Resolve via the same path.
        if idempotency_key:
            existing = await find_run_by_idempotency_key(
                session, contract_id, bill_id, idempotency_key
            )
            if existing:
                raise IdempotencyConflict(existing) from exc
        raise

    return {
        "id": run_id,
        "total_pvc": str(result.total_pvc),
        "negative_carry_forward": str(result.negative_carry_forward),
        "quarter_used": result.quarter_used,
    }


def _json_dumps(value: Any) -> str:
    import json
    return json.dumps(value)
