"""Tool implementations for the Cornerstone AI Agent v4.

Includes the 9 core tools from v3 plus:
- RAG search tool
- Memory tools (remember, recall, search_memory)
- GitHub tools (branch, commit, push, PR)
- Test generation tools
- Linting tools
- Multi-agent orchestration tool
- Plugin system
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
from typing import Any

from agent_v4.config import WORKSPACE

# ---------------------------------------------------------------------------
# Core tools (from v3)
# ---------------------------------------------------------------------------


def write_file(filepath: str, content: str) -> str:
    full = os.path.join(WORKSPACE, filepath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {len(content)} chars to {filepath}"
    except Exception as exc:
        return f"Error writing {filepath}: {exc}"


def read_file(filepath: str) -> str:
    full = os.path.join(WORKSPACE, filepath)
    try:
        with open(full, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: {filepath} not found."
    except Exception as exc:
        return f"Error reading {filepath}: {exc}"


def list_files(directory: str = ".") -> str:
    full = os.path.join(WORKSPACE, directory)
    try:
        result: list[str] = []
        for root, dirs, files in os.walk(full):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv"}]
            for f in sorted(files):
                rel = os.path.relpath(os.path.join(root, f), WORKSPACE)
                result.append(rel)
        return "\n".join(sorted(result)) or "(empty directory)"
    except Exception as exc:
        return f"Error listing {directory}: {exc}"


def run_command(command: str) -> str:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=60, cwd=WORKSPACE,
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as exc:
        return f"Error: {exc}"


def delete_file(filepath: str) -> str:
    full = os.path.join(WORKSPACE, filepath)
    try:
        os.remove(full)
        return f"Deleted {filepath}"
    except FileNotFoundError:
        return f"Error: {filepath} not found."
    except Exception as exc:
        return f"Error deleting {filepath}: {exc}"


def create_directory(directory: str) -> str:
    full = os.path.join(WORKSPACE, directory)
    try:
        os.makedirs(full, exist_ok=True)
        return f"Created directory {directory}"
    except Exception as exc:
        return f"Error creating {directory}: {exc}"


def search_in_files(pattern: str, directory: str = ".") -> str:
    full = os.path.join(WORKSPACE, directory)
    matches: list[str] = []
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv"}
    try:
        for root, dirs, files in os.walk(full):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in sorted(files):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if pattern.lower() in line.lower():
                                rel = os.path.relpath(fpath, WORKSPACE)
                                matches.append(f"{rel}:{i}: {line.rstrip()}")
                                if len(matches) >= 50:
                                    return "\n".join(matches) + "\n... (50 match limit)"
                except (OSError, UnicodeDecodeError):
                    continue
        return "\n".join(matches) or "No matches found."
    except Exception as exc:
        return f"Error: {exc}"


def git_status() -> str:
    try:
        status = subprocess.run(
            "git status", shell=True, capture_output=True, text=True,
            timeout=10, cwd=WORKSPACE,
        )
        diff = subprocess.run(
            "git diff --stat", shell=True, capture_output=True, text=True,
            timeout=10, cwd=WORKSPACE,
        )
        return status.stdout.strip() + "\n\n" + diff.stdout.strip()
    except Exception as exc:
        return f"Error: {exc}"


def patch_file(filepath: str, old_text: str, new_text: str) -> str:
    full = os.path.join(WORKSPACE, filepath)
    try:
        with open(full, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return f"Error: {filepath} not found."
    except Exception as exc:
        return f"Error reading {filepath}: {exc}"

    if old_text not in content:
        return f"Error: The specified text was not found in {filepath}."

    new_content = content.replace(old_text, new_text, 1)
    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"Patched {filepath}: replaced {len(old_text)} chars with {len(new_text)} chars."
    except Exception as exc:
        return f"Error writing {filepath}: {exc}"


# ---------------------------------------------------------------------------
# RAG search tool
# ---------------------------------------------------------------------------

def search_codebase(query: str, max_results: int = 10) -> str:
    """Semantic search over the indexed codebase."""
    from agent_v4.rag import CodebaseIndex
    # Use the shared index from session
    try:
        from agent_v4 import _shared_index
        index = _shared_index
    except (ImportError, AttributeError):
        index = CodebaseIndex()
        index.index_workspace(WORKSPACE)

    results = index.search(query, max_results)
    if not results:
        return f"No results found for: {query}"

    lines: list[str] = []
    for r in results:
        lines.append(f"**{r['filepath']}** (line {r['line_start']}, score: {r['score']})")
        lines.append(r["preview"])
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Memory tools
# ---------------------------------------------------------------------------

def remember(key: str, value: str) -> str:
    from agent_v4.memory import KnowledgeBase
    kb = KnowledgeBase()
    return kb.remember(key, value)


def recall(key: str) -> str:
    from agent_v4.memory import KnowledgeBase
    kb = KnowledgeBase()
    result = kb.recall(key)
    if result is None:
        return f"No memory found for: {key}"
    return result


def search_memory(query: str) -> str:
    from agent_v4.memory import KnowledgeBase
    kb = KnowledgeBase()
    results = kb.search(query)
    if not results:
        return f"No memories matching: {query}"
    lines: list[str] = []
    for r in results:
        lines.append(f"- **{r['key']}**: {r['value']} (updated: {r['updated_at']})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Plugin system
# ---------------------------------------------------------------------------

_plugin_tools: dict[str, Any] = {}
_plugin_defs: list[dict[str, Any]] = []


def _load_plugins() -> None:
    """Scan plugins/ for .py files and register any tools they export."""
    plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
    if not os.path.isdir(plugin_dir):
        return

    for fname in sorted(os.listdir(plugin_dir)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue

        fpath = os.path.join(plugin_dir, fname)
        module_name = f"agent_v4.plugins.{fname[:-3]}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, fpath)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            tool_def = getattr(mod, "TOOL_DEF", None)
            tool_func = getattr(mod, "tool_func", None)

            if tool_def and tool_func:
                name = tool_def.get("name", fname[:-3])
                _plugin_tools[name] = tool_func
                _plugin_defs.append(tool_def)
                print(f"[Plugin] Loaded: {name} from {fname}")
        except Exception as exc:
            print(f"[Plugin] Error loading {fname}: {exc}")


_load_plugins()

# ---------------------------------------------------------------------------
# Tool definitions (Anthropic tool-use schema)
# ---------------------------------------------------------------------------

CORE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "write_file",
        "description": "Write content to a file (creates parent dirs).",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "File path relative to workspace"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["filepath", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "File path relative to workspace"},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "list_files",
        "description": "Recursively list files in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory (default '.')", "default": "."},
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
                "command": {"type": "string", "description": "Shell command to execute"},
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
                "filepath": {"type": "string", "description": "File path to delete"},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "create_directory",
        "description": "Create a directory and any parent directories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory path to create"},
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
                "pattern": {"type": "string", "description": "Text pattern to search"},
                "directory": {"type": "string", "description": "Directory to search (default '.')", "default": "."},
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
        "description": "Replace a specific section in a file (safer than full rewrite).",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "File path"},
                "old_text": {"type": "string", "description": "Exact text to find"},
                "new_text": {"type": "string", "description": "Replacement text"},
            },
            "required": ["filepath", "old_text", "new_text"],
        },
    },
    {
        "name": "search_codebase",
        "description": "Semantic search over the indexed codebase. Finds relevant code by meaning, not just exact text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "max_results": {"type": "integer", "description": "Max results (default 10)", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "remember",
        "description": "Store a fact in persistent memory for future sessions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key/name for the memory"},
                "value": {"type": "string", "description": "Value/fact to remember"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "recall",
        "description": "Retrieve a fact from persistent memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key to look up"},
            },
            "required": ["key"],
        },
    },
    {
        "name": "search_memory",
        "description": "Search persistent memory by keyword.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
]

# Import extended tool definitions
from agent_v4.github_integration import GITHUB_TOOL_DEFINITIONS, GITHUB_TOOLS
from agent_v4.test_generator import TEST_TOOL_DEFINITIONS, TEST_TOOLS
from agent_v4.linter import LINT_TOOL_DEFINITIONS, LINT_TOOLS
from agent_v4.multi_agent import MULTI_AGENT_TOOL_DEFINITIONS

# Combine all tool definitions
TOOL_DEFINITIONS: list[dict[str, Any]] = (
    CORE_TOOL_DEFINITIONS
    + GITHUB_TOOL_DEFINITIONS
    + TEST_TOOL_DEFINITIONS
    + LINT_TOOL_DEFINITIONS
    + MULTI_AGENT_TOOL_DEFINITIONS
    + _plugin_defs
)

# Tool dispatcher map
_CORE_TOOLS: dict[str, Any] = {
    "write_file": lambda filepath, content: write_file(filepath, content),
    "read_file": lambda filepath: read_file(filepath),
    "list_files": lambda directory=".": list_files(directory),
    "run_command": lambda command: run_command(command),
    "delete_file": lambda filepath: delete_file(filepath),
    "create_directory": lambda directory: create_directory(directory),
    "search_in_files": lambda pattern, directory=".": search_in_files(pattern, directory),
    "git_status": lambda: git_status(),
    "patch_file": lambda filepath, old_text, new_text: patch_file(filepath, old_text, new_text),
    "search_codebase": lambda query, max_results=10: search_codebase(query, max_results),
    "remember": lambda key, value: remember(key, value),
    "recall": lambda key: recall(key),
    "search_memory": lambda query: search_memory(query),
}


def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Dispatch a tool call to the correct function."""
    # Check core tools
    if tool_name in _CORE_TOOLS:
        try:
            return _CORE_TOOLS[tool_name](**tool_input)
        except Exception as exc:
            return f"Error in {tool_name}: {exc}"

    # Check GitHub tools
    if tool_name in GITHUB_TOOLS:
        try:
            return GITHUB_TOOLS[tool_name](**tool_input)
        except Exception as exc:
            return f"Error in {tool_name}: {exc}"

    # Check test tools
    if tool_name in TEST_TOOLS:
        try:
            return TEST_TOOLS[tool_name](**tool_input)
        except Exception as exc:
            return f"Error in {tool_name}: {exc}"

    # Check lint tools
    if tool_name in LINT_TOOLS:
        try:
            return LINT_TOOLS[tool_name](**tool_input)
        except Exception as exc:
            return f"Error in {tool_name}: {exc}"

    # Check multi-agent (handled separately in session.py)
    if tool_name == "run_parallel_tasks":
        return "__MULTI_AGENT__"

    # Check plugins
    if tool_name in _plugin_tools:
        try:
            return _plugin_tools[tool_name](**tool_input)
        except Exception as exc:
            return f"Error in plugin {tool_name}: {exc}"

    return f"Unknown tool: {tool_name}"
