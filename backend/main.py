"""FastAPI app entrypoint. Wires routers, error contract, and CORS."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parent / ".env")

from api import (  # noqa: E402  (env must load before module-level imports)
    bills,
    carry_forwards,
    contract_items,
    contracts,
    documents,
    exports,
    extra_items,
    imports,
    indices,
    pvc_rules,
    pvc_runs,
    schedules,
)
from services.errors import register_exception_handlers  # noqa: E402

app = FastAPI(
    title="TenderAudit API",
    description="Billing OS for Indian Railway contractors — PVC calculation engine API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

for router in (
    contracts.router,
    schedules.router,
    contract_items.router,
    bills.router,
    extra_items.router,
    carry_forwards.router,
    imports.router,
    indices.router,
    pvc_rules.router,
    pvc_runs.router,
    documents.router,
    exports.router,
):
    app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "tenderaudit-api"}
