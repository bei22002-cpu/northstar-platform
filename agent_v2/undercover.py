"""Undercover mode — strip AI attribution from git operations.

Inspired by Claude Code's ``undercover.ts``.  When enabled, the agent
will not include AI-identifying markers in git commits, PR descriptions,
or code comments.

This is useful when the user wants the agent's contributions to look
like they were written by a human developer.

Configuration via environment variable:
    CORNERSTONE_UNDERCOVER=1    -> enable undercover mode
    CORNERSTONE_UNDERCOVER=0    -> disable (default)

Unlike Claude Code, there IS a force-off — the user controls this.
"""

from __future__ import annotations

import os
import re

from rich.console import Console

console = Console()

# Patterns that reveal AI authorship
_AI_MARKERS = [
    re.compile(r"(?i)\bClaude\b"),
    re.compile(r"(?i)\bAI\s*(?:agent|assistant|generated|authored|written)\b"),
    re.compile(r"(?i)\bgenerated\s+(?:by|with|using)\s+(?:AI|Claude|GPT|LLM)\b"),
    re.compile(r"(?i)\bCo-Authored-By:.*(?:Claude|AI|Bot)\b"),
    re.compile(r"(?i)\bCornerstone\s*AI\b"),
    re.compile(r"(?i)\banthro(?:pic)?\b"),
    re.compile(r"(?i)\b(?:auto-?generated|machine-?generated)\b"),
]

# Internal codenames that should never appear in public output
_INTERNAL_CODENAMES = [
    "Tengu", "Capybara", "KAIROS",
    "tengu_", "capybara_",
]

# Undercover system prompt addition
UNDERCOVER_PROMPT = (
    "\n\n[UNDERCOVER MODE ACTIVE]\n"
    "When making git commits, writing PR descriptions, or adding code comments:\n"
    "- NEVER include 'Claude', 'AI', 'Cornerstone AI', 'auto-generated', "
    "'machine-generated', or any AI attribution\n"
    "- NEVER add Co-Authored-By lines mentioning AI\n"
    "- Write commit messages as a human developer would — concise, "
    "technical, first-person\n"
    "- Do NOT mention that you are an AI in any output that will be "
    "committed to a repository\n"
    "- Write code comments in a natural human style\n"
    "BAD commit messages:\n"
    '  - "Generated with Cornerstone AI"\n'
    '  - "AI-assisted implementation of..."\n'
    '  - "Co-Authored-By: Cornerstone AI <ai@cornerstone.ai>"\n'
    "GOOD commit messages:\n"
    '  - "feat: Add user authentication middleware"\n'
    '  - "fix: Resolve race condition in connection pool"\n'
    '  - "refactor: Extract validation logic into shared utils"\n'
)


def is_undercover_enabled() -> bool:
    """Return True if undercover mode is active."""
    return os.getenv("CORNERSTONE_UNDERCOVER", "0").strip() in ("1", "true", "yes")


def get_undercover_prompt() -> str:
    """Return the undercover system prompt addition, or empty string if disabled."""
    if is_undercover_enabled():
        return UNDERCOVER_PROMPT
    return ""


def scrub_ai_markers(text: str) -> str:
    """Remove AI-identifying markers from *text*.

    Used to clean commit messages and PR descriptions before they are
    submitted to git.
    """
    if not is_undercover_enabled():
        return text

    cleaned = text
    for pattern in _AI_MARKERS:
        cleaned = pattern.sub("", cleaned)

    for codename in _INTERNAL_CODENAMES:
        cleaned = cleaned.replace(codename, "")

    # Clean up double spaces and empty lines left by removals
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def scrub_commit_message(message: str) -> str:
    """Clean a git commit message of AI attribution.

    Removes Co-Authored-By lines and other AI markers.
    """
    if not is_undercover_enabled():
        return message

    lines = message.split("\n")
    cleaned_lines: list[str] = []
    for line in lines:
        # Skip Co-Authored-By lines mentioning AI
        if re.match(r"(?i)^\s*Co-Authored-By:.*(?:Claude|AI|Bot|Cornerstone)", line):
            continue
        cleaned_lines.append(line)

    return scrub_ai_markers("\n".join(cleaned_lines))
