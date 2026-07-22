import { describe, expect, it } from "vitest";

import {
  DOCUMENT_TYPES,
  MAX_DOCUMENT_BYTES,
  documentFileError,
} from "./documents";

describe("documentFileError", () => {
  it("accepts files at the 50 MB API ceiling", () => {
    expect(documentFileError({ name: "agreement.pdf", size: MAX_DOCUMENT_BYTES })).toBeNull();
  });

  it("rejects files over the 50 MB API ceiling", () => {
    expect(
      documentFileError({ name: "agreement.pdf", size: MAX_DOCUMENT_BYTES + 1 }),
    ).toContain("50 MB");
  });

  it("rejects an empty file", () => {
    expect(documentFileError({ name: "empty.pdf", size: 0 })).toBe("Choose a non-empty file.");
  });
});

describe("DOCUMENT_TYPES", () => {
  it("matches the backend document_type enum", () => {
    expect(DOCUMENT_TYPES.map(({ value }) => value)).toEqual([
      "agreement",
      "mb",
      "bill",
      "recovery",
      "workbook",
      "other",
    ]);
  });
});
