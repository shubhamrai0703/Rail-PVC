"""SH-P5-1..4: GET bills + bill detail + bill_lines + recoveries.

The handlers use Postgres-specific `::text` UUID casts and `status::text`
ENUM casts that aiosqlite cannot parse, so we stub `session.execute` at
the boundary — same pattern as `test_p3_bf_3_recoveries.py`. The mock
preserves the call order so the gate vs. list SELECTs can be asserted
independently.

For the list endpoints the explicit "empty list, not 404" contract is
what justifies a dedicated test: the gate proving the parent exists is
the entirety of the existence check; a zero-row list is a legitimate
state of an owned parent and must not be conflated with "not found".
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.bills import (
    get_bill,
    list_bill_lines,
    list_bills,
    list_recoveries,
)
from services.auth import AuthUser
from services.errors import NotFoundProblem


def _user() -> AuthUser:
    return AuthUser(
        user_id="user-1",
        tenant_id="tenant-A",
        auth_id="auth-1",
        email="t@example.com",
        display_name="t@example.com",
    )


def _session_with(*results: tuple[str, object]) -> AsyncMock:
    """AsyncSession stub. Each tuple is (kind, payload).

      - ("first", row | None) — `.mappings().first()` returns `row`
      - ("all",   list[row])  — `.mappings().all()` returns `list`

    Calls to `session.execute()` consume the tuples in order.
    """
    session = AsyncMock()
    mocked = []
    for kind, payload in results:
        result = MagicMock()
        mappings = MagicMock()
        if kind == "first":
            mappings.first.return_value = payload
        elif kind == "all":
            mappings.all.return_value = payload
        else:  # pragma: no cover — defensive
            raise ValueError(f"unknown result kind: {kind}")
        result.mappings.return_value = mappings
        # Some callers also use the bare `.first()` / `.all()` — populate both.
        result.first.return_value = payload if kind == "first" else None
        mocked.append(result)
    session.execute = AsyncMock(side_effect=mocked)
    return session


# ---------------------------------------------------------------------------
# SH-P5-1 — GET /api/contracts/{contract_id}/bills
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_bills_returns_rows():
    bill_rows = [
        {
            "id": "bill-1",
            "contract_id": "contract-own",
            "bill_number": 1,
            "bill_date": date(2026, 1, 15),
            "measurement_date": date(2026, 1, 31),
            "gross_amount": Decimal("100000.00"),
            "net_amount": Decimal("95000.00"),
            "status": "Draft",
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
        },
        {
            "id": "bill-2",
            "contract_id": "contract-own",
            "bill_number": 2,
            "bill_date": date(2026, 2, 15),
            "measurement_date": date(2026, 2, 28),
            "gross_amount": Decimal("120000.00"),
            "net_amount": Decimal("115000.00"),
            "status": "Approved",
            "created_at": datetime(2026, 2, 15, 10, 0, 0),
        },
    ]
    # Gate SELECT returns truthy → assert_contract_belongs_to_tenant passes.
    session = _session_with(("first", {1: 1}), ("all", bill_rows))

    out = await list_bills(
        contract_id="contract-own", user=_user(), session=session
    )

    assert out == bill_rows
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_bills_empty_returns_empty_list_not_404():
    # Gate passes, but the contract has no bills yet. The contract exists
    # under the caller's tenant; an empty list is the correct response.
    session = _session_with(("first", {1: 1}), ("all", []))

    out = await list_bills(
        contract_id="contract-own", user=_user(), session=session
    )

    assert out == []
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_bills_wrong_tenant_raises_not_found():
    # Gate SELECT returns None → NotFoundProblem(entity="contract"). The
    # second SELECT must not be called.
    session = _session_with(("first", None))

    with pytest.raises(NotFoundProblem) as exc:
        await list_bills(
            contract_id="contract-foreign", user=_user(), session=session
        )

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "contract"
    assert exc.value.extra["id"] == "contract-foreign"
    assert session.execute.await_count == 1


# ---------------------------------------------------------------------------
# SH-P5-2 — GET /api/bills/{bill_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_bill_returns_detail():
    bill_row = {
        "id": "bill-1",
        "contract_id": "contract-own",
        "bill_number": 1,
        "bill_date": date(2026, 1, 15),
        "measurement_date": date(2026, 1, 31),
        "gross_amount": Decimal("100000.00"),
        "net_amount": Decimal("95000.00"),
        "status": "Draft",
        "created_at": datetime(2026, 1, 15, 10, 0, 0),
    }
    # Gate returns {contract_id} → ownership confirmed; detail SELECT
    # returns the row.
    session = _session_with(
        ("first", {"contract_id": "contract-own"}),
        ("first", bill_row),
    )

    out = await get_bill(bill_id="bill-1", user=_user(), session=session)

    assert out == bill_row
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_get_bill_wrong_tenant_raises_not_found():
    session = _session_with(("first", None))

    with pytest.raises(NotFoundProblem) as exc:
        await get_bill(bill_id="bill-foreign", user=_user(), session=session)

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "running_bill"
    assert exc.value.extra["id"] == "bill-foreign"
    assert session.execute.await_count == 1


# ---------------------------------------------------------------------------
# SH-P5-3 — GET /api/bills/{bill_id}/lines
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_bill_lines_returns_rows():
    line_rows = [
        {
            "id": "line-1",
            "bill_id": "bill-own",
            "item_id": "item-1",
            "qty_up_to_last": Decimal("0"),
            "qty_since_last": Decimal("10"),
            "qty_up_to_date": Decimal("10"),
            "amount_up_to_last": Decimal("0"),
            "amount_since_last": Decimal("5000.00"),
            "amount_up_to_date": Decimal("5000.00"),
            "special_condition_amount": Decimal("0"),
        },
        {
            "id": "line-2",
            "bill_id": "bill-own",
            "item_id": "item-2",
            "qty_up_to_last": Decimal("0"),
            "qty_since_last": Decimal("5"),
            "qty_up_to_date": Decimal("5"),
            "amount_up_to_last": Decimal("0"),
            "amount_since_last": Decimal("2500.00"),
            "amount_up_to_date": Decimal("2500.00"),
            "special_condition_amount": Decimal("0"),
        },
    ]
    session = _session_with(
        ("first", {"contract_id": "contract-own"}),
        ("all", line_rows),
    )

    out = await list_bill_lines(
        bill_id="bill-own", user=_user(), session=session
    )

    assert out == line_rows
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_bill_lines_empty_returns_empty_list_not_404():
    session = _session_with(
        ("first", {"contract_id": "contract-own"}),
        ("all", []),
    )

    out = await list_bill_lines(
        bill_id="bill-own", user=_user(), session=session
    )

    assert out == []
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_bill_lines_wrong_tenant_raises_not_found():
    session = _session_with(("first", None))

    with pytest.raises(NotFoundProblem) as exc:
        await list_bill_lines(
            bill_id="bill-foreign", user=_user(), session=session
        )

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "running_bill"
    assert exc.value.extra["id"] == "bill-foreign"
    assert session.execute.await_count == 1


# ---------------------------------------------------------------------------
# SH-P5-4 — GET /api/bills/{bill_id}/recoveries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_recoveries_returns_rows():
    recovery_rows = [
        {
            "id": "rec-1",
            "bill_id": "bill-own",
            "recovery_type": "security_deposit",
            "amount": Decimal("1000.00"),
            "affects_pvc_base": False,
        },
        {
            "id": "rec-2",
            "bill_id": "bill-own",
            "recovery_type": "income_tax",
            "amount": Decimal("500.00"),
            "affects_pvc_base": False,
        },
    ]
    session = _session_with(
        ("first", {"contract_id": "contract-own"}),
        ("all", recovery_rows),
    )

    out = await list_recoveries(
        bill_id="bill-own", user=_user(), session=session
    )

    assert out == recovery_rows
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_recoveries_empty_returns_empty_list_not_404():
    session = _session_with(
        ("first", {"contract_id": "contract-own"}),
        ("all", []),
    )

    out = await list_recoveries(
        bill_id="bill-own", user=_user(), session=session
    )

    assert out == []
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_recoveries_wrong_tenant_raises_not_found():
    session = _session_with(("first", None))

    with pytest.raises(NotFoundProblem) as exc:
        await list_recoveries(
            bill_id="bill-foreign", user=_user(), session=session
        )

    assert exc.value.status_code == 404
    assert exc.value.extra["entity"] == "running_bill"
    assert exc.value.extra["id"] == "bill-foreign"
    assert session.execute.await_count == 1
