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

---

# Golden PVC fixture extraction — 2026-07-15

Source: `tasks/handoffs/2026-07-15-pvc-golden-fixtures.md`
Branch: `saqlain/fup-backlog`

## Assumptions

- Continue on the existing feature branch; do not commit or push.
- Treat the five `.xlsx` workbooks in `PVC/` as read-only golden sources.
- Preserve workbook totals as expected values; model discrepancies explicitly with tolerance, xfail, and provenance notes.
- Do not modify engine calculation code or quarter resolution.

## Tasks

- [x] Inspect workbook structures and map source cells for contract rules, indices, bill inputs, dates, and expected totals.
- [x] Add a reproducible `engine/scripts/extract_pvc_fixtures.py` extractor and declare `openpyxl` as an engine dev dependency.
- [x] Extend fixture tests for optional tolerance and KU-001 xfail metadata, proving the new behavior test-first.
- [x] Generate and audit one fixture per bill across the five workbooks, retaining the two synthetic 252 fixtures because the workbook-derived versions do not supersede them exactly.
- [x] Run focused fixture tests, a passing single-fixture smoke check, and the full engine suite.
- [x] Perform a final diff/review pass and record paths, expected values, pass/xfail state, ambiguities, and verification summaries in the handoff `Results` section.

---

# KU-001 rolling-quarter remediation — 2026-07-16

Source: `tasks/handoffs/2026-07-16-sol-quarter-rolling-fix.md`
Branch: `saqlain/fup-backlog`

## Assumptions

- Continue on the prescribed feature branch without committing or pushing.
- For a measurement date in or before the base month, the resolver returns an empty label/window and the calculator emits the required blocking validation error.
- Preserve workbook ground-truth totals; only remove KU-001 xfails that the rolling resolver genuinely fixes.

## Tasks

- [x] Rewrite quarter resolver tests for rolling-from-base boundaries, year wrap, long-running contracts, and pre-Q1 dates; capture the expected pre-fix failures.
- [x] Implement rolling quarter resolution and thread `base_month` through engine/backend callers, including the explicit pre-Q1 validation error.
- [x] Refresh calculator assertions, synthetic fixture labels, and golden-fixture xfail pins/markers from actual rolling results.
- [x] Run focused fixture verification, full engine/backend suites, frontend type/lint/build checks, and the required fixture smoke command.
- [x] Review/simplify the diff, update STATUS/domain-handoff/types documentation, and write complete evidence to this handoff's Results section.

---

# Post-merge follow-ups (Fable + Opus sessions) — 2026-07-16

Source: `tasks/handoffs/2026-07-16-fable-next-open-items.md` + `2026-07-16-opus-ku001-adversarial-review.md`

## Tasks

- [x] KU-001-REVIEW: adversarial pass on the rolling-quarter change — no HIGH/MEDIUM defects; 1 LOW deferred (KU1R-L1, no DB CHECK on `base_month` day=01); formal cycle in REVIEW.md; 3 new boundary tests + HTTP-level pre-Q1 422 pin.
- [x] KU-001-STC-AVG investigation: workbook method decoded (mean of 3 months, rounded half-up 2dp; reproduces both STC totals to the paisa) — decision brief in the Fable handoff Results.
- [x] P5-IMP-FUP-2: templates apply/save UI in `ImportRowsModal` (`ImportTemplateControls`, `lib/importTemplates.ts`, 11 vitest, schema.ts regenerated); browser smoke test vs mock (Supabase paused).
- [ ] Saqlain: restore the paused Supabase project, then re-run the templates smoke test against the real stack.
- [ ] Saqlain: decide KU-001-STC-AVG (Option 1 keep full precision vs Option 2 adopt workbook 2dp rounding) — check whether JRH/BCT workbooks share the rounding convention first.
- [ ] When a real submission exists: validate C-3-FUP-NET (`net_amount` formula).
