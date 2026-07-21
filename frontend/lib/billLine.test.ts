import { describe, expect, it } from "vitest";

import { billLineSchema } from "./billLine";

const validValues = {
  item_id: "item-123",
  qty_up_to_last: "100.125",
  qty_since_last: "2.005",
  qty_up_to_date: "102.130",
  amount_up_to_last: "99999999999.1234",
  amount_since_last: "2500.50",
  amount_up_to_date: "99999999999.9999",
  special_condition_amount: "0",
};

describe("billLineSchema", () => {
  it("requires a selectable contract item", () => {
    const result = billLineSchema.safeParse({ ...validValues, item_id: "" });

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.flatten().fieldErrors.item_id).toContain(
        "select an item",
      );
    }
  });

  it.each(["", "not-a-number", "1,000", "1e3"])(
    "rejects an invalid decimal input: %j",
    (invalid) => {
      const result = billLineSchema.safeParse({
        ...validValues,
        amount_since_last: invalid,
      });

      expect(result.success).toBe(false);
    },
  );

  it.each(["100000000000", "0.00001", "-999999999999.9999"])(
    "rejects a decimal outside the database precision: %j",
    (invalid) => {
      const result = billLineSchema.safeParse({
        ...validValues,
        amount_since_last: invalid,
      });

      expect(result.success).toBe(false);
    },
  );

  it("does not count leading zeros toward database precision", () => {
    const result = billLineSchema.safeParse({
      ...validValues,
      amount_since_last: "000000000001.2500",
    });

    expect(result.success).toBe(true);
  });
});

describe("billLineSchema payload", () => {
  it("preserves every decimal as a string without number coercion", () => {
    const payload = billLineSchema.parse(validValues);

    expect(payload).toEqual(validValues);
    expect(payload.amount_up_to_last).toBe("99999999999.1234");
    expect(
      Object.values(payload).every((value) => typeof value === "string"),
    ).toBe(true);
  });

  it("trims surrounding whitespace without changing decimal text", () => {
    expect(
      billLineSchema.parse({
        ...validValues,
        item_id: "  item-123  ",
        qty_since_last: " 2.0050 ",
      }),
    ).toMatchObject({ item_id: "item-123", qty_since_last: "2.0050" });
  });
});
