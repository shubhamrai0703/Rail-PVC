# First-User Walkthrough — Guided Onboarding Session Script

Audience: Saqlain, sitting with the first external user (a railway contractor — referred to as **[CONTRACTOR]** below; his invited email as **[INVITE_EMAIL]**). No real names or emails in this file — substitute live at run time.

Plan for **45–60 minutes** at the table, plus **~30 minutes of solo prep the day before**. The contractor drives the keyboard from Part B onward; you narrate.

Goal of the session: take his **empty tenant** from signup to a computed PVC statement on **one of his real contracts** — one that already has **at least one bill he has manually computed in Excel**. That manual figure is the acceptance test.

---

## Part A — Before the meeting (Saqlain solo, day before)

### A1. Pick the target contract and bill (with him, on a phone call)

Ask him for one contract + one already-computed bill. Then apply this filter — it decides whether the session can succeed:

- **Best case: a bill with no cement/steel supply deductions and no extra (ExtraNS) items.** The app currently has **no UI for entering per-item bill lines** (`POST /api/bills/{id}/lines` is API-only; the bill page only displays lines). Cement/steel bucket deductions and extra-item amounts are derived from bill lines, so without lines the engine computes W = gross − PVC-affecting recoveries and puts everything through the "other" component weights. That matches his workbook **only** for a bill whose PVC statement has no cement/steel/extra-item deduction rows.
- If every candidate bill has cement/steel deductions: you must pre-enter that bill's lines yourself via the API (see Appendix 1) **before** the meeting, using quantities read off his workbook. Budget extra prep time and dry-run the numbers.
- Confirm the contract's **base month** and the bill's **measurement date** from his agreement/MB — you'll need both exactly.

### A2. Check index coverage for the bill's quarter

The rolling quarter is the 3 months containing the measurement date, counted from the month after the base month. The run **blocks** if any of those months (or the base month) is missing an index observation.

1. Log in to `tenderaudit.in` with your own account → **Indices** in the sidebar.
2. For each series the contract's zone uses, open the series and confirm observations exist for the base month and all 3 quarter months.
3. If a month is missing, enter it from the published RBI/JPC value before the meeting.

### A3. Provision the tenant + invite

From the repo root, on the trusted machine (reads `DATABASE_URL` from `backend/.env`):

```bash
PROVISION_TENANT_NAME="<contractor's firm name>" \
PROVISION_INVITE_EMAIL="[INVITE_EMAIL]" \
uv run python seeds/provision_tenant.py
```

- Safe to re-run; a repeat prints the same tenant UUID (`invite: skipped`).
- The invite is keyed on the **exact normalized email** — he must sign up with precisely this address (case doesn't matter, spelling does).
- Note the printed `TENANT_ID` somewhere private.

### A4. Full dry run of the auth path (mandatory)

The first-login provisioning hook merged in PR #23 and is only live once Railway's post-merge deploy finished. Prove it end-to-end with a **throwaway test email you control**:

1. Provision a scratch tenant for the test email (same command as A3, tenant name `Dry Run — delete me`).
2. On `tenderaudit.in` (private browser window): **Get started / Sign up** → test email + password → "Check your email" screen appears.
3. Open the confirmation email, click the link, land back on the app, **Sign in**.
4. You should land on **Contracts** with the "No contracts yet" empty state — that means the invite was consumed and the tenant attached.
5. Negative check (optional but worth it): sign up with a second, *non-invited* throwaway; after confirming and logging in, the app should show the "Authenticated user has no provisioned tenant" error instead of data. That's the invite gate working.

**Rollback rule: if any step of A4 fails, the meeting does not happen until it passes.** Debug on your own time, not his. (Failure modes to check first: Railway still deploying old `main`; Supabase free-tier project re-paused; confirmation email in spam.)

### A5. Pack the table

- His manual PVC workbook (Excel or print) for the target bill — open to the summary sheet.
- The agreement / rate list for BOQ entry (or a pre-agreed short list — see B3 note on scope).
- Your laptop as backup; **his machine drives** if at all possible.

---

## Part B — Signup & first login (~10 min, his hands on keyboard)

> Say: *"This is your private workspace. Nothing in it is shared with Railways or anyone else — it's your data, and only your login opens it."*

1. **`https://tenderaudit.in`** — let him look at the landing page for a moment. One line: *"This does the Clause 46A price-variation working you do in Excel, and keeps a record of every approved statement."*
2. Click **Get started** (top right) or **Create your account** (hero). Enter **[INVITE_EMAIL]** — it must be the same address you invited, warn him before he types a different one — and a password (min 8 characters, twice).
3. "Check your email" screen → he opens his inbox, clicks the confirmation link. If it isn't there in a minute, check spam.
4. Back on the site: **Sign in** with the same email + password.
5. He lands on **Contracts** — an empty list: "No contracts yet. Start with an LOA / tender number."

> Say: *"Empty on purpose. We're going to build one of your real contracts in it, right now, and check the app's answer against your own working."*

---

## Part C — Guided build of his real contract (~25 min)

### C1. Create the contract (~5 min)

Click **Add your first contract** (or "New contract" top right).

Fields — he reads them off his agreement; only 4 are mandatory:

| Field | What to say |
|---|---|
| Tender number * | "As printed on the tender/LOA." |
| Contractor name * | His firm's name, as on the agreement. |
| Railway zone * | Pick from the dropdown. |
| **Base month *** | *"This is the month your price variation is measured against — the base month in your PVC annexure. Everything downstream keys off this, so get it exactly right."* The picker takes month+year only; the app anchors it to day 1 itself. |
| Agreement/LOA number & dates, work description, start/completion dates, contract value, bid amount | Fill what's handy; all optional, editable later. |
| GST mode | Leave **Exclusive** unless his agreement says otherwise. |
| PVC applicable | Leave ticked. |
| **Overall rebate** | ⚠️ **Decimal, not percent**: a 5% rebate is entered as `0.05`. The label says "(as decimal, 0.15 = 15%)" — point at it, this is the most likely typo of the day. |

Click **Create contract** → lands on the contract detail page, status **Draft**.

### C2. Schedules (~3 min)

> Say: *"Schedules are the A/B/C parts of your agreement — the DSR items, the non-schedule items, and any extra items sanctioned later. Items live under a schedule."*

Tab **Schedules** → "Add schedule" form at the bottom:

- **Name**: e.g. `Schedule A`.
- **Type**: `DSR`, `NS`, or `ExtraNS`. For session 1, create only the schedule(s) the target bill needs — usually one DSR (and NS if his bill has NS items). **Skip ExtraNS today** unless the chosen bill genuinely has extra items (each one then needs an eligibility decision before the run — that's the "Manage extra-item decisions" link that appears in the header).
- **Bid discount**: same decimal convention as rebate (`0.05` = 5%). `0` if none.

### C3. BOQ items (~10 min — keep the scope small)

Tab **Items** → pick the schedule in the dropdown → the grid appears.

> Say: *"These are your BOQ lines. For today we'll enter just the items that appear in the bill we're checking — you can import the full BOQ from Excel later with the Import button."*

Per item, **+ Add row** and fill: Code, Description, Unit, Orig qty, Base rate, Agreement rate. Two flags matter for PVC:

- **Cement?** — tick on cement supply items.
- **Steel subtype** — set on steel items (angles / plates / tmt / other sections).

Save the grid (save button above it). Show him **Import rows** once — paste from Excel — but don't burn session time on a full import.

### C4. The bill (~5 min)

Header link **Bills →** → "New bill" form at the bottom of the list:

- **Bill no.** — his running-bill number.
- **Bill date** and **Measurement date** — ⚠️ the **measurement date decides the quarter**, so it must match his MB exactly. One line: *"The app works out which 3-month window this bill falls in from this date — same as the quarter column in your annexure."*
- **Gross amount (₹)** — the on-account bill total from the MB. The grey help note under the field says it: exclusions are deducted during the PVC run, not here.

**Add bill** → it appears in the list → **View**.

If his workbook's PVC base is net of recoveries (security deposit etc. that reduce the PVC-eligible amount): section **Recoveries** → "Add recovery" → type, amount, and tick **Affects PVC base** only if that deduction reduces W in his working. Otherwise skip recoveries entirely today.

*(If you pre-entered bill lines in A1: point at the "Bill lines" section, show the quantities match his MB, and move on.)*

### C5. Run it (~2 min)

Card **Price Variation (PVC)** → **Calculate PVC**.

- Success: Total PVC, negative carry-forward, and **Quarter used** appear inline. Check the quarter label against his annexure *first* — if the quarter is wrong, the base month or measurement date is wrong; fix and re-run (re-running supersedes the old draft run, nothing is lost).
- Failure: the card lists the engine's specific reasons (missing index month, undecided extra item, etc.). Read them aloud — they're actionable. Fix and re-run.

Click **View full results →**.

---

## Part D — The payoff: app vs workbook (~10 min)

On the run page, put his workbook next to the screen and walk downward:

1. **Total PVC** vs his statement's bottom line. To the rupee.
2. **W derivation** — every subtraction named, top to bottom. *"This is the working you normally do by hand — the on-account amount, minus each exclusion, down to the amount the variation applies to."*
3. **Component breakdown** — per category: eligible amount, base index, current average index, weight, PVC value. Match against his component rows; this is where a discrepancy localizes.

**If the numbers match:** show **Approve run** — one line: *"Approving freezes this statement forever; corrections become a new linked version, so there's always an audit trail."* Let **him** click it. Then export **Excel** and **PDF** (buttons unlock on approval) and open the Excel next to his own format.

**If the numbers don't match — do not debug live.** Script:

1. Say: *"Good — this is exactly what this session is for. Let me capture it and I'll come back to you with the reason."*
2. Capture: contract id + bill id (from the URL), a screenshot of the run page (W derivation + components), phone photos of his workbook's summary and index sheets, and which component row diverges.
3. Check the two classic causes on the spot, silently: quarter label mismatch (base month / measurement date entry) and the rebate-as-percent typo (`5` instead of `0.05`). If it's one of those, fix, re-run, re-compare — that's data entry, not debugging.
4. Anything else: log it as a finding in TASKS.md that evening and move to Part E. Do **not** approve a run he hasn't accepted.

---

## Part E — Wrap (~5 min)

What he can do alone before session 2:

- Enter the remaining BOQ items (Import rows from his Excel).
- Add his other bills' headers (bill no., dates, gross) — even without running them.
- Add his other contracts the same way.
- **Don't** approve runs he hasn't checked against his own working yet.

Feedback channel: one WhatsApp message per confusion — *"screenshot + what you expected"*. Agree a date for session 2 (target: his full BOQ imported + a second bill computed, ideally one with cement/steel once line entry ships).

---

## Appendix 1 — Pre-entering bill lines via API (only if A1 forced it)

No UI exists for bill lines yet. From a terminal, per line item (values from his workbook/MB):

```bash
TOKEN="<your-supabase-access-token-for-the-contractor-tenant>"   # never commit
curl -X POST "https://api.tenderaudit.in/api/bills/<BILL_ID>/lines" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "item_id": "<CONTRACT_ITEM_UUID>",
    "qty_up_to_last": 0, "qty_since_last": 120.5, "qty_up_to_date": 120.5,
    "amount_up_to_last": 0, "amount_since_last": 845000.00, "amount_up_to_date": 845000.00,
    "special_condition_amount": 0
  }'
```

Note: this requires an access token for a user **in the contractor's tenant** — i.e. run it as him after his account exists (or defer cement/steel bills to session 2). This friction is exactly why the bill-line entry UI is ticketed.

## Appendix 2 — Known rough edges to route around (from the 2026-05-31 usability audit + this rehearsal)

- **Rebate & bid discount are decimals** (`0.15` = 15%) — the audit flagged it (AUDIT-1-4, open); narrate it both times.
- **Document Vault is contract-scoped.** Select a contract, choose the document type, then upload a PDF or Excel file (maximum 50 MB); uploaded files can be downloaded from the same page.
- **Bill lines have no entry UI** — see A1/Appendix 1. Session 1 is scoped around it.
- **Items grid is desktop-only comfort** — do the session on a laptop, not a phone.
- Sidebar nav shows three working items: Contracts, Index Manager, and Document Vault.
