"""LLM client for AI-assisted column mapping (P5-IMP-3).

Calls Claude Haiku via OpenRouter's OpenAI-compatible chat completions
API (httpx directly — OpenRouter has no first-party Python SDK, and this
avoids adding one just for a single call site). The model is
configurable via `OPENROUTER_MODEL` since OpenRouter's model slugs can
shift independently of Anthropic's own naming.

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
import re
import time
from functools import lru_cache
from typing import Any

import httpx

from services.errors import ApiProblem

logger = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-haiku-4.5")
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
def _client() -> httpx.AsyncClient:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise LLMUnavailableProblem("OPENROUTER_API_KEY is not configured")
    return httpx.AsyncClient(
        base_url=_OPENROUTER_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30.0,
    )


class LLMUnavailableProblem(ApiProblem):
    """503 — upstream LLM provider unavailable or misconfigured. The
    frontend treats this as a soft failure and falls back to the manual
    mapper."""

    status_code = 503
    code = "llm_unavailable"


_CODE_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?|\n?```$")


def _strip_code_fence(content: str) -> str:
    """Some providers wrap JSON-mode output in a ```json ... ``` fence
    even though the response_format asked for raw JSON."""
    return _CODE_FENCE_RE.sub("", content.strip()).strip()


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
        http_response = await client.post(
            _OPENROUTER_URL,
            json={
                "model": _MODEL,
                "max_tokens": _MAX_TOKENS,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
                # Plain JSON mode, not a strict json_schema: the `mapping`
                # object's keys are the source headers (data-dependent, not
                # known ahead of time). Anthropic's structured-output
                # schema validator can't express that as `additionalProperties`
                # and silently returns an empty object under strict
                # enforcement — the shape is governed by the system prompt
                # instead, and content is JSON with possible ``` fences we
                # strip before parsing.
                "response_format": {"type": "json_object"},
            },
        )
        http_response.raise_for_status()
        response = http_response.json()
    except LLMUnavailableProblem:
        raise
    except Exception as exc:
        logger.warning("llm_call_failed: %s", exc, exc_info=False)
        raise LLMUnavailableProblem(f"Mapping service unavailable: {exc}") from exc

    elapsed_ms = int((time.monotonic() - started) * 1000)

    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LLMUnavailableProblem("Mapping service returned no content") from exc

    try:
        parsed = json.loads(_strip_code_fence(content))
    except json.JSONDecodeError as exc:
        raise LLMUnavailableProblem(
            f"Mapping service returned non-JSON output: {exc}"
        ) from exc

    usage = response.get("usage", {})
    logger.info(
        "llm_suggest_mapping: headers=%d sample_rows=%d elapsed_ms=%d "
        "prompt_tokens=%s completion_tokens=%s",
        len(headers),
        len(user_payload["sample_rows"]),
        elapsed_ms,
        usage.get("prompt_tokens"),
        usage.get("completion_tokens"),
    )

    return parsed
