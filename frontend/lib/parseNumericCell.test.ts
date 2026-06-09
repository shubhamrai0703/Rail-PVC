import { describe, it, expect } from "vitest";
import { parseNumericCell } from "./parseNumericCell";

describe("parseNumericCell", () => {
  it("treats null/undefined/blank as an explicit clear", () => {
    expect(parseNumericCell(null)).toEqual({ ok: true, value: null });
    expect(parseNumericCell(undefined)).toEqual({ ok: true, value: null });
    expect(parseNumericCell("")).toEqual({ ok: true, value: null });
    expect(parseNumericCell("   ")).toEqual({ ok: true, value: null });
  });

  it("parses plain decimals", () => {
    expect(parseNumericCell("123")).toEqual({ ok: true, value: 123 });
    expect(parseNumericCell("123.45")).toEqual({ ok: true, value: 123.45 });
    expect(parseNumericCell("-5")).toEqual({ ok: true, value: -5 });
    expect(parseNumericCell(987.6)).toEqual({ ok: true, value: 987.6 });
  });

  it("strips thousand separators and spaces", () => {
    expect(parseNumericCell("1,23,456")).toEqual({ ok: true, value: 123456 });
    expect(parseNumericCell("1,234.56")).toEqual({ ok: true, value: 1234.56 });
    expect(parseNumericCell(" 1 000 ")).toEqual({ ok: true, value: 1000 });
  });

  it("rejects non-numeric garbage instead of nulling it", () => {
    expect(parseNumericCell("abc")).toEqual({ ok: false, value: null });
    expect(parseNumericCell("12abc")).toEqual({ ok: false, value: null });
    expect(parseNumericCell("NaN")).toEqual({ ok: false, value: null });
  });

  it("rejects non-decimal numeric notations", () => {
    expect(parseNumericCell("0x10")).toEqual({ ok: false, value: null });
    expect(parseNumericCell("1e3")).toEqual({ ok: false, value: null });
    expect(parseNumericCell("Infinity")).toEqual({ ok: false, value: null });
  });
});
