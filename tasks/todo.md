# C-3 — Bill header edit + recovery delete + computed net_amount

Branch: `saqlain/p6-review` (continues from P6-REVIEW). TDD per item.

## Decision log
- **net_amount formula = gross − Σ(recoveries WHERE affects_pvc_base=FALSE)** (Saqlain 2026-06-08,
  option 1). FLAGGED for revisit — PVC-affecting recoveries treated as notional (reduce W via H1,
  not net payable). If field reconciliation disagrees, switch to "net of ALL recoveries". Track as
  `C-3-FUP-NET`. Computed server-side on read (backend owns derived financial values).

## Backend
- [x] B1. `_NET_AMOUNT_EXPR` SQL constant in bills.py; use in GET list, GET detail, PUT-return SELECT.
- [x] B2. `PUT /api/bills/{id}` — `BillUpdate` partial (model_fields_set). Tenant gate. Reject explicit
      null on NOT NULL (bill_number, measurement_date); reject bill_number<=0 / gross_amount<=0/null;
      409 on UNIQUE(contract_id, bill_number); empty body → current row. Returns computed net.
- [x] B3. `DELETE /api/bills/{id}/recoveries/{rid}` — `_assert_recovery_under_bill_for_tenant`
      two-step gate; 204; scope DELETE to (id, bill_id).
- [x] B4. Route count 40 → 42; bump `test_p3_08` assertion.

## Backend tests
- [x] T1. PUT: valid update, empty-body noop, wrong-tenant 404, dup bill_number 409,
      bill_number<=0 422, gross_amount<=0 422, null measurement_date FieldNotNullable.
- [x] T2. DELETE: valid, wrong-tenant 404, recovery-not-under-bill 404.
- [x] T3. net_amount formula via aiosqlite running the exported `_NET_AMOUNT_EXPR`
      (gross 100000, FALSE recovery 10000, TRUE recovery 5000 → net 90000).

## Frontend
- [x] F1. Bill header inline edit (Edit→form→PUT, 409 inline, invalidate `bill`).
- [x] F2. Recovery delete button per row (confirm → DELETE → invalidate recoveries + bill).
- [x] F3. net_amount label note ("net of non-PVC recoveries"); shows computed value.

## Verify + ship
- [x] V1. backend pytest, engine, vitest, tsc, eslint all green.
- [x] V2. Update REVIEW/STATUS/TASKS/SESSION_LOG + vault. Commit. Push branch.
