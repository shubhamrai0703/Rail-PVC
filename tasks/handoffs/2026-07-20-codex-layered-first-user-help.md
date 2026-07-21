# Handoff — Implement layered first-user help before the contractor demo

## Goal

Implement the requirements in `docs/plans/2026-07-20-001-feat-layered-first-user-help-plan.md` so a contractor principal who currently runs PVC manually in Excel can understand TenderAudit's contract-to-PVC workflow and complete the first real-contract demo with no help or only occasional clarification. Definition of done: the three protected moments have consistent layered guidance, the six-stage journey is visible on relevant screens, all critical copy is accurate and accessible, regression checks pass, and the full journey is browser-smoked at desktop and mobile widths.

## Current state

- Repo: `/Users/saqlainmomin/railPVC`.
- Current branch at handoff creation: `codex/tenant-demo-provisioning-results` tracking `origin/codex/tenant-demo-provisioning-results`.
- The worktree is already dirty with user-owned and other-session files. Run `git status --short --branch` first, preserve unrelated changes, and do not clean, reset, or overwrite them.
- The requirements-only Product Contract is complete at `/Users/saqlainmomin/railPVC/docs/plans/2026-07-20-001-feat-layered-first-user-help-plan.md`.
- The first-user session script already exists at `/Users/saqlainmomin/railPVC/tasks/walkthrough-first-user.md`. It identifies the real demo path and a load-bearing limitation: the UI cannot currently enter bill lines, so help must not imply that a PVC run creates them.
- Existing guidance is scattered: native grid-header tooltips, individual form notes, empty-state copy, and engine validation messages. There is no app-wide help surface or persisted onboarding-completion state.
- The Excel importer already supports upload or paste, sheet/header selection, column mapping, validation, preview, and commit. Extend its comprehension without replacing its working behavior.
- No contractor has completed a live demo yet. This is a deliberately small, preemptive slice; the demo will supply evidence for later iterations.

## Product decisions already made

- Use **layered contextual help**, not a forced tour and not a permanent side-by-side Excel companion.
- Limit pre-demo coverage to three moments:
  1. Contract and schedule setup.
  2. Excel item import plus cement, steel, NS, and ExtraNS classification.
  3. Bill entry, PVC calculation, result review, approval, and export.
- Treat the user as a PVC expert who is new to TenderAudit. Explain product structure, field mapping, and action consequences; do not teach basic PVC.
- Show calculation-critical facts inline. Use tooltips or expandable help only for supplementary detail.
- Do not add onboarding persistence, completion flags, analytics, a help centre, videos, or chatbot behavior.
- Do not expand help to login, Index Manager, Document Vault, or unrelated admin screens in this slice.

## Implementation shape

Use existing frontend conventions and make the smallest coherent system that satisfies the Product Contract.

1. Add a reusable six-stage journey guide for relevant contract, item, bill, and run screens: Contract → Items → NS decisions → Bill → Calculate → Review. It must identify the current stage without inventing persisted completion state or falsely marking work complete.
2. Establish one reusable visual/content pattern for page-level explanations and one accessible pattern for supplementary field help. Critical guidance must remain visible without hover.
3. Add contract and schedule guidance for base month, PVC applicability, schedule type, overall rebate, and bid discount. Make the decimal input convention unmistakable without changing stored values or backend contracts.
4. Make the Excel import progression visible and explain ambiguous mappings with selective Excel vocabulary. Preserve upload, paste, saved templates, auto-mapping, validation, and commit behavior.
5. Explain cement, steel subtype, NS, ExtraNS, and extra-item relevance where those choices occur. Existing conflict and blocking states must tell the user what to correct and why.
6. Add bill/run guidance for measurement date, gross amount, `Affects PVC base`, calculation prerequisites, blocking errors, result interpretation, approval immutability, and export gating.
7. Correct the two current bill-line claims that say a PVC run generates bill lines. The UI must describe the real behavior and must not conceal that line entry is not available in the current interface.
8. Add focused tests for any shared state/route mapping or content behavior introduced. Avoid snapshot-heavy tests that only pin markup.
9. Perform the build-time design pass, then one final browser pass before reporting. Keep the result visually restrained and consistent with the existing product.

## Key files

- `/Users/saqlainmomin/railPVC/AGENTS.md` — project read order and operating rules.
- `/Users/saqlainmomin/railPVC/STATUS.md` — current branch, live product, and blockers.
- `/Users/saqlainmomin/railPVC/PRODUCT.md` — domain authority and correctness constraints.
- `/Users/saqlainmomin/railPVC/ARCHITECTURE.md` — current frontend/backend boundaries.
- `/Users/saqlainmomin/railPVC/ENGINEERING_GUIDELINES.md` — implementation and review rules.
- `/Users/saqlainmomin/railPVC/docs/plans/2026-07-20-001-feat-layered-first-user-help-plan.md` — canonical requirements and acceptance examples.
- `/Users/saqlainmomin/railPVC/tasks/walkthrough-first-user.md` — exact first-demo journey and known rough edges.
- `/Users/saqlainmomin/railPVC/frontend/components/contracts/ContractForm.tsx` — contract fields and current rebate convention.
- `/Users/saqlainmomin/railPVC/frontend/components/contracts/ScheduleForm.tsx` — schedule type and bid-discount fields.
- `/Users/saqlainmomin/railPVC/frontend/components/contracts/ItemsGrid.tsx` — existing field tooltips, classifications, conflict state, and importer entry point.
- `/Users/saqlainmomin/railPVC/frontend/components/contracts/ImportRowsModal.tsx` — multi-step Excel import workflow.
- `/Users/saqlainmomin/railPVC/frontend/app/(app)/contracts/[id]/extra-items/page.tsx` — ExtraNS relevance decisions.
- `/Users/saqlainmomin/railPVC/frontend/components/contracts/BillForm.tsx` — measurement date and gross-amount entry.
- `/Users/saqlainmomin/railPVC/frontend/components/contracts/BillHeaderForm.tsx` — existing-bill editing guidance.
- `/Users/saqlainmomin/railPVC/frontend/components/contracts/RecoveryForm.tsx` — `Affects PVC base` decision.
- `/Users/saqlainmomin/railPVC/frontend/app/(app)/contracts/[id]/page.tsx` — contract Overview, Schedules, and Items shell.
- `/Users/saqlainmomin/railPVC/frontend/app/(app)/contracts/[id]/bills/page.tsx` — contract bill list/create surface.
- `/Users/saqlainmomin/railPVC/frontend/app/(app)/contracts/[id]/bills/[billId]/page.tsx` — Calculate PVC card, actionable errors, and inaccurate bill-line copy.
- `/Users/saqlainmomin/railPVC/frontend/app/(app)/contracts/[id]/bills/[billId]/runs/[runId]/page.tsx` — results, approval, and export surface.

## Constraints

- Do not change the PVC engine, formulas, indices, migrations, backend contracts, tenant provisioning, approval semantics, or export rules.
- Do not implement the missing bill-line entry feature under this help ticket. Describe the limitation accurately and leave capability work to a separate product decision.
- Do not add a new dependency unless the existing component primitives cannot satisfy an accessibility requirement; prefer no dependency.
- Do not use native `title` alone for essential information. Help triggers must be keyboard-operable and screen-reader-labelled.
- Do not overwhelm every field with an icon. Prioritize fields whose misunderstanding changes a calculation, classification, or next step.
- Preserve all current import validation and no-partial-commit behavior.
- Preserve user-owned worktree changes. Touch only files needed for this feature and remove only artifacts created by this implementation.
- Do not commit, push, deploy, or open a PR unless the user separately authorizes it.
- Do not put real contractor names, emails, workbook values, or credentials into source, tests, screenshots, or this handoff.

## Verification

Run from `/Users/saqlainmomin/railPVC/frontend` and record exact results:

```bash
npx tsc --noEmit
npm run lint
npm test
npm run build
```

Then browser-smoke the implementation with representative authenticated data at desktop and mobile widths:

1. Empty tenant/new contract: confirm journey stage, page explanation, base-month help, PVC applicability, and rebate convention.
2. Contract detail/schedule: confirm schedule-type and bid-discount guidance without obstructing entry.
3. Items: confirm supplemental field help is keyboard-accessible and critical classification consequences remain visible.
4. Excel upload and paste paths: confirm source → sheet/header → mapping → preview/commit guidance, saved templates, validation, and existing import behavior.
5. Cement/steel conflict and undecided extra item: confirm the affected decision and corrective action are understandable.
6. Bill create/edit/recovery: confirm measurement-date, gross-amount, and PVC-base guidance.
7. Calculate PVC: confirm both a blocking-error state and a successful result state; verify no copy claims that the run creates bill-line inputs.
8. Run result: confirm total, quarter, W derivation, approval consequence, and export gate guidance.
9. Confirm no console errors, no new horizontal overflow, usable keyboard focus, and readable mobile reflow.

The feature is not done on static inspection alone. If authenticated browser access is unavailable, exhaust safe local/mock paths and document the exact remaining smoke-test blocker rather than claiming full completion.

## Report back

Append a `## Results` section to this same file. Include:

- files changed and the guidance behavior added;
- any requirement or acceptance example not fully satisfied;
- exact typecheck, lint, test, and build results;
- browser-smoke evidence per protected moment at desktop and mobile widths;
- remaining product gaps discovered but not fixed;
- confirmation that no unrelated worktree files were changed and no commit/push/deploy occurred.

## Results

Implementation is complete and all non-browser quality gates are green. The
desktop/mobile browser gate remains open because this Codex session exposed no
browser backend (`agent.browsers.list()` returned `[]`); no visual smoke result
is claimed.

### Implemented

- Added a reusable six-stage journey guide, page-level guidance card, numbered
  workflow guide, native `<details>` supplementary help, and Excel field guide.
- Added contextual guidance across contract/schedule setup, item import and
  classification, ExtraNS decisions, bill/recovery entry, calculation errors,
  result review, approval, and export gating.
- Replaced the inaccurate bill-line-generation claims with an explicit statement
  that bill lines must already exist and are not currently editable in the UI.
- Formal review found and resolved three actionable findings: Total PVC guidance
  now includes prior negative carry-forward and the configured negative-PVC
  policy; PVC applicability and overall rebate copy no longer promises
  enforcement the calculator does not perform; five server-rendered component
  tests now pin stage order, `aria-current`, conditional next-step content,
  disclosure semantics, and Excel vocabulary.
- A follow-up responsive/accessibility code pass resolved four additional
  findings: the new-contract page now uses the same truthful contract guidance;
  the import dialog focuses on open, closes on Escape, traps Tab focus, and
  restores prior focus; the ExtraNS run blocker is visible whenever that
  schedule type is selected; and long journey-stage labels wrap instead of
  truncating.

### Verification

- Proof-first check: the focused test run failed before the corrected guidance
  exports existed and before the component import could render under Vitest.
- Focused tests after the fix: 8/8 passed across `firstUserHelp.test.ts` and
  `FirstUserHelp.test.tsx`.
- `npx tsc --noEmit`: passed.
- `npm run lint`: passed with zero warnings/errors.
- `npm test -- --run`: 76/76 passed across 12 files.
- `npm run build`: passed; 11/11 static pages generated. The sandboxed attempt
  failed only on Google Fonts network access, then the permitted network run
  compiled successfully.
- `git diff --check`: passed.
- Formal review artifact:
  `/tmp/compound-engineering-501/ce-code-review/20260720-214331-f3583ec5/review.json`.
  Correctness, project-standards, testing, and maintainability reviewers ran;
  all three retained findings passed independent validation. The configured
  Claude Opus cross-model adversarial pass could not authenticate and produced
  no usable output, so that lens is recorded as degraded rather than complete.

### Browser gate still open

- Attempted the required local frontend/backend stack on ports 3002/8000.
- Browser setup completed, but no in-app or Chrome backend was available to the
  session. Per the browser-control contract, no unrelated automation surface was
  substituted.
- Therefore there is no desktop/mobile evidence yet for contract/schedule,
  import/classification, or bill/calculate/result screens; console, focus, and
  overflow checks remain pending. In particular, the new import-dialog keyboard
  behavior is code-reviewed and type/test clean but still needs real-browser
  confirmation.

### Remaining gaps and scope

- Recovery actions still classify free-text engine messages. Stable typed issue
  codes would remove wording drift, but require an intentionally separate
  engine/API contract change and are outside this help-only ticket.
- Missing-index recovery links lead to an admin-gated editor; non-admin handoff
  wording should be evaluated during the browser pass.
- No unrelated worktree files were edited. No commit, push, deploy, migration,
  backend contract, or calculation behavior change was made.
