# CLAUDE.md — Startup Instructions For Implementation Work

This file is intentionally short.

Do not treat it as the full project handbook.
Use it to decide what to read next.

## Role

Claude implements and remediates RailPVC work.

Default expectation:

- read only the minimum relevant canonical docs
- do not re-read long historical files unless the task actually needs them
- do not duplicate project context into new files when a link is enough

## Read Order

### For normal implementation work

1. [STATUS.md](STATUS.md)
2. [PRODUCT.md](PRODUCT.md)
3. [ARCHITECTURE.md](ARCHITECTURE.md)
4. [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
5. [TASKS.md](TASKS.md)
6. [REVIEW.md](REVIEW.md) if the task is tied to an active finding

### For remediation after a failed review

1. [STATUS.md](STATUS.md)
2. [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
3. [TASKS.md](TASKS.md)
4. [REVIEW.md](REVIEW.md)
5. [SESSION_LOG.md](SESSION_LOG.md)
6. relevant source files only

## Boundaries

- Product/domain truth lives in [PRODUCT.md](PRODUCT.md)
- Technical architecture lives in [ARCHITECTURE.md](ARCHITECTURE.md)
- Coding/review rules live in [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Current branch/blocker state lives in [STATUS.md](STATUS.md)
- Current tasks live in [TASKS.md](TASKS.md)
- Active review findings live in [REVIEW.md](REVIEW.md)

## Operating Rule

Do not optimize for "just make it work."
Fix root causes, preserve auditability/security, and add tests that would have caught the failure.
