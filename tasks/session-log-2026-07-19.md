# Session Log — 2026-07-19 (vault fallback, Obsidian unreachable)

## RailPVC → TenderAudit — Railway deploy debugging + OpenRouter switch

### Goal
Get the FastAPI backend actually deploying on Railway for tenderaudit.in after the earlier rename/DEPLOY.md session; unblock the AI column-mapper on a shared OpenRouter key instead of a dedicated Anthropic key.

### What Happened
- Diagnosed three consecutive Railway build failures live from Saqlain's screenshots: (1) Root Directory=blank → generic image build failure; (2) Root Directory=backend → Railpack correctly auto-installed mise/python/uv but scoped the build context to `backend/`, so the editable `railpvc-engine` dependency at `../engine` (sibling dir) went missing (`Distribution not found at: file:///engine`); (3) Root Directory=blank + custom Build/Start commands → commands ran but `uv` was never provisioned (`sh: 1: uv: not found`), since custom commands skip Railpack's auto-provisioning; (4) Root Directory=blank + no custom commands → Railpack's own repo-root scan choked on ambiguity (multiple top-level docs/apps, no clear entrypoint).
- Root-caused it: this monorepo's cross-package relative dependency can't be satisfied by any Railpack Root Directory setting that also gets correct Python auto-detection. Fix: a repo-root `Dockerfile` (build context is always repo root regardless of platform heuristics) — `COPY engine ./engine`, `COPY backend ./backend`, `uv sync` from `/app/backend`. Verified locally without Docker itself: replicated the exact COPY layout in an isolated temp dir, ran the real `uv sync --locked --no-dev` there (resolved `railpvc-engine==0.1.0` cleanly), then imported `main.app` successfully — before pushing. Deployed clean on Railway on first try after that. [PR #21](https://github.com/saqlainmmomin/Rail-PVC/pull/21).
- Saqlain added Railway env vars but substituted `OPENROUTER_API_KEY` for the expected `ANTHROPIC_API_KEY` — he wants one shared OpenRouter key across projects rather than a dedicated Anthropic key. Rewrote `backend/services/llm.py`: dropped the `anthropic` SDK, now calls OpenRouter's OpenAI-compatible chat-completions endpoint via `httpx` (already a dependency, no new package). Model configurable via `OPENROUTER_MODEL` (default `anthropic/claude-haiku-4.5`) since the exact OpenRouter slug for the newest Claude Haiku wasn't certain. Verified with the full backend suite (171 passing) plus a live round-trip against a mocked OpenRouter response confirming request shape, model slug, and JSON parsing. [PR #22](https://github.com/saqlainmmomin/Rail-PVC/pull/22).
- Both fixes built in isolated `git worktree`s off `main` rather than the active branch (`codex/ku001-stc-avg-option2`, mid-flight with unrelated uncommitted STC-AVG work) — avoided disturbing that in-progress session entirely.
- Flagged in passing: Railway's DNS-config dialog showed "You have hit the custom domain limit for your plan" — worth resolving before wiring `api.tenderaudit.in` DNS at GoDaddy.

### Key Decisions
- Dockerfile beats fighting Railway/Railpack's monorepo heuristics for any repo with a cross-package relative-path dependency.
- AI column-mapping now goes through OpenRouter, not a direct Anthropic key. `OPENROUTER_MODEL` env override exists specifically because the OpenRouter slug for new models is uncertain and shouldn't require a redeploy to fix.

### Next Actions
- [Saqlain] Merge PR #21 and PR #22 into `main`; point the Railway service's source back at `main`.
- [Saqlain] Resolve the Railway custom-domain plan limit, then add `api.tenderaudit.in` CNAME + TXT records at GoDaddy.
- [Saqlain] Confirm `anthropic/claude-haiku-4.5` resolves as a valid model slug on the OpenRouter account; override via `OPENROUTER_MODEL` if not.
- Move to Vercel frontend deploy once the backend URL is confirmed live (rest of DEPLOY.md).

**Vault note:** Obsidian was closed this session — this log did not make it into the vault. Compile it in next time Obsidian is open (`04-logs/sessions/2026-07-19.md` + touch the `RailPVC` project note), then delete this fallback file.

## 19:03 — RailPVC KU-001-STC-AVG Option 2

### Goal
Implement the approved, rule-set-scoped STC quarter-average precision policy from the Option 2 handoff and record complete verification evidence without committing or pushing.

### What Happened
- Added `quarter_avg_precision` with compatibility default `full`; the opt-in `half_up_2dp` path rounds each quarterly mean with `ROUND_HALF_UP` and applies the documented two-stage rule to SL4.
- Threaded the policy through engine traces, migration 018, rule-set persistence/API reads and updates, run snapshot reconstruction, and the frontend API schema.
- Converted only the two STC fixtures from expected failures to strict passes while leaving their source observations and expected totals unchanged.
- Verified 136 engine tests and 180 backend tests, plus mypy, migration head, frontend typecheck/lint, both STC fixture smoke checks, and exact total invariance for the other nine fixtures.
- Completed a simplification and structured internal review. A detached Claude pass could not run because the local CLI was logged out, so it does not count as the mandated independent review.

### Key Decisions
- Quarter-average precision remains rule-set-scoped and defaults to full precision for compatibility; there is no universal behavior change.
- Under the opt-in policy, monthly observations and base values remain untouched. SL4 rounds its three series means first, then rounds their derived average; workbook evidence still cannot discriminate this ordering.
- The existing Approved-history update lock was not converted to version-on-write because that would expand the established MVP lifecycle beyond this implementation handoff. The limitation is carried into the formal review.

### Next Actions
- Run `KU-001-STC-AVG-REVIEW` as a separate adversarial review before merge, explicitly examining rule-version adoption for contracts with Approved history.
- When Obsidian is open, compile both entries in this fallback file into `04-logs/sessions/2026-07-19.md`, update the existing RailPVC project note and vault index, then delete the fallback file.

## 20:15 — RailPVC KU-001-STC-AVG adversarial review (Fable)

### Goal
Run the mandated `KU-001-STC-AVG-REVIEW` adversarial pass over Codex's uncommitted Option 2 implementation on `codex/ku001-stc-avg-option2`, fix any findings, then wrap and merge to `main`.

### What Happened
- Reviewed the full diff (engine precision threading, migration 018, API/run plumbing, fixtures, tests) and independently re-ran every verification claim: engine 136/7xf, backend 180, mypy, tsc/eslint, both STC strict passes, nine-fixture invariance, no-universalization grep, and direct `PVCRuleSet.model_validate` coercion probes with production-shaped rows.
- Found and fixed **KU1SA-M1 (MEDIUM)**: the rule-set PUT defaulted `quarter_avg_precision` to `"full"` and always wrote it, so any pre-change client PUTting weights would silently reset a `half_up_2dp` policy — a silent money-result change. Fixed with `QuarterAvgPrecision | None = None` + `COALESCE(:qap, quarter_avg_precision)`; repinned the test to preserve-on-omit and regenerated `schema.ts` from the live OpenAPI spec.
- Everything else held: trace/audit parity, SL4 two-stage ordering (comment + discriminating test), base values untouched, migration default backfill and CHECK.
- Review recorded as the active cycle in `REVIEW.md`, appended to the implementation handoff, TASKS.md row closed.

### Key Decisions
- Omitted-field PUT semantics for `quarter_avg_precision` are preserve-not-reset — a financial policy field must never change via a client that doesn't know it exists. Explicit values still persist.
- Deferred as pre-existing: rule-set version-on-write vs the Approved-run PUT lock; API-layer `str` typing of `rounding_mode`/`negative_pvc_policy`.

### Next Actions
- Merge `codex/ku001-stc-avg-option2` to `main`; triage and delete stale branches (this wrap).
- Compile this fallback file into the vault when Obsidian is open, then delete it.
