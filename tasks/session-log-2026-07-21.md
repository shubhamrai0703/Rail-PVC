# Session Log — 2026-07-21 (vault fallback, Obsidian unreachable)

## RailPVC — First-user walkthrough script + second design pass (Fable, autonomous)

### Goal
Execute `tasks/handoffs/2026-07-20-sonnet-walkthrough-design-review.md`: write the onboarding walkthrough for the first external contractor session, then run the second (final) design pass on the outward-facing UI.

### What Happened
- Wrote `tasks/walkthrough-first-user.md` — five-part 45–60 min session script (solo prep incl. provisioning + mandatory auth dry-run gate, signup/login, guided real-contract build, workbook side-by-side with a don't-debug-live mismatch script, wrap). Placeholders only, no real names/emails.
- Found the session-shaping gap: **bill lines have no entry UI.** `POST /api/bills/{id}/lines` has zero frontend callers; the PVC run snapshots lines (pvc_service.py:599), it does not generate them, so cement/steel buckets are empty without API-entered lines. Script routes around it (bill selection is a prep gate; curl appendix as fallback). Not ticketed anywhere — recommended as top post-session ticket. Saved to auto-memory.
- Rehearsed the public flow live on `tenderaudit.in` (desktop + mobile); fixed two control-name mismatches in the script. Auth-gated screens verified against source only — no test login existed this session; Saqlain's A4 dry run covers it.
- Design pass produced 8 findings, all awaiting Saqlain's triage, none fixed (approval constraint): D-1 no forgot-password (High, ticket), D-2 signup doesn't say invite-only → raw "no provisioned tenant" error (copy fix candidate), D-3 dead Document Vault nav item, D-4 invented hero figures, D-5 "Get started free" vs invite-gate, D-6 bill-page copy falsely claims runs "generate" lines, D-7 mobile auth dead space, D-8 = known AUDIT-1-4.
- Full Results section appended to the handoff. No code changed, no commits, no PRs.

### Key Decisions
- Session 1 with the contractor targets a bill **without** cement/steel/extra-item deductions (or pre-entered lines via API) — the only shape the UI-only flow can reconcile to his workbook today.
- Findings triage deliberately left to Saqlain per the handoff's per-finding-approval rule; recommended fix-now bundle is D-2+D-5+D-6 as one small copy branch.

### Next Actions
- [Saqlain] Triage D-1…D-7; approve/reject the copy-fix bundle.
- ~~Ticket bill-line entry UI~~ — discovered at wrap: already queued as `tasks/handoffs/2026-07-21-codex-bill-line-entry-ui.md`; D-6 copy fix also covered by the layered-help branch.
- [Saqlain] Run walkthrough Part A (provision + A4 dry run) before scheduling the contractor session.
- Compile this fallback file into the vault when Obsidian is open, then delete it.

## 19:20 — RailPVC — Three help-UI fixes + Continue-to-Bills nav (Sonnet)

### Goal
Execute `tasks/handoffs/2026-07-21-three-help-ui-fixes.md`: fix ScheduleForm input misalignment, wire the dormant AI-assisted column mapper button, write up navigation options for the ExtraNS-decisions page (then, per Saqlain's follow-up, implement the chosen option).

### What Happened
- **Issue 1** — `ScheduleForm.tsx`: `items-end` → `items-start` on the field grid, plus an invisible label spacer above the Add button. Root cause was bottom-alignment reacting to per-column help-text height differences added by the earlier first-user-help feature; fix needed no restructuring since all three labels render on one line. Verified aligned at desktop and mobile widths.
- **Issue 2** — `ImportRowsModal.tsx`: wired the "🤖 Auto-map with AI" button (previously `disabled` with a static tooltip, no `onClick`) to `POST /api/imports/suggest-mapping`, with loading state, sanitized target-field mapping, and inline error+fallback UX. Also fixed a real gap where `value_normalizations` was accepted by `normalizeImportRows` but never actually threaded through from the modal.
- **Found and fixed two real backend bugs in `backend/services/llm.py`** while testing the wiring, not touched otherwise: (1) `client.post("", ...)` against a non-`/`-terminated `base_url` silently hit `.../chat/completions/` (404) — fixed by posting the absolute URL; (2) Claude's structured-output `json_schema` mode can't express the mapping object's dynamic keys and silently returned an empty `{}` mapping (32 completion tokens, no work done) rather than erroring — confirmed by reproducing with and without `response_format`; fixed by switching to plain `json_object` mode plus a markdown-fence-stripping helper (this OpenRouter path still wraps JSON-mode output in fences). Verified end-to-end with a real OpenRouter/Claude Haiku call: 9/9 fields mapped correctly including one the deterministic matcher missed, two deliberately irrelevant columns correctly left unmapped (the explicit product requirement), value normalizations applied correctly in the preview. Also verified the failure path (missing API key → 503 → inline error, dropdowns stay usable).
- **Issue 3** — wrote up 3 concrete navigation options (conditional link / clickable JourneyGuide stages / shared completion hook) with tradeoffs; Saqlain picked option 1. Implemented: `ExtraItemDecisionList` reports `{ total, allDecided }` (gated on *saved* server state, not unsaved pending edits) via a callback; the extra-items page renders a "Continue to Bills →" link in `PageGuidance`'s `next` slot when true, plain text otherwise. Verified both directions (toggle→save→link disappears; toggle back→save→link reappears) and that the destination route renders correctly on direct navigation. Could not get a real click-through on the rendered `<Link>` to register via the browser-automation tool this session — same symptom on the pre-existing, untouched "Back to contract" link on the same page, while plain buttons responded fine — treated as a tooling limitation, flagged explicitly for Saqlain to click-test himself rather than silently assumed fine.
- Full static verification each round: `tsc --noEmit`, `npm run lint`, `npm test` (87 passed), `npm run build`, `uv run pytest -q` (196 passed) — all clean.
- Mid-session hiccup: local browser session (Supabase auth) expired unrelated to the code changes; per the no-credential-entry rule, asked Saqlain to sign back in rather than working around it. Separately, an untracked second backend process (started via the plain `.claude/launch.json` "backend" config) grabbed port 8000 mid-session and killed the manually-CORS-configured one — restarted cleanly, no lasting effect, flagged as a DX gap.
- One real-data write (`NS-1` eligibility toggled to "Undecided" and saved, to prove the nav gate reverts correctly) was explicitly reverted to its original "No" before ending the session.
- Full `## Results` section appended to the handoff file, including this Issue 3 addendum. Nothing committed or pushed; no unrelated worktree files touched.

### Key Decisions
- Issue 3: option 1 (page-local conditional link, gated on saved-not-pending state) — Saqlain's call, over the shared-hook or all-stages-clickable alternatives.
- The AI-mapper's `response_format` moved from strict `json_schema` to plain `json_object` — a deliberate trade of schema enforcement for actually getting a non-empty, useful response; the system prompt already fully specifies the shape, and the frontend's `sanitizeAiMapping` guards against any target the model invents outside the known schema.

### Next Actions
- [Saqlain] Real click-test "Continue to Bills →" on `BCT-24-25-252`'s NS-decisions page — automation couldn't confirm the click-through itself, only href/destination/gating logic independently.
- [Saqlain] Decide whether to pursue Issue-3 option 2 (clickable `JourneyGuide` stages, all six) as a follow-up.
- [Saqlain] Decide whether/when to experiment with swapping `OPENROUTER_MODEL` now that the AI-mapper wiring actually works end-to-end.
- Optional: give `backend/.claude/launch.json`'s "backend" config a `CORS_ORIGINS` default (or otherwise fix the recurring manual-restart friction / process-collision seen this session).
- Compile this fallback file (all entries) into the vault when Obsidian is open, then delete it.

## 22:50 — RailPVC — Seed BCT-23-24-296 for Ritesh

### Goal
Seed contract `BCT-23-24-296` from the checked-in workbook and signed PDFs into Ritesh's existing Banjara Construction production tenant, without affecting other tenant data.

### What Happened
- Resolved the exact production tenant through its consumed invite and active user mapping, then reconciled the contract header, schedules, bills, recoveries, cement, steel, and technical-withholding values from the source files and real-tender fixtures.
- Added a contract-specific transactional seed with explicit tenant and database-host guards, rollback-only dry-run support, duplicate detection, canonical reruns, and field-level verification. It loads 2 schedules, 6 source-labelled aggregate/steel items, 3 signed bills, 18 bill lines, and 12 recoveries.
- Committed the seed to production as contract `0351f862-c55a-4efc-8afd-6b30b703316f`, then reran it repeatedly to prove idempotency. No PVC runs, document uploads, or global index observations were created.
- Review found that cumulative quantities were synthetic, existing rule drift was insufficiently guarded, and bill-line technical withholding was ignored by the live PVC payload. Fixed all three, including sourcing the signed ₹1,249 withholding from `special_condition_amount`.
- An independent production query caught a four-decimal persistence edge on bill 2; cumulative amounts are now quantized before accumulation. Final SQL confirmed all bill totals, recoveries, quantity invariants, and amount invariants, and the backend suite passed 208 tests.

### Key Decisions
- Preserve the workbook's historical index boundary: do not overwrite global observations or create PVC runs until the JPC/index mismatch is resolved.
- Represent the available calculation evidence as six auditable aggregate/steel items rather than claiming a complete BOQ import.
- Require an explicit expected database host for every committed seed rerun so an ambient `DATABASE_URL` cannot produce a false production-success report.

### Next Actions
- Resolve the historical JPC/global-index boundary before calculating PVC runs for this contract.
- Import the complete source BOQ if Ritesh needs item-level auditability beyond the seeded calculation aggregates.
- Ship the reviewed seed and withholding changes if approved.
- Compile this fallback file into the vault when Obsidian is open, then delete it.
