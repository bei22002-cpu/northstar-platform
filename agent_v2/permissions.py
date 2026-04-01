"""Enhanced permission system — granular tool and path access control.

Inspired by Claude Code's permission system with allowlists and denylists.

Supports:
- Per-tool enable/disable
- Path-based restrictions (allowed/denied directories)
- Command allowlists and denylists (regex patterns)
- Permission presets (strict, standard, permissive)

Configuration via ``permissions.json`` in the agent_v2/ directory, or
via the ``CORNERSTONE_PERMISSION_PRESET`` environment variable.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Permission presets
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict[str, Any]] = {
    "strict": {
        "description": "Maximum safety — blocks most write operations and shell access",
        "allowed_tools": [
            "read_file", "list_files", "search_in_files", "git_status",
        ],
        "denied_tools": [
            "run_command", "delete_file",
        ],
        "allowed_paths": [],  # empty = all paths allowed
        "denied_paths": [
            r"\.env$", r"\.git/", r"node_modules/", r"__pycache__/",
            r"\.ssh/", r"\.aws/", r"credentials", r"secrets?\.json",
        ],
        "allowed_commands": [
            r"^git\s+(status|log|diff|show|branch)",
            r"^ls\b", r"^cat\b", r"^echo\b", r"^python\s+-c\b",
        ],
        "denied_commands": [
            r"\brm\b", r"\bsudo\b", r"\bchmod\b", r"\bchown\b",
            r"\bcurl\b.*\|.*\bsh\b", r"\bwget\b.*\|.*\bsh\b",
            r"\beval\b", r"\bexec\b", r"\bkill\b", r"\bpkill\b",
            r"\breboot\b", r"\bshutdown\b", r"\bformat\b",
            r"\bdrop\s+(?:database|table)\b",
        ],
    },
    "standard": {
        "description": "Balanced — allows most operations with sensible guardrails",
        "allowed_tools": [],  # empty = all tools allowed
        "denied_tools": [],
        "allowed_paths": [],
        "denied_paths": [
            r"\.env$", r"\.git/objects", r"\.ssh/", r"\.aws/",
            r"credentials", r"secrets?\.json",
        ],
        "allowed_commands": [],  # empty = all commands allowed (subject to denylists)
        "denied_commands": [
            r"\brm\s+-rf\s+/", r"\bsudo\s+rm\b",
            r"\bcurl\b.*\|.*\bsh\b", r"\bwget\b.*\|.*\bsh\b",
            r"\beval\b.*\$\(", r"\breboot\b", r"\bshutdown\b",
            r"\bformat\b", r":\(\)\s*\{.*\}", r"\bfork\s*bomb\b",
            r"\bdrop\s+(?:database|table)\b",
            r"\bdel\s+/[fF]\s+/[sS]\s+/[qQ]\b",
        ],
    },
    "permissive": {
        "description": "Minimal restrictions — only blocks catastrophic operations",
        "allowed_tools": [],
        "denied_tools": [],
        "allowed_paths": [],
        "denied_paths": [r"\.ssh/id_", r"\.aws/credentials"],
        "allowed_commands": [],
        "denied_commands": [
            r"\brm\s+-rf\s+/$",
            r":\(\)\s*\{.*\}",
            r"\bformat\s+[cCdD]:",
        ],
    },
}


# ---------------------------------------------------------------------------
# Active permission state
# ---------------------------------------------------------------------------

class PermissionManager:
    """Manages tool and path permissions for the agent."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = PRESETS["standard"].copy()
        self._preset_name: str = "standard"
        self._load_config()

    def _load_config(self) -> None:
        """Load permissions from env var preset or config file."""
        # Check for preset override
        preset = os.getenv("CORNERSTONE_PERMISSION_PRESET", "").strip().lower()
        if preset in PRESETS:
            self._config = PRESETS[preset].copy()
            self._preset_name = preset
            console.print(f"[dim]Permission preset: {preset}[/dim]")
            return

        # Check for config file
        config_path = os.path.join(os.path.dirname(__file__), "permissions.json")
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as fh:
                    custom = json.load(fh)
                self._config.update(custom)
                self._preset_name = "custom"
                console.print("[dim]Permission config loaded from permissions.json[/dim]")
            except (json.JSONDecodeError, OSError) as exc:
                console.print(f"[yellow]Failed to load permissions.json: {exc}[/yellow]")

    @property
    def preset_name(self) -> str:
        return self._preset_name

    def is_tool_allowed(self, tool_name: str) -> tuple[bool, str]:
        """Check if a tool is allowed.  Returns (allowed, reason)."""
        denied = self._config.get("denied_tools", [])
        if denied and tool_name in denied:
            return False, f"Tool '{tool_name}' is blocked by permission policy ({self._preset_name})"

        allowed = self._config.get("allowed_tools", [])
        if allowed and tool_name not in allowed:
            return False, (
                f"Tool '{tool_name}' is not in the allowlist. "
                f"Allowed tools: {', '.join(allowed)}"
            )

        return True, ""

    def is_path_allowed(self, filepath: str) -> tuple[bool, str]:
        """Check if a file path is allowed for read/write.  Returns (allowed, reason)."""
        denied_patterns = self._config.get("denied_paths", [])
        for pattern in denied_patterns:
            if re.search(pattern, filepath, re.IGNORECASE):
                return False, (
                    f"Path '{filepath}' matches denied pattern: {pattern}"
                )

        allowed_patterns = self._config.get("allowed_paths", [])
        if allowed_patterns:
            for pattern in allowed_patterns:
                if re.search(pattern, filepath, re.IGNORECASE):
                    return True, ""
            return False, f"Path '{filepath}' is not in the allowed paths list"

        return True, ""

    def is_command_allowed(self, command: str) -> tuple[bool, str]:
        """Check if a shell command is allowed.  Returns (allowed, reason)."""
        # Check denylists first
        denied_patterns = self._config.get("denied_commands", [])
        for pattern in denied_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False, (
                    f"Command blocked by permission policy: matches '{pattern}'"
                )

        # Check allowlists (if specified, command must match at least one)
        allowed_patterns = self._config.get("allowed_commands", [])
        if allowed_patterns:
            for pattern in allowed_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return True, ""
            return False, (
                "Command not in allowlist. Allowed patterns: "
                + ", ".join(allowed_patterns[:5])
            )

        return True, ""

    def check_tool_call(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> tuple[bool, str]:
        """Full permission check for a tool call.

        Checks tool allowlist, path restrictions, and command restrictions
        as applicable.

        Returns (allowed, reason).
        """
        # Check tool-level permission
        allowed, reason = self.is_tool_allowed(tool_name)
        if not allowed:
            return False, reason

        # Check path-based restrictions for file tools
        if tool_name in ("read_file", "write_file", "delete_file"):
            filepath = tool_input.get("filepath", "")
            if filepath:
                allowed, reason = self.is_path_allowed(filepath)
                if not allowed:
                    return False, reason

        # Check command restrictions for run_command
        if tool_name == "run_command":
            command = tool_input.get("command", "")
            if command:
                allowed, reason = self.is_command_allowed(command)
                if not allowed:
                    return False, reason

        return True, ""

    def get_status(self) -> dict[str, Any]:
        """Return current permission status for display."""
        return {
            "preset": self._preset_name,
            "description": self._config.get(
                "description", PRESETS.get(self._preset_name, {}).get("description", "")
            ),
            "denied_tools": self._config.get("denied_tools", []),
            "denied_path_patterns": len(self._config.get("denied_paths", [])),
            "denied_command_patterns": len(self._config.get("denied_commands", [])),
        }


# Module-level singleton
permissions = PermissionManager()
