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

## Results

### Verdict: **READY**

No release-blocking issues found. The implementation is ready to ship.

---

### Verification commands and outcomes

| Command | Outcome |
|---|---|
| `uv run pytest tests/test_p3_bf_4_documents.py tests/test_p3_08_clean_import.py -v` | **19/19 passed** in 0.92 s |
| `npm test` (frontend) | **92/92 passed** in ~1 s |
| `npm run lint` | **Clean** (no output) |
| `npx tsc --noEmit` | **Clean** (no output) |
| `npm run build` | **Succeeded** — `/documents` route compiled as static, all 15 app routes present |

---

### Findings — ordered by severity

#### No release-blocking findings

#### Low — `assert` at `documents.py:127` silently skips under `-O`

**File:** `backend/api/documents.py:127`

```python
assert row is not None
```

Running Python with `-O` skips `assert` statements. If the INSERT RETURNING returns no row and the bare `assert` is absent, execution reaches `row["id"]` with a `TypeError` instead of the expected `AssertionError`. The outer `except Exception` block still catches it and triggers storage compensation, so no orphaned object is left and the response is still an error — but the log message will be less clear. Not exploitable. Corrective action (optional): replace with `if row is None: raise RuntimeError(...)`.

#### Low — `storage_path` is present in `DocumentRecord` API responses

**File:** `backend/api/documents.py:141–148`, `frontend/lib/api/schema.ts:771–789`

The full Supabase object path (including `tenant_id`, `contract_id`, and UUID) is returned in every document record. Since the bucket is private and downloads require a tenant-gated signed URL, knowing the path alone grants no access. This is an information disclosure only: the path reveals the tenant's Supabase-level identifier to any authenticated user of that tenant. Not a cross-tenant risk. Corrective action (optional): omit `storage_path` from the public API response in a v2 schema.

#### Low — Supabase async client has no reconnection logic

**File:** `backend/services/storage.py:110–122`

`_client_holder` is a `lru_cache`-backed per-process singleton. If the Supabase session expires or the connection drops mid-deployment, all subsequent storage calls fail with `StorageProblem(503)` until the process is restarted. There is no health-check or retry-with-reinit path. This is an operational availability concern, not a security issue; the bucket's secondary 50 MB object limit is unaffected.

#### Coverage gap — no negative IDOR tests for upload and list endpoints

**File:** `backend/tests/test_p3_bf_4_documents.py`

The test file verifies the download endpoint's tenant gate via SQL assertion and verifies the storage compensation path, but does not contain integration-level tests confirming that `POST /api/contracts/{foreign_id}/documents` and `GET /api/contracts/{foreign_id}/documents` return 404 for a contract from a different tenant. The `assert_contract_belongs_to_tenant` function is already well-tested in the broader test suite (it is used across 6+ endpoints), so the absence of document-specific copies is a defense-in-depth gap, not an exploitable hole.

---

### Security properties confirmed

| Attack vector | Mitigation | Verdict |
|---|---|---|
| Cross-tenant upload IDOR | `assert_contract_belongs_to_tenant` gates on `contracts WHERE id = :id AND tenant_id = :tid` before any storage write | ✓ blocked |
| Cross-tenant download IDOR | Download SQL `JOIN contracts ON … WHERE d.id = :did AND c.tenant_id = :tid` — no document accessible without tenant ownership | ✓ blocked |
| Path traversal in filename | `sanitize_filename` strips both POSIX and Windows path components, collapses unsafe chars, strips leading dots, caps at 200 chars; UUID prefix ensures no collision | ✓ blocked |
| Upload size bypass via Content-Length spoofing | Size enforced from actual bytes read in 1 MB chunks; cap check before disk write; Supabase bucket has matching 50 MB object limit | ✓ blocked |
| Service-role key leakage | Key read from `SUPABASE_SERVICE_ROLE_KEY` env at call time; never in API responses or frontend code; `.env.example` documents it as server-only | ✓ contained |
| Signed URL credential exposure | Only the signed URL (60 s TTL, Supabase-issued) is returned; service credentials never reach the browser | ✓ contained |
| MIME spoofing / XSS via content-type | Files are private-bucket, download-only, not served as web content; v1 scope explicitly does not parse uploads | ✓ acceptable for v1 |
| DB/storage divergence on commit failure | Compensation path: `session.rollback()` then `delete_document(storage_path)` with independent exception handling and logging | ✓ handled |
| Temp file leak | `TemporaryFile` used as context manager; deleted on `with`-block exit including exception paths | ✓ handled |
| Multipart boundary erasure | `apiUpload` omits `content-type` header so browser sets the boundary; confirmed by `client.test.ts` | ✓ correct |
| Wrong-contract upload via URL race | Mutation captures `contractId` at submission time; post-success invalidation uses `input.contractId`, not current URL state | ✓ correct |
| SQL injection | All parameters bound via SQLAlchemy `text()` with named params | ✓ clean |

---

### Residual risks / coverage caveats

1. **No authenticated browser smoke test**: an authenticated local session was not available during the previous smoke run. The build passes and all API paths are unit-covered, but the end-to-end upload → download flow in a real browser session has not been re-verified in this session. The live Supabase smoke (prior session) confirmed the path works against the real bucket.

2. **`assert` under `-O`** (see Low finding above) — the only remediation is replacing the bare assert.

3. **Storage client reconnection** (see Low finding above) — a 503 storm after Supabase session expiry would require a process restart to recover. No user data at risk.

4. **IDOR negative tests absent for document endpoints specifically** — acceptable given shared gate function is tested. Adding two test cases for the upload and list endpoints would close this gap in a future diff.
