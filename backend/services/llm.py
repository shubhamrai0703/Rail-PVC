"""LLM client for AI-assisted column mapping (P5-IMP-3).

Uses Claude Haiku 4.5 via the official Anthropic Python SDK. The prompt
is split into a stable system block (cached — see Anthropic prompt-cache
docs) and a per-request user block with the source headers + sample rows.

Returns a strict JSON shape; structured-output enforcement keeps the
frontend's contract honest. Errors from the upstream service surface as
`LLMUnavailableProblem(503)` so the frontend can fall back to the
deterministic Option-A mapper without panicking.

Auditability: every call is logged with tenant-less metadata (header
count, sample-row count, latency, token usage). We don't log the
headers/sample values themselves — they may contain customer-identifying
strings.
"""
from __future__ import annotations

import json
import logging
import os
import time
from functools import lru_cache
from typing import Any

from services.errors import ApiProblem

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5"
_MAX_TOKENS = 1024

_SYSTEM_PROMPT = """You map source columns from a Bill of Quantities (BOQ) Excel sheet to a fixed canonical schema used by a railway PVC (Price Variation Clause) billing system.

The target schema has exactly these fields:

  - item_code         (string)  — e.g. "1.1", "10.2", "NS-1"
  - description       (string)  — line-item description
  - unit              (string)  — e.g. "Cum", "Sqm", "MT", "Each"
  - original_qty      (number)  — agreement quantity, decimal
  - revised_qty       (number)  — current/revised quantity, decimal
  - base_rate         (number)  — SOR/DSR base rate, decimal
  - agreement_rate    (number)  — contractor's quoted rate, decimal
  - is_cement_item    (boolean) — true if the item consumes cement (for PVC cement bucket)
  - steel_subtype     (enum)    — one of "angles", "plates", "other_sections", "tmt", or null

Indian Railway BOQs vary in column naming and order. Headers may be in English, Hindi, or abbreviated. Some columns may be unmapped (ignore them). Numeric columns may use commas as thousand separators.

For each source header you receive, decide which target field (if any) it maps to. If a header is irrelevant (e.g. serial number, remarks), set its target to null.

Additionally, for `is_cement_item` and `steel_subtype`, if the sample values use non-canonical tokens (e.g. "Yes"/"No", "Cement"/"Non-cement", "TMT Bar"), provide a value_normalizations entry that maps each observed source value to the canonical token:

  - is_cement_item: source value → "true" | "false"
  - steel_subtype:  source value → "angles" | "plates" | "other_sections" | "tmt" | ""

Output strict JSON with this shape:

{
  "mapping": { "<source_header>": "<target_field>" | null, ... },
  "value_normalizations": { "<target_field>": { "<source_value>": "<canonical_value>" }, ... },
  "confidence": 0.0..1.0,
  "unmapped": ["<source_header>", ...],
  "notes": "short explanation or null"
}

Rules:
  - Every input source_header MUST appear in `mapping` (target or null).
  - `unmapped` lists headers whose target is null AND that look like they should map to something — surface these so the user can intervene.
  - `confidence` is your overall confidence the proposed mapping is correct.
  - `value_normalizations` may be an empty object if no normalization is needed.
"""


@lru_cache(maxsize=1)
def _client():
    # Imported lazily so the backend can import this module without the SDK
    # installed (useful for tests that don't exercise the LLM path).
    from anthropic import AsyncAnthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMUnavailableProblem("ANTHROPIC_API_KEY is not configured")
    return AsyncAnthropic(api_key=api_key)


class LLMUnavailableProblem(ApiProblem):
    """503 — upstream LLM provider unavailable or misconfigured. The
    frontend treats this as a soft failure and falls back to the manual
    mapper."""

    status_code = 503
    code = "llm_unavailable"


_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "mapping": {
            "type": "object",
            # mapping has dynamic keys (source headers); the values must be
            # one of the target field names or null. additionalProperties
            # carries the per-value constraint.
            "additionalProperties": {
                "type": ["string", "null"],
            },
        },
        "value_normalizations": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "unmapped": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": ["string", "null"]},
    },
    "required": ["mapping", "value_normalizations", "confidence", "unmapped", "notes"],
}


async def suggest_mapping_via_llm(
    *,
    headers: list[str],
    sample_rows: list[list[str]],
    target_fields: list[str],
) -> dict[str, Any]:
    if not headers:
        raise LLMUnavailableProblem("No source headers provided")

    user_payload = {
        "source_headers": headers,
        "sample_rows": sample_rows[:5],  # cap on server side regardless of body
        "target_fields": target_fields,
    }

    started = time.monotonic()
    try:
        client = _client()
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                }
            ],
            output_config={
                "format": {"type": "json_schema", "schema": _RESPONSE_SCHEMA},
            },
        )
    except LLMUnavailableProblem:
        raise
    except Exception as exc:
        logger.warning("llm_call_failed: %s", exc, exc_info=False)
        raise LLMUnavailableProblem(f"Mapping service unavailable: {exc}") from exc

    elapsed_ms = int((time.monotonic() - started) * 1000)

    text_block = next(
        (b for b in response.content if getattr(b, "type", None) == "text"),
        None,
    )
    if text_block is None:
        raise LLMUnavailableProblem("Mapping service returned no text block")

    try:
        parsed = json.loads(text_block.text)
    except json.JSONDecodeError as exc:
        raise LLMUnavailableProblem(
            f"Mapping service returned non-JSON output: {exc}"
        ) from exc

    logger.info(
        "llm_suggest_mapping: headers=%d sample_rows=%d elapsed_ms=%d "
        "cache_read=%s cache_write=%s input=%s output=%s",
        len(headers),
        len(user_payload["sample_rows"]),
        elapsed_ms,
        getattr(response.usage, "cache_read_input_tokens", None),
        getattr(response.usage, "cache_creation_input_tokens", None),
        getattr(response.usage, "input_tokens", None),
        getattr(response.usage, "output_tokens", None),
    )

    return parsed
