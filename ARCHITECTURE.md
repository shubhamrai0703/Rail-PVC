# ARCHITECTURE.md — RailPVC

## System Layers

```
┌─────────────────────────────────────────────────────┐
│  PRESENTATION                                       │
│  Next.js 14 (App Router) · React 18 · TypeScript   │
│  AG Grid (spreadsheet tables) · TanStack Query v5  │
└──────────────────┬──────────────────────────────────┘
                   │ REST / fetch
┌──────────────────▼──────────────────────────────────┐
│  API LAYER                                          │
│  FastAPI (Python) · Pydantic v2 · SQLAlchemy async  │
│  Supabase JWT auth middleware · Alembic migrations  │
└──────────┬───────────────────────┬──────────────────┘
           │                       │
┌──────────▼──────────┐  ┌────────▼────────────────────┐
│  CALCULATION ENGINE │  │  DATA LAYER                 │
│  engine/ package    │  │  Supabase Postgres           │
│  Pure Python        │  │  Row-level tenancy           │
│  No DB, no HTTP     │  │  Append-only snapshot tables │
│  Deterministic      │  │  Supabase Storage (docs)     │
└─────────────────────┘  └─────────────────────────────┘
```

---

## Technology Choices

| Layer | Technology | Rationale |
|---|---|---|
| Frontend framework | Next.js 14 (App Router) | SSR, file-based routing, API routes, best-in-class DX for TS |
| UI language | React 18 + TypeScript | Type safety on a complex domain model |
| Table UX | AG Grid Community | Spreadsheet-grade editable tables — essential for bill entry |
| Server state | TanStack Query v5 | Cache, optimistic updates, background refetch |
| Backend | FastAPI (Python 3.11+) | Async, automatic OpenAPI docs, Pydantic v2 integration |
| ORM | SQLAlchemy 2.0 (async) | Mature, typed, async-native |
| Migrations | Alembic | Standard with SQLAlchemy |
| Auth | Supabase Auth | Email/password MVP; SSO later. Unified with DB provider. |
| Database | Supabase Postgres | Managed, RLS built-in, row-level tenancy out of the box |
| File storage | Supabase Storage | Document vault; same platform, no extra infra |
| Excel export | openpyxl | Pure Python, precise cell-level control for format parity |
| PDF export | WeasyPrint | HTML → PDF; allows using the same React templates |
| Engine testing | pytest + hypothesis | Property-based testing for W derivation invariants |
| Frontend testing | Vitest + Testing Library | Co-located with Next.js |

---

## Data Model — MVP Subset

Focus entities for Phase 1 (from the full 19-entity model):

### Core Operational Tables

```sql
-- Tenant isolation
tenants (id, name, created_at)
users (id, tenant_id, supabase_auth_id, email, created_at)

-- Contract hierarchy
contracts (
  id, tenant_id,
  tender_number, agreement_number, loa_number, loa_date,
  contractor_name, work_description,
  contract_value, bid_amount,
  start_date, completion_date,
  base_month,               -- "2024-12" — month prior to tender closing
  gst_mode,                 -- 'inclusive' | 'exclusive'
  pvc_applicable bool,
  overall_rebate numeric,
  status,                   -- Draft|Configured|Active|Completed|Archived
  created_at
)

schedules (
  id, contract_id, name,    -- 'A' | 'B' | 'C'
  schedule_type,            -- 'DSR' | 'NS' | 'ExtraNS'
  bid_discount_pct numeric,
  created_at
)

contract_items (
  id, contract_id, schedule_id,
  item_code, description, unit,
  original_qty, revised_qty,
  base_rate, agreement_rate,
  is_cement_item bool,
  steel_subtype,            -- NULL | 'angles' | 'plates' | 'other_sections' | 'tmt'
  created_at
)

-- Bills
running_bills (
  id, contract_id,
  bill_number, bill_date, measurement_date,
  gross_amount, net_amount,
  status,                   -- Draft|Imported|Reconciled|Approved|Submitted|Revised|Locked
  created_at
)

bill_lines (
  id, bill_id, item_id,
  qty_up_to_last, qty_since_last, qty_up_to_date,
  amount_up_to_last, amount_since_last, amount_up_to_date,
  special_condition_amount numeric DEFAULT 0
)

recoveries (
  id, bill_id,
  recovery_type,            -- 'security_deposit'|'income_tax'|'labour_cess'|'water'|'other'
  amount numeric,
  affects_pvc_base bool DEFAULT false
)

-- Carry-forward (first-class entity)
carry_forwards (
  id, contract_id, item_id,
  source_bill_id,           -- bill where quantity was recorded but not fully paid
  target_bill_id,           -- bill where carried qty is paid
  recorded_qty numeric,     -- total measured qty
  paid_qty_source numeric,  -- qty paid in source bill
  paid_ratio numeric,       -- paid_qty_source / recorded_qty
  carry_qty numeric,        -- recorded_qty - paid_qty_source → paid in target bill
  steel_subtype,            -- inherited from contract_item
  created_at
)

-- Indices
index_series (
  id, name,                 -- 'labour'|'plant_machinery'|'fuel'|'other_materials'
                            -- 'cement'|'tmt'|'angles'|'plates'|'other_sections'
  source_publication        -- 'RBI' | 'JPC'
)

index_observations (
  id, series_id,
  month date,               -- first day of month
  value numeric,
  source_ref,               -- publication issue ref
  revision_flag bool DEFAULT false,
  revised_at timestamptz,
  created_at
)
```

### PVC Run Tables

```sql
-- Rules (one per contract, versioned)
pvc_rule_sets (
  id, contract_id,
  version int,
  quarter_mode,             -- 'measurement_date' (default) | 'bill_date' | 'operator_override'
  component_weights jsonb,  -- {"labour": 0.20, "plant": 0.30, "fuel": 0.15, ...}
  extra_item_policy,        -- 'exclude_by_default' | 'include_by_default'
  adjustable_fraction numeric DEFAULT 0.85,  -- non-variable residual = 1 - adjustable
  quarter_avg_precision TEXT NOT NULL DEFAULT 'full',  -- 'full' | 'half_up_2dp'
  rounding_mode,            -- 'round_2' | 'truncate_2'
  negative_pvc_policy,      -- 'allow' | 'block' | 'zero_floor'
  created_at
)

-- Eligibility decisions (explicit, per item per contract)
extra_item_decisions (
  id, contract_id, item_id,
  eligible bool,            -- NULL = undecided (blocks run)
  decided_by,
  decided_at,
  notes
)

-- PVC Run (immutable once approved)
pvc_runs (
  id, contract_id, bill_id, rule_set_id,
  index_snapshot jsonb,     -- copy of all index values used — immutable after approval
  bill_snapshot jsonb,      -- copy of bill state at time of run
  w_derivation jsonb,       -- named breakdown: {on_account, cement, steel_angles, ...}
  status,                   -- Draft|Calculated|ExceptionFlagged|Approved|Exported|Superseded
  superseded_by uuid REFERENCES pvc_runs(id),
  approved_by,
  approved_at,
  created_at
)

pvc_components (
  id, run_id,
  category,                 -- 'labour'|'plant'|'fuel'|'materials'|'cement'|'steel_angles'|...
  eligible_amount numeric,
  base_index numeric,
  current_avg_index numeric,
  weight numeric,
  pvc_value numeric          -- eligible_amount * weight * (current - base) / base
)

-- Immutable snapshot (append-only, never updated)
revision_snapshots (
  id, run_id,
  snapshot_data jsonb,      -- complete serialized PVCRun + components at approval time
  created_at
)

-- Document vault
documents (
  id, contract_id,
  file_type,                -- 'agreement'|'mb'|'bill'|'recovery'|'workbook'|'other'
  storage_path,             -- Supabase Storage bucket path
  original_filename,
  uploaded_at
)
```

---

## API Surface

```
# Auth (Supabase handles login/logout/tokens)

# Contracts
POST   /api/contracts
GET    /api/contracts
GET    /api/contracts/{id}
PUT    /api/contracts/{id}

# Schedules + Items
POST   /api/contracts/{id}/schedules
GET    /api/contracts/{id}/schedules
POST   /api/schedules/{id}/items
GET    /api/contracts/{id}/items

# Bills
POST   /api/contracts/{id}/bills
GET    /api/contracts/{id}/bills
GET    /api/bills/{id}
PUT    /api/bills/{id}
POST   /api/bills/{id}/lines
POST   /api/bills/{id}/recoveries

# Carry-forwards
GET    /api/contracts/{id}/carry-forwards
PUT    /api/carry-forwards/{id}

# Extra-item decisions
GET    /api/contracts/{id}/extra-item-decisions
POST   /api/contracts/{id}/extra-item-decisions
PUT    /api/extra-item-decisions/{id}

# Indices
GET    /api/index-series
GET    /api/index-observations?series_id=&from=&to=
POST   /api/index-observations
PUT    /api/index-observations/{id}

# PVC Rules
GET    /api/contracts/{id}/pvc-rule-set
PUT    /api/contracts/{id}/pvc-rule-set

# PVC Runs
POST   /api/contracts/{id}/pvc-runs      # triggers engine
GET    /api/pvc-runs/{id}
POST   /api/pvc-runs/{id}/approve        # locks snapshot, immutable after this
GET    /api/pvc-runs/{id}/export/excel
GET    /api/pvc-runs/{id}/export/pdf

# Documents
POST   /api/contracts/{id}/documents
GET    /api/contracts/{id}/documents
```

---

## Calculation Engine Interface

The engine lives in `engine/` as a standalone Python package. It is imported by the FastAPI app but has zero dependency on it.

```python
# engine/types.py (Pydantic models)

class BillPayload(BaseModel):
    on_account_amount: Decimal
    cement_amount: Decimal       # from bill lines tagged is_cement_item
    steel_angles_amount: Decimal
    steel_plates_amount: Decimal
    steel_other_amount: Decimal
    technical_withheld: Decimal
    recoveries_affecting_pvc: Decimal = 0  # P6-H1-FUP-C — distinct from technical_withheld
    extra_item_amount: Decimal   # sum of non-eligible extra items (0 if all eligible)
    carry_forwards: list[CarryForwardPayload]
    measurement_date: date

class IndexSnapshot(BaseModel):
    base_month: date
    series: dict[str, dict[str, Decimal]]  # {category: {YYYY-MM: value}}

class PVCRuleSet(BaseModel):
    quarter_mode: Literal["measurement_date", "bill_date"]
    component_weights: dict[str, Decimal]
    adjustable_fraction: Decimal
    negative_pvc_policy: Literal["allow", "block", "zero_floor"]
    rounding_mode: Literal["round_2", "truncate_2"]

class PVCRunResult(BaseModel):
    w: Decimal                          # derived PVC base
    w_derivation: WDerivation           # named breakdown — every step explicit
    components: list[PVCComponent]      # per-category results
    total_pvc: Decimal
    quarter_used: str                   # "Q2" — plain ordinal, rolling from contract base_month, stored not re-derived
    quarter_months: list[str]           # ["2025-04", "2025-05", "2025-06"]
    trace: dict                         # full provenance tree
    validation_errors: list[str]        # non-empty → run blocked, no result produced

# engine/calculator.py

def calculate_pvc(
    bill: BillPayload,
    indices: IndexSnapshot,
    rules: PVCRuleSet,
) -> PVCRunResult:
    """
    Pure function. Same inputs → same output, always.
    No database calls. No HTTP calls. No global state.
    If validation_errors is non-empty, total_pvc is None and the run must be blocked.
    """
```

**Invariants enforced by the engine (not the API layer):**
- `w == on_account_amount - cement - steel_angles - steel_plates - steel_other - technical_withheld - recoveries_affecting_pvc - extra_items`
- All required index values for base month + current quarter must be present, or validation error
- If any carry-forward `paid_ratio` is outside `[0, 1]`, validation error
- Negative PVC handling per `negative_pvc_policy`

---

## Repository Structure (Target)

```
railpvc/
├── frontend/                   # Next.js app
│   ├── app/                    # App Router pages
│   ├── components/
│   └── lib/
├── backend/                    # FastAPI app
│   ├── api/                    # route handlers
│   ├── models/                 # SQLAlchemy models
│   ├── services/               # business logic (calls engine)
│   ├── migrations/             # Alembic
│   └── main.py
├── engine/                     # Pure Python calc package
│   ├── types.py
│   ├── calculator.py
│   ├── w_derivation.py
│   ├── quarter_resolver.py
│   ├── carry_forward.py
│   └── tests/
├── seeds/                      # Index seed data (RBI/JPC historical)
├── TASKS.md
├── CODEX.md
├── CLAUDE.md
└── PRODUCT.md
```
