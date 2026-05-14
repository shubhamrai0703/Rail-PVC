# Review: Phase 0 and Phase 1

This document records my review of the repository after the Phase 1 work captured in commit `cc0de0c`.

Audience:
- Claude Code during or after Phase 2
- future reviewers who need to know which early-phase decisions are solid and which still need cleanup

Review boundary:
- Phase 0 scaffolding
- Phase 1 schema, migration, seed, and RLS work
- no judgment here on Phase 2 calculation correctness beyond noting the current engine baseline

## Executive Summary

Phase 0 and Phase 1 are in a usable state, but not in a fully closed state from a source-control and auditability perspective.

What is solid:
- repo structure exists and broadly matches the intended architecture
- backend Alembic setup is real and coherent
- migrations `001` through `008` create the expected Phase 1 schema
- the seed script exists and is idempotent
- the RLS policy design is now documented and appears internally consistent

What is still open:
- RLS is documented but not yet captured as Alembic migration `009`
- the checked-in `TASKS.md` acceptance criteria for P1-009 do not match the actual seeded dataset
- several docs still describe target-state engine files and capabilities that do not exist yet

## Phase 0 Observations

### What is good

- The repository is cleanly split into `frontend/`, `backend/`, and `engine/`, which matches the product and architecture documents.
- `backend/pyproject.toml` and `engine/pyproject.toml` establish the intended package boundaries.
- The backend healthcheck app is minimal but valid and gives the project a concrete runtime entrypoint.
- Alembic is configured with an async environment in [backend/migrations/env.py](/Users/saqlainmomin/railPVC/backend/migrations/env.py:1), which is aligned with the chosen FastAPI + SQLAlchemy async stack.

### Gaps and inconsistencies

- The documentation overstates current implementation maturity. For example, the README repository tree lists `backend/api/`, `backend/models/`, `backend/services/`, and multiple engine modules that do not exist yet in [README.md](/Users/saqlainmomin/railPVC/README.md:52).
- The engine package remains a stub. `calculate_pvc()` still returns a blocked result with `"Engine not yet implemented — Phase 2"` in [engine/calculator.py](/Users/saqlainmomin/railPVC/engine/calculator.py:14).
- `README.md` says local setup is `TBD` in [README.md](/Users/saqlainmomin/railPVC/README.md:142), which is honest, but it means Phase 0 is not fully productized for a new contributor.

### Recommendations

- Keep architecture docs, but trim target-state trees so they do not read as current-state facts.
- When Phase 2 lands, update README examples to reflect the actual engine API rather than the planned one.

## Phase 1 Observations

### Verified strengths

- The migration sequence `001` through `008` exists and is coherent.
- The schema covers the expected core entities:
  - tenant and user identity
  - contracts, schedules, and items
  - running bills, bill lines, and recoveries
  - carry-forwards
  - index series and observations
  - PVC rule sets
  - PVC runs, components, and revision snapshots
  - extra-item decisions and documents
- The DDL is largely aligned with `ARCHITECTURE.md`, including enum usage, foreign keys, and key uniqueness constraints.
- The seed script in [seeds/seed_indices.py](/Users/saqlainmomin/railPVC/seeds/seed_indices.py:1) is idempotent and practical for current development.
- The manually applied RLS policy set is coherent and now documented in [backend/RLS_POLICIES.md](/Users/saqlainmomin/railPVC/backend/RLS_POLICIES.md:1).

### Important caveats

#### 1. P1-009 plan text no longer matches reality

`TASKS.md` still says P1-009 requires `Jan 2022 – present` coverage and `at least 36 months` per series in [TASKS.md](/Users/saqlainmomin/railPVC/TASKS.md:36).

The actual seed script provides:
- `Dec-2024` through `Dec-2025`
- 13 months of RBI coverage
- partial JPC coverage, with Q1 and Q3 explicitly absent from the workbook-derived dataset

This is not necessarily wrong for MVP progress, but it is a planning mismatch and should be corrected explicitly.

#### 2. RLS is not yet reproducible from git

Operationally, the Supabase dashboard policies may be in place. For repository auditability, they are still missing from Alembic.

That means a fresh environment cannot be recreated from migrations alone yet.

#### 3. `revision_snapshots` DB-level immutability is only partially demonstrated in repo

The documented policy set gives `revision_snapshots` only `SELECT` and `INSERT` policies for authenticated users, which is good.

But until the RLS SQL is migrated into git, the repository alone does not prove this guarantee.

#### 4. Some schema choices are workable but deserve review later

- Many tables rely on join-based tenant scoping instead of direct `tenant_id`.
- `pvc_runs.approved_by` is currently `TEXT`, not a user foreign key.
- The choice to keep index tables globally readable is reasonable, but service-key write assumptions should be documented where the backend ingestion code will live.

These are not Phase 1 blockers, but they are worth revisiting before hardening Phase 3 and Phase 4.

## Fit Against Product Constraints

### Good alignment

- `running_bills.measurement_date` exists in [003_bills.py](/Users/saqlainmomin/railPVC/backend/migrations/versions/003_bills.py:36), which supports the product rule that quarter mapping should be based on measurement date.
- `extra_item_decisions.eligible` is nullable in [008_extra_items_documents.py](/Users/saqlainmomin/railPVC/backend/migrations/versions/008_extra_items_documents.py:29), which supports the rule that undecided extra items must block PVC runs.
- `pvc_runs` stores snapshots in JSONB in [007_pvc_runs.py](/Users/saqlainmomin/railPVC/backend/migrations/versions/007_pvc_runs.py:39), which is compatible with immutable run provenance.

### Needs follow-through

- The schema supports the intended product rules, but the engine and API layers do not enforce them yet.
- Phase 2 and Phase 3 should be judged partly on whether they preserve these early invariants instead of weakening them through convenience shortcuts.

## Guidance For Phase 2 Review

When Phase 2 is finished, I would review it against these specific risks:

- Does the engine use `measurement_date`-driven quarter resolution by default?
- Does it block on missing indices or undecided extra-item eligibility instead of producing fallback numbers?
- Does it avoid `float` for money-sensitive calculations?
- Does it preserve snapshot-friendly provenance rather than returning only totals?
- Does it align with the schema categories already established in Phase 1?

## Recommended Closeout Actions

Before calling early-foundation work fully closed, I recommend:

1. Add `backend/migrations/versions/009_rls_policies.py` from the documented SQL.
2. Update `TASKS.md` to reflect the actual accepted scope of seeded index history.
3. Tighten README language where target-state structure is currently presented like implemented structure.
4. Keep this document and `backend/RLS_POLICIES.md` under version control until the RLS migration is committed, then retain them as audit artifacts.
