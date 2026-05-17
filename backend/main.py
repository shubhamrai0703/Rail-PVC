"""FastAPI app entrypoint. Wires routers, error contract, and CORS."""
from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from api import (  # noqa: E402  (env must load before module-level imports)
    bills,
    carry_forwards,
    contracts,
    extra_items,
    indices,
    pvc_rules,
    pvc_runs,
)
from services.errors import register_exception_handlers  # noqa: E402

app = FastAPI(
    title="RailPVC API",
    description="Billing OS for Indian Railway contractors — PVC calculation engine API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

for router in (
    contracts.router,
    bills.router,
    extra_items.router,
    carry_forwards.router,
    indices.router,
    pvc_rules.router,
    pvc_runs.router,
):
    app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "railpvc-api"}
