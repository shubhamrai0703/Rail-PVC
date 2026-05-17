"""GCC 46A.9(2) — JPC city mapping by Railway zone (KU-006).

Used by `pvc_service.build_index_snapshot` to pick the correct city-specific
JPC steel series. Authority for this table is the GCC PDF; the migration
(010_railway_zone.py) constrains the ENUM, this module maps zone → city.
"""
from __future__ import annotations

from typing import Literal

City = Literal["Delhi", "Kolkata", "Mumbai", "Chennai"]

ZONE_TO_JPC_CITY: dict[str, City] = {
    "NR": "Delhi", "NCR": "Delhi", "NWR": "Delhi", "NER": "Delhi",
    "ER": "Kolkata", "ECR": "Kolkata", "ECOR": "Kolkata",
    "NFR": "Kolkata", "SER": "Kolkata", "SECR": "Kolkata",
    "CR": "Mumbai", "WR": "Mumbai", "WCR": "Mumbai",
    "SR": "Chennai", "SCR": "Chennai", "SWR": "Chennai",
}

VALID_ZONES: frozenset[str] = frozenset(ZONE_TO_JPC_CITY)

# Steel series that have city-specific JPC variants. The generic name is the
# fallback used when zoning data isn't available; the *_<city> form is the
# authoritative price for a contract in that zone.
STEEL_SERIES_NAMES: tuple[str, ...] = ("steel_tmt", "steel_angles", "steel_plates")


def city_for_zone(zone: str) -> City:
    try:
        return ZONE_TO_JPC_CITY[zone]
    except KeyError as exc:
        raise ValueError(f"Unknown railway zone: {zone!r}") from exc


def expected_series_names(zone: str) -> tuple[set[str], set[str]]:
    """Return (required_series, city_specific_series) for a zone.

    `required_series` lists every series name the engine snapshot must contain.
    `city_specific_series` lists the city-suffixed variants that, if present,
    MUST be aliased over the generic name (P3-04 remediation).
    """
    city = city_for_zone(zone)
    generic = set(STEEL_SERIES_NAMES) | {"cement", "labour", "plant", "fuel", "materials"}
    city_specific = {f"{name}_{city.lower()}" for name in STEEL_SERIES_NAMES}
    return generic, city_specific
