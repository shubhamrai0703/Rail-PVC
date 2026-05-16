// Indian numbering system: 1,23,45,678.90 (lakh/crore grouping)
// Used for any rupee amount surfaced in the UI.
const INR_FORMATTER = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatINR(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "—";
  return INR_FORMATTER.format(n);
}

export function formatINRWithSymbol(value: number | string | null | undefined): string {
  const formatted = formatINR(value);
  if (formatted === "—") return formatted;
  return `₹${formatted}`;
}
