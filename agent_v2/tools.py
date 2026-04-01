"""Tool implementations for the Cornerstone AI Agent v2."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from agent_v2.config import WORKSPACE


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

def write_file(filepath: str, content: str = "") -> str:
    """Write *content* to a file relative to WORKSPACE, creating parents."""
    if not content:
        return (
            f"Error: 'content' argument is required for write_file. "
            f"You called write_file with filepath='{filepath}' but no content. "
            f"Please retry with both filepath AND content arguments."
        )
    try:
        full = os.path.join(WORKSPACE, filepath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return f"Successfully wrote {len(content)} characters to {filepath}"
    except Exception as exc:
        return f"Error writing file: {exc}"


def read_file(filepath: str) -> str:
    """Read and return the contents of a file relative to WORKSPACE."""
    try:
        full = os.path.join(WORKSPACE, filepath)
        if not os.path.isfile(full):
            return f"Error: file not found — {filepath}"
        with open(full, "r", encoding="utf-8") as fh:
            return fh.read()
    except Exception as exc:
        return f"Error reading file: {exc}"


def list_files(directory: str = ".") -> str:
    """Recursively list all files under *directory* relative to WORKSPACE."""
    try:
        full = os.path.join(WORKSPACE, directory)
        if not os.path.isdir(full):
            return f"Error: directory not found — {directory}"
        files: list[str] = []
        for root, _dirs, filenames in os.walk(full):
            for name in filenames:
                rel = os.path.relpath(os.path.join(root, name), WORKSPACE)
                files.append(rel)
        files.sort()
        return "\n".join(files) if files else "(empty directory)"
    except Exception as exc:
        return f"Error listing files: {exc}"


def run_command(command: str) -> str:
    """Run a shell command inside WORKSPACE with a 60-second timeout."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 60 seconds."
    except Exception as exc:
        return f"Error running command: {exc}"


def delete_file(filepath: str) -> str:
    """Delete a file relative to WORKSPACE."""
    try:
        full = os.path.join(WORKSPACE, filepath)
        if not os.path.isfile(full):
            return f"Error: file not found — {filepath}"
        os.remove(full)
        return f"Successfully deleted {filepath}"
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
    """Search for *pattern* recursively across files, max 50 matches."""
    try:
        full = os.path.join(WORKSPACE, directory)
        if not os.path.isdir(full):
            return f"Error: directory not found — {directory}"
        matches: list[str] = []
        for root, _dirs, filenames in os.walk(full):
            for name in filenames:
                fpath = os.path.join(root, name)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                        for lineno, line in enumerate(fh, start=1):
                            if pattern in line:
                                rel = os.path.relpath(fpath, WORKSPACE)
                                matches.append(
                                    f"{rel}:{lineno}: {line.rstrip()}"
                                )
                                if len(matches) >= 50:
                                    matches.append(
                                        "... (results truncated at 50 matches)"
                                    )
                                    return "\n".join(matches)
                except (OSError, UnicodeDecodeError):
                    continue
        return "\n".join(matches) if matches else "No matches found."
    except Exception as exc:
        return f"Error searching files: {exc}"


def git_status() -> str:
    """Return ``git status`` and ``git diff --stat`` from WORKSPACE."""
    try:
        status = subprocess.run(
            "git status",
            shell=True,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=30,
        )
        diff = subprocess.run(
            "git diff --stat",
            shell=True,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = status.stdout
        if diff.stdout:
            output += "\n" + diff.stdout
        return output or "(no git output)"
    except Exception as exc:
        return f"Error running git commands: {exc}"


# ---------------------------------------------------------------------------
# Tool definitions (Anthropic tool-use schema)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "write_file",
        "description": "Write content to a file relative to the workspace. Creates parent directories if needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file relative to workspace root.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file.",
                },
            },
            "required": ["filepath", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read and return the contents of a file relative to the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file relative to workspace root.",
                },
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "list_files",
        "description": "Recursively list all files in a directory relative to the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path relative to workspace root. Defaults to '.'",
                    "default": ".",
                },
            },
            "required": [],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command inside the workspace directory. 60-second timeout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "delete_file",
        "description": "Delete a file relative to the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file relative to workspace root.",
                },
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "create_directory",
        "description": "Create a directory (and parents) relative to the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path to create relative to workspace root.",
                },
            },
            "required": ["directory"],
        },
    },
    {
        "name": "search_in_files",
        "description": "Search for a text pattern recursively across files. Returns filename, line number, and matched line. Max 50 results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text pattern to search for.",
                },
                "directory": {
                    "type": "string",
                    "description": "Directory to search in relative to workspace root. Defaults to '.'",
                    "default": ".",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "git_status",
        "description": "Run git status and git diff --stat in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_TOOL_MAP = {
    "write_file": write_file,
    "read_file": read_file,
    "list_files": list_files,
    "run_command": run_command,
    "delete_file": delete_file,
    "create_directory": create_directory,
    "search_in_files": search_in_files,
    "git_status": git_status,
}


MAX_TOOL_OUTPUT = 50_000  # cap tool output to prevent history bloat


def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Dispatch a tool call by name and return the string result."""
    func = _TOOL_MAP.get(tool_name)
    if func is None:
        return f"Error: unknown tool '{tool_name}'"
    try:
        result = func(**tool_input)
    except TypeError as exc:
        # Claude sometimes drops required arguments on large tool calls.
        # Return a helpful error so the agent can retry.
        return (
            f"Error: {exc}. "
            f"The tool '{tool_name}' was called with arguments: {list(tool_input.keys())}. "
            f"Please retry with all required arguments included. "
            f"For write_file, you MUST provide both 'filepath' and 'content'. "
            f"Try writing the content in smaller chunks if it's very large."
        )
    if len(result) > MAX_TOOL_OUTPUT:
        return result[:MAX_TOOL_OUTPUT] + f"\n\n... (output truncated at {MAX_TOOL_OUTPUT:,} chars)"
    return result
