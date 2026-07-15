# Session Log — 2026-07-15 (fallback; Obsidian closed — port into vault on next compile)

## RailPVC — PVC golden-data review, KU-001 falsification, engine reconciliation

### Goal
Assess the real Banjara PVC data (WhatsApp rar → `railPVC/PVC/`) for workflow testing, verify cc-sh's review of it, and extract maximum value before blocking on the railway contact's quarter-convention answer.

### What Happened
- Decoded all five contract workbooks (COP/STC, BCT-24-25-252, BCT-24-25-183, BCT-23-24-296, JRH) — not one contract as cc-sh reported; ~14 bills of golden reference data.
- **Falsified KU-001**: all five workbooks use rolling quarters from base month. KU-001's "calendar quarters" was confirmed on 252, whose Dec-24 base makes the two conventions coincide. 296 (Q1=Mar–May-24) and COP (Q3=Feb–Apr-24) disambiguate.
- **Reconciled engine vs COP workbook** (bypassing quarter resolution): Bill 1 Δ₹0.01, Bill 2 Δ₹0.12 — component math verified correct. Bills 3–4 divergences fully explained as workbook double-counts (Bill 3: TMT in both general W and its bucket, +₹3,262.48; Bill 4: SS-plate/MS-tubes in W and in steel-other bucket, hybrid total −130259.32 vs consistent −60034.59/−156249.28).
- Split remaining work: Codex Sol 5.6 → fixture extraction + xfail tests (`tasks/handoffs/2026-07-15-pvc-golden-fixtures.md`, incl. reconciliation addendum); CC-S → quarter.py redesign brief (`tasks/handoffs/2026-07-15-ccs-quarter-convention.md`).
- Housekeeping: `PVC/` gitignored, `~$` Excel lock files deleted, auto-memory updated (KU-001 flagged likely wrong; new pvc-golden-workbooks memory).

### Key Decisions
- Workbook FINAL indices as fixture ground truth; `negative_pvc_policy="allow"` for these contracts (workbooks carry raw negatives — KU-003 zero-floor default also challenged).
- Workbook totals stay as `expected.total_pvc` even where the workbook is wrong, with `workbook_divergence` notes — the engine's refusal to double-count is correct behaviour, not a bug.
- quarter.py fix deferred to CC-S, blocked on Saqlain's contact confirming rolling-from-base is the only Apr-2022-GCC convention.

### Next Actions
- Saqlain: ask contact (a) rolling-from-base only, or do calendar-quarter contracts exist? (b) were the Bill 3/4 double-counts intentional practice or error?
- Check Sol's Results section in the fixtures handoff; verify 183 actually passes (predicted, unverified).
- After contact's answer: CC-S implements quarter fix; xfail fixtures flipping green = acceptance test.
- Investigate 252 plant-index anomaly (~160 vs ~89 in other workbooks) before using 252 for reconciliation.
