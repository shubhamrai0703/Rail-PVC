"""SH-P5-5/6: download an approved PVC run as Excel or PDF.

Both endpoints share the same gate: the run must be visible to the caller's
tenant (else 404, indistinguishable from "doesn't exist" per P3-06) and must
be Approved (else 422 `run_not_approved`). Generation lives in
`services/exports.py`; this module is gating + response wiring only.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import AuthUser, get_current_user
from services.db import get_session
from services.errors import NotFoundProblem, RunNotApprovedProblem
from services.exports import build_run_excel, build_run_pdf

router = APIRouter(prefix="/api", tags=["exports"])

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


async def _load_approved_run(
    session: AsyncSession, run_id: str, tenant_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Tenant-gate (404) then status-gate (422) a run, returning the run row
    (with contract metadata) and its component rows ready for export."""
    run = (
        await session.execute(
            text("""
                SELECT r.id::text AS id, r.status::text AS status,
                       r.approved_by, r.approved_at, r.created_at, r.quarter_used,
                       c.tender_number, c.contractor_name
                FROM pvc_runs r
                JOIN contracts c ON c.id = r.contract_id
                WHERE r.id = :rid AND c.tenant_id = :tid
            """),
            {"rid": run_id, "tid": tenant_id},
        )
    ).mappings().first()
    if run is None:
        raise NotFoundProblem("Run not found", entity="pvc_run", id=run_id)
    if run["status"] != "Approved":
        raise RunNotApprovedProblem(run_id, run["status"])

    components = (
        await session.execute(
            text("""
                SELECT category::text AS category, eligible_amount, base_index,
                       current_avg_index, weight, pvc_value
                FROM pvc_components WHERE run_id = :rid
                ORDER BY category
            """),
            {"rid": run_id},
        )
    ).mappings().all()
    return dict(run), [dict(c) for c in components]


@router.get("/pvc-runs/{run_id}/export/excel")
async def export_run_excel(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    run, components = await _load_approved_run(session, run_id, user.tenant_id)
    content = build_run_excel(run, components)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="pvc_run_{run_id}.xlsx"',
        },
    )


@router.get("/pvc-runs/{run_id}/export/pdf")
async def export_run_pdf(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    run, components = await _load_approved_run(session, run_id, user.tenant_id)
    content = build_run_pdf(run, components)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="pvc_run_{run_id}.pdf"',
        },
    )
