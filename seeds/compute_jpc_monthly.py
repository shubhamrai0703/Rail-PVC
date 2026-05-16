#!/usr/bin/env python3
"""
Compute monthly JPC steel price averages from fortnightly bulletin data.

Input:  REFERENCES/jpc_raw_extracted.csv
Output: REFERENCES/jpc_monthly_averages.csv  (columns: month, item, kolkata, delhi, mumbai, chennai, avg_4city)
        REFERENCES/jpc_monthly_warnings.log  (rows with high intra-city variance or outliers)

Method per month+item:
  1. Collect all fortnightly readings (1 or 2 per month).
  2. For each city, average available readings.
  3. Compute avg_4city = mean of 4 city averages.
  4. Flag if any city deviates >30% from the median of the other 3 (possible OCR error).

Idempotent: overwrites output on each run.
"""
import csv
import logging
import statistics
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV  = REPO_ROOT / "REFERENCES" / "jpc_raw_extracted.csv"
OUTPUT_CSV = REPO_ROOT / "REFERENCES" / "jpc_monthly_averages.csv"
WARN_LOG   = REPO_ROOT / "REFERENCES" / "jpc_monthly_warnings.log"

TARGET_ITEMS = [
    "TMT 10 MM", "TMT 25 MM", "ANGLES 75X75X6 MM",
    "CHANNELS 150X75 MM", "PLATES 10 MM", "PLATES 25 MM",
]
CITIES = ["kolkata", "delhi", "mumbai", "chennai"]

logging.basicConfig(
    filename=WARN_LOG,
    filemode="w",
    level=logging.WARNING,
    format="%(message)s",
)


def load_raw() -> dict:
    """Return {(month, item): [{city: value, ...}, ...]}"""
    data: dict = defaultdict(list)
    with open(INPUT_CSV) as f:
        for row in csv.DictReader(f):
            month = row["date"][:7]
            key = (month, row["item"])
            data[key].append({c: int(row[c]) for c in CITIES})
    return data


def city_avg(readings: list, city: str) -> float | None:
    vals = [r[city] for r in readings if r[city] > 0]
    return sum(vals) / len(vals) if vals else None


def flag_outliers(month: str, item: str, city_avgs: dict) -> None:
    for city, val in city_avgs.items():
        others = [v for k, v in city_avgs.items() if k != city]
        if len(others) < 3:
            continue
        med = statistics.median(others)
        if med > 0 and abs(val - med) / med > 0.30:
            logging.warning(
                f"{month} {item}: {city}={val:.0f} deviates >30%% from peer median {med:.0f}"
            )


def compute_monthly() -> list[dict]:
    raw = load_raw()
    results = []
    for month in sorted({k[0] for k in raw}):
        for item in TARGET_ITEMS:
            readings = raw.get((month, item))
            if not readings:
                logging.warning(f"{month} {item}: NO DATA")
                continue
            city_avgs = {}
            for city in CITIES:
                avg = city_avg(readings, city)
                if avg is not None:
                    city_avgs[city] = avg

            if len(city_avgs) < 4:
                logging.warning(
                    f"{month} {item}: only {len(city_avgs)}/4 cities have data"
                )

            flag_outliers(month, item, city_avgs)

            avg_4city = (
                sum(city_avgs.values()) / len(city_avgs) if city_avgs else None
            )
            results.append({
                "month": month,
                "item": item,
                **{c: f"{city_avgs[c]:.0f}" if c in city_avgs else "" for c in CITIES},
                "avg_4city": f"{avg_4city:.2f}" if avg_4city is not None else "",
                "bulletin_count": len(readings),
            })
    return results


def main() -> None:
    results = compute_monthly()
    fieldnames = ["month", "item", *CITIES, "avg_4city", "bulletin_count"]
    with open(OUTPUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    months = len({r["month"] for r in results})
    print(f"Written {len(results)} rows across {months} months → {OUTPUT_CSV}")
    print(f"Warnings → {WARN_LOG}")

    # Quick Dec-2024 cross-check
    dec24 = {r["item"]: r for r in results if r["month"] == "2024-12"}
    if dec24:
        print("\nDec-2024 cross-check (known: TMT~57812, Angles~58000, Plates-10~57370):")
        for item in TARGET_ITEMS:
            if item in dec24:
                r = dec24[item]
                print(f"  {item}: avg_4city={r['avg_4city']}  (n={r['bulletin_count']})")


if __name__ == "__main__":
    main()
