# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- Active workstream: Phase 3 remediation closure + Phase 4 scaffolding
- Review state: Phase 3 remediation landed; awaiting re-review
- Current branch in repo: `saqlain/phase-3-remediation`

## Current Blockers

- None merge-blocking. Phase 3 remediation has resolved `P3-01…P3-08`. Awaiting Codex-S re-review against the new branch.
- `P3-09` (MEDIUM) was fixed in the same cycle.

## Active Review Cycle

- Active review file: [REVIEW.md](REVIEW.md)
- Cycle: Phase 3 remediation — all findings carry `CC Response` resolution notes
- Next action: Codex-S re-review of `saqlain/phase-3-remediation` against `main`

## Branch State

- Active branch: `saqlain/phase-3-remediation` (branched off `main`)
- Quarantined: `shubham/phase-3` — deleted; do not restore
- Parked: `saqlain/phase-4` — Phase 4 scaffolding, will rebase on top once P3 lands

## What To Read

### If you are implementing fixes

1. [PRODUCT.md](PRODUCT.md)
2. [ARCHITECTURE.md](ARCHITECTURE.md)
3. [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
4. [TASKS.md](TASKS.md)
5. [REVIEW.md](REVIEW.md)
6. [SESSION_LOG.md](SESSION_LOG.md)

### If you are doing adversarial review

1. [PRODUCT.md](PRODUCT.md)
2. [ARCHITECTURE.md](ARCHITECTURE.md)
3. [TASKS.md](TASKS.md)
4. [REVIEW.md](REVIEW.md)
5. [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)

## Current Priorities

1. Codex-S re-reviews `saqlain/phase-3-remediation` against `main` per the P3-REVIEW checklist
2. CC-S rebases `saqlain/phase-4` on top after merge
3. Backfill the remaining Phase 3 endpoints not covered by the remediation pass (schedules, recoveries, documents) only as Phase 4/5 UI needs them

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
