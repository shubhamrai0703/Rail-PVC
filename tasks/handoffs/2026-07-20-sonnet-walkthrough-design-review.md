# Handoff — Feature walkthrough script for the first external user, then the pre-exposure design pass

Owner: Sonnet (interactive session with Saqlain). Date: 2026-07-20. Repo: `/Users/saqlainmomin/railPVC`, branch `main`.

This is a **collaborative session, not autonomous execution**. Saqlain is in the chat; propose, ask, iterate. Two deliverables, in this order:

1. A **feature walkthrough script** Saqlain can use to onboard the first external user — a railway contractor (Saqlain will supply the name; do not write real names or emails into any committed file).
2. The **second design pass** on the outward-facing UI (landing + auth + first-run screens), owed under the two-pass design rule before any outsider sees the app. This comes *after* the walkthrough script is done.

## Goal

**Definition of done:**
- A walkthrough document exists at `tasks/walkthrough-first-user.md`: a step-by-step session script Saqlain can follow while sitting with the contractor, taking an **empty tenant** from signup to a computed PVC statement on one of the contractor's real contracts. Every step names the exact screen/route, what to click, what to say (one plain-language line per concept), and what the contractor should verify against his own manual workbook.
- The design pass is completed and its findings either fixed in-branch (cosmetic, low-risk only) or ticketed in TASKS.md — with Saqlain deciding which, per finding.

## Current state

- **Live production:** frontend on Vercel (`tenderaudit.in`), backend on Railway (`api.tenderaudit.in`), Supabase DB at alembic head **019**. `/` is a public marketing landing page; `/signup` and `/login` use real Supabase auth with email confirmation on.
- **Invite-only provisioning just merged** (PR #23, 2026-07-20): a pre-created `tenant_invites` row keyed on email lets a first login auto-provision the user into a prepared tenant. Non-invited signups get "Authenticated user has no provisioned tenant". Railway deploys from `main`; the hook is live once the post-merge deploy completes.
- **Decision already made — the contractor starts with an EMPTY tenant.** The BCT-24-25-252 demo seed is blocked on a reconciliation finding (DEMO-2 in TASKS.md) and is deliberately **not** part of onboarding. The first session is a guided build of the contractor's own real contract. Do not relitigate this or suggest running `seeds/seed_demo_contract.py`.
- The landing page + auth split-panel redesign (2026-07-19) had its first design pass at build time. The second (final) pass is this session's task 2. No outsider has seen the app yet.
- What the app does: computes Indian Railways **Price Variation Clause (PVC)** adjustments for works contracts — contract → schedules (DSR/NS/ExtraNS) → BOQ items (cement/steel/other buckets) → running bills with measured quantities → engine computes PVC per rolling quarter from RBI/index series → recoveries and carry-forward. Domain truth is in PRODUCT.md.

## Key files (read order)

- `/Users/saqlainmomin/railPVC/PRODUCT.md` — domain model and feature list; the walkthrough's backbone.
- `/Users/saqlainmomin/railPVC/STATUS.md` — current state; skim the Current Phase section only.
- `/Users/saqlainmomin/railPVC/frontend/app/` — route structure = the screens to walk through (`(auth)/`, `contracts/`, nested schedule/item/bill routes).
- `/Users/saqlainmomin/railPVC/tasks/session-log-2026-07-19.md` — landing/auth redesign notes (what pass 1 covered).
- `/Users/saqlainmomin/railPVC/TASKS.md` — where design-pass findings get ticketed (AUDIT-1 section exists for usability items).
- `"RailPVC Smoke Test & Usability Audit.pdf"` (repo root, uncommitted) — a prior usability audit; mine it for known rough edges the walkthrough should route around.

## Task 1 — walkthrough script

Structure it as a ~45–60 min session plan:

1. **Before the meeting (Saqlain solo):** provision the tenant + invite (`PROVISION_TENANT_NAME=... PROVISION_INVITE_EMAIL=... uv run python seeds/provision_tenant.py` — real values from Saqlain at run time, never committed), then a full dry run of the signup → login path with a test email to confirm the just-deployed auth hook works live. Include a rollback note: if the dry run fails, the meeting doesn't happen until it passes.
2. **Signup & first login (contractor's hands on keyboard):** signup, email confirmation, login, landing in the empty tenant.
3. **Guided build of a real contract:** pick one of the contractor's actual contracts *with at least one bill already manually computed* — that manual figure is the acceptance test. Walk: create contract (base month matters — day 1 constraint), schedules, BOQ items, enter a bill's quantities, run the PVC computation, compare against his workbook to the rupee.
4. **The payoff moment:** side-by-side of app output vs his manual workbook. Script what to do if numbers *don't* match (capture inputs, don't debug live, log it as a finding).
5. **Wrap:** what he can do on his own before the next session; what feedback to send.

Keep language non-technical — the audience computes PVC in Excel today. Rehearse the script against the live app (browser) before calling it done; fix any step that doesn't match the real UI.

## Task 2 — design pass (after task 1)

Second and final pass per the two-pass rule: landing page, login/signup split-panel, and the screens the walkthrough exposes (empty states especially — the contractor lands in an empty tenant; an ugly empty `/contracts` is the first thing he sees). Review against the live site, not screenshots from memory. Output: a short findings list; Saqlain triages each as fix-now (cosmetic, low-risk, ship on a branch via normal PR flow) or ticket in TASKS.md. Do not expand scope into logic changes.

## Constraints

- No real names/emails in committed files — placeholders only.
- Do not touch engine code, seeds, or backend logic. Frontend cosmetic fixes only, and only those Saqlain approves.
- Do not run the demo seed or re-open the empty-tenant decision.
- Two-pass rule: this is the final design pass. If a third polish round is proposed later, cite the rule.
- Frontend checks before any commit: `tsc`, `eslint`, `next build`, vitest — all clean.

## Verification

- Walkthrough: every step rehearsed once against live `tenderaudit.in` (or a local run against prod API if auth-gated steps need a provisioned account — coordinate with Saqlain for a test login). No step may reference a control that doesn't exist.
- Design fixes (if any shipped): browser-smoke at desktop + mobile widths, before/after screenshots.

## Report back

Append a `## Results` section to this file: link to the walkthrough doc, dry-run outcome, design findings list with per-item disposition (fixed / ticketed / dropped), and any PR opened.

## Results

Executed 2026-07-20 by a Fable session running autonomously (Saqlain not in chat). Everything executable without him is done; the two things that need his hands or his call are marked ⏳.

### Task 1 — walkthrough script: DONE

**Deliverable: [tasks/walkthrough-first-user.md](../walkthrough-first-user.md).** ~45–60 min session plan in five parts (solo prep → signup/login → guided contract build → workbook comparison → wrap), one plain-language line per concept, placeholders only ([CONTRACTOR] / [INVITE_EMAIL]).

**Load-bearing finding baked into the script — bill lines have no entry UI.** The PVC run does not generate bill lines; it *snapshots* whatever `bill_lines` exist (`persist_run_result`, backend/services/pvc_service.py:599), and cement/steel bucket deductions + extra-item amounts are aggregated *from* those lines (`build_bill_payload`). `POST /api/bills/{id}/lines` exists but nothing in the frontend calls it — the bill page only displays lines. Consequences:

- With no lines, the engine computes W = gross − PVC-affecting recoveries and runs everything through the "other" component — which only matches the contractor's workbook for a bill with **no cement/steel/extra-item deduction rows**.
- The script therefore makes bill selection a prep-time gate (Part A1): pick a bill without those deductions, or pre-enter lines via API (Appendix 1 has the curl shape + the token caveat).
- Two pieces of live UI copy actively mislead here: the PVC card says the run "generates its bill lines" and the empty-lines state says lines "are generated when a PVC run is executed" (`bills/[billId]/page.tsx:233,365`). Listed as design finding D-6 below.
- No TASKS.md ticket exists for bill-line entry UI. **Recommend ticketing it as the top post-session-1 item** — it's the difference between "session 1 works on a carefully chosen bill" and "the app handles his normal bills".
- *Correction at wrap:* the gap is already being addressed — `tasks/handoffs/2026-07-21-codex-bill-line-entry-ui.md` (queued in tasks/todo.md) builds the entry form, and the 2026-07-20 layered-help handoff already removed the inaccurate "run generates lines" copy in the working tree, which covers D-6. The walkthrough's A1 gate stays valid until that branch ships.

**Rehearsal status.** Public flow (landing → Get started → signup form → check-your-email state; login form) rehearsed live on `tenderaudit.in` at desktop + mobile widths — control names in the script match the live UI (fixed two mismatches found while rehearsing: header CTA is "Get started", hero is "Create your account"). Auth-gated steps (contract form, schedules, items grid, bill form, run card, run page, approve/export) were verified control-by-control against current `main` source of every screen, not against the live DOM — ⏳ **no test login existed in this session**. Every named control was confirmed to exist in code; residual risk is cosmetic drift only. Saqlain's A4 dry run (mandatory in the script) doubles as the live rehearsal of the gated path.

**Dry-run outcome: ⏳ not run.** The A3/A4 provisioning + signup dry run needs real emails and Saqlain at the keyboard; the script makes it a hard gate — if A4 fails, the meeting doesn't happen.

### Task 2 — design pass (second and final, per two-pass rule): DONE — findings below, all awaiting Saqlain's per-item triage

Reviewed against the live site (desktop 1600px + mobile 375px): landing `/`, `/login`, `/signup` incl. the check-your-email state; empty states reviewed in source (no authenticated session available). Overall verdict: the outward surface is in good shape — the landing reads professional, the split-panel auth is clean, and the `/contracts` first-landing empty state (icon + "No contracts yet" + CTA) is exactly what the contractor should see first. Nothing found that should block the first session. **No fixes were shipped** — the handoff requires Saqlain's approval per finding, and he wasn't in the chat; every item below is awaiting triage. Recommended dispositions marked.

| # | Finding | Where | Severity | Recommended |
|---|---|---|---|---|
| D-1 | No "Forgot password" link on login — a locked-out contractor has no self-serve path (Supabase reset flow never wired) | `(auth)/login/page.tsx` | High (functional, not cosmetic) | **Ticket** in TASKS.md; needed before/soon after first exposure |
| D-2 | Signup copy doesn't say access is invite-only ("Your team admin may have sent you an invite…"). A non-invited signup succeeds, confirms email, logs in — then hits raw API error "Authenticated user has no provisioned tenant" on /contracts | `(auth)/signup/page.tsx:74`; error surfaced via `services/auth.py:174` | Medium | **Fix-now candidate** (copy only): e.g. "TenderAudit is invite-only right now — sign up with the email your invite was sent to." Friendlier no-tenant error screen → ticket |
| D-3 | "Document Vault" sits in the 3-item sidebar but upload is not wired (P5-006 / AUDIT-1-5) — dead nav item is the kind of thing a first user clicks | `components/shell/nav.ts` | Medium | Saqlain's call: hide until P5-006 (one-line, low-risk) or leave + narrate (walkthrough already routes around it) |
| D-4 | Hero PVC-run card figures are invented (CA-2023-WR-114, ₹6,38,412.00) — flagged at build time; a real contractor may treat them as a reference case | `app/page.tsx` | Low | Swap for anonymized golden-workbook numbers when convenient; not session-blocking |
| D-5 | Landing CTA "Get started free" implies self-serve while signup is invite-gated (overlaps D-2) | `app/page.tsx` (CTA section) | Low | Fix-now candidate alongside D-2, or drop |
| D-6 | Bill-page copy claims the run "generates its bill lines" — false (run snapshots existing lines); will confuse the contractor when no lines appear | `bills/[billId]/page.tsx:233,365` | Medium (copy) | **Fix-now candidate** (wording only), or fold into the bill-line-UI ticket |
| D-7 | Mobile auth pages: form is vertically centered leaving a large dead zone under the compact header (~30% of viewport) | `(auth)/layout.tsx:67` | Cosmetic-minor | Drop, or `justify-start pt-16` on mobile if D-2/D-5 get a fix branch anyway |
| D-8 | Rebate + bid discount entered as decimals (0.05 = 5%) — already ticketed as AUDIT-1-4 (open); walkthrough narrates it twice as mitigation | `ContractForm.tsx`, `ScheduleForm.tsx` | Known | No new action; AUDIT-1-4 stands |

Browser-pane note: full-page desktop screenshots below the landing fold came back blank after programmatic scroll (capture artifact — content verified present and `opacity:1` via DOM inspection + page text; lower sections were also browser-smoked in the 2026-07-19 pass one).

### Ticket/PR state

- **No PR opened, no code changed, nothing committed** — walkthrough doc + this Results section are new/edited files in the working tree.
- TASKS.md untouched (ticketing is Saqlain's triage per the handoff). Suggested new tickets from this session: bill-line entry UI (top priority), D-1 forgot-password, D-2 no-tenant error screen.
- If Saqlain approves the fix-now bundle (D-2 copy + D-5 + D-6, optionally D-3/D-7), it's a single small frontend-copy branch; run tsc/eslint/next build/vitest before commit per constraints, plus desktop+mobile browser smoke.
