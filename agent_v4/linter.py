"""Linting and type checking integration (#8).

After code changes, auto-runs configured linters (ruff, mypy, eslint, etc.)
and returns the results. The agent can then fix issues before reporting done.
"""

from __future__ import annotations

import subprocess
from typing import Any

from agent_v4.config import LINT_COMMAND, TYPECHECK_COMMAND, WORKSPACE


def _run_cmd(cmd: str) -> str:
    """Run a linting/typecheck command and return output."""
    if not cmd:
        return "No command configured."
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=120, cwd=WORKSPACE,
        )
        output = result.stdout.strip()
        if result.stderr.strip():
            output += "\n" + result.stderr.strip()
        if result.returncode == 0:
            return output or "All checks passed."
        return f"Issues found (exit code {result.returncode}):\n{output}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds."
    except Exception as exc:
        return f"Error: {exc}"


def run_lint(command: str = "") -> str:
    """Run the linter. Uses LINT_COMMAND from config if no command given."""
    cmd = command or LINT_COMMAND
    if not cmd:
        # Auto-detect common linters
        detected = _detect_linter()
        if detected:
            cmd = detected
        else:
            return ("No linter configured. Set LINT_COMMAND in .env or install "
                    "ruff/flake8/eslint in the workspace.")
    return _run_cmd(cmd)


def run_typecheck(command: str = "") -> str:
    """Run the type checker. Uses TYPECHECK_COMMAND from config if none given."""
    cmd = command or TYPECHECK_COMMAND
    if not cmd:
        detected = _detect_typechecker()
        if detected:
            cmd = detected
        else:
            return ("No type checker configured. Set TYPECHECK_COMMAND in .env "
                    "or install mypy/pyright in the workspace.")
    return _run_cmd(cmd)


def run_lint_file(filepath: str) -> str:
    """Run the linter on a specific file."""
    cmd = LINT_COMMAND or _detect_linter()
    if not cmd:
        return "No linter available."
    return _run_cmd(f"{cmd} {filepath}")


def _detect_linter() -> str:
    """Try to auto-detect an installed linter."""
    for cmd in ["ruff check .", "python -m flake8 .", "npx eslint ."]:
        check = cmd.split()[0]
        try:
            result = subprocess.run(
                f"which {check}" if check != "npx" else "which npx",
                shell=True, capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return cmd
        except Exception:
            continue
    return ""


def _detect_typechecker() -> str:
    """Try to auto-detect an installed type checker."""
    for cmd in ["python -m mypy .", "npx pyright ."]:
        check = cmd.split()[1] if "python" in cmd else cmd.split()[0]
        try:
            result = subprocess.run(
                f"python -m {check} --version" if check == "mypy" else f"which {check}",
                shell=True, capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return cmd
        except Exception:
            continue
    return ""


# ---------------------------------------------------------------------------
# Tool definitions for the agent
# ---------------------------------------------------------------------------

LINT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "run_lint",
        "description": (
            "Run the project linter (ruff, flake8, eslint, etc.) on the workspace. "
            "Returns any lint errors or warnings. Auto-detects linter if not configured."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Custom lint command (optional, uses auto-detected or configured if empty)",
                    "default": "",
                },
            },
            "required": [],
        },
    },
    {
        "name": "run_typecheck",
        "description": (
            "Run the type checker (mypy, pyright) on the workspace. "
            "Returns type errors. Auto-detects checker if not configured."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Custom typecheck command (optional)",
                    "default": "",
                },
            },
            "required": [],
        },
    },
    {
        "name": "run_lint_file",
        "description": "Run the linter on a specific file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to file to lint (relative to workspace)",
                },
            },
            "required": ["filepath"],
        },
    },
]

LINT_TOOLS: dict[str, Any] = {
    "run_lint": lambda command="": run_lint(command),
    "run_typecheck": lambda command="": run_typecheck(command),
    "run_lint_file": run_lint_file,
}
