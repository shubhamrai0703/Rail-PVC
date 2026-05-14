# RailPVC

Billing OS for Indian Railway contractors automating PVC calculations under GCC Clause 46A. Normalizes the document chain (agreement → MB → bill → recoveries → indices) into a deterministic, auditable PVC output. Displaces Excel workbooks and IRPVC SaaS.

## Key Files

| File | Purpose |
|---|---|
| `PRODUCT.md` | MVP scope, personas, 3 non-negotiables |
| `ARCHITECTURE.md` | Stack, data model, engine interface, API surface |
| `TASKS.md` | Build plan — CC owns `[CC]` tasks, Codex acts on `[CODEX]`/`[CODEX-REVIEW]` |
| `CODEX.md` | Codex role, review format, hard boundaries |
| `engine/` | Pure Python PVC calc package — no DB, no HTTP, deterministic |
| `seeds/` | Historical RBI/JPC index data |

## Stack

Next.js 14 (App Router) + TypeScript · FastAPI (Python) · Supabase (Postgres + Auth + Storage) · AG Grid tables · TanStack Query · openpyxl (Excel export)

## Critical Domain Rules

**W derivation (never default):**
`W = OnAccountBill − Cement − SteelAngles − SteelPlates − SteelOther − TechWithheld − ExcludedExtraItems`
Any missing eligibility decision must block the run — never assume included or excluded.

**Quarter mapping:** `measurement_date` = "To" date of MB period. Calendar quarters Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec within Indian FY (Apr-Mar). Format: `Q2-FY2025-26`. Stored as immutable field on every PVC run, never re-derived.

**Immutability:** Approved PVC runs cannot be modified. Revisions create superseding runs. `revision_snapshots` is append-only.

## Architecture Decisions

- Single-user per org for MVP; multi-user RBAC (3 roles) is immediate post-MVP priority
- `engine/` is a pure function package — imported by FastAPI, never calls DB or HTTP
- Supabase Postgres with row-level tenancy (`tenant_id` on all tables)
- Excel-parity export from day one (openpyxl matching BCT-24-25-252 workbook layout)
- Manual index entry + seeded historical data; no PDF parsing in v1

## Resolved Domain Confirmations

- KU-001 ✓: Calendar quarter Q2=Apr-Jun etc; "To" date is anchor. Verify non-WR zones before templating zone rules.
- KU-002 ✓: Extra NS items in W subtraction are intentional (eligible=False). Engine blocks on eligible=None.
- KU-003 ✓: Negative PVC → zero-floor + `negative_carry_forward` stored for recovery on next bill.

## Vault

Search Obsidian for `RailPVC` or `PVC calculation` for any updated session notes.
