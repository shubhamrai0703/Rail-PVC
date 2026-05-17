# ENGINEERING_GUIDELINES.md — RailPVC

Canonical coding and review rules for this repo.

Read this before making non-trivial changes.

## Purpose

RailPVC is a correctness-critical financial system.
The standard is not "make it run" or "make the UI work."
The standard is:

- deterministic financial behavior
- explicit blocking on ambiguous input
- secure trust boundaries
- auditability of every PVC result
- clean-environment operability

## Read Order

For implementation work:

1. [STATUS.md](STATUS.md)
2. [PRODUCT.md](PRODUCT.md)
3. [ARCHITECTURE.md](ARCHITECTURE.md)
4. [TASKS.md](TASKS.md)
5. [REVIEW.md](REVIEW.md)
6. relevant source files

For review work:

1. [STATUS.md](STATUS.md)
2. [PRODUCT.md](PRODUCT.md)
3. [ARCHITECTURE.md](ARCHITECTURE.md)
4. [TASKS.md](TASKS.md)
5. [REVIEW.md](REVIEW.md)
6. relevant source files

## Non-Negotiables

1. No silent financial fallbacks
2. Security over convenience
3. Invalid states should be unrepresentable where possible
4. Auditability is a product feature, not a reporting extra
5. Clean checkout must boot from declared dependencies and documented env vars

## Coding Rules

### Security

- Never commit real secrets, credentials, direct database passwords, or copied production-like tokens.
- `.env.example` files must use placeholders only.
- Do not assume database RLS protects an API path if the backend uses privileged credentials.
- Trust boundaries must be enforced in backend code, not delegated to the frontend.

### Domain Integrity

- If a required classification, index, mapping, or relationship is missing, block explicitly.
- Never allow the frontend to derive financial values the backend or engine should own.
- Any endpoint constructing engine payloads must be checked for parity with a canonical hand-built payload.
- Zone-specific, schedule-specific, and rule-specific branching must be explicit. Weak fallback order is not acceptable when it can silently select the wrong rule.

### Runtime Quality

- No hidden `PYTHONPATH`, editor-specific setup, or one-machine assumptions.
- Startup instructions must work from a clean checkout.
- If packaging is broken, fix packaging. Do not normalize hacks.

### Error Contracts

- Backend error payloads are API contracts.
- If the backend returns structured detail, shared frontend clients must preserve it.
- Blocking errors must be actionable.

### Testing

- Each correctness-critical fix must add or update a test that would have failed before the fix.
- Prioritize tests for:
  - tenant isolation
  - entity ownership validation
  - engine payload construction parity
  - idempotency
  - immutability
  - blocking on ambiguous input

## Review Rules

Every review should check:

1. Can this produce a plausible but wrong PVC number?
2. Can one tenant affect another tenant's data or global reference data?
3. Is the backend trusting the frontend for derived or authoritative values?
4. Can the wrong domain rule be selected silently?
5. Does this work from a clean environment?
6. Is the error contract usable by the UI?
7. Is the fix pinned by tests?

## Branch / PR Hygiene

- Do not merge with open `CRITICAL` or `HIGH` findings in [REVIEW.md](REVIEW.md).
- If a branch is compromised by committed secrets, quarantine it: close the PR, delete the branch, rotate the credentials, and rebuild from a clean branch.
- Log significant review/quarantine decisions in [SESSION_LOG.md](SESSION_LOG.md).

## Related Docs

- Product truth: [PRODUCT.md](PRODUCT.md)
- Technical truth: [ARCHITECTURE.md](ARCHITECTURE.md)
- Current status and branch state: [STATUS.md](STATUS.md)
- Current task board: [TASKS.md](TASKS.md)
- Active review cycle: [REVIEW.md](REVIEW.md)
- Historical session archive: [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
