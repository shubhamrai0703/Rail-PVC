# RailPVC

**Billing operating system for Indian Railway contractors** — automates Price Variation Clause (PVC) calculations under GCC Clause 46A.

Replaces fragile per-engineer Excel workbooks with a governed, traceable system. Every calculation is reproducible, every approved run is immutable, and every output number traces back to its source.

---

## What It Does

Indian Railway works contracts entitle contractors to cost escalation compensation when material, labour, and fuel prices move against them. Calculating this correctly requires normalizing a chain of documents:

```
Tender → Agreement → Schedule/BOQ → MB → Running Bill → Recoveries → PVC Sheet → Submission
```

RailPVC automates this pipeline. The PVC calculation is a downstream output, not the entry point.

---

## Key Features (MVP)

- **Contract setup** — agreement metadata, LOA, schedules A/B/C, base month, component weights, GCC clause
- **W derivation pipeline** — `W = OnAccountBill − Cement − Steel(angles/plates/other) − TechWithheld − ExcludedExtraItems`
- **Carry-forward tracking** — first-class entity with paid ratio and per-bill allocation history
- **Extra-item eligibility** — explicit per-item decision; blocks PVC run if undecided (never defaults)
- **Index master** — seeded historical RBI/JPC values + manual monthly entry
- **Deterministic PVC engine** — pure Python package, no side effects, same inputs always produce same output
- **Immutable snapshots** — approved runs locked; revisions create superseding runs, never overwrites
- **Excel-parity export** — output matches the bill-style format Railway field accounts expect at submission
- **PDF print pack** — for Railway division submission

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) · React 18 · TypeScript |
| Tables | AG Grid Community Edition |
| Server state | TanStack Query v5 |
| Backend API | FastAPI (Python 3.11+) |
| Database | Supabase Postgres (row-level tenancy) |
| Auth | Supabase Auth |
| Storage | Supabase Storage (document vault) |
| Calc engine | Pure Python package (`engine/`) |
| Excel export | openpyxl |
| PDF export | WeasyPrint |

---

## Repository Structure

```
railpvc/
├── frontend/               # Next.js app (App Router)
├── backend/                # FastAPI app
│   ├── api/                # Route handlers
│   ├── models/             # SQLAlchemy models
│   ├── services/           # Business logic
│   └── migrations/         # Alembic
├── engine/                 # Pure Python PVC calculation package
│   ├── types.py            # Pydantic input/output types
│   ├── calculator.py       # Main entry point
│   ├── w_derivation.py     # W pipeline (cement, steel, extra-item)
│   ├── quarter_resolver.py # Measurement date → quarter → index avg
│   ├── carry_forward.py    # Paid ratio and proration logic
│   └── tests/              # pytest + hypothesis
├── seeds/                  # Historical RBI/JPC index data
├── PRODUCT.md              # What we're building, personas, MVP scope
├── ARCHITECTURE.md         # Full technical spec, data model, API surface
├── TASKS.md                # Build plan (CC-owned, Codex-readable)
├── CODEX.md                # Codex role and review protocol
└── CLAUDE.md               # Claude Code project context
```

---

## Core Domain Rules (Non-Negotiable)

### 1. W is not the gross bill amount

Every subtraction is a named, confirmed step. Missing input → run blocked. No silent defaults.

### 2. Quarter mapping

PVC quarter is determined by the bill's **measurement date**, not submission date. Stored as an immutable field on every run.

### 3. Immutability

Once a PVC run is approved it cannot be modified. Revisions create new superseding runs. The original persists with its original index snapshot and rule snapshot.

---

## Calculation Engine

The engine lives in `engine/` and is a pure Python package:

```python
from engine import calculate_pvc
from engine.types import BillPayload, IndexSnapshot, PVCRuleSet

result = calculate_pvc(bill=payload, indices=index_snapshot, rules=rule_set)
# result.w              → derived PVC base
# result.components     → per-category breakdown
# result.total_pvc      → final amount
# result.trace          → full provenance tree
# result.validation_errors → non-empty = run blocked
```

No database calls. No HTTP calls. No global state. Fully unit-testable in isolation.

### Testing With Real Tender Data

The repo now supports a simple replay workflow for real tenders:

1. Put one real bill into a JSON fixture under `engine/tests/fixtures/real_tenders/`.
2. Include the trusted workbook/manual PVC number in `expected.total_pvc`.
3. Run:

```bash
python scripts/run_engine_fixture.py engine/tests/fixtures/real_tenders/<your-file>.json --fail-on-mismatch
```

If the engine output differs from the known PVC value, the command exits non-zero. Once the fixture is committed, `pytest` treats it as a golden regression test so future engine changes cannot silently alter that result.

---

## Build Plan

See [`TASKS.md`](./TASKS.md) for the full phased build plan (9 phases, ~55 tasks).

**Phase overview:**

| Phase | Focus |
|---|---|
| 0 | Scaffolding |
| 1 | Data model + migrations |
| 2 | Calculation engine ← Codex review checkpoint |
| 3 | API layer ← Codex review checkpoint |
| 4 | Frontend shell |
| 5 | Contract setup UI |
| 6 | Bill entry UI |
| 7 | PVC run + results UI |
| 8 | Export layer ← Codex review checkpoint |
| 9 | Integration + testing |

---

## Development Workflow

**Two-tool model:** Claude Code (CC) is the primary orchestrator. Codex acts as adversarial reviewer and UI component generator under CC supervision. See [`CODEX.md`](./CODEX.md) for Codex's role and boundaries.

**Git:** GitHub Flow — `main` + feature branches. Branch naming: `feat/P2-001-calc-engine`.

**Local setup:** TBD (Phase 0 scaffolding).

---

## Domain Reference

- GCC Clause 46A governs PVC for Indian Railways works contracts
- Sample tender: `BCT-24-25-252`, Agreement `WR/BCT/Civil/2025/0059`
- Index sources: RBI WPI publications (labour, plant, fuel, materials), JPC Steel Price Index (angles, plates, other sections, TMT)
- Known unknowns requiring domain confirmation before engine ships: see `TASKS.md` Known Unknowns table
