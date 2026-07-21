# Handoff — Fix three issues found reviewing the first-user help UI, pre-demo with Ritesh

## Goal

Fix three concrete issues Saqlain found while manually clicking through the uncommitted "layered first-user help" feature, ahead of a live onboarding demo with a real contractor (Ritesh, Banjara Construction Corporation — Mumbai). Work the three in order: (1) is a straightforward CSS fix, (2) is a real feature build (wire an already-built backend endpoint to a currently-inert frontend button), (3) is a navigation-design question Saqlain wants to decide together, not have solved unilaterally.

Definition of done:
- Issue 1: the three ScheduleForm fields visually align in one row, at desktop and mobile width, regardless of which columns have help text under them.
- Issue 2: the "🤖 Auto-map with AI" button actually calls the backend, applies the result, handles loading/failure, and Saqlain has verified with a real BOQ-like file that irrelevant columns come back unmapped rather than force-filled.
- Issue 3: NOT implemented yet — instead, 2-3 concrete navigation options with tradeoffs are written up and presented to Saqlain for a decision, after 1 and 2 are done.

## Current state

- Repo: `/Users/saqlainmomin/railPVC`, branch `codex/tenant-demo-provisioning-results`.
- The working tree is already dirty with an uncommitted feature: layered first-user contextual help (six-stage journey guide, page-level guidance, supplementary field help) added across contract/schedule/items/bill/run screens. Full background: `tasks/handoffs/2026-07-20-codex-layered-first-user-help.md` (implementation notes + its own `## Results` section) and `tasks/walkthrough-first-user.md` (the actual demo script this all supports).
- There are other uncommitted/untracked files in the tree unrelated to this work (see `git status --short`). **Do not touch, commit, or clean any of them.**
- This session (the one that produced this handoff) already:
  - Provisioned a real tenant + invite for Ritesh (`seeds/provision_tenant.py`, tenant `BANJARA CONSTRUCTION CORPORATION- MUMBAI`, invite `claudebotkar@gmail.com`) — production Supabase, already done, don't repeat.
  - Built the frontend locally (`npm run build` in `frontend/`) and ran it via `.claude/launch.json` config `"frontend-prod"` (`npm run start --prefix frontend`), which auto-picked port 51892 (port 3000 was occupied by an unrelated WhatsApp-bridge process — do not kill that one, it's not ours).
  - Added a `"backend"` config to `.claude/launch.json` running `uvicorn main:app --app-dir backend --port 8000`.
  - Restarted the local backend with `CORS_ORIGINS="http://localhost:51892,http://localhost:3000"` so the local frontend can reach it (default `CORS_ORIGINS` in `backend/main.py` is only `http://localhost:3000`; adjust again if the frontend lands on yet another auto-assigned port).
  - Saqlain manually added a real `OPENROUTER_API_KEY` to `backend/.env` (gitignored, local-only) and the backend was restarted with it loaded. **Never print, log, or move that key.**
- Saqlain and Codex/Claude walked through the live UI together and found three issues, each confirmed with file/line evidence (below) — not guesses.

## Issue 1 — ScheduleForm field misalignment (do first)

**File:** `frontend/components/contracts/ScheduleForm.tsx:58`

The form row is `grid grid-cols-1 items-end gap-3 md:grid-cols-[1fr_160px_200px_auto]` (Name / Type / Bid discount / Add-button columns). `items-end` bottom-anchors each column's entire content block. The three field columns no longer have equal content height because the help-UI work added:
- a `SupplementaryHelp` disclosure under **Type** (~line 74), shown always, plus a conditional amber ExtraNS warning paragraph;
- a permanent help paragraph under **Bid discount** (~line 95, "Enter a fraction: 0.05 means 5%...");
- **Name** has neither — label + input only.

Because `items-end` aligns each column's whole div to the bottom of the row, and the divs have different total heights, the actual `<input>`/`<select>` elements land at different vertical offsets across the three columns — visually staggered (see Saqlain's annotated screenshot in the parent conversation, not attached here).

**Fix direction:** stop relying on `items-end` for this. The likely correct approach is to separate the "controls row" (label+input, which should align via `items-start` or a fixed input row) from the help-text row underneath, so all three inputs sit on one line regardless of how much help text trails each column. Don't just delete the help text — restructure the layout so it doesn't affect input alignment.

**Verify:** screenshot the Schedules tab "Add schedule" row at desktop width and at mobile width (resize_window) after the fix; confirm all three inputs are on one visual line.

## Issue 2 — Wire the AI-assisted column mapper (real feature, not a toggle)

**Backend is fully built already, do not modify it unless you find an actual bug:**
- `POST /api/imports/suggest-mapping` — see `backend/api/imports.py` and `backend/services/llm.py`.
- Calls Claude Haiku 4.5 via OpenRouter's OpenAI-compatible chat-completions API (`backend/services/llm.py:34-35`, `_OPENROUTER_URL`, `_MODEL` from `OPENROUTER_MODEL` env, default `anthropic/claude-haiku-4.5`).
- Requires `OPENROUTER_API_KEY` (`llm.py:81-83`, raises `LLMUnavailableProblem` — 503 — if missing). Already set locally by Saqlain in `backend/.env`.
- The system prompt (`llm.py:37-72`) already targets the exact canonical BOQ schema (item_code, description, unit, original_qty, revised_qty, base_rate, agreement_rate, is_cement_item, steel_subtype) and already instructs: map irrelevant headers to `null`, surface uncertain ones in an `unmapped` list, return `value_normalizations` for non-canonical yes/no or steel-subtype tokens, and an overall `confidence` score.

**Frontend is NOT wired — this is the actual work:**
- `frontend/components/contracts/ImportRowsModal.tsx:592` — the "🤖 Auto-map with AI" button is `disabled` as a static hardcoded JSX attribute, wrapped in a `<span title="The AI-assisted mapper ships in the next release...">`. **It has no `onClick` at all.** It has never called the endpoint.
- There's a separate, already-working deterministic fuzzy-header matcher (no LLM) that auto-populates the mapping table on load, and a "Re-run auto-map" button next to the AI button that re-triggers it (same file, same area). Reuse that same mapping state shape when wiring the AI path — don't invent a parallel state model.
- What to build: on click, call `POST /api/imports/suggest-mapping` with the parsed sheet's headers + a few sample rows; on success, apply the returned `mapping` and `value_normalizations` onto the existing mapping state (same target the deterministic matcher writes to); show a loading state on the button while the call is in flight; on `LLMUnavailableProblem` (503) or any other failure, show a clear inline/toast error that falls back to manual/deterministic mapping — never fail silently. Remove the "ships in the next release" tooltip and the hardcoded `disabled` once it's real.

**Product requirement, Saqlain's own words (capture faithfully, don't rephrase away the intent):** *"our AI should be smart enough to know if something's not relevant, and it should simply not just fill in values."* The system prompt already asks for this (null target + `unmapped` list for anything the model isn't confident about) — but verify this actually holds by testing with a real-ish BOQ file that includes a few clearly irrelevant columns (e.g. serial number, remarks, a stray blank column) and confirming they come back unmapped, not force-mapped to some target field.

**Also explore with Saqlain, not a fixed requirement:** he wants to try swapping `OPENROUTER_MODEL` to open-source alternatives available on OpenRouter, to compare cost/quality against Claude Haiku 4.5 specifically for this BOQ-mapping task. Treat this as an experiment to run together once the wiring works, not something to land unilaterally.

**Scope guard:** this is pre-demo prep for a real contractor tenant (`BANJARA CONSTRUCTION CORPORATION- MUMBAI`, invited via `claudebotkar@gmail.com`, provisioned via `seeds/provision_tenant.py`). Do not touch production Supabase data, migrations, or that tenant while building/testing this. Test locally against Saqlain's own seeded account (`saqlain.nmims@gmail.com`) instead.

## Issue 3 — No forward navigation from ExtraNS decisions (discuss, don't implement yet)

**File:** `frontend/app/(app)/contracts/[id]/extra-items/page.tsx:71-76` (back-link) and `~95` (`PageGuidance` `next` prop).

The only navigation control on this page is "← Back to contract." The `PageGuidance` component's `next` prop already says *"Create the bill after every extra item has an explicit decision"* but it's plain descriptive text, not a link — there is no direct path from this screen to Bills.

**Do not implement a fix unprompted.** Instead, prepare 2-3 concrete options with tradeoffs, for example:
- A "Continue to Bills →" button/link that appears once every ExtraNS item has an explicit decision (ties completion state to the existing decision data, no new persisted state needed).
- Making the relevant stage in the six-stage `JourneyGuide` (Contract → Items → NS decisions → Bill → Calculate → Review) a clickable link to the next stage, consistently across all stages, not just this one page.
- Some other pattern Saqlain may prefer once he sees the above.

Present these to Saqlain and get his choice before writing any code for issue 3. This was explicit: he wants to walk through navigation options together.

## Key files

- `/Users/saqlainmomin/railPVC/frontend/components/contracts/ScheduleForm.tsx` — issue 1.
- `/Users/saqlainmomin/railPVC/frontend/components/contracts/ImportRowsModal.tsx` — issue 2, AI button + existing deterministic auto-map to model wiring after.
- `/Users/saqlainmomin/railPVC/backend/services/llm.py` — issue 2, backend LLM client (read-only reference, don't modify absent a real bug).
- `/Users/saqlainmomin/railPVC/backend/api/imports.py` — issue 2, the route the frontend needs to call.
- `/Users/saqlainmomin/railPVC/frontend/app/(app)/contracts/[id]/extra-items/page.tsx` — issue 3.
- `/Users/saqlainmomin/railPVC/frontend/components/help/` — the shared help components (`JourneyGuide`, `PageGuidance`, `SupplementaryHelp`) all three issues touch or relate to.
- `/Users/saqlainmomin/railPVC/tasks/handoffs/2026-07-20-codex-layered-first-user-help.md` — full background on the help feature these fixes sit on top of.
- `/Users/saqlainmomin/railPVC/tasks/walkthrough-first-user.md` — the actual demo script; issue 2 in particular changes what's said/shown during "Import rows from Excel."
- `/Users/saqlainmomin/railPVC/STATUS.md` — current branch/blocker state; read before starting.
- `/Users/saqlainmomin/railPVC/.claude/launch.json` — local dev server configs (`frontend-prod`, `backend`) added this session.

## Constraints

- Do not commit, push, or clean the working tree. Preserve every other uncommitted/untracked file exactly as found — check `git status --short` before and after, and diff only your own intended files.
- Do not touch the PVC engine, migrations, or backend calculation logic.
- Do not modify production Supabase data, the demo/Ritesh tenant, or run any seed/provisioning script.
- Never print, log, commit, or otherwise expose the `OPENROUTER_API_KEY` value in `backend/.env`.
- Match existing code style (Tailwind utility classes, existing component patterns in the same files) — no new dependencies for issue 1 or 2 unless something is truly impossible without one.
- For issue 3, do not write implementation code until Saqlain has picked an option.

## Verification

Run from `/Users/saqlainmomin/railPVC/frontend`:
```
npx tsc --noEmit
npm run lint
npm test
npm run build
```
Then browser-smoke against the local stack (rebuild + restart `frontend-prod` after each change, since it's a production build, not dev-mode HMR; restart `backend` if you change backend env/CORS):
1. **Issue 1:** Schedules tab, "Add schedule" row — desktop and mobile width screenshots, confirm one-line alignment.
2. **Issue 2:** Items tab → Import rows → upload a real-ish `.xlsx` (or paste) with a few deliberately irrelevant columns → click "🤖 Auto-map with AI" → confirm loading state, confirm mapped fields are correct, confirm irrelevant columns show as unmapped (not force-filled), confirm a forced-failure path (e.g. temporarily unset `OPENROUTER_API_KEY` and confirm the error message and fallback-to-manual path) — then restore the key.
3. Confirm no console errors introduced, no new horizontal overflow.

This is not done on static inspection alone — prove each with a real browser interaction and record what you saw.

## Report back

Append a `## Results` section to this same file, covering: what changed per issue (file-level), exact verification command output, browser-smoke evidence for issues 1 and 2, the 2-3 navigation options prepared for issue 3 (not implemented), any open questions for Saqlain, and confirmation that no unrelated worktree files were touched and nothing was committed/pushed.

## Results

### Issue 1 — ScheduleForm alignment (done)

**File:** [frontend/components/contracts/ScheduleForm.tsx](../../frontend/components/contracts/ScheduleForm.tsx)

Root cause confirmed exactly as diagnosed: `items-end` bottom-anchored each column div, and since Name/Type/Bid-discount now carry different amounts of trailing help text, the input elements landed at different heights. Fix:

- Changed the grid from `items-end` to `items-start`. Since the label text for all three columns (`Name *`, `Type *`, `Bid discount (0.05 = 5%)`) renders on one line at both the `md:grid-cols-[1fr_160px_200px_auto]` widths and full mobile width, each column's label+input block now starts at the same offset regardless of what help text trails below the input — no restructuring into separate label/input/help grid rows was needed.
- The Add button had no label above it, so under `items-start` it would land above the input row instead of level with it. Added an invisible spacer (`<span aria-hidden="true" className="... invisible">Add</span>`) matching `labelCls` above the button so it still lands on the input line.

Did not touch the help-text content or the `SupplementaryHelp`/amber-warning logic — only the alignment mechanism.

### Issue 2 — Wire the AI-assisted column mapper (done, with two real backend bugs found and fixed)

**Files:**
- [frontend/components/contracts/ImportRowsModal.tsx](../../frontend/components/contracts/ImportRowsModal.tsx) — wired the button.
- [backend/services/llm.py](../../backend/services/llm.py) — two real bugs fixed (see below); untouched otherwise.

**Frontend wiring:**
- Added a `useMutation` (`suggestMapping`) that POSTs `{ headers, sample_rows: source.body.slice(0, 5) }` to `/api/imports/suggest-mapping` via the existing `apiFetch`.
- On success: sanitizes the returned mapping against `TARGET_FIELDS` (`sanitizeAiMapping` — any target the model invents outside the known schema is coerced to `null` rather than trusted) and merges it into the existing `mappingOverrides` state — same state the deterministic matcher and the manual dropdowns already write to, per the handoff's instruction not to invent a parallel model.
- Also wired `value_normalizations` into `normalizeImportRows` — this was previously accepted by the function (`normalizeImportRows.ts` already had the parameter) but **never actually passed in from the modal**, so even a working AI response would have had no way to normalize "Yes"/"No" → boolean or "TMT Bar" → `tmt`. Added a `valueNormalizations` state slice, threaded it into the `parsed` memo, and reset it whenever the source headers change or the deterministic re-map runs.
- Removed the hardcoded `disabled` + "ships in the next release" tooltip. Button now shows "Mapping…" while `suggestMapping.isPending`, and an inline banner shows either the AI result summary (confidence %, unmapped columns) or the error message + "Falling back to manual mapping" on failure — dropdowns stay fully live in both cases.

**Two real bugs found in `llm.py` while testing (not touched otherwise, per the handoff's "don't modify unless you find an actual bug"):**

1. **Wrong endpoint URL.** `_client()` sets `base_url=_OPENROUTER_URL` (no trailing slash) and the call site did `client.post("", ...)`. httpx's relative-URL merge against a non-`/`-terminated base appends a trailing slash, so every request actually hit `.../chat/completions/` → OpenRouter 404'd every single call. Confirmed via `httpx.AsyncClient(base_url=...).build_request()` before touching code. Fix: `client.post(_OPENROUTER_URL, ...)` — pass the absolute URL, which httpx uses as-is regardless of `base_url`.
2. **Structured-output schema rejected by every backend OpenRouter tried.** After fixing #1, calls got a 400: `output_config.format.schema: For 'number' type, properties maximum, minimum are not supported`, reproduced consistently across Bedrock, Azure, and Anthropic (OpenRouter's own fallback chain, all three tried and failed on the `confidence: {"minimum": 0, "maximum": 1}` schema property). Deeper problem found once that was stripped: with strict `json_schema` enforcement, Claude Haiku returned a *valid but empty* `{"mapping": {}, "unmapped": [], "confidence": 0, ...}` for every call — 32 completion tokens, no actual mapping work done. Root cause: the `mapping` property is a dynamic-keyed object (`additionalProperties` only, no `properties`) because the keys are the source spreadsheet's own headers, unknowable ahead of time — this shape isn't expressible in a way Anthropic's structured-output validator handles usefully, so the model silently gives up rather than erroring. Confirmed by re-running the identical prompt with `response_format` removed entirely: the model correctly mapped 9/9 fields with the right nulls. Fix: switched `response_format` to plain `{"type": "json_object"}` (schema no longer enforced; the system prompt already fully specifies the shape) and added `_strip_code_fence()` before `json.loads`, since this provider path still wraps JSON-mode output in ```` ```json ... ``` ```` fences even without a schema.

Removed the now-dead `_RESPONSE_SCHEMA` dict entirely rather than leaving it unused.

**Backend tests:** `uv run pytest -q` → **196 passed** (was 196 before too; `tests/test_p5_imp_imports.py`'s 11 tests don't touch the LLM call path, no regressions).

### Verification — static checks

From `frontend/`:
```
npx tsc --noEmit         → clean, no output
npm run lint              → clean, no output
npm test                  → 13 test files, 87 tests passed
npm run build              → ✓ Compiled successfully, ✓ TypeScript clean, all 15 routes generated
```
From `backend/`: `uv run pytest -q` → **196 passed**.

### Verification — browser smoke (real interaction, local stack)

Stack: `frontend-prod` (production build, `npm run start`) against local `uvicorn` backend on `:8000`, both restarted after each code change. Frontend auto-picked ports across restarts (3000 was occupied by the unrelated WhatsApp-bridge process the earlier session flagged — left untouched); backend's `CORS_ORIGINS` was updated to match each new frontend port. Tested against Saqlain's own seeded account (`saqlain.nmims@gmail.com`) on contract `BCT-24-25-252` — never touched the Ritesh/Banjara demo tenant or production provisioning.

**Issue 1:**
- Desktop (1280px): set Schedule type to `ExtraNS` (the tallest help-content case — disclosure + amber warning under Type, permanent help text under Bid discount, nothing under Name) and confirmed all three inputs and the Add button sit on one visual line. Screenshot taken and reviewed.
- Mobile (375×812): confirmed the form still stacks one field per row correctly with no regression from the alignment change.

**Issue 2:**
- Built a real-ish BOQ paste (11 columns: `BOQ Item`, `Item Particulars`, `UOM`, `Qty (Agreement)`, `Qty (Executed)`, `SOR Rate (Rs)`, `Tendered Rate (Rs)`, `Cement Used`, `Steel Category`, plus two deliberately irrelevant columns `Remarks` and `Internal Ref No`), 3 sample rows.
- Before the AI call, the existing deterministic matcher (untouched, confirmed still working) mapped 8/9 required fields correctly and correctly left `Remarks`/`Internal Ref No` unmapped — but missed `Item Particulars` → `Description` (showed "Missing required: Description"), giving a good real test of whether the AI path adds value.
- First click surfaced the auth-session-expiry issue below; second click hit bug #1 (404); third hit bug #2 (400, then silent-empty); after both backend fixes, the AI call succeeded end-to-end:
  - Banner: *"AI mapping applied (confidence 95%). All columns mapped."*
  - All 9 target fields mapped correctly, including the one the deterministic matcher missed (`Item Particulars → Description`).
  - `Remarks` and `Internal Ref No` came back **`— ignore —`**, not force-filled — this was the explicit product requirement ("should simply not just fill in values").
  - Preview table showed value normalizations applied correctly per row: `No → (blank)`, `Yes → yes` for Cement; `Angles → angles`, `TMT Bar → tmt` for Steel.
  - Cancelled the modal rather than committing the 3 test rows into the real schedule.
- Deliberately re-broke it: restarted the backend with `OPENROUTER_API_KEY` overridden to empty (never touched the real value in `backend/.env`) and clicked Auto-map again. Got the inline error *"OPENROUTER_API_KEY is not configured. Falling back to manual mapping — use the dropdowns below."* with the mapping table remaining fully editable — no crash, no stuck spinner. Restarted the backend again with the key restored (verified programmatically that the key is present again, without printing it) before continuing.
- No new console errors or horizontal overflow observed outside of expected transient `Failed to fetch` noise during the ~1–2s windows I killed/restarted the backend myself mid-test (not a product bug).

**Note on the session hiccup:** mid-verification, the local browser tab's Supabase session expired/cleared (browser preview environment reset, cause unclear — possibly triggered by the `resize_window` desktop/mobile toggle) and the app fell back to the sign-in screen. Per the standing safety rule, I don't type credentials into any field — even a benign local dev login — so I asked Saqlain to sign back in himself before continuing. This added a pause but no workaround was taken.

### Issue 3 — navigation options (not implemented, for discussion)

**File in question:** [frontend/app/(app)/contracts/[id]/extra-items/page.tsx](<../../frontend/app/(app)/contracts/[id]/extra-items/page.tsx>) — only nav control is "← Back to contract"; `PageGuidance`'s `next` prop is plain text, not a link.

Three concrete options, roughly in order of effort:

1. **Conditional "Continue to Bills →" link, this page only.** Add a link/button next to (or replacing) the current `next` guidance text that appears once every ExtraNS item in `decisions` has an explicit `eligible !== null` — no new persisted state, just derived from data already fetched on this page (`decisions.data`). Smallest change, but only fixes this one page; Items → NS-decisions and Bill → Calculate still have the same gap if it exists there too (worth checking).
   - *Tradeoff:* cheap and scoped, but doesn't generalize — if the same "no forward link" gap exists on other stage pages, this doesn't fix them.

2. **Make `JourneyGuide`'s stage pills clickable, consistently across all six stages.** `JourneyGuide` (`frontend/components/help/FirstUserHelp.tsx:9`) already renders all six stages with the current one highlighted; it's pure presentation today (`<li>`, not `<a>`/`<Link>`). Turning each non-current stage into a link to its own page (`contract`→Overview, `items`→Items tab, `decisions`→extra-items, `bill`→Bills, etc.) gives free forward *and* backward navigation everywhere `JourneyGuide` is already mounted, for one change.
   - *Tradeoff:* touches a shared component so needs care (e.g. should a not-yet-reachable future stage, like Bill before any schedule exists, be a disabled/greyed link or just always clickable and let the destination page handle empty state?). Larger surface area than option 1, but fixes the pattern everywhere at once rather than page-by-page.

3. **Completion-gated forward link, but data-model-driven rather than page-local.** Same visual outcome as option 1 (a "Continue to Bills →" affordance), but instead of computing "all decisions made" ad hoc in each page component, expose it as a small shared hook/helper (e.g. `useExtraItemDecisionsComplete(contractId)`) that both this page and `JourneyGuide`/`PageGuidance` could consume later — so if option 2 is done later too, the "is this stage done" logic isn't duplicated.
   - *Tradeoff:* most future-proof if you expect to add completion-gating to other stages (e.g. "Bill" stage gated on at least one bill line entered), but it's speculative scope for a problem that's currently only confirmed on this one page — possibly overbuilding for what's needed today.

My lean, if useful: start with option 1 for the immediate gap, since it's the one Saqlain actually hit; option 2 is worth doing but as its own follow-up once you've decided whether "always clickable" or "gated" is the right feel for the whole journey guide, not bundled into this fix.

**Saqlain's decision (2026-07-21): option 1.** Implemented below.

### Issue 3 — implemented: conditional "Continue to Bills →" link

**Files:**
- [frontend/components/contracts/ExtraItemDecisionList.tsx](../../frontend/components/contracts/ExtraItemDecisionList.tsx) — added an optional `onStatusChange?: (status: { total: number; allDecided: boolean }) => void` prop, reported via `useEffect` whenever `rows` changes.
- [frontend/app/(app)/contracts/[id]/extra-items/page.tsx](<../../frontend/app/(app)/contracts/[id]/extra-items/page.tsx>) — added `decisionStatus` state fed by that callback; `PageGuidance`'s `next` prop now renders a `<Link href={`/contracts/${id}/bills`}>Continue to Bills →</Link>` when `decisionStatus.allDecided`, otherwise the original plain-text guidance.

**Deliberate design choice:** the gate reads `r.serverVerdict` (the last *saved* state from the `decisions` query), not the locally staged `pending` edits or the merged `effectiveVerdict` the row buttons display. An unsaved toggle — in either direction — doesn't move the link until "Save changes" actually persists it. This matches the existing component's own pattern (the "undecided count" banner already distinguishes saved vs. pending elsewhere) and avoids the user clicking through to Bills on the strength of an edit that a page reload would silently discard.

**Verification:**
- `npx tsc --noEmit`, `npm run lint`, `npm test` (87 passed), `npm run build` — all clean, re-run after these edits.
- Browser: on contract `BCT-24-25-252`'s one ExtraNS item (`NS-1`, decided "No"), confirmed:
  - Initial state (all decided): "Next: **Continue to Bills →**" renders as a link with the correct `href` (`/contracts/d50b8b6a.../bills`) — confirmed via the accessibility tree, not just visually.
  - Toggled `NS-1` to "Undecided" but **before saving**: link stayed visible (gate correctly still reads the old saved "No", not the unsaved pending edit) — this is the "don't let an unsaved edit unlock nav" case working as designed.
  - Clicked "Save changes": banner flipped to "1 item(s) undecided — PVC run will be blocked...", and the link correctly reverted to plain, unlinked text.
  - Toggled back to "No" and saved again: banner and link both reverted to the "all decided" state, restoring the row to exactly what it was before I touched it.
  - Direct navigation to `/contracts/d50b8b6a.../bills` confirmed the destination page itself renders correctly (journey guide correctly highlights stage 4 "Bill").
- **One thing I could not cleanly prove:** clicking the rendered `<Link>` via the browser-automation tool's synthetic click did not trigger client-side navigation in this environment — but neither did clicking the pre-existing, untouched "Back to contract" link on the same page, while plain `<button onClick>` elements on the same page responded to clicks correctly every time. Since (a) the `href` is confirmed correct, (b) the destination route works when navigated to directly, and (c) this component uses the exact same `next/link` `Link` pattern already used elsewhere in the app (e.g. the "Bills →" link on the contract overview page, `next-item-decisions` link), I'm treating this as a limitation of the automated click-dispatch in this specific tool/session rather than a defect in the new code — but flagging it explicitly rather than papering over it, since I couldn't get a real click-through to fire in this session to rule it out with full confidence.

### Open questions for Saqlain

1. Please do a real click on "Continue to Bills →" yourself when you get a chance (contract `BCT-24-25-252` → NS decisions tab) — I could not get a working click-through in the automated browser this session (see caveat above) even though the `href`, gating logic, and destination route all check out independently.
2. You mentioned wanting to try swapping `OPENROUTER_MODEL` against other OpenRouter models to compare cost/quality for BOQ mapping — want to do that together now that the wiring actually works end-to-end (previously nothing was reachable to compare)?
3. The `_strip_code_fence` fix works around this specific OpenRouter routing path (Bedrock/Azure/Anthropic) still wrapping `json_object`-mode output in markdown fences — that's provider behavior, not something we control. Worth knowing if you swap `OPENROUTER_MODEL` to a non-Anthropic model per Q2, in case its fencing behavior differs (the strip function handles fenced or unfenced content either way, so it should be safe, but flagging it).
4. `backend/.claude/launch.json`'s `"backend"` config doesn't carry `CORS_ORIGINS` — every session that starts the frontend on a new auto-picked port needs the backend restarted with an updated `CORS_ORIGINS` env var by hand (as this session and the prior one both did manually). This session it also got more disruptive: midway through, an untracked second `uvicorn` process (started via the plain `.claude/launch.json` "backend" config, without my `CORS_ORIGINS` override) grabbed port 8000 and silently killed my manually-started one, briefly reintroducing CORS 400s. Cause unclear (possibly the harness's own dev-server management reacting to a tool call). Worth a `.env` default or launch.json env-var support so this stops costing setup time and avoiding surprise process takeovers.
5. Option 2 from the writeup above (clickable `JourneyGuide` stage pills, all six stages) is still on the table as a follow-up whenever you want the same pattern everywhere rather than just this one page — not done here, scope was explicitly option 1 only.

### Worktree / commit hygiene

- `git status --short` before and after matches exactly, except the intended files: [ScheduleForm.tsx](../../frontend/components/contracts/ScheduleForm.tsx), [ImportRowsModal.tsx](../../frontend/components/contracts/ImportRowsModal.tsx), and [extra-items/page.tsx](<../../frontend/app/(app)/contracts/[id]/extra-items/page.tsx>) were already dirty from the pre-existing first-user-help work (edited further, not newly touched); [backend/services/llm.py](../../backend/services/llm.py) and [ExtraItemDecisionList.tsx](../../frontend/components/contracts/ExtraItemDecisionList.tsx) are the two newly-modified files this session.
- No other uncommitted/untracked file from the original list was touched, created, or removed.
- Nothing was committed, amended, or pushed. `backend/.env` (with the real `OPENROUTER_API_KEY`) was restored to its original state and never printed, logged, or moved.
- The one real-data write this session (`NS-1`'s eligibility toggled to "Undecided" and saved, to verify the gate reverts correctly) was explicitly reverted back to its original "No" and re-saved before ending the session — contract `BCT-24-25-252` is left exactly as found.
- No production Supabase data, migrations, or the Ritesh/Banjara demo tenant were touched — all testing was against Saqlain's own local seeded contract.
