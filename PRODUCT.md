# PRODUCT.md — RailPVC

## What RailPVC Is

RailPVC is a vertical billing operating system for Indian Railway contractors that automates Price Variation Clause (PVC) calculations under GCC Clause 46A. The platform normalizes a chain of contract documents — agreement, schedules, MB, running bills, recovery sheets, published RBI/JPC indices — into a deterministic, auditable PVC calculation that replaces fragile per-engineer Excel workbooks. Every approved run is immutable, every output number is traceable to its source, and the export matches the submission format Railway field accounts expect.

---

## Core User Personas

| Persona | Role | Primary Pain |
|---|---|---|
| **Billing Engineer** | Primary operator | 4–8 hours per bill on manual transcription, index averaging, carry-forward management. Formula knowledge siloed in one person. |
| **Contractor Principal** | Management / P&L owner | No real-time PVC receivables visibility across the portfolio. Cannot tell if claims are complete or money is being left on the table. |
| **Contract Admin** | Setup & compliance | Manually translates GCC clause 46A into formula configuration. One misread breaks all bills for the contract lifetime. |
| **Accounts Operator** | Recoveries & deductions | Reconciles gross bill, net payable, and PVC base in separate registers. Recovery-to-PVC-eligibility link is opaque. |
| **Reviewer / Approver** | Internal quality gate | Cannot verify formula correctness without opening the spreadsheet. No structured review workflow, no signed approval record. |

---

## MVP Definition

### In Scope

- Contract setup: agreement metadata, LOA, base month, schedules A/B/C (DSR/NS), component weights, GCC clause, PVC applicability
- Manual bill and recovery entry (no PDF/Excel parsing in v1)
- Index master with seeded historical RBI/JPC values (2022–present) + manual monthly entry for new months
- W derivation pipeline: cement bucket, steel buckets (angles / plates / other sections), extra-item eligibility decisions (blocks run if undecided), carry-forward proration across bills
- Component-wise PVC calculation via pure deterministic engine
- Immutable PVC run snapshots — revisions create superseding runs, never overwrites
- Excel-parity export matching current contractor submission format
- PDF print pack for Railway field submission
- Document vault: upload and store PDFs/Excel files (no parsing in v1)
- Single-user per org

### Explicitly Out of Scope for v1

| Feature | Reason |
|---|---|
| PDF/Excel document parsing | Phase 2 — OCR confidence on scanned Railway docs is insufficient for financial accuracy without human review |
| Multi-user RBAC (3 roles) | **Immediate post-MVP priority** — add before first external beta |
| Offline PWA + sync engine | Phase 3 |
| Zone-specific rule template library | Phase 2/3 |
| Portfolio analytics dashboard | Phase 3 |
| AI-assisted clause extraction | Phase 4 |
| ERP / Tally integrations | Phase 4 |
| Railway-side collaboration portal | Phase 4 |
| Retroactive index revision alerting | Phase 2 |
| Provisional calculation mode | Phase 2 |

---

## 3 Non-Negotiable Correctness Requirements

### 1. W Derivation Must Be Explicit

W is not the gross bill amount. Every subtraction is a named, confirmed step:

```
W = OnAccountBill
  − CementAmount
  − SteelAnglesAmount
  − SteelPlatesAmount
  − SteelOtherAmount
  − TechnicalWithheld
  − ExcludedExtraItems
```

If any required eligibility decision is missing (extra-item not yet classified as in/out, cement or steel bucket not configured), the PVC run must **block** with an explicit error. No silent defaults. No calculation with assumed values.

### 2. Quarter Mapping: Rolling From Contract Base Month (confirmed 2026-07-15)

Quarters are **rolling, not calendar**, anchored to the contract's `base_month` (input by the contractor at contract creation). Quarter 1 is the three months immediately after the base month; Quarter N continues in three-month windows for the life of the contract (including extensions), labelled with plain ordinals (`Q1`, `Q2`, ... unbounded). The quarter is determined by the **bill's measurement date** — the window containing it — and the index average is `(index_M-2 + index_M-1 + index_M) / 3` over that window.

Confirmed by a Western Railway field contact ("rolling quarter, start date will be input by contractor") and independently verified against five real GCC-April-2022 PVC workbooks. This falsified the earlier KU-001 assumption of fixed calendar quarters with FY labels (e.g. `Q2-FY2025-26`) — two of the five confirming contracts happened to have December base months, making rolling and calendar windows coincide, which is what let the wrong convention pass an earlier domain check. See `tasks/handoffs/2026-07-15-ccs-quarter-convention.md` and `tasks/handoffs/2026-07-16-sol-quarter-rolling-fix.md` for evidence and implementation. The approved quarter is stored as an immutable field on every PVC run — it cannot be re-derived post-hoc.

### 3. Approved PVC Runs Are Immutable

Once a PVC run is approved:
- It cannot be modified
- Revisions create a new superseding run linked to the original
- The original run persists with its original values, index snapshot, rule snapshot, and operator record
- This is not optional for MVP and not configurable
