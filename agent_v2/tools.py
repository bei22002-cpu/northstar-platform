"""Tool implementations for the Cornerstone AI Agent v2.

Includes the Task tool for sub-agent delegation (Claude Code Agent Teams)
and undercover-mode-aware git operations.
"""

from __future__ import annotations

import os
import re
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
    # Scrub AI markers from git commit messages if undercover mode is on
    from agent_v2.undercover import is_undercover_enabled, scrub_commit_message
    if is_undercover_enabled() and "git commit" in command:
        match = re.search(r'-m\s+["\'](.+?)["\']', command)
        if match:
            original = match.group(1)
            scrubbed = scrub_commit_message(original)
            if scrubbed != original:
                command = command.replace(original, scrubbed)

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


def patch_file(filepath: str, find: str, replace: str) -> str:
    """Find-and-replace within a file.  Reads the file, replaces the first
    occurrence of *find* with *replace*, and writes it back.
    """
    try:
        full = os.path.join(WORKSPACE, filepath)
        if not os.path.isfile(full):
            return f"Error: file not found \u2014 {filepath}"
        with open(full, "r", encoding="utf-8") as fh:
            content = fh.read()
        if find not in content:
            return f"Error: pattern not found in {filepath}"
        new_content = content.replace(find, replace, 1)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(new_content)
        return f"Successfully patched {filepath}"
    except Exception as exc:
        return f"Error patching file: {exc}"


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
    {
        "name": "patch_file",
        "description": "Find and replace text within a file. Replaces the first occurrence of 'find' with 'replace'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file relative to workspace root.",
                },
                "find": {
                    "type": "string",
                    "description": "The exact text to find in the file.",
                },
                "replace": {
                    "type": "string",
                    "description": "The text to replace it with.",
                },
            },
            "required": ["filepath", "find", "replace"],
        },
    },
    {
        "name": "task",
        "description": (
            "Delegate a focused sub-task to a sub-agent with its own context window. "
            "The sub-agent can use all tools except 'task' (no recursive spawning). "
            "Use this for complex operations that would bloat the main conversation: "
            "code generation, multi-file refactoring, research, analysis. "
            "The sub-agent returns its results as a string."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Clear description of the task for the sub-agent to complete.",
                },
                "context": {
                    "type": "string",
                    "description": "Optional context from the current conversation to help the sub-agent.",
                    "default": "",
                },
            },
            "required": ["task"],
        },
    },
    # --- 3D Printing tools ---
    {
        "name": "generate_3d_part",
        "description": (
            "Generate a 3D printable part as an OpenSCAD (.scad) file. "
            "Use part_type for templates (box, bracket, cylinder_mount, gear, "
            "phone_stand, cable_clip, hinge, spacer) with params JSON, "
            "or provide custom_scad code directly. "
            "The user can open the .scad file in OpenSCAD to preview and export to STL for printing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "part_type": {
                    "type": "string",
                    "description": "Template name: box, bracket, cylinder_mount, gear, phone_stand, cable_clip, hinge, spacer",
                },
                "name": {
                    "type": "string",
                    "description": "Filename for the part (without .scad extension).",
                },
                "params": {
                    "type": "string",
                    "description": 'JSON string of parameters to customize the template. E.g. {\"width\": 80, \"height\": 50}',
                    "default": "{}",
                },
                "custom_scad": {
                    "type": "string",
                    "description": "Raw OpenSCAD code to write directly (ignores part_type if provided).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "list_3d_templates",
        "description": "List all available 3D part templates with their parameters.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_3d_parts",
        "description": "List all previously generated 3D parts.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # --- Game Development tools ---
    {
        "name": "create_game_project",
        "description": (
            "Create a new game project from a template. "
            "Frameworks: pygame, phaser. "
            "Genres: platformer, topdown_rpg, space_shooter, puzzle, endless_runner. "
            "Generates all source files ready to run."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name (used as directory name).",
                },
                "framework": {
                    "type": "string",
                    "description": "Game framework: pygame, phaser, godot, love2d, unity",
                    "default": "pygame",
                },
                "genre": {
                    "type": "string",
                    "description": "Game genre template: platformer, topdown_rpg, space_shooter, puzzle, endless_runner",
                    "default": "platformer",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "clone_game_repo",
        "description": (
            "Clone a game repository from GitHub into the game projects directory. "
            "Use this to pull in game engines, frameworks, or example projects."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_url": {
                    "type": "string",
                    "description": "GitHub repository URL to clone.",
                },
                "name": {
                    "type": "string",
                    "description": "Optional local directory name. Defaults to repo name.",
                    "default": "",
                },
            },
            "required": ["repo_url"],
        },
    },
    {
        "name": "list_game_projects",
        "description": "List all game projects that have been created or cloned.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_game_frameworks",
        "description": "List all supported game development frameworks with install and run instructions.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_game_genres",
        "description": "List all available game genre templates.",
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

from agent_v2.printing3d import generate_3d_part, list_3d_templates, list_3d_parts
from agent_v2.gamedev import (
    create_game_project,
    clone_game_repo,
    list_game_projects,
    list_game_frameworks,
    list_game_genres,
)

_TOOL_MAP = {
    "write_file": write_file,
    "read_file": read_file,
    "list_files": list_files,
    "run_command": run_command,
    "delete_file": delete_file,
    "create_directory": create_directory,
    "search_in_files": search_in_files,
    "git_status": git_status,
    "patch_file": patch_file,
    # 3D Printing
    "generate_3d_part": generate_3d_part,
    "list_3d_templates": list_3d_templates,
    "list_3d_parts": list_3d_parts,
    # Game Development
    "create_game_project": create_game_project,
    "clone_game_repo": clone_game_repo,
    "list_game_projects": list_game_projects,
    "list_game_frameworks": list_game_frameworks,
    "list_game_genres": list_game_genres,
    # "task" is handled specially in session.py -- not dispatched here
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
