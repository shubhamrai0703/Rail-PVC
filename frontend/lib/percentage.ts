export const MAX_PERCENT_INPUT = 999.99;

export function optionalPercentInput(value: unknown): number | undefined {
  return value === "" || value === null || value === undefined
    ? undefined
    : Number(value);
}

export function percentInputOrZero(value: unknown): number {
  return optionalPercentInput(value) ?? 0;
}

export function percentToFraction(
  percent: number | undefined,
): number | undefined {
  return percent === undefined ? undefined : percent / 100;
}

export function fractionToPercent(
  fraction: string | number | null | undefined,
): number | undefined {
  return fraction === null || fraction === undefined
    ? undefined
    : Number(fraction) * 100;
}

export function formatFractionAsPercent(
  fraction: string | number,
): string {
  return `${fractionToPercent(fraction)?.toFixed(2)}%`;
}
