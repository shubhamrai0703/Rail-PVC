// Deterministic header-to-target-field matcher for the smart items-import
// flow (P5-IMP, Option A). Pure module — unit-testable.
//
// Given an array of source headers from a BOQ Excel sheet, suggest a
// mapping to the canonical contract_items schema. Falls back to AI
// (Option B) only when this matcher leaves required fields unmapped.

export const TARGET_FIELDS = [
  "item_code",
  "description",
  "unit",
  "original_qty",
  "revised_qty",
  "base_rate",
  "agreement_rate",
  "is_cement_item",
  "steel_subtype",
] as const;

export type TargetField = (typeof TARGET_FIELDS)[number];

export const REQUIRED_FIELDS: ReadonlySet<TargetField> = new Set([
  "item_code",
  "description",
  "unit",
  "original_qty",
  "base_rate",
  "agreement_rate",
]);

// Synonyms are scored by best-match: exact normalized match = 1.0,
// substring or token containment = lower. Order within each list does
// not matter for matching but the first entry is treated as the
// canonical display label.
const SYNONYMS: Record<TargetField, readonly string[]> = {
  item_code: [
    "item code",
    "item no",
    "item number",
    "item",
    "code",
    "boq code",
    "boq item",
    "sl no",
    "s no",
    "sno",
    "sr no",
    "serial",
  ],
  description: [
    "description",
    "item description",
    "description of item",
    "description of work",
    "particulars",
    "work description",
    "details",
  ],
  unit: ["unit", "uom", "units", "unit of measurement"],
  original_qty: [
    "original qty",
    "original quantity",
    "agreement qty",
    "agreement quantity",
    "boq qty",
    "boq quantity",
    "tendered qty",
    "tender qty",
    "as per agreement",
    "qty as per agreement",
    "quantity",
    "qty",
  ],
  revised_qty: [
    "revised qty",
    "revised quantity",
    "current qty",
    "current quantity",
    "updated qty",
    "executed qty",
    "executed quantity",
    "actual qty",
    "actual quantity",
  ],
  base_rate: [
    "base rate",
    "sor rate",
    "dsr rate",
    "schedule rate",
    "estimate rate",
    "estimated rate",
    "ssr rate",
    "ussor rate",
  ],
  agreement_rate: [
    "agreement rate",
    "contract rate",
    "tender rate",
    "tendered rate",
    "quoted rate",
    "accepted rate",
    "rate",
  ],
  is_cement_item: [
    "is cement item",
    "is cement",
    "cement item",
    "cement",
  ],
  steel_subtype: [
    "steel subtype",
    "steel type",
    "steel category",
    "steel",
  ],
};

export interface HeaderMatch {
  source: string;
  target: TargetField | null;
  confidence: number;
}

export interface MapResult {
  mapping: Record<string, TargetField | null>;
  confidence: Record<TargetField, number>;
  unmapped: string[];
  missingRequired: TargetField[];
}

function normalize(s: string): string {
  return s
    .toLowerCase()
    .replace(/[._\-/\\()[\]{}:;,]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function tokens(s: string): string[] {
  return normalize(s).split(" ").filter((t) => t.length > 0);
}

function scoreSynonym(headerNorm: string, headerTokens: string[], synonym: string): number {
  const synNorm = normalize(synonym);
  if (headerNorm === synNorm) return 1.0;

  const synTokens = tokens(synonym);
  if (synTokens.length === 0) return 0;

  // Substring match (e.g. "agreement qty (cum)" contains "agreement qty").
  if (headerNorm.includes(synNorm)) {
    return 0.85;
  }
  if (synNorm.includes(headerNorm) && headerNorm.length >= 3) {
    return 0.75;
  }

  // Token-set overlap.
  const headerSet = new Set(headerTokens);
  const overlap = synTokens.filter((t) => headerSet.has(t)).length;
  if (overlap === synTokens.length) return 0.7;
  if (overlap > 0) return 0.4 + 0.2 * (overlap / synTokens.length);
  return 0;
}

function bestTargetForHeader(header: string): {
  target: TargetField | null;
  confidence: number;
} {
  const headerNorm = normalize(header);
  if (headerNorm === "") return { target: null, confidence: 0 };
  const headerTokens = tokens(header);

  let best: { target: TargetField | null; confidence: number } = {
    target: null,
    confidence: 0,
  };

  for (const target of TARGET_FIELDS) {
    let fieldBest = 0;
    for (const syn of SYNONYMS[target]) {
      const s = scoreSynonym(headerNorm, headerTokens, syn);
      if (s > fieldBest) fieldBest = s;
    }
    if (fieldBest > best.confidence) {
      best = { target, confidence: fieldBest };
    }
  }

  // Threshold below which we treat the header as unmapped.
  if (best.confidence < 0.55) return { target: null, confidence: best.confidence };
  return best;
}

export function fuzzyHeaderMap(headers: readonly string[]): MapResult {
  const mapping: Record<string, TargetField | null> = {};
  const confidence: Record<TargetField, number> = Object.fromEntries(
    TARGET_FIELDS.map((f) => [f, 0]),
  ) as Record<TargetField, number>;
  const unmapped: string[] = [];

  // First pass: best target per header.
  const candidates: HeaderMatch[] = headers.map((h) => {
    const { target, confidence: c } = bestTargetForHeader(h);
    return { source: h, target, confidence: c };
  });

  // Resolve collisions: if two headers want the same target, keep the
  // higher-confidence one and demote the loser to null.
  const byTarget = new Map<TargetField, HeaderMatch>();
  for (const cand of candidates) {
    if (cand.target === null) continue;
    const existing = byTarget.get(cand.target);
    if (existing === undefined || cand.confidence > existing.confidence) {
      if (existing !== undefined) {
        // Demote the previous winner.
        const demoted = candidates.find((c) => c === existing);
        if (demoted) demoted.target = null;
      }
      byTarget.set(cand.target, cand);
    } else {
      cand.target = null;
    }
  }

  for (const cand of candidates) {
    mapping[cand.source] = cand.target;
    if (cand.target === null) {
      unmapped.push(cand.source);
    } else {
      confidence[cand.target] = cand.confidence;
    }
  }

  const missingRequired = [...REQUIRED_FIELDS].filter(
    (f) => !byTarget.has(f),
  );

  return { mapping, confidence, unmapped, missingRequired };
}
