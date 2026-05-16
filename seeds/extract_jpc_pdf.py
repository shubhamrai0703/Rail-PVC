#!/usr/bin/env python3
"""
OCR pipeline: extract JPC steel price bulletin data from scanned PDF.

Input:  REFERENCES/JPC Rate Apr 22 to April 26.pdf  (197 pages, pages 1-196 are data)
Output: REFERENCES/jpc_raw_extracted.csv  (columns: date, item, kolkata, delhi, mumbai, chennai)
Errors: REFERENCES/jpc_extraction_errors.log

Idempotent: skips dates already present in the CSV.

OCR strategy:
  v1 = 2x scale + binary threshold 128           (best for 2022-2023 scans)
  v2 = 3x scale + binary threshold 180           (best for 2024+ scans)
  v3 = 3x scale + RGB smart de-highlight         (for pages with orange/color highlights)
  Per-page: try v1 → v2 → v3, keep whichever yields most items.
"""

import csv
import logging
import re
import sys
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path
from statistics import median

import fitz  # PyMuPDF
import numpy as np
import pytesseract
from PIL import Image

# ── Paths ──────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = REPO_ROOT / "REFERENCES" / "JPC Rate Apr 22 to April 26.pdf"
OUTPUT_CSV = REPO_ROOT / "REFERENCES" / "jpc_raw_extracted.csv"
ERROR_LOG = REPO_ROOT / "REFERENCES" / "jpc_extraction_errors.log"

# ── Target items ───────────────────────────────────────────────────────────────

TARGET_ITEMS = [
    "TMT 10 MM",
    "TMT 25 MM",
    "ANGLES 75X75X6 MM",
    "CHANNELS 150X75 MM",
    "PLATES 10 MM",
    "PLATES 25 MM",
]

# ── Date parsing ───────────────────────────────────────────────────────────────

MONTH_MAP = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
    "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
    "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}
_MONTH_PAT = "|".join(MONTH_MAP.keys())

# "JPC MARKET PRICE RETAIL FOR 1ST APRIL 2022" — use this date, not the "DATE:" line
FOR_DATE_RE = re.compile(
    r'FOR\s+(\d{1,2})\s*(?:ST|ND|RD|TH)\s+(' + _MONTH_PAT + r')\s+(\d{4})',
    re.IGNORECASE,
)
ANY_DATE_RE = re.compile(
    r'(\d{1,2})\s*(?:ST|ND|RD|TH)\s+(' + _MONTH_PAT + r')\s+(\d{4})',
    re.IGNORECASE,
)


def _date_from_match(m: re.Match) -> datetime | None:
    groups = m.groups()
    day, month_str, year = int(groups[-3]), groups[-2].upper(), int(groups[-1])
    month = MONTH_MAP.get(month_str)
    if not month:
        return None
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def parse_bulletin_date(text: str) -> datetime | None:
    """Extract the 'FOR xth MONTH YEAR' date (actual bulletin date, not publication date)."""
    lines = text.splitlines()
    for line in lines[:15]:
        m = FOR_DATE_RE.search(line.upper())
        if m:
            d = _date_from_match(m)
            if d:
                return d
    for line in lines[:10]:
        m = ANY_DATE_RE.search(line.upper())
        if m:
            d = _date_from_match(m)
            if d:
                return d
    return None


# ── Price parsing ──────────────────────────────────────────────────────────────

CLEAN_PRICE_RE = re.compile(r'\b(\d{1,3}(?:,\d{3})+|\d{5,6})\b')
ZERO_PREFIX_RE = re.compile(r'\b(0\d{3})\b')


def parse_price(s: str) -> int | None:
    val_str = s.replace(",", "")
    if not val_str.isdigit():
        return None
    val = int(val_str)
    return val if 20_000 <= val <= 200_000 else None


def recover_zero_prefix(s: str, context: list[int]) -> int | None:
    """Recover a 4-digit OCR price like '0280' that lost its leading digit."""
    val_str = s.replace(",", "")
    if not (len(val_str) == 4 and val_str[0] == '0' and val_str.isdigit()):
        return None
    if not context:
        return None
    med = median(context)
    candidates = [int(d + val_str) for d in "56789" if 20_000 <= int(d + val_str) <= 200_000]
    if not candidates:
        return None
    return min(candidates, key=lambda x: abs(x - med))


# ── Item name matching ─────────────────────────────────────────────────────────

_OCR_NORM = str.maketrans({'O': '0', 'o': '0', 'I': '1', 'l': '1',
                            'S': '5', 's': '5', 'Z': '2', 'z': '2', 'B': '8'})


def _normalize_ocr(s: str) -> str:
    return s.translate(_OCR_NORM)


def _is_excluded(candidate_upper: str, item: str) -> bool:
    """
    Return True if the candidate clearly describes a DIFFERENT item from the target.
    Prevents false-positive pairs (CHANNELS-75X40 → CHANNELS-150X75, etc.).
    """
    # BILLETS never maps to any of our targets
    if "BILLET" in candidate_upper:
        return True

    if item == "ANGLES 75X75X6 MM":
        # ANGLES 50X50X6 (SL 13): has "50X50" pattern
        if re.search(r'[5S][0O][Xx][5S][0O]', candidate_upper):
            if not re.search(r'[7][5S][Xx][7][5S]', candidate_upper):
                return True

    if item == "CHANNELS 150X75 MM":
        # CHANNELS 75X40 (SL 17): reject
        if re.search(r'[7][5S][Xx]4[0O]', candidate_upper):
            return True

    if item in ("PLATES 10 MM", "PLATES 25 MM"):
        # PLATES 6 MM, PLATES 8 MM — wrong thickness (handles "PLATES6MM" no-space)
        if re.search(r'\bPLATES?\s*[68]', candidate_upper):
            return True
        # PLATES 12 MM (handles "PLATES12MM" and "PLATES 12 MM")
        if re.search(r'\bPLATES?\s*12', candidate_upper):
            return True
        # BILLETS 100MM
        if re.search(r'\b100\b', candidate_upper) and "PLATE" not in candidate_upper:
            return True

    if item == "PLATES 25 MM":
        # Reject if clearly PLATES 10 — but "10" appears in "PLATES 10"
        if re.search(r'\bPLATES?\s*10', candidate_upper) and "25" not in candidate_upper:
            return True

    if item == "PLATES 10 MM":
        # Reject if clearly PLATES 25
        if re.search(r'\bPLATES?\s*25', candidate_upper):
            return True

    if item == "TMT 25 MM":
        # "TMT 12 MM" (SL 9) OCR false-positive: reject any candidate containing TMT 1x
        if re.search(r'TMT\s*1[2]', candidate_upper):
            return True

    if item in ("TMT 10 MM", "TMT 25 MM"):
        # Reject non-TMT items
        if "TMT" not in candidate_upper and "TNT" not in candidate_upper:
            # Allow "TNTIOMM" style OCR garbling (TMT with noise)
            normed = _normalize_ocr(candidate_upper)
            if "TMT" not in normed:
                # Last check: does it have T_T pattern with 5+ ratio?
                from difflib import SequenceMatcher
                best_ratio = max(
                    SequenceMatcher(None, candidate_upper, t).ratio()
                    for t in ["TMT 10 MM", "TMT 25 MM"]
                )
                if best_ratio < 0.55:
                    return True

    return False


def match_item(candidate: str) -> str | None:
    """Fuzzy-match a candidate string against the 6 target items."""
    upper = candidate.upper()

    def _check(item: str) -> str | None:
        """Return item if not excluded (always checked against original upper)."""
        return None if _is_excluded(upper, item) else item

    def _best_match(text: str) -> str | None:
        # 1. Direct substring
        for item in TARGET_ITEMS:
            if item in text:
                return _check(item)
        # 2. Fuzzy
        hits = get_close_matches(text, TARGET_ITEMS, n=1, cutoff=0.60)
        if hits:
            return _check(hits[0])
        return None

    # Try on original
    result = _best_match(upper)
    if result:
        return result

    # Try with OCR noise normalization
    normed = _normalize_ocr(upper)
    result = _best_match(normed)
    if result:
        return result

    # Try token-level reconstruction
    tokens = re.findall(r'[A-Z0-9]+(?:\.[0-9]+)?', normed)
    reconstructed = " ".join(tokens)
    hits = get_close_matches(reconstructed, TARGET_ITEMS, n=1, cutoff=0.60)
    if hits:
        return _check(hits[0])

    return None


# ── Row parsing ────────────────────────────────────────────────────────────────

_BRACKET_ROW_RE = re.compile(
    r'^\[?\s*(\d+)\s*[|\]]\s*(.+?)\s*[|\]]\s*([\d,]+)',
)


def _parse_bracket_row(line: str) -> tuple[str, list[int]] | None:
    """Parse 2026-style bracket-table lines: [N | ITEM NAME | p1 | p2 | p3 | p4 |"""
    m = _BRACKET_ROW_RE.match(line.strip())
    if not m:
        return None
    item_candidate = m.group(2).strip()
    # Extract all prices from the remainder of the line
    prices: list[int] = []
    for pm in CLEAN_PRICE_RE.finditer(line[m.start(3):]):
        val = parse_price(pm.group(1))
        if val is not None:
            prices.append(val)
        if len(prices) == 4:
            break
    if len(prices) < 4:
        return None
    return item_candidate, prices


def _extract_items_from_text(text: str) -> dict[str, list[int]]:
    """Parse all OCR lines, match items, collect 4 city prices per item."""
    extracted: dict[str, list[int]] = {}

    for line in text.splitlines():
        clean_prices: list[int] = []
        first_pos: int | None = None

        for m in CLEAN_PRICE_RE.finditer(line):
            val = parse_price(m.group(1))
            if val is not None:
                if first_pos is None:
                    first_pos = m.start()
                clean_prices.append(val)
            if len(clean_prices) == 4:
                break

        prices = clean_prices

        # Attempt recovery of zero-prefix garbled prices if short
        if len(prices) < 4 and len(prices) >= 2:
            recovered = list(prices)
            for m in ZERO_PREFIX_RE.finditer(line):
                val = recover_zero_prefix(m.group(1), prices)
                if val is not None and val not in recovered:
                    recovered.append(val)
                    if first_pos is None:
                        first_pos = m.start()
                if len(recovered) == 4:
                    break
            prices = recovered

        if len(prices) < 4 or first_pos is None:
            # Try bracket-table format before giving up on this line
            br = _parse_bracket_row(line)
            if br is not None:
                item_candidate, br_prices = br
                item = match_item(item_candidate)
                if item and item not in extracted:
                    extracted[item] = br_prices
            continue

        item_text = line[:first_pos].upper().strip()
        item = match_item(item_text)
        if item and item not in extracted:
            extracted[item] = prices[:4]

    return extracted


# ── OCR ────────────────────────────────────────────────────────────────────────

def _ocr(page: fitz.Page, scale: float, threshold: int) -> str:
    """Grayscale render + binary threshold."""
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
    img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
    img = img.point(lambda px: 255 if px > threshold else 0, "L")
    return pytesseract.image_to_string(img, config="--psm 6 -l eng")


def _ocr_decolor(page: fitz.Page, scale: float = 3.0) -> str:
    """
    RGB render with smart de-highlighting.
    Handles orange/yellow cell highlights (common in 2024+ bulletins) by
    extracting dark text within highlighted regions using the green channel.
    """
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)  # RGB
    arr = np.array(Image.frombytes("RGB", [pix.width, pix.height], pix.samples),
                   dtype=np.int32)

    # Warm-tint highlight detection: R significantly > B
    # Catches both orange (R>180,G>130,B<100) and red/pink (R>180,G<130,B<100) highlights
    r_minus_b = arr[:, :, 0] - arr[:, :, 2]
    highlight = r_minus_b > 120

    result = np.ones(arr.shape[:2], dtype=np.uint8) * 255  # start white

    # Non-highlighted areas: standard luminance threshold
    gray = (arr[:, :, 0] * 299 + arr[:, :, 1] * 587 + arr[:, :, 2] * 114) // 1000
    result[~highlight & (gray < 160)] = 0

    # Highlighted areas: text is dark (low G/B channels on warm bg)
    result[highlight & (arr[:, :, 1] < 140)] = 0

    img = Image.fromarray(result, mode="L")
    return pytesseract.image_to_string(img, config="--psm 6 -l eng")


def ocr_best(page: fitz.Page) -> tuple[str, dict[str, list[int]]]:
    """
    Try v1 → v2 → v3, return (text, extracted_items) from the strategy
    that yields the most target items.
    """
    text1 = _ocr(page, scale=2.0, threshold=128)
    items1 = _extract_items_from_text(text1)
    if len(items1) >= 5:
        return text1, items1

    text2 = _ocr(page, scale=3.0, threshold=180)
    items2 = _extract_items_from_text(text2)
    best_text, best_items = (text2, items2) if len(items2) >= len(items1) else (text1, items1)
    if len(best_items) >= 5:
        return best_text, best_items

    text3 = _ocr_decolor(page, scale=3.0)
    items3 = _extract_items_from_text(text3)
    if len(items3) > len(best_items):
        return text3, items3
    return best_text, best_items


# ── Per-page extraction ────────────────────────────────────────────────────────

def extract_page(
    page_num: int,
    page: fitz.Page,
    existing_dates: set[str],
    writer: csv.DictWriter,
    log: logging.Logger,
) -> bool:
    text, extracted = ocr_best(page)

    bulletin_date = parse_bulletin_date(text)
    if bulletin_date is None:
        log.warning("Page %d: date not found. Head: %s",
                    page_num, " | ".join(text.splitlines()[:4]))
        return False

    date_str = bulletin_date.strftime("%Y-%m-%d")

    if date_str in existing_dates:
        return True  # second sheet of same bulletin, or already done

    if len(extracted) < 3:
        log.warning(
            "Page %d (%s): only %d/6 target items found: %s",
            page_num, date_str, len(extracted), list(extracted.keys()),
        )
        return False

    for item in TARGET_ITEMS:
        if item in extracted:
            k, d, m, c = extracted[item]
            writer.writerow({"date": date_str, "item": item,
                             "kolkata": k, "delhi": d, "mumbai": m, "chennai": c})

    existing_dates.add(date_str)
    return True


# ── Idempotency ────────────────────────────────────────────────────────────────

def load_existing_dates(csv_path: Path) -> set[str]:
    if not csv_path.exists():
        return set()
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        return {row["date"] for row in reader}


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(
        filename=str(ERROR_LOG),
        filemode="a",
        level=logging.WARNING,
        format="%(asctime)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log = logging.getLogger("jpc_ocr")

    if not PDF_PATH.exists():
        sys.exit(f"PDF not found: {PDF_PATH}")

    existing_dates = load_existing_dates(OUTPUT_CSV)
    print(f"Already extracted: {len(existing_dates)} unique dates")

    doc = fitz.open(str(PDF_PATH))
    total = len(doc)  # 197
    data_range = range(0, total - 1)  # skip page 196 (disclaimer)

    csv_is_new = not OUTPUT_CSV.exists()
    fieldnames = ["date", "item", "kolkata", "delhi", "mumbai", "chennai"]

    ok = fail = 0
    with open(OUTPUT_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if csv_is_new:
            writer.writeheader()

        for i in data_range:
            success = extract_page(i + 1, doc[i], existing_dates, writer, log)
            if success:
                ok += 1
            else:
                fail += 1
            if (i + 1) % 20 == 0:
                f.flush()
                print(f"  {i + 1}/{len(data_range)} pages — {ok} ok, {fail} failed")

    print(f"\nDone. {ok} pages OK, {fail} failed. Errors → {ERROR_LOG}")


if __name__ == "__main__":
    main()
