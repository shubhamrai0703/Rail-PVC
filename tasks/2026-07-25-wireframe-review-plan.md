# Wireframe review with Ritesh — plan and next steps

**Date:** 2026-07-25
**Status:** wireframes built and verified; **no production code written, and none to be written
until Ritesh has reviewed.**
**Branch:** `shubham/extraction-wireframe`

Two wireframes are ready to show:

| Route | What it is | Origin |
|---|---|---|
| `/wireframes/extraction` | Document-assisted prefill, 5 screens | `tasks/handoffs/2026-07-25-shubham-extraction-wireframe.md` |
| `/wireframes/journey` | Guided journey — "where do I start" | `tasks/handoffs/2026-07-25-guided-journey.md` |

They are separate routes but one design: the journey is the map of a contract's life, and
extraction is a shortcut across the setup half of it. Neither is a subset of the other.

## How to show them to Ritesh

The wireframes are **dev-only** — `app/(app)/wireframes/layout.tsx` calls `notFound()` when
`NODE_ENV === "production"`, and all three routes prerender as 404 in a production build. They
are also behind the Supabase auth proxy like every other app route. That shapes the options.

### Option A — screen share on a call (recommended for the first pass)

```
cd frontend && npm run dev      # http://localhost:3000
```

Sign in, go to `/wireframes`, and drive while he talks.

- Nothing to deploy, nothing to un-deploy afterwards, no code change.
- You can ask "why" the moment he hesitates — which is the entire value of this review.
- He cannot explore alone, and you have to be available.

**This is the one to do first.** The questions below are worth more than the clicks.

### Option B — temporary preview deploy (only if he must explore alone)

Requires one change: gate the wireframes on an explicit env flag rather than `NODE_ENV`, e.g.
`process.env.NEXT_PUBLIC_ENABLE_WIREFRAMES === "1"`, set only on the preview environment.

- He needs an invited tenant account (provisioning is invite-only since PR #23/#25).
- The flag must be removed or left off for `tenderaudit.in`. A wireframe reachable in production
  is worse than no wireframe — the numbers on it are fictional.
- Do not point this at the live Supabase project without deciding which tenant he lands in.

### Option C — recorded walkthrough (good leave-behind, poor primary)

Record a click-through of both wireframes, including the failure states. Async, no infra, easy to
forward to anyone else. He cannot click the unhappy paths himself, and those are exactly where
the open questions live — so use this alongside A, not instead of it.

## What to actually ask him

A demo without specific questions produces "looks nice" and no information. Each of these maps to
an open decision that is currently blocking design:

**On pricing (extraction screen 2)**

1. Do "advertised value" and "accepted value" match the words he uses? If he calls them something
   else, the labels should be his, not the tabulation statement's.
2. When the LOA and the tabulation statement disagree on a bid percentage — which one does he
   treat as correct? If there is a rule, the conflict screen should apply it instead of asking
   every time.
3. Does he ever see a contract where the overall rebate is not zero? Two of four sampled had one,
   but he described 58.58% on a different contract than we assumed.

**On items and bills (screens 3–4)**

4. Would he know how many bills have been raised before starting, or should the bundle be
   inferred from the documents? This changes screen 4's first question.
5. What does he do today with the signed recoveries sheet, given it is a scan? If he already
   re-types it, the "unreadable" path is normal rather than an error state.
6. Does classifying cement/steel once per item — rather than per bill — match how he works?

**On the journey wireframe**

7. Does "setup once, billing repeats" match his mental model, or does he expect to revisit setup?
8. On his first sign-in, what did he expect to see? The empty-tenant screen is a guess at that.
9. When he got stuck, what was he stuck *on*? The wireframe assumes missing index data is the
   most common dead end — worth confirming rather than designing around a hunch.

**Do not ask** whether he likes the visual design. It is deliberately unpolished (design pass one
of two) and his answer will not be actionable.

## Next steps — after review, not before

Owner rule for this phase: **LLM/extraction-model work → Saqlain. Backend work → Shubham.**
UI work is assigned to Shubham below on the basis that he owns the wireframes — flagged as an
assumption, since the rule does not cover it.

### Blocked on Ritesh's review

| ID | Task | Owner |
|---|---|---|
| RW-0 | Run the review, capture answers to Q1–Q9 in this file's Results section | Saqlain |

### LLM / extraction model — `[Saqlain]`

| ID | Task | Notes |
|---|---|---|
| LLM-1 | Document classifier for screen 1 | Proposes a type per uploaded document + a confidence. The wireframe assumes this is fallible and shows an "Unrecognised" state |
| LLM-2 | Structured field extraction from FIN-TAB / LOA / agreement | Table extraction is **not yet proven** — the text-op counts may be letterhead and stamps. Prove feasibility before committing to the screens |
| LLM-3 | Item cement/steel classification proposals | Feeds screen 3. Must return a confidence, and must be allowed to abstain |
| LLM-4 | Confidence calibration + an eval set | The screens key their entire behaviour off high/medium/low. Uncalibrated confidence makes the design lie |
| LLM-5 | OCR decision for scanned recoveries | Whether to attempt it at all. The wireframe currently degrades to manual entry; that may be the right permanent answer |
| LLM-6 | Model + prompt selection, cost per contract | Note the existing AI column-mapper already moved from the Anthropic SDK to OpenRouter (PR #22) — match that path |

### Backend — `[Shubham]`

| ID | Task | Notes |
|---|---|---|
| BE-1 | Pending-extraction staging schema + migration | **Open question #1** from the extraction handoff. Where a half-confirmed extraction lives if the user walks away. Blocks everything else here |
| BE-2 | Per-field provenance persistence | Document, page, locator, confidence, and whether the value was confirmed or hand-entered. The audit trail is the point |
| BE-3 | Upload → extract → propose → confirm → commit endpoints | The commit is one transaction, matching screen 5 |
| BE-4 | Server-side reconciliation checks | The six checks on screen 5 must run on the server, not only in the UI. A check that cannot run must report, never pass |
| BE-5 | Index-coverage check | Powers the journey's named blocker. Given a bill's quarter, return the missing months |
| BE-6 | Journey stage derivation | Pure function over contract data — schedule count, item count, decisions, bill/run status. No new columns |

### Frontend — `[Shubham]` *(assumed — confirm)*

| ID | Task | Notes |
|---|---|---|
| FE-1 | Guided journey, production | Per `tasks/handoffs/2026-07-25-guided-journey.md`. **Must land after the flow reorder**, or it describes an order the app does not have |
| FE-2 | Landing route + `NAV_ITEMS` entry + `proxy.ts` redirect target | Needs Saqlain's decision on whether it replaces `/contracts` post-login |
| FE-3 | Extraction screens, production | Only after LLM-2 proves extraction is feasible on real documents |

### Sequencing

```
flow reorder (Sonnet, in flight)  →  FE-1 / FE-2 (journey)  →  extraction (LLM-* + BE-* + FE-3)
```

The journey cannot ship before the reorder. Extraction should not start before LLM-2 answers
whether structured extraction works on this document bundle at all — the screens are designed
for partial results, but "partial" and "nothing" are different products.

## Results

<!-- Ritesh's answers to Q1-Q9, and any change they force on the wireframes. -->
