# REVIEW.md — Active Review Cycle

Use this file for the current live review state only.

## Canonical Links

- Current project state: [STATUS.md](STATUS.md)
- Coding/review rules: [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Current task board: [TASKS.md](TASKS.md)
- Historical review pointer: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md)

## Active Cycle

**None.** No open review.

## Most Recent Closed Cycle

**P5-REVIEW** — closed 2026-05-20. Adversarial pass by CC-S (Codex-S unavailable) on `saqlain/phase-5` (commits `29352a9` P5-001…P5-008 + `0e3b31f` P5-F1…F5). 14 findings: 1 CRITICAL, 3 HIGH, 6 MEDIUM, 4 LOW. All CRITICAL/HIGH/MEDIUM closed, L-4 closed inline, L-1/L-2/L-3 deferred to TASKS.md (P5-FUP-L1…L3). Pre-existing lint dirt on the branch resolved in the same chain.

Verification on clean Python 3.11 venv built from `backend/pyproject.toml` against the declared dep range floor (`fastapi==0.115.12`, `pytest-asyncio==1.3.0`): **82/82 backend** (up from 67; 15 new regression pins), **99/99 engine**, **16/16 frontend vitest** (new infra: `vitest@2.1.9`), **`next build` clean**, **`npm run lint` clean** (0 errors, 0 warnings).

Headline fixes:
- **C-1**: PEP 563 + `-> None` + 204 → `assert is_body_allowed_for_status_code` at decorator time. Dropped `-> None`; audit confirmed single offender across `backend/api/`.
- **H-1**: `parseTsvImport` extracted to a pure module with strict accept-lists for `is_cement_item` / `steel_subtype`; 12 vitest cases pin behavior.
- **H-2**: `FieldNotNullableProblem` + per-model NOT NULL constants reject explicit-null at the API boundary with structured 422.
- **H-3**: `setError` moved out of render body into `useEffect`.
- **M-3**: `CementSteelConflictProblem` enforced on POST + PUT (PUT uses effective-row merge); client Save All also gates on conflict.
- **M-4**: zod schema emits `null` for cleared nullable optional fields so the Edit form actually clears columns.
- **M-5**: `saveChanges` snapshots `savedKeys` and uses functional `setPending` filter so mid-flight toggles survive.
- **L-4**: UPDATE/DELETE on `contract_items` scoped to `(id, schedule_id)`.

Full per-finding detail (rationale, code references, test pins, audit conclusions) is preserved in git history. Commit chain:

```
3555474 P5-REVIEW lint cleanup: replace set-state-in-effect patterns
259d0cb P5-REVIEW: close findings + sync docs to actual post-remediation state
2a6a05a P5-REVIEW H-3, M-4, M-5: setError as effect + clear-nullable + race-safe save
a74bf1c P5-REVIEW H-2, M-3-backend, M-6, L-4: structured 422s + scoped writes
293b453 P5-REVIEW H-1, M-2, M-3-client: strict TSV parser + Add/Save gates
ab8b29c P5-REVIEW C-1: drop -> None on delete_contract_item
```

To read the full CC Response paragraphs that were appended under each finding, run:

```
git show 259d0cb -- REVIEW.md
```

## Resolution Protocol

1. Open cycles record findings inline with severity (CRITICAL > HIGH > MEDIUM > LOW), file references, and proposed fixes.
2. Each finding closes with a **CC Response** paragraph noting the fix and the test that pins it.
3. CRITICAL and HIGH are blockers per ENGINEERING_GUIDELINES branch hygiene; merge requires zero open in those tiers.
4. MEDIUM and LOW may defer to follow-up tasks in TASKS.md with explicit acceptance criteria.
5. On cycle close, this file collapses to a closure paragraph pointing at the merge SHA + per-finding detail in git history.
