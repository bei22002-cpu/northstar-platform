"""Memory writer — LLM-powered extraction of structured data from user input.

Given a raw user message, the writer asks Claude to extract stable, reusable
key-value facts (name, role, project, preferences, etc.) and returns clean
JSON.  Noise, greetings, and transient data are ignored.
"""

from __future__ import annotations

import json
from typing import Any

_EXTRACTION_PROMPT = """\
You are a memory extraction engine.  Given the user message below, extract
ONLY stable, reusable, high-value facts as a flat JSON object.

Rules:
- Keys must be short, snake_case identifiers (e.g. "user_name", "project_name").
- Values must be concise strings or numbers.
- Ignore greetings, filler, questions, and transient requests.
- If there is nothing worth remembering, return an empty JSON object: {{}}
- Do NOT wrap the JSON in markdown code fences.

User message:
{message}

Respond with ONLY the JSON object, nothing else."""


async def extract_facts(
    user_message: str,
    *,
    llm_call: Any,
) -> dict[str, Any]:
    """Extract structured facts from *user_message* via an LLM call.

    Parameters
    ----------
    user_message:
        The raw text the user typed.
    llm_call:
        An async callable with signature ``async (system, user_msg) -> str``
        that sends a single-turn request to the LLM and returns the text
        response.  This keeps the writer decoupled from any specific API
        client.

    Returns
    -------
    dict
        Flat key-value pairs extracted from the message, or ``{}`` if nothing
        worth storing was found.
    """
    prompt = _EXTRACTION_PROMPT.format(message=user_message)

    try:
        raw = await llm_call(
            "You are a concise JSON extraction engine. Respond with ONLY valid JSON.",
            prompt,
        )
        # Strip markdown fences if the model wraps anyway
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        if not isinstance(data, dict):
            return {}
        # Only keep string/number values
        return {
            k: v
            for k, v in data.items()
            if isinstance(v, (str, int, float)) and v != ""
        }
    except (json.JSONDecodeError, Exception):
        return {}
