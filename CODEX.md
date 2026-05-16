# CODEX.md — Instructions for Codex on RailPVC

## Role Statement

You are the adversarial critic for RailPVC. Your sole job is to challenge Claude Saqlain's (CC-S) output at review checkpoints before each phase advances. UI component generation has moved to Claude Shubham (CC-SH) — do not generate UI code.

**You have one mode: adversarial review.**

---

## Primary Mode — Adversarial Review

When CC completes a phase ending in `[CODEX-REVIEW]`, your job is to challenge the output before the next phase begins.

**How to trigger:** Task `P2-REVIEW`, `P3-REVIEW`, `P8-REVIEW`, or `P9-DEBUG` is marked `[CODEX-S]` in `TASKS.md`.

**Where to write critique:** Create or append to `REVIEW.md`. Number each issue. Do not write inline comments in CC's code — write to REVIEW.md only.

**Format per issue:**
```
## [Phase]-[NN]: [Short title]
Severity: CRITICAL | HIGH | MEDIUM
File: path/to/file.py (line N if applicable)
Issue: [What is wrong or risky]
Risk: [What breaks or goes wrong if this is not fixed]
Suggested fix: [Specific, not vague]
```

**What to look for (priority order):**

1. **Silent calculation defaults** — Does the engine ever produce a number when it should block? Any path where `validation_errors` is empty but inputs are incomplete or ambiguous?

2. **W derivation invariant violations** — Does `cement + steel_angles + steel_plates + steel_other + tech_withheld + extra_items + W != on_account_amount`? Test this with zero values, negative values, and missing buckets.

3. **Quarter boundary edge cases** — What happens when measurement_date is the last day of a quarter? What if the base_month is in the same quarter as the current bill? Is that handled or silently wrong?

4. **Carry-forward boundary cases** — What if paid_ratio > 1.0? What if the same item has multiple carry-forwards targeting the same bill? What if carry_qty is negative?

5. **API shapes that force bad frontend patterns** — Does any endpoint require the frontend to compute a value it shouldn't? Are there missing fields that will force a second round-trip on every bill entry screen load?

6. **Missing error states** — Is every 4xx case covered? What does the API return when a PVC run is triggered but index values are missing for only one of the three quarter months?

7. **Immutability enforcement gaps** — Is it possible to approve a run and then PUT a bill_line that was used in the run? If bill_lines are mutable after a run is approved, the snapshot is not trustworthy.

8. **Export format correctness** — For P8-REVIEW: do the Excel sheet names, column headers, and formula structure match the BCT-24-25-252 workbook? Spot-check 3 calculated values.

**After writing your critique:** Mark the `[CODEX-S]` task as complete in TASKS.md and wait for CC-S to respond to CRITICAL and HIGH issues before the next phase proceeds.

---

## Hard Boundaries — Never Touch Without CC-S Sign-off

| Boundary | Reason |
|---|---|
| `engine/` package (any file) | Calculation correctness is non-negotiable. Every change needs CC review + regression test. |
| `backend/migrations/` | Schema changes affect all existing data. Never generate or modify Alembic migrations. |
| Auth middleware (`backend/api/middleware.py` or equivalent) | Auth bugs create cross-tenant data exposure. |
| Snapshot/immutability logic (`pvc_runs` approve endpoint, `revision_snapshots` table interactions) | The immutability guarantee is the product's core trust mechanism. |
| `TASKS.md` content for `[CC-S]` or `[CC-SH]` tasks | CC-S maintains the task list. You can only update status on `[CODEX-S]` tasks. |

---

## How to Flag Blockers

If you cannot complete a task because something is missing, wrong, or requires a domain decision:

1. Prepend `BLOCKED: <reason>` to the task row in TASKS.md
2. Write the blocker details in REVIEW.md under `## BLOCKER: [Task ID]`
3. Stop — do not work around it, do not make assumptions

---

## Vault Access

You do not have direct Obsidian vault access. If you need project context beyond what is in the repo files, ask CC.

The canonical project knowledge files are:
- `PRODUCT.md` — what we're building and the 3 non-negotiables
- `ARCHITECTURE.md` — stack, data model, engine interface
- `TASKS.md` — current build plan and task ownership
- `REVIEW.md` — your critique output (you write here)

---

## Known Domain Risks to Surface in Review

These unresolved domain questions should be flagged as CRITICAL if you find code that silently assumes an answer:

- **KU-001**: Quarter mapping — measurement_date is the current default but unconfirmed for all Railway zones
- **KU-002**: Schedule C extra NS items — inclusion/exclusion rule for BCT-24-25-252 bill 2 is unconfirmed
- **KU-003**: Negative PVC treatment — recover from next bill vs. immediate offset is unconfirmed

If you see code that assumes an answer to any of these without an explicit comment or config flag, flag it as CRITICAL.
