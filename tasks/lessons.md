# Lessons

Running log of corrections and hard-won judgments. Review at session start.

---

## 2026-05-16 — 8 GB M2 is below the practical floor for `next dev` + heavy desktop

**Incident:** Laptop hard-froze twice in a row while bringing up the Next.js 16.2.6 + Turbopack dev server on `saqlain/phase-4` and probing all four routes via a curl loop. Screen went black; had to hold power. No kernel panic (`/Library/Logs/DiagnosticReports/` shows no `.ips` for either crash) — pure memory-pressure deadlock. Load average hit 56.87 (5-min) within minutes of boot post-crash.

**Hardware:** 13" MacBook Pro M2 2022, **8 GB RAM**, macOS Tahoe 26.3.1.

**Concurrent load at crash time:** Antigravity (multi-window Electron AI IDE), Arc with many tabs, Spotify, NordVPN, iPhone Mirroring, Photos, Messages, Ghostty, Claude Code, then `next dev` compiling 5 routes (`/`, `/contracts`, `/indices`, `/documents`, `/nonexistent`) concurrently via a back-to-back curl probe loop.

**Root cause:** Structural ~9–10 GB demand on an 8 GB box. macOS compressed, swapped, jetsam'd, then WindowServer choked. Not a Next.js bug — sizing problem.

**Rules going forward:**

- **Do not run `next dev` and Antigravity (or any other Electron AI IDE) concurrently on this machine.** Pick one.
- **For verification runs, prefer `next build && next start` over `next dev`.** Production server is one-shot compile, then steady-state ~150–250 MB. Turbopack dev easily hits 1–2 GB on first-compile of multiple routes.
- **Don't probe all routes back-to-back with curl.** Forces Turbopack to compile them concurrently. Probe one, let it settle, then the next.
- **Before any dev session:** quit Photos, iPhone Mirroring, Messages, Spotify, extra Electron apps. Arc (lean) + Ghostty + Claude Code + Next dev fits in 8 GB.
- **Watch the Memory tab in Activity Monitor.** If "Memory Used" is already > 5.5 GB before starting dev, close more apps first.

**Also fixed during diagnosis:** stray `~/package-lock.json` (91 bytes, empty, from March 2026) was making Next pick `$HOME` as the workspace root — we'd added a `turbopack.root` workaround in `frontend/next.config.ts`. Deleted the lockfile, reverted the config. One fewer moving part.

**Symptom signature to recognise next time:** screen blacks out, no panic file, load avg shows huge 5-min number on next boot, swap was thrashing pre-crash. That's memory-pressure deadlock, not a kernel bug. Don't chase it as a software issue.
