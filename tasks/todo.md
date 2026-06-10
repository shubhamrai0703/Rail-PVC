# Phase 7 — PVC Run + Results UI (D-1…D-4)

Branch: `saqlain/phase-7` off `main` (a88b85e + 0c90a72 docs).
Owner: [CC-S]. Gate: C-3 stable ✅. Review: `P7-REVIEW` (Codex-S) after it lands.

## Decisions locked (2026-06-09)

1. **Dedicated run page** — `/contracts/[id]/bills/[billId]/runs/[runId]`. Calculate card links to it.
2. **Full slice** in one PR: results view + breakdown + bill lines + approve + run history + export buttons.
3. **Defer W-bucket (P6-H1-FUP-C)** — keep interim approach A; label the conflated bucket honestly in the
   W-derivation display ("Technical withheld (incl. PVC-affecting recoveries)"). Real C migration is its
   own engine-touching PR.

## Backend state (already on main — reuse, don't rebuild)

- `POST /contracts/{id}/pvc-runs` → `{id, total_pvc, negative_carry_forward, quarter_used}` (idempotent)
- `POST /pvc-runs/{id}/approve` → 409 `ImmutableApprovedRun` if already approved
- `GET /pvc-runs/{id}` → `{id, contract_id, bill_id, status, w_derivation, approved_by, approved_at,
  created_at, components[]}` — **missing total/carry/quarter**
- `GET /pvc-runs/{id}/export/{excel,pdf}` → approved-only, 422 `run_not_approved` otherwise
- **Missing:** list-runs endpoint for history.

## Tasks

### D-1 — Backend: results completeness + run list
- [x] D-1a: **Migration 015** — add `total_pvc NUMERIC(15,4)`, `negative_carry_forward NUMERIC(15,4)`,
      `quarter_used TEXT` (all nullable) to `pvc_runs`. Decision 2026-06-09: output carry-forward was
      persisted nowhere (latent audit gap). Write them at run INSERT from the engine result.
      Extend `GET /pvc-runs/{id}` to return them (additive keys). Backfill: leave existing rows NULL
      (dev-only data; `total_pvc` still derivable as Σ components if needed).
- [x] D-1b: New `GET /contracts/{id}/pvc-runs` — list runs (id, bill_id, bill_number, status, total_pvc,
      created_at, approved_at), newest first. Tenant gate via contract→tenant. Empty list (not 404).
      Route count 42→43.
- [x] D-1c: Tests — totals in GET detail; list endpoint (happy, empty, wrong-tenant 404). Bump route-count
      assertion in `test_p3_08_clean_import.py`.

### D-2 — Frontend: run results page
- [x] D-2a: Route `/contracts/[id]/bills/[billId]/runs/[runId]/page.tsx`. TanStack Query on `GET /pvc-runs/{runId}`.
- [x] D-2b: Header — status Badge (Draft/Approved/Superseded), total PVC, carry-forward, quarter, created/approved meta.
- [x] D-2c: Component breakdown table — category, eligible_amount, base_index, current_avg_index, weight, pvc_value.
- [x] D-2d: W-derivation panel — render JSONB as named subtraction steps (PRODUCT.md rule 1). Honest bucket label (decision 3).
- [x] D-2e: Generated bill-lines table — populated post-run; reuse the read-only lines table (`GET /bills/{id}/lines`).

### D-3 — Frontend: approve flow + exports
- [x] D-3a: Approve button (Draft only) → `POST /pvc-runs/{id}/approve`; status flip + invalidate. 409 inline (silent toast).
- [x] D-3b: Export buttons (Excel/PDF) — enabled only when status=Approved; disabled + tooltip otherwise (mirror 422).
- [x] D-3c: Wire Calculate-PVC card (bill detail) to link to the new run page via returned `id` ("View full results →").

### D-4 — Frontend: run history + tests
- [x] D-4a: Run-history list on bill detail from `GET /contracts/{id}/pvc-runs` filtered to this bill; link each to its run page.
- [x] D-4b: Pure helpers + vitest: w_derivation → display steps, export-enablement gate, status→badge mapping.
- [x] D-4c: `npm run build` + `tsc` + `eslint` + `vitest` clean.

### Wrap
- [ ] Full backend suite green, engine 99/99 unchanged, vitest green, route count 43.
- [x] Docs sync: STATUS (Phase 7 done), TASKS (D-1…D-4 rows), SESSION_LOG entry.
- [ ] Open PR → `main`, request `P7-REVIEW`.

## Open verifications during impl
- Where the engine persists `negative_carry_forward` + `quarter_used` (w_derivation vs bill_snapshot) — drives D-1a.
- Superseded runs: `superseded_by` column exists — show "Superseded" badge when non-null.
