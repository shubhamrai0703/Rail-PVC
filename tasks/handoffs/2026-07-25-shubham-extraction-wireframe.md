# Handoff — Document-extraction prefill: wireframe

**Date:** 2026-07-25
**From:** Claude Opus session (Saqlain)
**To:** `[CC-SH]` Claude Shubham — UI generation
**Repo:** `/Users/saqlainmomin/railPVC`
**Branch:** `shubham/extraction-wireframe` off `main`
**Scope:** Wireframe only. No backend, no LLM calls, no migrations, no production wiring.

## Goal

Design the UI for **document-assisted prefill**: the user uploads real tender documents, the
system proposes field values, and the user confirms before anything is written.

We are not building extraction in this ticket. We are deciding what the screens look like, so
that the extraction work behind them has a fixed target. Produce screens driven by static
fixture data.

## The one non-negotiable rule

**Extraction never writes to `contracts` / `schedules` / `contract_items` / `bills` directly.**
It proposes. A human confirms. This is financial data feeding a PVC calculation that gets
submitted to Indian Railways — a silently wrong prefill is worse than no prefill.

Concretely, every screen you design must satisfy:

1. Every extracted value shows **where it came from** — document name, page number, and ideally
   the highlighted region or spreadsheet cell.
2. Every financially meaningful field requires **explicit confirmation**. No "looks fine, saved".
3. **Missing or conflicting values block** — they must never silently default to zero or blank.
   A blocked field needs an obvious "why" and an obvious manual-entry escape hatch.
4. The user can always **reject the extraction entirely** and type values by hand. Extraction is
   an accelerator, never the only path.

## Source documents — what we actually have

Real documents live in `PVC/` (**gitignored** — real contractor data, never commit them, never
paste their contents into an artifact or anything published). Five contracts, each roughly:
agreement PDF, LOA, FIN-TAB tabulation statement, MB (measurement book), signed bill, signed
recoveries, plus a "golden" Banjara workbook holding the approved final PVC calculation.

I probed every PDF in `PVC/BCT-23-24-296/` for a text layer. This determines feasibility per
document type and should shape which upload targets you design first:

| Document | Status |
|---|---|
| `1st/2nd MB 10.1.xlsx` | **Native Excel**, single `Table 1` sheet — easiest target |
| `1st–3rd MB.pdf` | Digital text layer (~32–48k text ops) |
| `1st–3rd Bill.pdf` | Digital text layer (~2.2k text ops) |
| `Final Agreement.pdf` (114p), `LOA`, `FIN-TAB` | Digital |
| `*Bill Signed Recoveries.pdf` | **Image-only — the only OCR case** |

Design implication: the flow is mostly "parse a structured document", not "OCR a scan". But the
recoveries sheet is scanned, so at least one path must degrade gracefully to low confidence or
full manual entry. Do not design as if every document parses cleanly.

Caveat worth knowing: text-op counts can come from stamps and letterheads rather than table
content. Structured-table extraction is not yet proven — design for a world where extraction
returns partial results.

## Domain model the screens must respect

Confirmed from `PVC/BCT-23-24-296/FIN-TAB-BCT-23-24-296.pdf` on 2026-07-25, verified exact to
the paisa. The tabulation statement has a literal **`Advt. Value (Rs.)`** column header.

```
basic cost →(escalation %)→ ADVERTISED VALUE   [per item, summed per schedule]
           →(schedule bid % below)→ schedule bid amount
           →(Σ schedules)→ Gross Offer Value
           →(rebate on gross value %)→ NET OFFER VALUE = accepted value
```

Worked example (BCT-23-24-296, BANJARA CONSTRUCTION CORPORATION, Inter-se Rank L1):

| | Schedule A (All DSR Items) | Schedule B (All Non Scheduled items) |
|---|---|---|
| Basic cost | 15,735,671.28 | 6,485,964.02 |
| Escalation (%) | `(-) 10.00` per item | `At Par` |
| **Advt. Value** | 14,162,104.18 | 6,485,964.02 |
| Bid Rate | 49.00 % Below | 44.00 % Below |
| Bid Amount | 7,222,673.13 | 3,632,139.85 |

Gross Offer Value 10,854,812.98 → Rebate on Gross Value **0.00 (%)** → Net Offer Value
10,854,812.98. Total advertised 20,648,068.20.

**Validated across four contracts (2026-07-25).** All 13 schedule checks and 4 gross→net checks
recomputed independently, exact to the paisa. Use these as your fixture set:

| Contract | Schedules | Bid % below | Rebate on Gross |
|---|---|---|---|
| BCT-23-24-296 | A DSR, B NS | 49.00 / 44.00 | 0.00 % |
| BCT-24-25-252 | A DSR, B NS | **58.58** / 49.00 | **2.75 %** |
| BCT-24-25-183 | A DSR, B NS | 54.00 / 48.00 | **0.50 %** |
| BCT-23-24-48 (JRH) | A DSR, B **IRUSSOR**, C NS | 34.00 / 20.00 / 32.00 | 0.00 % |

Five things this forces on the design:

- **Advertised ≠ accepted.** Two distinct values, both shown, never conflated.
- **The overall rebate applies to the gross schedule total, not to item rates.** Do not draw a
  chain implying rebate modifies an item's agreement rate. It sits one level up.
- **Do not assume two schedules.** JRH has three. Schedule count is variable and the layout must
  handle it without horizontal scrolling or a broken summary.
- **A contract can have several schedule percentages and a 0% overall rebate.** Two of the four
  do. A form leading with a single contract-level rebate field misrepresents real contracts.
  Schedule percentages are the primary input; overall rebate is secondary.
- **Escalation % is per-item** and follows a consistent rule — DSR schedules `(-) 10.00`, every
  other type `At Par`. It has **no column in the schema today**. Show it as a proposed field and
  flag it as an open schema decision rather than assuming it in.

**Schedule shape is changing under you.** A parallel Codex session is splitting
`schedule_type` into two fields, because the current enum `('DSR','NS','ExtraNS')` conflates
*which rate book the schedule prices from* with *whether its items need an extra-item
eligibility decision*. Design against the new shape:

- `rate_source` — free text with suggestions (DSR, NS, IRUSSOR, …). **Not a closed dropdown** —
  more Railway rate books exist and users must be able to enter one you have not seen.
- `is_extra_items` — an explicit boolean. This is the field that actually drives the PVC
  eligibility gate, so extraction proposing it wrongly has calculation consequences. Treat it as
  a high-stakes confirmation, not a checkbox users skim past.

See `tasks/handoffs/2026-07-25-codex-schedule-axis-split.md` for the full rationale.

## What to reuse — do not invent a new pattern

The confirm-before-write UX already exists in this codebase. Extend its visual language rather
than designing a second, competing one:

- `frontend/components/contracts/ImportRowsModal.tsx` — file upload + paste + fuzzy column
  mapper, including a wired AI-assisted mapping call. **This is the closest existing precedent
  and your primary reference.**
- `frontend/components/contracts/ImportTemplateControls.tsx` — saved mapping templates
- `frontend/lib/normalizeImportRows.ts`, `frontend/lib/parseTsvImport.ts` — row normalization
- `frontend/components/documents/DocumentVault.tsx`, `frontend/lib/documents.ts` — upload,
  listing, signed-URL download. Documents are already stored; they are simply never parsed.
- `frontend/components/help/*` — the layered help patterns; extraction needs heavy explanation
- `frontend/components/contracts/ContractForm.tsx`, `ScheduleForm.tsx`, `ItemsGrid.tsx`,
  `BillForm.tsx`, `BillLineForm.tsx` — the forms prefill would populate

## Screens to wireframe

### 1. Upload and classify
Drop several documents at once. System proposes a type per document (agreement / LOA / FIN-TAB /
schedule-BOQ / MB / signed bill / recoveries); user corrects. Show which documents are still
missing for the contract to be complete.

### 2. Contract and pricing confirmation
The heart of it. Show the derivation chain above as an inspectable sequence, not just final
numbers: advertised → per-schedule bid % → schedule bid amount → gross → rebate → net accepted.
Each extracted number carries its source. The user confirms per field or accepts a whole
schedule at once.

This screen replaces the current single contract-value field, and it is a genuine restructuring
of the contract section rather than an upload button bolted onto the existing form.

### 3. Items and classification
Item master proposed from the schedule/BOQ. System suggests which items contain cement and which
contain steel; user confirms each. Steel subtype (angles / plates / TMT / other) is classified
once on the item master, not per bill. Show classification confidence and make disagreement cheap.

### 4. Bill bundle intake
"How many bills have been raised?" → N slots, each wanting an MB plus a signed bill, optionally a
recoveries sheet. Per bill, prefill: bill number, bill date, measurement period, gross value,
item list, previous/current/cumulative quantities and amounts, and recoveries.

Measurement date rule: the MB prints e.g. `Date of Measurement: From 09/05/2025 to 18/06/2025`.
**`18/06/2025` — the period end — is the measurement date driving quarter selection.** The full
period is retained as evidence. Show both; make clear which one drives the calculation.

### 5. Reconciliation and blocking
Before anything saves, show deterministic check results: cumulative = previous + current; bill
totals reconcile to line totals; item codes exist in the confirmed schedule; bid % and rebate
agree with the stated values; bill sequence does not go backwards; MB and signed bill agree.
Design the **failure** state properly — this screen earns its keep when numbers disagree, and
that is the state most likely to be under-designed.

## Deliverable

Wireframes as working React screens under a dev-only route (suggest
`frontend/app/(app)/_wireframes/extraction/`), fed by static fixture data. Fidelity: structure,
state, and copy — not final visual polish. Cover the unhappy paths explicitly: low confidence,
conflicting values between two documents, unreadable scan, partial extraction, user rejects
everything.

Note the two-pass design rule: this is design pass one. Do not spend a second polish pass here.

## Definition of done

- [ ] All five screens exist and are navigable end-to-end with fixture data
- [ ] Every extracted field displays a source reference in every screen
- [ ] Blocked / conflicting / low-confidence / unreadable states are designed, not just happy paths
- [ ] Manual-entry escape hatch reachable from every extraction screen
- [ ] The pricing chain renders at the correct levels (rebate on gross total, not on item rates)
- [ ] Advertised and accepted values are visibly distinct
- [ ] Layout holds for a **three-schedule** contract (use JRH) and for a non-zero overall rebate
- [ ] `rate_source` is a suggestions combobox, not a closed dropdown; `is_extra_items` is
      designed as a high-stakes confirmation
- [ ] Proposed `escalation %` field flagged as a schema decision, not silently assumed in
- [ ] `tsc` + `eslint` + `next build` clean
- [ ] No real contractor data committed; fixtures are synthetic or anonymized
- [ ] Open questions recorded in the Results section below

## Related

- Field notes that prompted this: `tasks/handoffs/2026-07-25-ritesh-document-ingestion-notes.md`
- Sequencing and the confirmed pricing chain: `tasks/todo.md` (top section)
- `PRODUCT.md` defers parsing to Phase 2 citing OCR confidence on scanned documents. That
  rationale does not describe this bundle — most of it is digital. Flagged for correction.

## Results

**Session:** Claude Opus (Shubham), 2026-07-25. **Branch:** `shubham/extraction-wireframe` off
`main` `03e2f8f`. Wireframe only — no backend, no LLM calls, no migrations, nothing wired to the
API.

### What was built

| Path | What it is |
|---|---|
| `frontend/app/(app)/wireframes/layout.tsx` | Dev-only gate + wireframe banner |
| `frontend/app/(app)/wireframes/page.tsx` | Index of both wireframe sets |
| `frontend/app/(app)/wireframes/extraction/page.tsx` | Step navigator hosting all five screens |
| `frontend/components/wireframes/Primitives.tsx` | `SourceChip`, `FieldRow`, `BlockedCallout`, `ManualEntryEscape`, `SchemaGapNote` |
| `frontend/components/wireframes/useFieldOverrides.ts` | Confirm / reject / resolve state |
| `frontend/components/wireframes/extraction/Step1…Step5` | The five screens |
| `frontend/lib/wireframes/extraction.ts` | Fixture data + pricing helpers |
| `frontend/components/wireframes/extraction/extraction.test.tsx` | 23 tests pinning the DoD invariants |

### Deviation from the brief — the suggested route would not have existed

The brief suggested `frontend/app/(app)/_wireframes/extraction/`. An underscore prefix makes a
folder **private** in the App Router: it and every subfolder are opted out of routing entirely
(`node_modules/next/dist/docs/01-app/01-getting-started/02-project-structure.md`, "Private
Folders" — *"opting the folder and all its subfolders out of routing"*). The screens would have
compiled and been unreachable at any URL, failing the first DoD line.

Built at `wireframes/` (no underscore) with a runtime guard instead:
`if (process.env.NODE_ENV === "production") notFound()`. Verified rather than assumed — all
three routes prerender with `"status": 404` in `.next/server/app/wireframes*.meta` from a real
`next build`.

### Design decisions

- **Provenance is a permanent row element, not a tooltip.** `SourceChip` renders document, page
  and locator inline under every proposed value. A value whose source is one hover away is a
  value people stop checking.
- **Blocked values render as blank with a reason, never as `0`.** `FieldRow` prints *"nothing
  extracted — blank, not zero"* and refuses the Confirm control while `conflict` / `missing` /
  `unreadable`.
- **Conflicts show both sides with their sources** and a "Use this one" per alternative, rather
  than picking a winner and mentioning the disagreement in small print.
- **"Accept this whole schedule" skips blocked fields** and says how many it skipped. Bulk accept
  that silently swallows a conflict would defeat the point of the screen.
- **The rebate is rendered in a separate contract-level panel**, visually outside the schedule
  cards, with the chain `Σ schedules → gross → rebate → net`. Nothing in the schedule cards can
  be read as the rebate touching an item rate.
- **Advertised and accepted sit side by side** in contrasting treatments, both labelled, on the
  same screen.
- **Schedules stack vertically**, so three schedules (or five) need no horizontal scroll.
- **`rate_source` is an `<input list=…>` combobox** with DSR / NS / IRUSSOR / USSOR / LAR as
  suggestions — any other value is typeable. **`is_extra_items` is a `FieldRow` flagged "Affects
  the calculation"**, not a checkbox in a row of checkboxes.
- **Per-item escalation % renders inside a dashed `SchemaGapNote`** marked "Open schema decision
  — not stored today", so it reads as a proposal rather than an assumed field.
- **The measurement period end is the visually dominant of the two dates**, in amber with
  "selects the quarter"; the start is muted and labelled "evidence only".
- **Reconciliation leads with the verdict.** Failure is the designed state: `fail` shows
  found-vs-expected side by side, `skipped` explains why it could not run, and a check that
  cannot run blocks the write exactly like one that fails. No partial save is offered.

### Fixtures

Synthetic. Tender numbers, contractor names and every rupee amount are invented; only the
*shapes* are borrowed from the verified statements. Two contracts:

- **TA-24-25-101** — 2 schedules, 0% rebate, with a seeded LOA-vs-FIN-TAB bid-percentage conflict.
- **TA-24-25-207** — 3 schedules (DSR / **IRUSSOR** / NS), **2.75%** rebate, missing base month.
  Gross 15,380,000.00 → net 14,957,050.00; total advertised 28,000,000.00.

No file under `PVC/` was read, copied or referenced by content.

### Verification

- `npx tsc --noEmit` — clean.
- `npm run lint` — clean.
- `npm run build` — compiled, 14/14 static pages, all three wireframe routes registered.
- Production 404 guard — confirmed from build artefacts (above).
- `npm test` — **125 passed / 19 files** (was 102 / 18). 23 new tests assert the DoD invariants
  directly: escape hatch on every screen, advertised ≠ accepted, three-schedule arithmetic,
  combobox not dropdown, schema-gap note present, missing base month blocked, both conflict
  sources offered, scanned-document degradation, period-end labelling, write refused on failure.
- **Not done: no authenticated browser click-through.** The routes sit behind the Supabase auth
  proxy and I had no test session; `curl` gets a 307 to `/login`. The render tests above are what
  I could actually verify. Someone with a session should still click through all five screens.

### One infrastructure change

Added `frontend/vitest.config.ts` mirroring the `@/*` alias from `tsconfig.json`. Vitest had no
config at all, so `@/…` never resolved in tests — which is why the suite had only ever covered
modules using relative imports. Additive; the full pre-existing suite passes unchanged.

### Open questions for Saqlain

1. **Does confirming an extraction create a pending record, or write straight through on the last
   step?** The wireframe implies a staging area (nothing writes until reconciliation passes) but
   does not model where a half-confirmed extraction lives if the user leaves. This is a schema
   question, not a UI one.
2. **Who wins when the LOA and the FIN-TAB disagree?** The screens make the user choose every
   time. If one document is authoritative by rule, the conflict screen should say so and default
   accordingly.
3. **Is per-item `escalation_pct` + `basic_cost` going onto `contract_items`?** Screen 2 shows the
   full printed chain; if the schema never models escalation, the advertised value has to be
   entered directly and one rung of the chain becomes non-derivable. Same open item as
   `tasks/todo.md`.
4. **Bill slots assume the user knows how many bills exist.** For a contract being onboarded
   mid-flight with eight historical bills, is that the right question, or should the bundle be
   inferred from the documents?
5. **Steel sub-line decomposition is not in these screens** — flagged in the brief as an
   engine-boundary item. Confirm it stays out of the prefill path.

### Alignment with the parallel sessions

Read `2026-07-25-sonnet-contract-flow-reorder.md` and `2026-07-25-codex-schedule-axis-split.md`
before building. No file owned by either session is touched — everything here is new, under
`wireframes/`. Specifically: the journey ordering in the second wireframe (below) follows
Sonnet's target order (contract → schedules → items → pricing summary → bills) rather than the
current `JOURNEY_STAGES`, and the derivation chain on screen 2 is deliberately the same chain
Sonnet is building as a read-only production component — the intent is that prefill feeds that
component, not that a second one gets built.

### Also on this branch — a second wireframe, not from this brief

`/wireframes/journey`, responding to review feedback that arrived during this session: *"the UI
is not intuitive, I don't understand where to start or what to do next"*, reported as the one
comment common to everyone shown the app. Diagnosis and proposal are written up in
`tasks/handoffs/2026-07-25-guided-journey.md`. It is a wireframe only — no production file is
modified.

