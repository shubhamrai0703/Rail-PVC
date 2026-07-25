# Handoff — Guided journey: "I don't know where to start"

**Date:** 2026-07-25
**From:** Claude Opus session (Shubham)
**To:** whoever picks up the production change — needs a design decision from Saqlain first
**Branch to create:** `shubham/guided-journey` off `main`
**Status:** wireframe built and reviewable at `/wireframes/journey`; **no production file
touched.**

## The feedback

Every person shown the app has given the same comment, unprompted:

> "The UI is not intuitive. I do not understand where to start, or what to do next."

That is not a styling complaint and it will not be fixed by more help text. Three specific,
verifiable causes:

### 1. There is no landing page

`frontend/components/shell/nav.ts` has exactly three entries — Contracts, Index Manager,
Document Vault. All three are lists. `proxy.ts:40-44` redirects a signed-in user hitting `/`
straight to `/contracts`, so the first thing anyone ever sees is a table with a "New contract"
button in the corner and no statement of what this application wants them to do.

### 2. The journey ribbon is decorative

`JOURNEY_STAGES` (`frontend/lib/firstUserHelp.ts:1-8`) is a fixed six-item list. `JourneyGuide`
renders it identically on every page it appears on. It never reflects state — it cannot say which
stages are done, which is current, or which is blocked, because it is not passed any data beyond
a hardcoded `stage` prop.

It is also absent from the two pages users actually land on:

| Page | Renders `JourneyGuide`? |
|---|---|
| `/contracts` (the landing target) | **no** |
| `/contracts/[id]` (the detail hub, 524 lines) | **no** |
| `/contracts/new` | yes — `stage="contract"` |
| `/contracts/[id]/bills` | yes — `stage="bill"` |
| `/contracts/[id]/bills/[billId]` | yes — `stage="calculate"` |
| `.../runs/[runId]` | yes — `stage="review"` |

Two of the six stages — `items` and `decisions` — have no page that renders the guide at all.

### 3. It implies one linear pass, and the real shape is two phases

Setup happens **once** per contract. The bill cycle **repeats** for every measurement book. A
flat six-step ribbon says neither. This is the part that produces "what do I do next" *after* the
first bill: the user has walked the ribbon end to end and has no idea whether they are finished
or supposed to start again.

## The proposal

Three changes, wireframed at `/wireframes/journey` (dev builds only):

1. **A real landing route.** Empty tenant gets one instruction — "Start by adding your first
   contract" — plus three numbered steps that name index data as a prerequisite before anyone
   hits the dead end in cause 3 below. Populated tenant gets a per-contract "Do this next" card.
2. **Stage state derived from data, not hardcoded.** `done` / `current` / `blocked` / `todo` per
   stage, computed from what the contract already has: schedule count, item count, extra-item
   decisions, bill status, run status. No new columns.
3. **Setup separated from the repeating bill cycle**, with the cadence stated on each phase
   ("Once — you will not come back here" / "Repeats — once for every measurement book").

Plus the highest-value single item:

4. **Name the index-coverage dead end.** The most common way to get stuck is a bill whose quarter
   has no index observations. Today the calculation just refuses. It should be a named blocker on
   the journey with a link to the exact months to add. This is modelled in the `BLOCKED` fixture.

## Stage order — coordinate with the reorder

The wireframe uses the order being implemented on `saqlain/contract-flow-reorder`:

**Setup (once):** contract → schedules → items → extra-item decisions → pricing check
**Billing (repeats):** bill → calculate → review

This deliberately differs from the current `JOURNEY_STAGES`. **Do not ship this before the flow
reorder lands**, or the journey will describe an order the app does not have. `JOURNEY_STAGES`
should end up as the single source both features read.

## Scope when it is built

- `frontend/lib/journeyState.ts` — pure derivation from contract data. Unit-testable, and the
  place the logic belongs; nothing about it is presentational.
- A state-aware `JourneyRail` replacing `JourneyGuide`, rendered on `/contracts` and
  `/contracts/[id]` as well as the pages that already have it.
- A "Do this next" component taking one derived action, on the contract detail page.
- A landing route + a fourth `NAV_ITEMS` entry, and the `proxy.ts:40-44` redirect target changed.

**Not in scope:** any change to calculation, exports, or the contract forms themselves. This is
navigation and state display only.

## Definition of done

- [ ] Stage derivation is a pure function with unit tests covering: empty contract, mid-setup,
      blocked-on-index, steady state with N approved bills
- [ ] Journey renders on `/contracts` and `/contracts/[id]`
- [ ] Every stage shows real state; no hardcoded `stage` props remain
- [ ] Index-coverage gaps surface as a named blocker with the missing months listed
- [ ] Empty tenant sees a single unambiguous first action
- [ ] Setup vs repeating cadence is explicit
- [ ] `tsc` + `eslint` + `next build` + vitest clean
- [ ] Authenticated browser pass, evidence in Results

## Decision needed from Saqlain before starting

1. **Does the landing page replace `/contracts` as the post-login target, or sit alongside it?**
   Changing `proxy.ts` affects every user immediately.
2. **Is "extra-item decisions" a journey stage or a sub-step of items?** It only applies to
   contracts that have non-scheduled schedules, so it may be conditional rather than always shown.
3. **Should the journey be per-contract only, or is there a cross-contract "what needs me today"
   view?** The wireframe shows per-contract. A portfolio view is a different, larger feature.

## Related

- Wireframe: `/wireframes/journey` (dev builds only), `frontend/lib/wireframes/journey.ts`
- Flow reorder that must land first: `tasks/handoffs/2026-07-25-sonnet-contract-flow-reorder.md`
- Existing help layer this extends: `frontend/components/help/FirstUserHelp.tsx`

## Results

<!-- Fill in when the production change ships. -->
