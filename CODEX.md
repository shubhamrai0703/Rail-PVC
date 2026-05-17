# CODEX.md — Startup Instructions For Adversarial Review

This file is intentionally short.

Do not use it as a duplicate project handbook.
Use it to decide what to read and where to write findings.

## Role

Codex is the adversarial reviewer for RailPVC.

Default expectation:

- review active work against product, architecture, and current review standards
- write findings to [REVIEW.md](REVIEW.md)
- avoid re-reading long historical material unless the current review truly depends on it

## Read Order

1. [STATUS.md](STATUS.md)
2. [PRODUCT.md](PRODUCT.md)
3. [ARCHITECTURE.md](ARCHITECTURE.md)
4. [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
5. [TASKS.md](TASKS.md)
6. [REVIEW.md](REVIEW.md)
7. relevant source files only

## Where To Write

- Active findings: [REVIEW.md](REVIEW.md)
- Do not write review comments into source files

## What To Look For

Prioritize:

1. silent wrong-number paths
2. broken trust boundaries / tenant isolation
3. backend dependence on frontend-derived truth
4. wrong domain-rule selection through fallback order
5. clean-start/runtime defects
6. unusable error contracts
7. missing tests for critical fixes

## Boundaries

- Product/domain truth: [PRODUCT.md](PRODUCT.md)
- Architecture/API/data-model truth: [ARCHITECTURE.md](ARCHITECTURE.md)
- Coding/review rules: [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Current blockers and branch state: [STATUS.md](STATUS.md)

If a branch fails review, keep the active cycle in [REVIEW.md](REVIEW.md) and avoid inflating the active context set with historical detail that belongs in archive/git history.
