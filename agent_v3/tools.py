"""Tool implementations for Cornerstone AI Agent v3.

Includes the original 8 tools plus:
- patch_file: insert/replace/delete specific lines
- Plugin system: drop .py files into agent_v3/plugins/ to add custom tools
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path
from typing import Any

from agent_v3.config import WORKSPACE

# ---------------------------------------------------------------------------
# Core tools
# ---------------------------------------------------------------------------


def write_file(filepath: str, content: str) -> str:
    """Write *content* to a file relative to WORKSPACE."""
    try:
        full = os.path.join(WORKSPACE, filepath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {filepath}"
    except Exception as exc:
        return f"Error writing file: {exc}"


def read_file(filepath: str) -> str:
    """Read and return file content relative to WORKSPACE."""
    try:
        full = os.path.join(WORKSPACE, filepath)
        with open(full, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found — {filepath}"
    except Exception as exc:
        return f"Error reading file: {exc}"


def list_files(directory: str = ".") -> str:
    """Recursively list files in *directory* relative to WORKSPACE."""
    try:
        full = os.path.join(WORKSPACE, directory)
        files: list[str] = []
        for root, _dirs, filenames in os.walk(full):
            for fn in sorted(filenames):
                rel = os.path.relpath(os.path.join(root, fn), WORKSPACE)
                files.append(rel)
        files.sort()
        return "\n".join(files) if files else "(empty directory)"
    except Exception as exc:
        return f"Error listing files: {exc}"


def run_command(command: str) -> str:
    """Run a shell command inside WORKSPACE (60s timeout)."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=60, cwd=WORKSPACE,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n--- stderr ---\n" + result.stderr)
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as exc:
        return f"Error running command: {exc}"


def delete_file(filepath: str) -> str:
    """Delete a file relative to WORKSPACE."""
    try:
        full = os.path.join(WORKSPACE, filepath)
        os.remove(full)
        return f"Successfully deleted {filepath}"
    except FileNotFoundError:
        return f"Error: File not found — {filepath}"
    except Exception as exc:
        return f"Error deleting file: {exc}"


def create_directory(directory: str) -> str:
    """Create a directory (and parents) relative to WORKSPACE."""
    try:
        full = os.path.join(WORKSPACE, directory)
        os.makedirs(full, exist_ok=True)
        return f"Successfully created directory {directory}"
    except Exception as exc:
        return f"Error creating directory: {exc}"


def search_in_files(pattern: str, directory: str = ".") -> str:
    """Search for *pattern* recursively in files. Max 50 results."""
    try:
        full = os.path.join(WORKSPACE, directory)
        results: list[str] = []
        for root, _dirs, filenames in os.walk(full):
            for fn in sorted(filenames):
                fpath = os.path.join(root, fn)
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if pattern in line:
                                rel = os.path.relpath(fpath, WORKSPACE)
                                results.append(f"{rel}:{i}: {line.rstrip()}")
                                if len(results) >= 50:
                                    return "\n".join(results) + "\n... (50 match limit)"
                except (OSError, UnicodeDecodeError):
                    continue
        return "\n".join(results) if results else "No matches found."
    except Exception as exc:
        return f"Error searching: {exc}"


def git_status() -> str:
    """Run git status + git diff --stat in WORKSPACE."""
    try:
        status = subprocess.run(
            "git status", shell=True, capture_output=True, text=True,
            cwd=WORKSPACE,
        )
        diff = subprocess.run(
            "git diff --stat", shell=True, capture_output=True, text=True,
            cwd=WORKSPACE,
        )
        return (status.stdout + "\n" + diff.stdout).strip()
    except Exception as exc:
        return f"Error getting git status: {exc}"


def patch_file(filepath: str, old_text: str, new_text: str) -> str:
    """Replace *old_text* with *new_text* in an existing file.

    This is safer than rewriting entire files — it only changes the
    specific section that needs updating.
    """
    try:
        full = os.path.join(WORKSPACE, filepath)
        with open(full, encoding="utf-8") as f:
            content = f.read()

        if old_text not in content:
            return (f"Error: Could not find the specified text in {filepath}. "
                    "Make sure the old_text matches exactly (including whitespace).")

        count = content.count(old_text)
        if count > 1:
            return (f"Warning: Found {count} occurrences of old_text in "
                    f"{filepath}. Replacing the first occurrence only.")

        new_content = content.replace(old_text, new_text, 1)
        with open(full, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"Successfully patched {filepath} ({len(old_text)} chars → {len(new_text)} chars)"
    except FileNotFoundError:
        return f"Error: File not found — {filepath}"
    except Exception as exc:
        return f"Error patching file: {exc}"


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

_CORE_TOOLS: dict[str, Any] = {
    "write_file": write_file,
    "read_file": read_file,
    "list_files": list_files,
    "run_command": run_command,
    "delete_file": delete_file,
    "create_directory": create_directory,
    "search_in_files": search_in_files,
    "git_status": git_status,
    "patch_file": patch_file,
}


# ---------------------------------------------------------------------------
# Tool definitions (Anthropic schema)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "write_file",
        "description": "Write content to a file. Creates parent directories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path relative to workspace"},
                "content": {"type": "string", "description": "File content to write"},
            },
            "required": ["filepath", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read and return a file's contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path relative to workspace"},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "list_files",
        "description": "Recursively list all files in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory relative to workspace", "default": "."},
            },
            "required": [],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command in the workspace (60s timeout).",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "delete_file",
        "description": "Delete a file from the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path relative to workspace"},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "create_directory",
        "description": "Create a directory (and parents) in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory path relative to workspace"},
            },
            "required": ["directory"],
        },
    },
    {
        "name": "search_in_files",
        "description": "Search for a text pattern across files (max 50 results).",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Text pattern to search for"},
                "directory": {"type": "string", "description": "Directory to search", "default": "."},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "git_status",
        "description": "Show git status and diff stats.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "patch_file",
        "description": "Replace a specific section of text in an existing file. Safer than rewriting the whole file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path relative to workspace"},
                "old_text": {"type": "string", "description": "Exact text to find and replace"},
                "new_text": {"type": "string", "description": "Replacement text"},
            },
            "required": ["filepath", "old_text", "new_text"],
        },
    },
]


# ---------------------------------------------------------------------------
# Plugin system — load custom tools from agent_v3/plugins/
# ---------------------------------------------------------------------------

_PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "plugins")
_plugin_tools: dict[str, Any] = {}


def _load_plugins() -> None:
    """Scan plugins/ for .py files and register any tools they export."""
    if not os.path.isdir(_PLUGIN_DIR):
        return

    for fname in sorted(os.listdir(_PLUGIN_DIR)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue

        fpath = os.path.join(_PLUGIN_DIR, fname)
        mod_name = f"agent_v3.plugins.{fname[:-3]}"

        try:
            spec = importlib.util.spec_from_file_location(mod_name, fpath)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Plugin must export TOOL_DEF (dict) and tool_func (callable)
            if hasattr(mod, "TOOL_DEF") and hasattr(mod, "tool_func"):
                name = mod.TOOL_DEF["name"]
                _plugin_tools[name] = mod.tool_func
                TOOL_DEFINITIONS.append(mod.TOOL_DEF)
                print(f"[plugin] Loaded tool '{name}' from {fname}")
        except Exception as exc:
            print(f"[plugin] Error loading {fname}: {exc}")


_load_plugins()


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Route a tool call to the correct function."""
    func = _CORE_TOOLS.get(tool_name) or _plugin_tools.get(tool_name)
    if func is None:
        return f"Error: Unknown tool '{tool_name}'"
    try:
        return func(**tool_input)
    except Exception as exc:
        return f"Error executing {tool_name}: {exc}"
