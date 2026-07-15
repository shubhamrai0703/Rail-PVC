Add one JSON file per real tender bill in this directory.

Recommended workflow:
1. Pick one bill from a real tender workbook that already has a trusted PVC value.
2. Convert the bill inputs, index snapshot, and rules into JSON. For the five
   Banjara workbooks, run `uv run python scripts/extract_pvc_fixtures.py` from
   `engine/`; the script is the provenance record for all source cells.
3. Pin the known-good workbook output in `expected.total_pvc`.
4. Run:
   `uv run python scripts/run_engine_fixture.py tests/fixtures/real_tenders/<file>.json --fail-on-mismatch`
5. Add the fixture to git so pytest keeps it as a regression test.

Optional reconciliation metadata:

- `expected.tolerance`: maximum absolute difference, as a decimal string.
- `notes.xfail_reason`: a non-strict pytest xfail reason. Real-tender xfails
  must identify `KU-001` so quarter-resolution debt stays visible.
- `notes.current_engine_total`: exact engine output currently hidden by a
  numeric xfail. This pin makes unrelated arithmetic changes fail loudly.
- `notes.expected_validation_errors`: exact ordered validation errors currently
  hidden by an xfail; broad error-pattern matching is intentionally forbidden.
- `notes.workbook_divergence`: explicit workbook/engine inconsistency with
  source cells; never alter source inputs merely to force reconciliation.
- `notes.reconciliation_status`: `reconciles`, `ku_001_pending`, or
  `workbook_divergence`.

Fixture shape:

```json
{
  "bill": {
    "on_account_amount": "8903877.99",
    "cement_amount": "0",
    "steel_angles_amount": "125000.00",
    "steel_plates_amount": "0",
    "steel_other_amount": "450000.00",
    "technical_withheld": "0",
    "extra_item_decisions": [
      {
        "item_id": "NS-1",
        "amount": "1600000.00",
        "eligible": false
      }
    ],
    "carry_forwards": [],
    "measurement_date": "2025-06-18",
    "prior_negative_carry_forward": "0"
  },
  "indices": {
    "base_month": "2024-12-01",
    "series": {
      "labour": {
        "2024-12": "143.7",
        "2025-04": "144.167",
        "2025-05": "144.167",
        "2025-06": "144.167"
      },
      "plant_machinery": {
        "2024-12": "160.0",
        "2025-04": "161.5",
        "2025-05": "161.5",
        "2025-06": "161.5"
      },
      "fuel": {
        "2024-12": "160.48",
        "2025-04": "157.0",
        "2025-05": "157.0",
        "2025-06": "157.0"
      },
      "other_materials": {
        "2024-12": "155.7",
        "2025-04": "156.0",
        "2025-05": "156.0",
        "2025-06": "156.0"
      },
      "cement": {
        "2024-12": "130.2",
        "2025-04": "129.5",
        "2025-05": "129.5",
        "2025-06": "129.5"
      },
      "steel_angles": {
        "2024-12": "58000.0",
        "2025-04": "57500.0",
        "2025-05": "57500.0",
        "2025-06": "57500.0"
      },
      "steel_plates": {
        "2024-12": "57370.0",
        "2025-04": "57000.0",
        "2025-05": "57000.0",
        "2025-06": "57000.0"
      },
      "steel_other_sections": {
        "2024-12": "57727.5",
        "2025-04": "57200.0",
        "2025-05": "57200.0",
        "2025-06": "57200.0"
      }
    }
  },
  "rules": {
    "quarter_mode": "measurement_date",
    "component_weights": {
      "labour": "0.20",
      "plant": "0.30",
      "fuel": "0.15",
      "materials": "0.20"
    },
    "adjustable_fraction": "0.85",
    "negative_pvc_policy": "zero_floor",
    "rounding_mode": "round_2"
  },
  "expected": {
    "total_pvc": "0.00"
  },
  "notes": {
    "source_tender": "BCT-24-25-252",
    "source_bill": "Bill-1",
    "source_workbook_tab": "PVC Sheet",
    "verified_against": "manual workbook"
  }
}
```
