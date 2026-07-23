# Phase 8 — Multi-sheet export workbook — 2026-07-23

Source: `tasks/handoffs/2026-07-23-chatgpt-phase8-export-ui.md`
Branch: `codex-phase8-export-ui`

### Assumptions

- Preserve the existing Bill sheet layout and its seven-row summary block; put Zone and Base Month on Cover.
- Use persisted `w_derivation` as the authoritative W breakdown.
- Show prior negative PVC carry-forward separately from W arithmetic, sourced from `bill_snapshot`.
- Keep PDF unchanged because the handoff marks it lower priority and the Phase 8 Definition of Done is Excel-specific.
- Preserve all pre-existing dirty worktree changes and stage only Phase 8-owned files.

### Tasks

- [x] Run the 13-test export baseline before production changes.
- [x] Add proof-first tests for sheet order, Cover content/summary, W derivation, and route enrichment.
- [x] Implement tenant-safe contract/sibling-run loading and the pure three-sheet generator.
- [x] Run focused export tests, workbook smoke, full backend tests, and frontend verification.
- [x] Review/simplify the diff; update `TASKS.md`, `STATUS.md`, and the handoff Results section.
- [x] Commit, push, and open the Phase 8 PR against `main` (commit `844b9b5`, PR #26).

---

# Phase 7 — PVC Run + Results UI (D-1…D-4)

## AUDIT13-14 review remediation — 2026-07-23

Source: `REVIEW.md` (`AUDIT13-14-REVIEW`)

### Assumptions

- Continue in the existing dirty checkout without committing, pushing, deploying, or overwriting unrelated documentation/artifacts.
- Preserve audit history: contracts with PVC runs or carry-forwards must be rejected with a structured 422 rather than cascaded.
- Contract deletion must not make private document objects unreachable; storage cleanup must be durable and retryable.
- Preserve fractional API/storage semantics for rebate fields while keeping the UI percent-based.

### Tasks

- [x] Add proof-first backend tests for non-deletable children and retryable document cleanup.
- [x] Implement production-safe Draft contract deletion and storage cleanup.
- [x] Add frontend regression tests for percent round-trips/boundaries and delete cache invalidation.
- [x] Resolve the legacy-compatible rebate domain, correct comments, and regenerate the OpenAPI client schema.
- [x] Run targeted and full backend/frontend verification.
- [x] Close all AUDIT13-14 findings in `REVIEW.md` with test evidence.
- [ ] Deployment gate: apply migration 020 before deploying the backend, then verify the cleanup queue/policies and authenticated delete flow against the real stack.

---

## First-user walkthrough + second design pass — 2026-07-21

Source: `tasks/handoffs/2026-07-20-sonnet-walkthrough-design-review.md` (Results filled)

- [x] Walkthrough script at `tasks/walkthrough-first-user.md`; public flow rehearsed live, gated screens verified against source.
- [x] Second design pass (two-pass rule satisfied): 8 findings D-1…D-8 in the handoff Results, none shipped.
- [ ] Saqlain: triage D-1…D-7 (recommended fix-now bundle: D-2 invite-only copy + D-5; D-6 already covered by the layered-help branch).
- [ ] Saqlain: run walkthrough Part A (provision + A4 auth dry run) before scheduling the contractor session.

---

## Bill-line entry UI — 2026-07-21

Source: `tasks/handoffs/2026-07-21-codex-bill-line-entry-ui.md`
Branch: `codex/tenant-demo-provisioning-results`

### Assumptions

- Continue in the existing dirty checkout without committing, pushing, or changing branches; preserve unrelated first-user-help edits.
- Source selectable items from every schedule under the bill's contract and retain schedule context in each option label.
- Keep all seven decimal inputs as strings through validation and payload construction so JavaScript number coercion cannot reduce precision.

### Tasks

- [x] Add proof-first tests for bill-line validation and precision-preserving payload construction.
- [x] Build the schedule-aware bill-line form with inline client/API errors and reset-on-success behavior.
- [x] Wire the form into bill detail and invalidate the existing `bill-lines` query after creation.
- [x] Run focused tests, full frontend/backend suites, typecheck/lint, and the production build.
- [x] Browser-smoke the authenticated form (desktop width; mobile not yet checked) — Sonnet, 2026-07-21: real click-through on Banjara contract bill #1, line created correctly, item picker excludes it afterward. See session log 2026-07-21 13:11.
- [x] Review and simplify the diff, then record exact evidence and decisions in the handoff Results section.
- [ ] Update stale copy on the bills-**list** page (`bills/page.tsx`) claiming line entry isn't available on-screen — contradicts the now-working bill-detail form.
- [x] Fix `backend/main.py` `load_dotenv()` resolving to repo-root `.env` instead of `backend/.env` when launched from repo root (silently drops backend-only env vars, e.g. `CORS_ORIGINS`) — flagged as background task task_f59c1521. Fixed 2026-07-21 evening: both `backend/main.py` and `backend/migrations/env.py` now resolve `.env` relative to file location; regression coverage in `backend/tests/test_dotenv_paths.py`. See `tasks/handoffs/2026-07-21-dotenv-wrap-and-push.md`.

---

## In-app help requirements brainstorm — 2026-07-20

- [x] Check what already exists.
- [x] Ask scoping questions.
- [x] Weigh approaches and recommend.
- [x] Confirm scope before writing.
- [x] Write the requirements plan.

Plan: `docs/plans/2026-07-20-001-feat-layered-first-user-help-plan.md`
Implementation handoff: `tasks/handoffs/2026-07-20-codex-layered-first-user-help.md`

---

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
- [x] AUDIT-1-3 (delete affordance): `DELETE /api/contracts/{id}` (Draft-only, cascade, 204) + Trash button in UI — **Saqlain: use the Delete button in the live tenant to clear the junk drafts**.
- [x] AUDIT-1-4 (rebate % input): `bid_discount_pct` + `overall_rebate` now accept percent values; display updated; tsc + vitest + build clean.
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

---

# Landing page + auth redesign — 2026-07-19 (evening)

No handoff file; session log in `tasks/session-log-2026-07-19.md` (20:43 entry).

## Tasks

- [x] Public marketing landing page at `/` (`frontend/app/page.tsx`) — hero with stylized PVC-run card, stat strip, 6 features, how-it-works, CTA; proxy allows `/` logged-out, logged-in still → `/contracts`.
- [x] Auth redesign: split-panel `(auth)/layout.tsx` (dark brand panel + proof points), login/signup forms restyled, no logic changes.
- [x] Verified: `next build` clean ×2; browser smoke of landing (desktop+mobile), login, signup via `next start`.
- [ ] Second design pass on landing + auth before first outside exposure (two-pass rule).
- [ ] Optional: swap invented hero figures for a real golden-workbook case (PVC/ gitignored sources).

---

# Tenant demo provisioning — 2026-07-19

Source: `tasks/handoffs/2026-07-19-codex-tenant-demo-provisioning.md`
Branch: `codex/tenant-demo-provisioning`

## Assumptions

- Provisioning is invite-only: an uninvited Supabase user keeps the exact existing rejection.
- The real contact's name and email remain runtime-only environment variables.
- Live migration, test-email provisioning, demo seeding, and browser smoke are required before completion.

## Tasks

- [x] Review the existing BCT-24-25-252 seed for idempotency, FK ordering, precision, and fixture reconciliation (DEMO-2); reconciliation failed and is recorded as a blocker.
- [x] Add migration 019 for case-insensitive, consumable tenant invites.
- [x] Implement race-safe invite consumption in `get_current_user` with real-dependency tests.
- [x] Add an idempotent tenant/invite provisioning script and document the operator flow.
- [x] Run focused and full backend verification, then review/simplify the diff.
- [x] Apply migration 019 live and verify the API health endpoint.
- [ ] Provision and seed a test tenant twice, then browser-smoke invited and uninvited signup flows.
- [x] Update project status/task records and write evidence plus blockers to the handoff Results section.

---

# Layered first-user help — 2026-07-20

Source: `tasks/handoffs/2026-07-20-codex-layered-first-user-help.md`
Branch: `codex/tenant-demo-provisioning-results`

## Assumptions

- Continue on the existing feature branch; preserve all pre-existing dirty files and do not commit, push, or deploy.
- Treat the executable handoff as implementation authority for the linked requirements-only Product Contract.
- Keep calculation-critical consequences inline; use accessible disclosure controls only for supplementary definitions.
- Describe the missing bill-line entry UI honestly without expanding this ticket into capability work.

## Tasks

- [x] Add the reusable journey, page-guidance, and supplementary-help patterns with focused tests.
- [x] Add contract, schedule, item-import, and classification guidance.
- [x] Add bill, calculation, blocking-error, result, approval, and export guidance; remove inaccurate bill-line claims.
- [x] Run typecheck, lint, unit tests, build, simplification, and code review; resolve findings.
- [ ] Browser-smoke all three protected moments at desktop and mobile widths and record evidence in the handoff Results section.

---

# Three help-UI fixes + Continue-to-Bills nav — 2026-07-21

Source: `tasks/handoffs/2026-07-21-three-help-ui-fixes.md` (Results filled)
Branch: `codex/tenant-demo-provisioning-results`

## Tasks

- [x] Issue 1: ScheduleForm input misalignment — `items-end` → `items-start` + invisible Add-button label spacer; verified desktop + mobile.
- [x] Issue 2: wire the dormant AI-assisted column mapper (`ImportRowsModal.tsx` → `POST /api/imports/suggest-mapping`), loading/error/fallback states; also fixed two real bugs found in `backend/services/llm.py` (wrong OpenRouter URL, structured-output schema silently returning empty mappings) — verified end-to-end with a real Claude Haiku call and the deliberate-failure path.
- [x] Issue 3: wrote up 3 navigation options; Saqlain chose option 1 (conditional "Continue to Bills →" link gated on saved decision state); implemented in `ExtraItemDecisionList.tsx` + `extra-items/page.tsx`, verified both directions of the gate.
- [ ] Saqlain: real click-test "Continue to Bills →" on `BCT-24-25-252` (automation couldn't confirm the click-through itself this session, only href/destination/gating logic independently — see handoff caveat).
- [ ] Saqlain: decide on Issue-3 option 2 (clickable `JourneyGuide` stages, all six) as a follow-up, or leave as-is.
- [ ] Saqlain: experiment with swapping `OPENROUTER_MODEL` now that the AI-mapper wiring works end-to-end.

---

# Seed BCT-23-24-296 for Ritesh — 2026-07-21

Branch: `codex/tenant-demo-provisioning-results`

## Assumptions

- Target the already-provisioned `BANJARA CONSTRUCTION CORPORATION- MUMBAI` tenant associated with Ritesh; resolve its UUID read-only before any write.
- Seed only contract `BCT-23-24-296`; do not modify the existing BCT-24-25-252 demo seed or any other tenant data.
- Treat the checked-in real-tender fixtures as calculation truth and the source workbook/PDFs as contract, bill, and UI-record truth.
- Production writes must be idempotent, transaction-scoped, and followed by exact row/count verification.

## Tasks

- [x] Confirm the target tenant and prove the contract is not already present.
- [x] Extract and reconcile contract metadata, schedules/items, and three bills from the source files.
- [x] Add an idempotent BCT-23-24-296 seed path with focused tests.
- [x] Run dry-run/reconciliation and backend smoke checks.
- [x] Seed the production tenant, re-run for idempotency, and verify the visible contract/bill records.

## Follow-ups

- [ ] Resolve the historical JPC/global-index mismatch before creating PVC runs for BCT-23-24-296.
- [ ] Import the complete BOQ if Ritesh needs item-level auditability beyond the six seeded calculation aggregates.

---

# Document Vault adversarial review — 2026-07-22

Source: `tasks/handoffs/2026-07-22-claude-document-vault-adversarial-review.md`
Branch: `codex/tenant-demo-provisioning-results`

## Tasks

- [x] Adversarial review of upload, list, and signed-URL download (P3-BF-4): no release-blocking issues found. Verdict: **READY**.
- [x] Verified: 19/19 backend tests, 92/92 frontend tests, ESLint clean, TypeScript clean, production build green.
- [ ] Optional hardening: replace `assert row is not None` (documents.py:127) with explicit raise.
- [ ] Optional hardening: omit `storage_path` from public `DocumentRecord` API schema in v2.
- [ ] Optional hardening: add IDOR negative tests for document upload and list endpoints.

---

# AUDIT-1-3 / AUDIT-1-4 adversarial review — 2026-07-23

Source: `tasks/handoffs/2026-07-23-chatgpt-review-audit13-14.md`
Branch: `main`

## Tasks

- [x] Review draft-contract deletion for tenant isolation, cascade safety, and status-change races.
- [x] Trace schedule discount and contract rebate percent round-trips, including blank/zero/NaN and precision behavior.
- [x] Run targeted verification and record the verdict in the handoff Results section.
- [x] Defects found: add an `AUDIT13-14-REVIEW` cycle to `REVIEW.md`.
