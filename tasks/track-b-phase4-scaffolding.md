# Track B — Phase 4 Scaffolding (Fresh Window Prompt)

**Date prepared:** 2026-05-16 (Session 4)
**For:** Next CC-S window, fresh context
**Estimated effort:** 45–90 min
**Branch:** `saqlain/phase-4` (create from `main`)

---

## Paste this prompt into a fresh Claude Code window

> I'm working on RailPVC. Read these in order before doing anything else:
>
> 1. `CLAUDE.md` (project root)
> 2. `SESSION_LOG.md` — especially "Session 4 — 2026-05-16" at the bottom (parallel-track session that just closed P2-06)
> 3. `TASKS.md` — Phase 4 section (P4-001 through P4-006)
> 4. `ARCHITECTURE.md` — frontend stack + API surface
> 5. Vault: search Obsidian for `RailPVC` and read `01-projects/RailPVC.md` for current state
>
> **What I want to do this session:** Phase 4 scaffolding while Shubham continues `shubham/phase-3` in parallel. Specifically:
>
> - **P4-003** — App shell (sidebar nav: Contracts / Index Manager / Document Vault; header; layout wrapper)
> - **P4-005** — Error boundary + global error handling (toast for API errors, friendly fallback for unhandled)
> - **P4-006 (base)** — TanStack Query provider setup + `openapi-typescript` config so types regenerate from Shubham's FastAPI OpenAPI schema the moment it's available
>
> **Hard boundaries — do not touch:**
> - `backend/api/` — Shubham's Phase 3 surface
> - `engine/`, `backend/migrations/`, auth middleware, snapshot/immutability code
> - Anything Shubham would conflict with on merge
>
> **Design quality is the brief, not an afterthought.** Excel was the last tool users had for this — the bar is "polished and modern, not dated and boring." Field operators recognise grid-based workflows; we want to honour that recognition while making the product feel like 2026 software, not 2010 software. Specifically:
>
> - **Excel-style formula bar** — explore where this pattern fits beyond just the BillLine grid (Phase 6). For Phase 4, think about whether the app shell needs a persistent "current run context" bar; whether numeric input cells in the shell-level toasts (e.g., "Approved run #14 — total ₹76,959.55") deserve mono treatment; whether keyboard shortcuts (Ctrl+K command palette?) belong in the shell.
> - **Numeric cells / formula display** — wherever a Decimal renders, the type face matters. Tabular numerals on; right-align by default in any grid; mono for formula expressions.
> - **Polished without being ornamental.** Real PVC contracts run to crores — the UI has to feel trustworthy first, opinionated second. Hairline borders, generous whitespace, restrained colour. No gradients-for-the-sake-of-it.
>
> **Before writing any code, use AskUserQuestion to align on:**
>
> 1. Visual identity direction (typeface family, accent colour, density)
> 2. Sidebar shape (icon-only collapsed vs labeled expanded vs auto-collapse on narrow)
> 3. Whether to introduce a command palette / global keyboard shortcuts now or defer
> 4. Toast lib choice (Sonner vs custom radix-based vs other)
>
> Surface 3–4 concrete previews (ASCII mockups OR small code snippets) per question — I'll pick. Then implement.
>
> **Verification:** `npm run dev` from `frontend/` (or whatever the Next.js root is) must show the shell on `/`, navigation works between the three sections (with placeholder pages), unhandled errors surface as toasts not stack traces, TanStack Query DevTools panel shows in dev.
>
> **When done:** append a "Session 5" entry to `SESSION_LOG.md` and update vault per the protocol in `CLAUDE.md`. Mention P4-001 (auth client) is still blocked on P3-001 merging — don't start it.

---

## Why a fresh window

This session's context is heavy with engine internals (TraceContract types, GCC formulas, RLS migration details). Phase 4 is a different mental mode — frontend layout, design tokens, component composition. A clean window costs nothing and lets the new session focus on UI judgment without dragging engine details forward.

## Decisions already made (don't relitigate)

- Stack: Next.js 14 App Router + TypeScript + Tailwind + AG Grid + TanStack Query
- `@supabase/ssr` for auth client (P4-001 — blocked on P3-001)
- `openapi-typescript` for codegen from FastAPI's `/openapi.json`
- Three top-level navigation sections for MVP: Contracts, Index Manager, Document Vault

## What success looks like

End-of-session state:
- `saqlain/phase-4` branch with P4-003 + P4-005 + P4-006 base committed
- App shell renders; three sections route correctly to placeholder pages
- One AG Grid placeholder somewhere shows the design language working with tabular data
- TanStack QueryClientProvider wraps app; ReactQueryDevtools mounted in dev only
- `frontend/openapi-codegen.config.ts` (or equivalent) ready to point at Shubham's API URL
- Error boundary catches unhandled component errors → branded fallback page; API errors → toast
- AskUserQuestion log captured in `tasks/track-b-design-decisions.md` for future reference
- Session entry in `SESSION_LOG.md` + vault updates

## What to defer to a later session

- P4-001 auth client (blocked on P3-001 merge)
- P4-002 auth pages (CC-SH task per TASKS.md)
- P4-004 contract list (needs P3-002 endpoint live)
- The actual ContractItem / BillLine grids (Phases 5 + 6)

## Reminder of in-flight blockers (project-level, not Track B)

- RBI historical seed (Apr 2022 – Nov 2024) — Saqlain sourcing in parallel
- JPC zone-specific snapshot construction (P3-009, CC-SH)
- Phase 3 merge gate is fully clear from CC-S side — engine + migrations done
