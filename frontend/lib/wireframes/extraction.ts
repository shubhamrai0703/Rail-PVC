/**
 * Fixture data for the document-extraction prefill wireframes.
 *
 * WIREFRAME ONLY. Nothing here talks to the API, and nothing here is real
 * contractor data — tender numbers, contractor names and every rupee amount are
 * synthetic. The *structure* mirrors what was verified against the real
 * tabulation statements (see tasks/todo.md): a two-schedule contract with a
 * zero overall rebate, and a three-schedule contract (DSR / IRUSSOR / NS) with a
 * non-zero rebate on the gross offer value.
 *
 * The pricing chain modelled here is:
 *
 *   basic cost →(escalation %)→ ADVERTISED VALUE   [per item, summed per schedule]
 *              →(schedule bid % below)→ schedule bid amount
 *              →(Σ schedules)→ Gross Offer Value
 *              →(rebate on gross value %)→ NET OFFER VALUE = accepted value
 */

/** How much the extractor trusts a value it proposed. */
export type Confidence = "high" | "medium" | "low";

/**
 * Lifecycle of a single proposed field.
 *
 * `conflict` / `missing` / `unreadable` are *blocking* — the wireframes must
 * never let these save, and must never quietly coerce them to 0 or "".
 */
export type FieldState =
  | "proposed"
  | "confirmed"
  | "rejected"
  | "conflict"
  | "missing"
  | "unreadable";

export const BLOCKING_STATES: readonly FieldState[] = [
  "conflict",
  "missing",
  "unreadable",
];

export function isBlocking(state: FieldState): boolean {
  return BLOCKING_STATES.includes(state);
}

/** Where a proposed value came from. Never optional on a proposed value. */
export type SourceRef = {
  /** Document label as shown in the vault. */
  doc: string;
  /** 1-indexed page, or null for spreadsheet sources. */
  page: number | null;
  /** Human-readable locator: table caption, cell address, or region note. */
  locator: string;
};

export type Extracted<T> = {
  value: T | null;
  state: FieldState;
  confidence: Confidence;
  /** null only when state is `missing` — there is no source for a value that isn't there. */
  source: SourceRef | null;
  /** Populated when two documents disagree. Drives the conflict resolution UI. */
  alternatives?: { value: T; source: SourceRef }[];
  /** Why this is blocked / uncertain. Shown verbatim to the user. */
  note?: string;
};

export function extracted<T>(
  value: T,
  source: SourceRef,
  confidence: Confidence = "high",
  state: FieldState = "proposed",
): Extracted<T> {
  return { value, state, confidence, source };
}

// ---------------------------------------------------------------------------
// Screen 1 — documents
// ---------------------------------------------------------------------------

export type DocKind =
  | "agreement"
  | "loa"
  | "fin_tab"
  | "boq"
  | "mb"
  | "signed_bill"
  | "recoveries"
  | "unknown";

export const DOC_KIND_LABEL: Record<DocKind, string> = {
  agreement: "Agreement",
  loa: "LOA",
  fin_tab: "Tabulation statement (FIN-TAB)",
  boq: "Schedule / BOQ",
  mb: "Measurement book",
  signed_bill: "Signed bill",
  recoveries: "Signed recoveries",
  unknown: "Unrecognised",
};

/**
 * `text` = digital text layer, parseable.
 * `native` = spreadsheet, the easiest target.
 * `scanned` = image-only, the one OCR case — must degrade, never silently fail.
 */
export type TextLayer = "native" | "text" | "scanned";

export type UploadedDoc = {
  id: string;
  filename: string;
  sizeLabel: string;
  pages: number | null;
  textLayer: TextLayer;
  proposedKind: DocKind;
  confidence: Confidence;
  /** Set when the classifier could not decide — user must pick. */
  note?: string;
};

/** Documents a complete contract wants. Drives the "what's still missing" list. */
export const REQUIRED_DOC_KINDS: readonly DocKind[] = [
  "agreement",
  "loa",
  "fin_tab",
  "boq",
];

// ---------------------------------------------------------------------------
// Screen 2 — contract & pricing
// ---------------------------------------------------------------------------

export type ScheduleFixture = {
  id: string;
  name: string;
  /**
   * Free text with suggestions — NOT a closed dropdown. More Railway rate books
   * exist than we have seen (DSR, NS, IRUSSOR, …).
   */
  rateSource: Extracted<string>;
  /**
   * The field that actually drives the PVC extra-item eligibility gate.
   * Proposing this wrongly has calculation consequences — high-stakes confirm.
   */
  isExtraItems: Extracted<boolean>;
  basicCost: Extracted<number>;
  /**
   * Per-item in the printed statement (DSR `(-) 10.00`, everything else `At Par`).
   * NOT modelled in the schema today — surfaced as a proposed field only.
   */
  escalationPct: Extracted<number>;
  advertisedValue: Extracted<number>;
  bidBelowPct: Extracted<number>;
  bidAmount: Extracted<number>;
};

export type ContractFixture = {
  id: string;
  label: string;
  blurb: string;
  tenderNumber: Extracted<string>;
  contractorName: Extracted<string>;
  baseMonth: Extracted<string>;
  railwayZone: Extracted<string>;
  schedules: ScheduleFixture[];
  /** Applies to the gross schedule total — never to item rates. */
  overallRebatePct: Extracted<number>;
};

const FIN_TAB = (page: number, locator: string): SourceRef => ({
  doc: "FIN-TAB tabulation statement.pdf",
  page,
  locator,
});

const LOA = (page: number, locator: string): SourceRef => ({
  doc: "LOA.pdf",
  page,
  locator,
});

const AGREEMENT = (page: number, locator: string): SourceRef => ({
  doc: "Final Agreement.pdf",
  page,
  locator,
});

/**
 * Fixture A — two schedules, zero overall rebate.
 *
 * Basic 12,000,000.00 →(-10%)→ advertised 10,800,000.00 →(45% below)→ 5,940,000.00
 * Basic  5,000,000.00 →(At Par)→ advertised 5,000,000.00 →(40% below)→ 3,000,000.00
 * Gross 8,940,000.00 →(0.00%)→ net 8,940,000.00.  Total advertised 15,800,000.00.
 */
const CONTRACT_A: ContractFixture = {
  id: "ta-24-25-101",
  label: "TA-24-25-101 — two schedules, 0% rebate",
  blurb:
    "The common shape: one DSR schedule at (-) 10.00 escalation, one non-scheduled at par, and no rebate on the gross value.",
  tenderNumber: extracted("TA-24-25-101", LOA(1, "Letter head, ref. line")),
  contractorName: extracted(
    "Meridian Infra Pvt Ltd",
    LOA(1, "Addressee block"),
  ),
  baseMonth: extracted("2024-12", AGREEMENT(3, "Clause 3.2 — base month")),
  railwayZone: extracted("WR", LOA(1, "Issuing office")),
  overallRebatePct: extracted(
    0,
    FIN_TAB(2, "'Rebate on Gross Value (%)' row"),
  ),
  schedules: [
    {
      id: "a",
      name: "Schedule A — All DSR Items",
      rateSource: extracted("DSR", FIN_TAB(2, "Schedule heading")),
      isExtraItems: extracted(
        false,
        FIN_TAB(2, "Schedule heading"),
        "medium",
      ),
      basicCost: extracted(12_000_000, FIN_TAB(2, "'Basic cost' column")),
      escalationPct: extracted(-10, FIN_TAB(2, "'Escalation (%)' column")),
      advertisedValue: extracted(
        10_800_000,
        FIN_TAB(2, "'Advt. Value (Rs.)' column"),
      ),
      bidBelowPct: extracted(45, FIN_TAB(2, "'Bid Rate' column")),
      bidAmount: extracted(5_940_000, FIN_TAB(2, "'Bid Amount' column")),
    },
    {
      id: "b",
      name: "Schedule B — All Non Scheduled Items",
      rateSource: extracted("NS", FIN_TAB(2, "Schedule heading")),
      isExtraItems: extracted(false, FIN_TAB(2, "Schedule heading"), "low", "conflict"),
      basicCost: extracted(5_000_000, FIN_TAB(2, "'Basic cost' column")),
      escalationPct: extracted(0, FIN_TAB(2, "'Escalation (%)' column — 'At Par'")),
      advertisedValue: extracted(
        5_000_000,
        FIN_TAB(2, "'Advt. Value (Rs.)' column"),
      ),
      bidBelowPct: {
        value: 40,
        state: "conflict",
        confidence: "low",
        source: FIN_TAB(2, "'Bid Rate' column"),
        alternatives: [
          { value: 40, source: FIN_TAB(2, "'Bid Rate' column") },
          { value: 40.5, source: LOA(2, "Acceptance para, line 4") },
        ],
        note: "The tabulation statement and the LOA state different bid percentages for this schedule. Both are quoted below — pick the governing document, or enter the value by hand.",
      },
      bidAmount: extracted(3_000_000, FIN_TAB(2, "'Bid Amount' column")),
    },
  ],
};

/**
 * Fixture B — three schedules including IRUSSOR, non-zero rebate.
 *
 * Basic 20,000,000.00 →(-10%)→ 18,000,000.00 →(55% below)→ 8,100,000.00
 * Basic  4,000,000.00 →(At Par)→ 4,000,000.00 →(20% below)→ 3,200,000.00
 * Basic  6,000,000.00 →(At Par)→ 6,000,000.00 →(32% below)→ 4,080,000.00
 * Gross 15,380,000.00 →(2.75%)→ net 14,957,050.00.  Total advertised 28,000,000.00.
 */
const CONTRACT_B: ContractFixture = {
  id: "ta-24-25-207",
  label: "TA-24-25-207 — three schedules, 2.75% rebate",
  blurb:
    "The shape that breaks two-schedule assumptions: a third IRUSSOR schedule whose rate book is not in any enum we ship, plus a real rebate on the gross offer value.",
  tenderNumber: extracted("TA-24-25-207", LOA(1, "Letter head, ref. line")),
  contractorName: extracted(
    "Northgate Constructions",
    LOA(1, "Addressee block"),
  ),
  baseMonth: {
    value: null,
    state: "missing",
    confidence: "low",
    source: null,
    note: "No base month found. The agreement clause that normally carries it is on a page with no text layer. Base month drives every quarter in the calculation — it cannot be defaulted.",
  },
  railwayZone: extracted("WR", LOA(1, "Issuing office")),
  overallRebatePct: extracted(
    2.75,
    FIN_TAB(3, "'Rebate on Gross Value (%)' row"),
  ),
  schedules: [
    {
      id: "a",
      name: "Schedule A — All DSR Items",
      rateSource: extracted("DSR", FIN_TAB(3, "Schedule heading")),
      isExtraItems: extracted(false, FIN_TAB(3, "Schedule heading"), "medium"),
      basicCost: extracted(20_000_000, FIN_TAB(3, "'Basic cost' column")),
      escalationPct: extracted(-10, FIN_TAB(3, "'Escalation (%)' column")),
      advertisedValue: extracted(
        18_000_000,
        FIN_TAB(3, "'Advt. Value (Rs.)' column"),
      ),
      bidBelowPct: extracted(55, FIN_TAB(3, "'Bid Rate' column")),
      bidAmount: extracted(8_100_000, FIN_TAB(3, "'Bid Amount' column")),
    },
    {
      id: "b",
      name: "Schedule B — IRUSSOR Items",
      rateSource: extracted("IRUSSOR", FIN_TAB(3, "Schedule heading"), "low"),
      isExtraItems: extracted(false, FIN_TAB(3, "Schedule heading"), "low"),
      basicCost: extracted(4_000_000, FIN_TAB(3, "'Basic cost' column")),
      escalationPct: extracted(0, FIN_TAB(3, "'Escalation (%)' column — 'At Par'")),
      advertisedValue: extracted(
        4_000_000,
        FIN_TAB(3, "'Advt. Value (Rs.)' column"),
      ),
      bidBelowPct: extracted(20, FIN_TAB(3, "'Bid Rate' column")),
      bidAmount: extracted(3_200_000, FIN_TAB(3, "'Bid Amount' column")),
    },
    {
      id: "c",
      name: "Schedule C — All Non Scheduled Items",
      rateSource: extracted("NS", FIN_TAB(3, "Schedule heading")),
      isExtraItems: extracted(true, FIN_TAB(3, "Schedule heading"), "low"),
      basicCost: extracted(6_000_000, FIN_TAB(3, "'Basic cost' column")),
      escalationPct: extracted(0, FIN_TAB(3, "'Escalation (%)' column — 'At Par'")),
      advertisedValue: extracted(
        6_000_000,
        FIN_TAB(3, "'Advt. Value (Rs.)' column"),
      ),
      bidBelowPct: extracted(32, FIN_TAB(3, "'Bid Rate' column")),
      bidAmount: extracted(4_080_000, FIN_TAB(3, "'Bid Amount' column")),
    },
  ],
};

export const CONTRACT_FIXTURES: readonly ContractFixture[] = [
  CONTRACT_A,
  CONTRACT_B,
];

/** Rate books we can suggest. The input must still accept anything else. */
export const RATE_SOURCE_SUGGESTIONS: readonly string[] = [
  "DSR",
  "NS",
  "IRUSSOR",
  "USSOR",
  "LAR",
];

export function grossOfferValue(c: ContractFixture): number {
  return c.schedules.reduce((sum, s) => sum + (s.bidAmount.value ?? 0), 0);
}

export function totalAdvertised(c: ContractFixture): number {
  return c.schedules.reduce((sum, s) => sum + (s.advertisedValue.value ?? 0), 0);
}

export function netOfferValue(c: ContractFixture): number {
  const gross = grossOfferValue(c);
  const rebate = c.overallRebatePct.value ?? 0;
  return gross * (1 - rebate / 100);
}

// ---------------------------------------------------------------------------
// Screen 3 — items
// ---------------------------------------------------------------------------

export type SteelSubtype = "angles" | "plates" | "tmt" | "other" | null;

export type ItemFixture = {
  id: string;
  scheduleId: string;
  code: string;
  description: string;
  unit: string;
  originalQty: number;
  baseRate: number;
  agreementRate: number;
  isCement: Extracted<boolean>;
  /** Classified once on the item master, never per bill. */
  steelSubtype: Extracted<SteelSubtype>;
};

export const ITEM_FIXTURES: readonly ItemFixture[] = [
  {
    id: "i1",
    scheduleId: "a",
    code: "3.11.2",
    description: "Providing and laying M-25 design mix cement concrete",
    unit: "cum",
    originalQty: 420,
    baseRate: 6_850,
    agreementRate: 3_767.5,
    isCement: extracted(true, { doc: "Schedule BOQ.xlsx", page: null, locator: "Sheet 'Table 1', row 12" }),
    steelSubtype: extracted(null, { doc: "Schedule BOQ.xlsx", page: null, locator: "Sheet 'Table 1', row 12" }),
  },
  {
    id: "i2",
    scheduleId: "a",
    code: "5.02.1",
    description: "Supplying and fixing TMT reinforcement bars, cut and bent",
    unit: "MT",
    originalQty: 38,
    baseRate: 74_200,
    agreementRate: 40_810,
    isCement: extracted(false, { doc: "Schedule BOQ.xlsx", page: null, locator: "Sheet 'Table 1', row 21" }),
    steelSubtype: extracted("tmt", { doc: "Schedule BOQ.xlsx", page: null, locator: "Sheet 'Table 1', row 21" }),
  },
  {
    id: "i3",
    scheduleId: "a",
    code: "5.09.4",
    description: "Structural steel work in built-up sections, angles and plates",
    unit: "MT",
    originalQty: 12,
    baseRate: 91_500,
    agreementRate: 50_325,
    isCement: extracted(false, { doc: "Schedule BOQ.xlsx", page: null, locator: "Sheet 'Table 1', row 24" }),
    steelSubtype: {
      value: "angles",
      state: "proposed",
      confidence: "low",
      source: { doc: "Schedule BOQ.xlsx", page: null, locator: "Sheet 'Table 1', row 24" },
      note: "The description names both angles and plates. Subtype routes the line to a different PVC bucket, so this needs a human decision rather than a guess.",
    },
  },
  {
    id: "i4",
    scheduleId: "b",
    code: "NS-1",
    description: "Non-scheduled: supply and installation of proprietary drainage assembly",
    unit: "nos",
    originalQty: 6,
    baseRate: 128_000,
    agreementRate: 76_800,
    isCement: {
      value: null,
      state: "unreadable",
      confidence: "low",
      source: {
        doc: "Signed recoveries.pdf",
        page: 2,
        locator: "Scanned region — no text layer",
      },
      note: "This item's classification row falls on a scanned page. Nothing was extracted; classify it by hand.",
    },
    steelSubtype: {
      value: null,
      state: "unreadable",
      confidence: "low",
      source: {
        doc: "Signed recoveries.pdf",
        page: 2,
        locator: "Scanned region — no text layer",
      },
    },
  },
];

// ---------------------------------------------------------------------------
// Screen 4 — bills
// ---------------------------------------------------------------------------

export type BillFixture = {
  id: string;
  slot: number;
  billNumber: Extracted<string>;
  billDate: Extracted<string>;
  /** Retained as evidence only. */
  measurementPeriodStart: Extracted<string>;
  /** The period END drives quarter selection. */
  measurementPeriodEnd: Extracted<string>;
  grossValue: Extracted<number>;
  lineCount: number;
  /** Documents attached to this bill slot, by kind. */
  attached: DocKind[];
  missing: DocKind[];
};

const MB = (page: number, locator: string): SourceRef => ({
  doc: "1st–3rd MB.pdf",
  page,
  locator,
});

const BILL = (page: number, locator: string): SourceRef => ({
  doc: "1st–3rd Bill.pdf",
  page,
  locator,
});

export const BILL_FIXTURES: readonly BillFixture[] = [
  {
    id: "b1",
    slot: 1,
    billNumber: extracted("1st on-account", BILL(1, "Bill header")),
    billDate: extracted("2025-06-28", BILL(1, "Bill header")),
    measurementPeriodStart: extracted("2025-05-09", MB(4, "'Date of Measurement: From'")),
    measurementPeriodEnd: extracted("2025-06-18", MB(4, "'Date of Measurement: to'")),
    grossValue: extracted(2_184_500, BILL(3, "'Gross value of work done'")),
    lineCount: 14,
    attached: ["mb", "signed_bill"],
    missing: [],
  },
  {
    id: "b2",
    slot: 2,
    billNumber: extracted("2nd on-account", BILL(6, "Bill header")),
    billDate: extracted("2025-09-30", BILL(6, "Bill header")),
    measurementPeriodStart: extracted("2025-06-19", MB(11, "'Date of Measurement: From'")),
    measurementPeriodEnd: extracted("2025-09-12", MB(11, "'Date of Measurement: to'")),
    grossValue: {
      value: null,
      state: "conflict",
      confidence: "low",
      source: BILL(8, "'Gross value of work done'"),
      alternatives: [
        { value: 3_412_775, source: BILL(8, "'Gross value of work done'") },
        { value: 3_412_275, source: MB(19, "Abstract total") },
      ],
      note: "The signed bill and the measurement book abstract differ by ₹500.00. Neither is authoritative on its own — resolve before this bill can save.",
    },
    lineCount: 21,
    attached: ["mb", "signed_bill", "recoveries"],
    missing: [],
  },
  {
    id: "b3",
    slot: 3,
    billNumber: {
      value: null,
      state: "missing",
      confidence: "low",
      source: null,
      note: "No third bill document has been uploaded to this slot yet.",
    },
    billDate: { value: null, state: "missing", confidence: "low", source: null },
    measurementPeriodStart: { value: null, state: "missing", confidence: "low", source: null },
    measurementPeriodEnd: { value: null, state: "missing", confidence: "low", source: null },
    grossValue: { value: null, state: "missing", confidence: "low", source: null },
    lineCount: 0,
    attached: [],
    missing: ["mb", "signed_bill"],
  },
];

// ---------------------------------------------------------------------------
// Screen 5 — reconciliation
// ---------------------------------------------------------------------------

export type CheckStatus = "pass" | "fail" | "skipped";

export type ReconCheck = {
  id: string;
  label: string;
  /** What the check actually compares, in the user's language. */
  detail: string;
  status: CheckStatus;
  /** Shown for failures: the two numbers that disagree. */
  observed?: string;
  expected?: string;
  /** Why it could not run. */
  skipReason?: string;
  fixHref?: string;
  fixLabel?: string;
};

export const RECON_CHECKS: readonly ReconCheck[] = [
  {
    id: "r1",
    label: "Cumulative = previous + current",
    detail: "Per bill line, the cumulative quantity must equal the previous cumulative plus this bill's quantity.",
    status: "fail",
    observed: "Line 5.02.1 — cumulative 41.000 MT",
    expected: "38.000 + 2.500 = 40.500 MT",
    fixLabel: "Open bill 2, line 5.02.1",
  },
  {
    id: "r2",
    label: "Bill total reconciles to line totals",
    detail: "The gross value printed on the bill must equal the sum of its line amounts.",
    status: "skipped",
    skipReason: "Bill 2 gross value is unresolved — two documents disagree. Resolve the conflict on the bill screen first.",
    fixLabel: "Resolve bill 2 gross value",
  },
  {
    id: "r3",
    label: "Item codes exist in the confirmed schedule",
    detail: "Every code billed must appear in the confirmed item master.",
    status: "fail",
    observed: "Code 6.14.9 appears on bill 1 but not in any confirmed schedule",
    expected: "All billed codes present in the item master",
    fixLabel: "Add 6.14.9 or correct the bill line",
  },
  {
    id: "r4",
    label: "Bid % and rebate agree with the stated values",
    detail: "Recomputed schedule bid amounts and the net offer value must match the tabulation statement.",
    status: "pass",
  },
  {
    id: "r5",
    label: "Bill sequence does not go backwards",
    detail: "Each bill's measurement period must start on or after the previous bill's period end.",
    status: "pass",
  },
  {
    id: "r6",
    label: "MB and signed bill agree",
    detail: "Quantities in the measurement book must match the signed bill for the same line.",
    status: "skipped",
    skipReason: "Bill 3 has no measurement book. The check cannot run against a missing document.",
    fixLabel: "Upload bill 3 documents",
  },
];

export const UPLOADED_DOCS: readonly UploadedDoc[] = [
  {
    id: "d1",
    filename: "Final Agreement.pdf",
    sizeLabel: "4.2 MB",
    pages: 114,
    textLayer: "text",
    proposedKind: "agreement",
    confidence: "high",
  },
  {
    id: "d2",
    filename: "LOA.pdf",
    sizeLabel: "310 KB",
    pages: 3,
    textLayer: "text",
    proposedKind: "loa",
    confidence: "high",
  },
  {
    id: "d3",
    filename: "FIN-TAB tabulation statement.pdf",
    sizeLabel: "88 KB",
    pages: 4,
    textLayer: "text",
    proposedKind: "fin_tab",
    confidence: "high",
  },
  {
    id: "d4",
    filename: "Schedule BOQ.xlsx",
    sizeLabel: "142 KB",
    pages: null,
    textLayer: "native",
    proposedKind: "boq",
    confidence: "high",
  },
  {
    id: "d5",
    filename: "1st–3rd MB.pdf",
    sizeLabel: "9.1 MB",
    pages: 46,
    textLayer: "text",
    proposedKind: "mb",
    confidence: "medium",
    note: "Most of the text found on these pages is letterhead and stamps. Table structure is not yet proven — expect partial results.",
  },
  {
    id: "d6",
    filename: "1st–3rd Bill.pdf",
    sizeLabel: "1.4 MB",
    pages: 12,
    textLayer: "text",
    proposedKind: "signed_bill",
    confidence: "high",
  },
  {
    id: "d7",
    filename: "Signed recoveries.pdf",
    sizeLabel: "6.8 MB",
    pages: 5,
    textLayer: "scanned",
    proposedKind: "recoveries",
    confidence: "low",
    note: "Image-only — no text layer. Nothing can be read from this document without OCR, and OCR on a signed scan is not trustworthy for money. Expect to enter these by hand.",
  },
  {
    id: "d8",
    filename: "scan_0042.pdf",
    sizeLabel: "2.1 MB",
    pages: 2,
    textLayer: "scanned",
    proposedKind: "unknown",
    confidence: "low",
    note: "Could not be classified. Pick a type, or leave it out of the extraction.",
  },
];
