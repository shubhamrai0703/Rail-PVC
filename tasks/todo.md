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
- [x] Full backend suite green, engine 99/99 unchanged, vitest green, route count 43. (Merged via PR #14.)
- [x] Docs sync: STATUS (Phase 7 done), TASKS (D-1…D-4 rows), SESSION_LOG entry.
- [x] Open PR → `main`, request `P7-REVIEW`. (PR #14 merged 2026-06-11.)

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
- [x] Saqlain: restore the paused Supabase project, then re-run the templates smoke test against the real stack.
- [x] Saqlain: decide KU-001-STC-AVG — Option 2 selected with rule-set scope, HALF-UP 2dp, average-first ordering, and `full` as the compatibility default; implementation evidence is recorded below.
- [ ] When a real submission exists: validate C-3-FUP-NET (`net_amount` formula).

---

# P5-IMP-FUP-2 real-stack smoke test — 2026-07-16

Source: `tasks/handoffs/2026-07-16-codex-supabase-smoke-test.md`

## Tasks

- [x] Confirm Supabase Auth/DB reachability and migration head 016.
- [x] Build and start the production frontend plus real backend without duplicating existing listeners.
- [x] Drive the authenticated template save/reload/apply/duplicate/preview/import flow in a real browser.
- [x] Verify persisted tenant-scoped template data directly and clean up created templates.
- [x] Record per-step evidence, logs/errors, defects, and verdict in the handoff Results section.

---

# Parallel backlog (WS-A/B/C/D) — 2026-07-17

Source: `tasks/handoffs/2026-07-17-fable-parallel-backlog.md` (Results filled)
Branch: `saqlain/parallel-backlog` → PR #19

## Tasks

- [x] WS-A: usability-audit triage — AUDIT-1 table in TASKS.md; quick wins AUDIT-1-1 (gross-amount help note) + AUDIT-1-2 (contracts-list Value ₹ column) shipped.
- [x] WS-B: export parity first pass — submission column order/headers, native number formats, live =SUM total, Quarter in summary; +4 test pins; real-run smoke on 8bfc1f40.
- [x] WS-C: migration 017 `contracts_base_month_first_day` CHECK — applied to live DB (head 017), day≠1 INSERT rejected; KU1R-L1 closed.
- [x] WS-D: ItemsGrid → AG Grid v35 rowSelection object API; deprecated options gone repo-wide.
- [x] Authenticated browser pass — /contracts Value column, both gross-amount help-note surfaces, and Items-grid console free of AG Grid/deprecation warnings (Codex, 2026-07-18; evidence in the dedicated handoff Results).
- [ ] Saqlain: merge PR #19 (note: migration 017 already applied to DB).
- [ ] Saqlain: AUDIT-1-3 (delete junk draft contracts) + AUDIT-1-4 (rebate % input UX call).
- [ ] Saqlain: check hermes-agent WhatsApp bridge respawning on port 3000 (see handoff Results env notes).
- [ ] P8-REVIEW: answer the 4 open export-parity questions (multi-sheet workbook, steel sub-lines, clause codes, "W" header wording).

---

# Authenticated browser smoke caveat — 2026-07-18

Source: `tasks/handoffs/2026-07-18-codex-browser-smoke-caveat.md`
Branch: `saqlain/parallel-backlog`

## Tasks

- [x] Confirm the production frontend is serving on localhost:3000 and open a real authenticated browser session.
- [x] Verify the contracts-list Value (₹) column, including INR formatting and the null-value em dash.
- [x] Verify the Gross amount help text in both the new-bill form and the existing-bill header form.
- [x] Verify the Items grid checkbox placement and that the console has no AG Grid/deprecation warnings.
- [x] Record per-check observations and the overall caveat verdict in the handoff Results section.

---

# TenderAudit rebrand + go-live prep — 2026-07-18

Branch: `saqlain/tenderaudit-rename` (off `parallel-backlog`), 3 commits, suites green.

## Tasks

- [x] Rename all user-facing RailPVC → TenderAudit (shell, metadata, error/404, API title/health id); Python dist names intentionally unchanged.
- [x] Backend CORS env-driven via `CORS_ORIGINS` (localhost default; documented in `.env.example`).
- [x] DEPLOY.md go-live runbook (Railway backend + Vercel frontend + GoDaddy DNS + Supabase allowlist + smoke checklist).
- [x] Saqlain: merge order `parallel-backlog` (PR #19) → `fup-backlog` → `tenderaudit-rename` — all merged to `main`; branches deleted in the 2026-07-19 wrap.
- [x] Saqlain: create Railway + Vercel projects, set env vars per DEPLOY.md §1–2.
- [x] Saqlain: GoDaddy DNS records (DEPLOY.md §3) + Supabase auth redirect allowlist (§4).
- [ ] Saqlain: decide Supabase Pro vs keep-alive ping (free tier auto-pauses).
- [ ] Provision tenant + seed demo contract per contact before they log in.
- [ ] Future ticket: auto-provision tenant on signup.

---

# KU-001-STC-AVG Option 2 implementation — 2026-07-19

Source: `tasks/handoffs/2026-07-19-ku001-stc-avg-option2-implementation.md`
Branch: `codex/ku001-stc-avg-option2`

## Tasks

- [x] Capture pre-change engine/backend suite counts and byte-exact totals for the 9 currently passing real-tender fixtures.
- [x] Add the rule-set-scoped engine precision policy, strict STC fixtures, trace parity, and focused regression tests.
- [x] Add migration 018 and thread the policy through rule-set create/read/update and per-run engine construction.
- [x] Run focused and full engine/backend verification, smoke both STC fixtures, and diff the 9-fixture totals.
- [x] Review/simplify the diff and record complete evidence in the implementation handoff Results section.
- [x] KU-001-STC-AVG-REVIEW: adversarial pass complete 2026-07-19 (Fable). 1 MEDIUM found+fixed (KU1SA-M1 — PUT omitting `quarter_avg_precision` silently reset the policy; now COALESCE-preserved). Record in REVIEW.md + handoff. Merged to `main` at wrap.

---

# Railway deploy debugging + OpenRouter switch — 2026-07-19

Branches: `saqlain/railway-dockerfile` (PR #21), `saqlain/openrouter-llm` (PR #22), both off `main`.

## Tasks

- [x] Diagnose 3 Railway build failures (context-scoping vs. auto-provisioning vs. detection ambiguity); root-cause: Railpack can't satisfy backend's `../engine` relative dependency under any Root Directory setting.
- [x] Add repo-root Dockerfile + .dockerignore; verified locally (simulated COPY layout, real `uv sync`, app import) before push. Deployed clean on Railway.
- [x] Switch AI column-mapper (`backend/services/llm.py`) from Anthropic SDK to OpenRouter (`httpx`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` override); dropped `anthropic` dep; 171 backend tests + live mocked round-trip green.
- [x] DEPLOY.md + `.env.example` updated to match (Dockerfile-based deploy steps, OpenRouter env vars).
- [x] Saqlain: merge PR #21 + PR #22 into `main`; point Railway service source back at `main`.
- [x] Saqlain: resolve Railway custom-domain plan limit, then add `api.tenderaudit.in` CNAME + TXT at GoDaddy.
- [ ] Saqlain: confirm `anthropic/claude-haiku-4.5` resolves on the OpenRouter account (override via `OPENROUTER_MODEL` if not).
- [x] Vercel frontend deploy once backend URL confirmed live — hit `MIDDLEWARE_INVOCATION_FAILED` (Next 16 middleware.ts→proxy.ts) and a Framework Preset mismatch along the way, both fixed 2026-07-19. `tenderaudit.in` is live.
