# Claude Adversarial Review — Document Vault

## Goal

Perform a report-only adversarial review of the completed Document Vault implementation. Determine whether the feature is safe and production-ready as implemented; do not modify source code. Append findings and a final **READY** or **NOT READY** verdict to `## Results` in this file.

## Current state

- Branch: `codex/tenant-demo-provisioning-results`
- The former pending/placeholder screen has been replaced with a contract-scoped document vault that supports upload, list, and signed-URL download.
- The backend now validates document metadata with typed models, enforces a 50 MB limit, streams uploads through a disk-backed temporary file, stores objects under tenant-scoped paths, and removes uploaded objects if the database write fails.
- Downloads use a tenant-gated API endpoint that returns a short-lived signed URL; the browser never receives server credentials.
- The live Supabase project has a private `documents` bucket with a 50 MB object limit. A reversible live smoke test completed upload, signed download, delete, and cleanup successfully, leaving no test object behind.
- Automated verification currently passes: backend `210 passed`, frontend `92 passed`, ESLint clean, TypeScript clean, and the production frontend build succeeds.
- Browser smoke on localhost reached the expected `/login` redirect, but an authenticated local browser session was not available. Treat this as a coverage caveat, not evidence of an application failure.
- The worktree also contains unrelated pre-existing changes. Review only the files listed below and do not stage, revert, or edit anything.

## Key files

- `/Users/saqlainmomin/railPVC/backend/api/documents.py` — authenticated upload, list, and signed-download endpoints.
- `/Users/saqlainmomin/railPVC/backend/services/storage.py` — Supabase Storage operations, limits, temporary-file handling, cleanup, and signed URLs.
- `/Users/saqlainmomin/railPVC/backend/tests/test_p3_bf_4_documents.py` — document API security and behavior coverage.
- `/Users/saqlainmomin/railPVC/backend/tests/test_p3_08_clean_import.py` — route-count regression update.
- `/Users/saqlainmomin/railPVC/backend/.env.example` — non-secret storage configuration examples.
- `/Users/saqlainmomin/railPVC/frontend/app/(app)/documents/page.tsx` — URL-selected contract state and query orchestration.
- `/Users/saqlainmomin/railPVC/frontend/components/documents/DocumentVault.tsx` — contract picker, upload, list, download, and user feedback UI.
- `/Users/saqlainmomin/railPVC/frontend/app/(app)/contracts/[id]/page.tsx` — navigation into the vault with a selected contract.
- `/Users/saqlainmomin/railPVC/frontend/lib/api/client.ts` — authenticated multipart request support.
- `/Users/saqlainmomin/railPVC/frontend/lib/api/client.test.ts` — multipart client regression tests.
- `/Users/saqlainmomin/railPVC/frontend/lib/api/schema.ts` — document response types.
- `/Users/saqlainmomin/railPVC/frontend/lib/documents.ts` — document formatting and validation helpers.
- `/Users/saqlainmomin/railPVC/frontend/lib/documents.test.ts` — helper boundary tests.
- `/Users/saqlainmomin/railPVC/frontend/app/(app)/documents/page.tsx` and `/Users/saqlainmomin/railPVC/TASKS.md` — feature status and product-facing completion notes.
- `/Users/saqlainmomin/railPVC/tasks/walkthrough-first-user.md` — updated first-user walkthrough.

## Constraints

- This is an adversarial review, not an implementation task. Do not edit code or configuration.
- Do not expose, copy, or report credentials. Server-side service-role credentials must remain server-only.
- Inspect the exact working-tree diff for the key files; do not include unrelated modified or untracked files in the review scope.
- Look specifically for cross-tenant access, IDOR, unsafe object paths, public-bucket assumptions, signed-URL leakage or excessive lifetime, spoofed MIME/filename behavior, upload-size bypasses, temporary-file leaks, database/storage divergence, incomplete rollback, multipart boundary mistakes, stale query invalidation, wrong-contract uploads, URL/state races, schema drift, and missing negative tests.
- Verify that storage operations consistently use tenant ownership established by authenticated database access rather than trusting tenant or contract identifiers from the browser.
- Treat any exploitable security or data-integrity defect as release-blocking. Separate confirmed findings from optional hardening or style suggestions.

## Verification

Run the relevant checks if the environment permits:

- `uv run pytest tests/test_p3_bf_4_documents.py tests/test_p3_08_clean_import.py` from `/Users/saqlainmomin/railPVC/backend`
- `npm test` from `/Users/saqlainmomin/railPVC/frontend`
- `npm run lint` from `/Users/saqlainmomin/railPVC/frontend`
- `npx tsc --noEmit` from `/Users/saqlainmomin/railPVC/frontend`
- `npm run build` from `/Users/saqlainmomin/railPVC/frontend`

Do not repeat live Supabase writes unless necessary. If you do, use a reversible test object and prove cleanup.

## Report back

Append a `## Results` section below containing:

1. Verdict: **READY** or **NOT READY**.
2. Findings ordered by severity, with exact file and line references.
3. Verification commands run and their outcomes.
4. Residual risks or coverage caveats.

If no actionable findings remain, explicitly state that the reviewed implementation is ready to ship. If any release-blocking issue exists, use **NOT READY** and explain the smallest corrective action required.
