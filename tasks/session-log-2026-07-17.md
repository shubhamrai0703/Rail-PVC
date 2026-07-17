# Session Log — 2026-07-17 (fallback; Obsidian closed — merge into vault 04-logs/sessions/2026-07-17.md later)

## ~17:00 — RailPVC

### Goal
Execute `tasks/handoffs/2026-07-17-fable-parallel-backlog.md`: orchestrate WS-A (audit triage) / WS-B (export parity) / WS-C (base_month CHECK) / WS-D (AG Grid cleanup) via Sonnet subagents, judgment on Fable, while Codex owned KU-001-STC-AVG.

### What Happened
- 3 parallel Sonnet subagents (PDF extraction, workbook/export inventory, AG Grid migration); triage, gap analysis, parity code, and migration stayed on Fable.
- WS-A: audit dated 2026-05-31 — all 3 BLOCKERs already fixed on main. AUDIT-1 table added to TASKS.md; quick wins shipped (gross-amount help note, contracts-list Value ₹ column + backend SELECT).
- WS-B: exports now match submission Bill-sheet order/headers, native number formats, live =SUM total, Quarter in summary; +4 test pins; real-stack smoke on run 8bfc1f40. Gap report + 4 open questions in handoff Results.
- WS-C: migration 017 CHECK on contracts.base_month, applied to live DB (head 017), day≠1 INSERT verified rejected. KU1R-L1 closed.
- WS-D: ItemsGrid → AG Grid v35 rowSelection object API; deprecated options gone repo-wide.
- Shipped: branch `saqlain/parallel-backlog`, 5 commits, PR #19. Backend 171 / frontend 65 vitest + tsc/eslint/build clean.

### Key Decisions
- Audit's "before GST" tooltip wording rejected — unconfirmed domain; used PRODUCT.md W-derivation phrasing instead.
- F4 logo "typo" = icon badge + wordmark → won't-fix. F6 superseded by IDX.
- Proceeded with WS-C despite Codex in flight: nothing landed touching schema and Codex's declared scope excludes migrations.
- Stopped pursuing authenticated browser smoke after two deliberate classifier blocks (session-token injection) + unresponsive Chrome extension — recorded as pending manual check rather than working around.

### Next Actions
- Saqlain: manual look at /contracts (Value column), new-bill form (help note), Items-grid console (zero AG Grid warnings) → closes PR #19's caveat; merge PR #19 (migration 017 already applied to DB).
- Saqlain: KU-001-STC-AVG decision (Codex dropped `2026-07-17-ku001-stc-avg-decision-consult.md` mid-session); AUDIT-1-3 junk-data cleanup; AUDIT-1-4 rebate UX call.
- Investigate hermes-agent WhatsApp bridge auto-respawning on port 3000 if not intentional.
- P8-REVIEW open questions (multi-sheet export, steel sub-lines) when Phase 8 starts.
