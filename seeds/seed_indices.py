"""
Seed RBI/JPC index data into the database.

Three sources:
  1. BCT-24-25-252 workbook (hardcoded) — Dec-2024 through Dec-2025 (13 months).
     JPC steel series only (steel_tmt/angles/plates/other_sections). The workbook's
     RBI columns are NO LONGER seeded from here: they carried a systematic +70.0
     error on plant_machinery and fuel (confirmed to the penny across all overlap
     months). RBI series now come from source 3 (authoritative) instead.

  2. OCR extraction (REFERENCES/jpc_monthly_averages.csv) — Apr-2022 through Nov-2024.
     JPC only. Series mapping:
       steel_tmt            = avg(TMT 10 MM, TMT 25 MM)
       steel_angles         = ANGLES 75X75X6 MM
       steel_plates         = avg(PLATES 10 MM, PLATES 25 MM)
       steel_other_sections = CHANNELS 150X75 MM
     Quality caveats — see REFERENCES/jpc_monthly_warnings.log and OCR gap notes below.

  3. Authoritative RBI/WPI/CPI/PPAC backfill — Apr-2022 onward. The 5 non-steel
     series, derived from official publications into clean CSVs in REFERENCES/:
       labour          ← CPI-IW (Labour Bureau, base 2016)   cpiw_labour_2016base.csv
       cement          ← WPI 'e. Manufacture of cement…'     wpi_rbi_derived.csv
       plant_machinery ← WPI 'k. Manufacture of machinery…'  wpi_rbi_derived.csv
       other_materials ← WPI 'All commodities'               wpi_rbi_derived.csv
       fuel            ← PPAC diesel RSP, 4-metro monthly avg ppac_diesel_monthly.csv
     These are source-of-truth and OVERWRITE any existing rows (ON CONFLICT DO UPDATE),
     correcting the +70 workbook error. WPI base 2011-12=100; fuel stored as raw ₹/L
     (the PVC engine normalises per-series, so absolute scale is irrelevant).

OCR data gaps (months with 0 bulletins for a series → None inserted):
  TMT series: 2022-07, 2022-10, 2025-05 (2026-03 excluded — after hardcoded period)
  ANGLES:     2022-10, 2026-01
  CHANNELS:   2023-01, 2023-02, 2024-04, 2025-04, 2025-05, 2025-06
  PLATES:     2022-05 (plates-10), 2022-10, 2022-12, 2025-02, 2025-04

Run:       uv run python seeds/seed_indices.py   (from repo root or backend/)
Idempotent: workbook + JPC OCR use ON CONFLICT DO NOTHING;
            authoritative RBI backfill uses ON CONFLICT DO UPDATE (overwrite).
"""

import asyncio
import csv
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

# Allow running from repo root or backend/
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv

    import asyncpg
    from sqlalchemy.engine.url import make_url
except ModuleNotFoundError:
    if os.environ.get("RAILPVC_SEED_BACKEND_UV") != "1":
        env = os.environ.copy()
        env["RAILPVC_SEED_BACKEND_UV"] = "1"
        os.execvpe(
            "uv",
            [
                "uv",
                "--project",
                str(BACKEND_DIR),
                "run",
                "python",
                str(Path(__file__).resolve()),
            ],
            env,
        )
    raise

load_dotenv(BACKEND_DIR / ".env", override=True)

MONTHLY_AVG_CSV = REPO_ROOT / "REFERENCES" / "jpc_monthly_averages.csv"

# Source 3 — authoritative RBI/WPI/CPI/PPAC backfill (clean derived CSVs).
WPI_RBI_CSV = REPO_ROOT / "REFERENCES" / "wpi_rbi_derived.csv"
PPAC_FUEL_CSV = REPO_ROOT / "REFERENCES" / "ppac_diesel_monthly.csv"
CPIW_LABOUR_CSV = REPO_ROOT / "REFERENCES" / "cpiw_labour_2016base.csv"

RBI_BACKFILL_START = "2022-04"  # YYYY-MM lexical lower bound (contract domain)

_MON_ABBR = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

RBI_SOURCE_REF = {
    "labour": "CPI-IW (Labour Bureau, base 2016) — cpiw_labour_2016base.csv",
    "cement": "WPI 2011-12=100, eaindustry monthly_index_202604.xls — "
              "'e. Manufacture of cement, lime and plaster'",
    "plant_machinery": "WPI 2011-12=100, eaindustry monthly_index_202604.xls — "
                       "'k. Manufacture of machinery for mining, quarrying and construction'",
    "other_materials": "WPI 2011-12=100, eaindustry monthly_index_202604.xls — "
                       "'All commodities'",
    "fuel": "PPAC diesel RSP, 4-metro monthly average — ppac_diesel_monthly.csv",
}

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


# RBI/non-steel series, now sourced authoritatively (source 3), not from the workbook.
RBI_SERIES = {"labour", "plant_machinery", "fuel", "other_materials", "cement"}


def load_historical_rbi() -> dict[str, dict[str, float]]:
    """
    Authoritative values for the 5 RBI/non-steel series, Apr-2022 onward.

    Reads three clean derived CSVs (no xls/pdf parsing → no backend deps):
      labour                            ← cpiw_labour_2016base.csv
      cement/plant_machinery/other_materials ← wpi_rbi_derived.csv
      fuel                              ← ppac_diesel_monthly.csv

    These overwrite any existing index_observations rows (the workbook RBI columns
    carried a +70 error on plant_machinery and fuel). Returns
    {month_str: {series_name: value}}, months >= RBI_BACKFILL_START only.
    """
    result: dict[str, dict[str, float]] = defaultdict(dict)

    # labour — CPI-IW (Survey Year + abbreviated Survey Month)
    if CPIW_LABOUR_CSV.exists():
        with open(CPIW_LABOUR_CSV) as f:
            for row in csv.DictReader(f):
                mon = _MON_ABBR.get(row["Survey Month"].strip())
                if not mon:
                    continue
                month = f'{int(row["Survey Year"]):04d}-{mon:02d}'
                if month >= RBI_BACKFILL_START and row["Index Value"].strip():
                    result[month]["labour"] = float(row["Index Value"])
    else:
        print(f"  WARNING: {CPIW_LABOUR_CSV} not found — labour not seeded")

    # cement / plant_machinery / other_materials — WPI derived
    if WPI_RBI_CSV.exists():
        with open(WPI_RBI_CSV) as f:
            for row in csv.DictReader(f):
                month = row["month"]
                if month < RBI_BACKFILL_START:
                    continue
                for s in ("cement", "plant_machinery", "other_materials"):
                    if row.get(s, "").strip():
                        result[month][s] = float(row[s])
    else:
        print(f"  WARNING: {WPI_RBI_CSV} not found — WPI series not seeded")

    # fuel — PPAC diesel 4-metro monthly average
    if PPAC_FUEL_CSV.exists():
        with open(PPAC_FUEL_CSV) as f:
            for row in csv.DictReader(f):
                month = row["month"]
                if month >= RBI_BACKFILL_START and row.get("avg_4city", "").strip():
                    result[month]["fuel"] = float(row["avg_4city"])
    else:
        print(f"  WARNING: {PPAC_FUEL_CSV} not found — fuel not seeded")

    return dict(result)


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

        inserted = skipped = rbi_written = 0

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

        async def _upsert(month_date: date, series_name: str, value: float, source_ref: str) -> None:
            """Source-of-truth write: overwrite any existing row for this series/month."""
            nonlocal rbi_written
            await conn.execute(
                """
                INSERT INTO index_observations (series_id, month, value, source_ref)
                VALUES ($1, $2::date, $3, $4)
                ON CONFLICT (series_id, month)
                DO UPDATE SET value = EXCLUDED.value, source_ref = EXCLUDED.source_ref
                """,
                series_ids[series_name],
                month_date,
                value,
                source_ref,
            )
            rbi_written += 1

        # --- Source 1: workbook JPC steel data (Dec-2024 → Dec-2025) ---
        # RBI series are intentionally skipped here — they are seeded authoritatively
        # by source 3 (the workbook's RBI columns had a +70 error on machinery/fuel).
        print("\n[1/3] Seeding workbook JPC steel observations (Dec-2024 – Dec-2025)...")
        for obs in WORKBOOK_OBSERVATIONS:
            month_str = obs[0]
            year, month = month_str.split("-")
            month_date = date(int(year), int(month), 1)
            values = dict(zip(SERIES_NAMES, obs[1:]))
            for series_name, value in values.items():
                if value is not None and series_name not in RBI_SERIES:
                    await _insert(month_date, series_name, value, "BCT-24-25-252 workbook")

        workbook_count = sum(
            1 for obs in WORKBOOK_OBSERVATIONS
            for name, v in zip(SERIES_NAMES, obs[1:])
            if v is not None and name not in RBI_SERIES
        )
        print(f"  {workbook_count} workbook JPC observations processed.")

        # --- Source 2: OCR-extracted historical JPC data (Apr-2022 – Nov-2024) ---
        print("\n[2/3] Seeding OCR historical JPC data (Apr-2022 – Nov-2024)...")
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

        # --- Source 3: authoritative RBI/WPI/CPI/PPAC backfill (Apr-2022 onward) ---
        # Source-of-truth: overwrites existing rows (corrects the +70 workbook error).
        print("\n[3/3] Seeding authoritative RBI series (Apr-2022 onward, overwrite)...")
        rbi = load_historical_rbi()
        for month_str, series_vals in sorted(rbi.items()):
            year, month = month_str.split("-")
            month_date = date(int(year), int(month), 1)
            for series_name, value in series_vals.items():
                await _upsert(month_date, series_name, value, RBI_SOURCE_REF[series_name])

        rbi_months = sorted(rbi)
        span = f"{rbi_months[0]} – {rbi_months[-1]}" if rbi_months else "none"
        print(f"  {rbi_written} RBI observations upserted across {len(rbi)} months ({span}).")

        print(
            f"\nDone. {inserted} inserted, {skipped} already existed, "
            f"{rbi_written} RBI upserted."
        )

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
