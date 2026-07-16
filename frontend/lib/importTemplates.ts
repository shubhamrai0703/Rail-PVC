// Saved column-mapping templates for the smart items-import flow
// (P5-IMP-FUP-2). Pure module — unit-testable. Server CRUD lives in
// backend/api/imports.py; this module holds the client-side types and
// the deterministic pieces (source signature, template application).

import { TARGET_FIELDS, normalizeHeader, type TargetField } from "./fuzzyHeaderMap";
import type { Mapping } from "./normalizeImportRows";

export interface ImportTemplate {
  id: string;
  name: string;
  source_signature: string;
  mapping: Record<string, string | null>;
  value_normalizations: Record<string, Record<string, string>>;
  created_at: string;
  updated_at: string;
}

/**
 * Deterministic signature of a header set, used so a template saved from
 * one vendor's BOQ format is recognized the next time the same format is
 * imported. Header order and cosmetic differences (case, punctuation,
 * extra whitespace) don't change the signature; adding/removing/renaming
 * a column does. FNV-1a 32-bit — stable, dependency-free, and well under
 * the backend's 200-char `source_signature` limit.
 */
export function headerSignature(headers: readonly string[]): string {
  const canonical = headers
    .map(normalizeHeader)
    .filter((h) => h.length > 0)
    .sort()
    .join("\x1f");
  let hash = 0x811c9dc5;
  for (let i = 0; i < canonical.length; i++) {
    hash ^= canonical.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return `v1-${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

const VALID_TARGETS = new Set<string>(TARGET_FIELDS);

/**
 * Resolve a saved template against the current source headers. Matching is
 * by normalized header, so "Item Code" in the template still applies to
 * "item code" in a new file. Headers the template doesn't know about map
 * to null (ignore); template entries whose target is no longer a valid
 * field are dropped rather than crashing the mapper.
 */
export function applyTemplateMapping(
  template: Pick<ImportTemplate, "mapping">,
  headers: readonly string[],
): Mapping {
  const byNormalized = new Map<string, TargetField | null>();
  for (const [src, tgt] of Object.entries(template.mapping)) {
    const target = tgt !== null && VALID_TARGETS.has(tgt) ? (tgt as TargetField) : null;
    byNormalized.set(normalizeHeader(src), target);
  }
  const out: Mapping = {};
  for (const h of headers) {
    out[h] = byNormalized.get(normalizeHeader(h)) ?? null;
  }
  return out;
}
