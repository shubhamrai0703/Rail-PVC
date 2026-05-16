"""
Seed RBI/JPC index data into the database.

Two sources:
  1. BCT-24-25-252 workbook (hardcoded) — Dec-2024 through Dec-2025 (13 months).
     RBI: all 13 months. JPC: Dec-2024 base + Q2/Q4-2025. Q1/Q3-2025 JPC = None.
     These values are authoritative — do not override with OCR data.

  2. OCR extraction (REFERENCES/jpc_monthly_averages.csv) — Apr-2022 through Nov-2024.
     JPC only. RBI not available for this period — must be sourced separately.
     Series mapping:
       steel_tmt            = avg(TMT 10 MM, TMT 25 MM)
       steel_angles         = ANGLES 75X75X6 MM
       steel_plates         = avg(PLATES 10 MM, PLATES 25 MM)
       steel_other_sections = CHANNELS 150X75 MM
     Quality caveats — see REFERENCES/jpc_monthly_warnings.log and OCR gap notes below.

OCR data gaps (months with 0 bulletins for a series → None inserted):
  TMT series: 2022-07, 2022-10, 2025-05 (2026-03 excluded — after hardcoded period)
  ANGLES:     2022-10, 2026-01
  CHANNELS:   2023-01, 2023-02, 2024-04, 2025-04, 2025-05, 2025-06
  PLATES:     2022-05 (plates-10), 2022-10, 2022-12, 2025-02, 2025-04

Run:       uv run python seeds/seed_indices.py   (from repo root or backend/)
Idempotent: INSERT ... ON CONFLICT DO NOTHING
"""

import asyncio
import csv
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

# Allow running from repo root or backend/
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env", override=True)

import asyncpg
from sqlalchemy.engine.url import make_url

REPO_ROOT = Path(__file__).resolve().parent.parent
MONTHLY_AVG_CSV = REPO_ROOT / "REFERENCES" / "jpc_monthly_averages.csv"

SERIES = [
    ("labour",               "RBI"),
    ("plant_machinery",      "RBI"),
    ("fuel",                 "RBI"),
    ("other_materials",      "RBI"),
    ("cement",               "RBI"),
    ("steel_tmt",            "JPC"),
    ("steel_angles",         "JPC"),
    ("steel_plates",         "JPC"),
    ("steel_other_sections", "JPC"),
]

# Authoritative workbook data. Covers Dec-2024 onwards — OCR data must not overwrite.
# Columns: month_str, labour, plant_machinery, fuel, other_materials, cement,
#          steel_tmt, steel_angles, steel_plates, steel_other_sections
# None = not published / not in workbook for that month.
WORKBOOK_OBSERVATIONS = [
    # Base month
    ("2024-12", 143.7, 160.0,   160.48, 155.7,  130.2,  57812.5,  58000.0,  57370.0,  57727.5),
    # Q1 2025 — RBI only
    ("2025-01", 143.2, 161.0,   160.48, 155.0,  130.2,  None,     None,     None,     None),
    ("2025-02", 142.8, 161.4,   160.48, 154.16, 132.8,  None,     None,     None,     None),
    ("2025-03", 143.0, 161.6,   160.48, 154.8,  131.0,  None,     None,     None,     None),
    # Q2 2025 — RBI + JPC
    ("2025-04", 143.5, 162.3,   160.48, 154.2,  130.5,  61917.5,  61133.33, 62902.5,  61984.44),
    ("2025-05", 144.0, 162.5,   160.51, 153.7,  133.0,  59765.0,  60928.33, 63637.5,  61443.61),
    ("2025-06", 145.0, 162.7,   160.53, 153.7,  132.8,  56690.0,  59205.0,  62385.0,  59426.67),
    # Q3 2025 — RBI only
    ("2025-07", 146.5, 163.0,   160.52, 154.4,  133.1,  None,     None,     None,     None),
    ("2025-08", 147.1, 162.16,  160.53, 155.2,  133.5,  None,     None,     None,     None),
    ("2025-09", 147.3, 162.16,  160.53, 154.16, 133.7,  None,     None,     None,     None),
    # Q4 2025 — RBI + JPC
    ("2025-10", 147.7, 163.0,   160.53, 155.1,  131.3,  52752.5,  55820.0,  59850.0,  56140.83),
    ("2025-11", 148.2, 163.3,   160.53, 156.2,  130.5,  51980.0,  54800.0,  58202.5,  54994.17),
    ("2025-12", 148.2, 163.1,   160.53, 157.2,  130.3,  52435.0,  54476.67, 56785.0,  54565.56),
]

SERIES_NAMES = [
    "labour", "plant_machinery", "fuel", "other_materials", "cement",
    "steel_tmt", "steel_angles", "steel_plates", "steel_other_sections",
]

# OCR data must not overwrite authoritative workbook months
_WORKBOOK_MONTHS = {obs[0] for obs in WORKBOOK_OBSERVATIONS}


def load_historical_jpc() -> dict[str, dict[str, float | None]]:
    """
    Read jpc_monthly_averages.csv and return JPC series values for months
    not covered by the workbook (i.e. before Dec-2024).

    Returns: {month_str: {series_name: value_or_None}}
    Only months strictly before Dec-2024 are returned.
    """
    if not MONTHLY_AVG_CSV.exists():
        print(f"  WARNING: {MONTHLY_AVG_CSV} not found — skipping historical JPC seed")
        return {}

    by_month: dict[str, dict[str, float]] = defaultdict(dict)
    with open(MONTHLY_AVG_CSV) as f:
        for row in csv.DictReader(f):
            if not row["avg_4city"]:
                continue
            by_month[row["month"]][row["item"]] = float(row["avg_4city"])

    result: dict[str, dict[str, float | None]] = {}
    for month, items in sorted(by_month.items()):
        if month in _WORKBOOK_MONTHS:
            continue

        year, m = month.split("-")
        if date(int(year), int(m), 1) >= date(2024, 12, 1):
            continue  # guard: workbook is authoritative from Dec-2024 onward

        series: dict[str, float | None] = {}

        tmt_vals = [items[k] for k in ("TMT 10 MM", "TMT 25 MM") if k in items]
        series["steel_tmt"] = mean(tmt_vals) if tmt_vals else None

        series["steel_angles"] = items.get("ANGLES 75X75X6 MM")

        plates_vals = [items[k] for k in ("PLATES 10 MM", "PLATES 25 MM") if k in items]
        series["steel_plates"] = mean(plates_vals) if plates_vals else None

        series["steel_other_sections"] = items.get("CHANNELS 150X75 MM")

        result[month] = series

    return result


async def seed() -> None:
    raw = os.environ["DATABASE_URL"].strip()
    u = make_url(raw)

    conn = await asyncpg.connect(
        host=u.host,
        port=u.port,
        user=u.username,
        password=str(u.password),
        database=u.database,
    )

    try:
        # Upsert series definitions
        series_ids: dict[str, int] = {}
        for name, source in SERIES:
            row = await conn.fetchrow(
                """
                INSERT INTO index_series (name, source_publication)
                VALUES ($1, $2::index_source)
                ON CONFLICT (name) DO UPDATE SET source_publication = EXCLUDED.source_publication
                RETURNING id
                """,
                name, source,
            )
            series_ids[name] = row["id"]
            print(f"  series: {name} ({source}) → {row['id']}")

        inserted = skipped = 0

        async def _insert(month_date: date, series_name: str, value: float, source_ref: str) -> None:
            nonlocal inserted, skipped
            result = await conn.execute(
                """
                INSERT INTO index_observations (series_id, month, value, source_ref)
                VALUES ($1, $2::date, $3, $4)
                ON CONFLICT (series_id, month) DO NOTHING
                """,
                series_ids[series_name],
                month_date,
                value,
                source_ref,
            )
            if result == "INSERT 0 1":
                inserted += 1
            else:
                skipped += 1

        # --- Source 1: authoritative workbook data (Dec-2024 → Dec-2025) ---
        print("\n[1/2] Seeding workbook observations (Dec-2024 – Dec-2025)...")
        for obs in WORKBOOK_OBSERVATIONS:
            month_str = obs[0]
            year, month = month_str.split("-")
            month_date = date(int(year), int(month), 1)
            values = dict(zip(SERIES_NAMES, obs[1:]))
            for series_name, value in values.items():
                if value is not None:
                    await _insert(month_date, series_name, value, "BCT-24-25-252 workbook")

        workbook_count = sum(1 for obs in WORKBOOK_OBSERVATIONS for v in obs[1:] if v is not None)
        print(f"  {workbook_count} workbook observations processed.")

        # --- Source 2: OCR-extracted historical JPC data (Apr-2022 – Nov-2024) ---
        print("\n[2/2] Seeding OCR historical JPC data (Apr-2022 – Nov-2024)...")
        historical = load_historical_jpc()
        jpc_series = ("steel_tmt", "steel_angles", "steel_plates", "steel_other_sections")
        ocr_total = 0
        ocr_none = 0
        for month_str, series_vals in sorted(historical.items()):
            year, month = month_str.split("-")
            month_date = date(int(year), int(month), 1)
            for series_name in jpc_series:
                value = series_vals.get(series_name)
                if value is not None:
                    await _insert(month_date, series_name, value, "JPC PDF OCR — jpc_monthly_averages.csv")
                    ocr_total += 1
                else:
                    ocr_none += 1

        print(f"  {ocr_total} OCR observations inserted ({ocr_none} gaps skipped).")
        print(f"  Historical months covered: {len(historical)}")

        print(f"\nDone. {inserted} inserted, {skipped} already existed.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
