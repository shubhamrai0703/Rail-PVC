import type { components } from "./api/schema";

export const MAX_DOCUMENT_BYTES = 50 * 1024 * 1024;

export const DOCUMENT_TYPES = [
  { value: "agreement", label: "Agreement" },
  { value: "mb", label: "Measurement book (MB)" },
  { value: "bill", label: "Bill" },
  { value: "recovery", label: "Recovery memo" },
  { value: "workbook", label: "PVC workbook" },
  { value: "other", label: "Other" },
] as const;

export type VaultDocument = components["schemas"]["DocumentRecord"];
export type DocumentType = VaultDocument["file_type"];

export function documentFileError(file: Pick<File, "name" | "size">): string | null {
  if (file.size === 0) return "Choose a non-empty file.";
  if (file.size > MAX_DOCUMENT_BYTES) return "File must be 50 MB or smaller.";
  return null;
}

export function documentTypeLabel(type: DocumentType): string {
  return DOCUMENT_TYPES.find(({ value }) => value === type)?.label ?? type;
}
