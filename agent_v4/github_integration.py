"""GitHub integration — branches, commits, PRs (#3).

Uses the GitHub REST API to create branches, commits, and pull requests
directly from the agent. Requires a GITHUB_TOKEN and GITHUB_REPO in config.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from agent_v4.config import GITHUB_REPO, GITHUB_TOKEN, WORKSPACE


def _run_git(cmd: str) -> str:
    """Run a git command in the workspace and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=30, cwd=WORKSPACE,
        )
        output = result.stdout.strip()
        if result.stderr.strip():
            output += "\n" + result.stderr.strip()
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Git command timed out."
    except Exception as exc:
        return f"Error: {exc}"


def git_create_branch(branch_name: str) -> str:
    """Create and switch to a new git branch."""
    return _run_git(f"git checkout -b {branch_name}")


def git_commit(message: str) -> str:
    """Stage all changes and commit with the given message."""
    _run_git("git add -A")
    return _run_git(f'git commit -m "{message}"')


def git_push(branch_name: str = "") -> str:
    """Push the current branch to origin."""
    if branch_name:
        return _run_git(f"git push -u origin {branch_name}")
    return _run_git("git push")


def git_current_branch() -> str:
    """Return the current branch name."""
    return _run_git("git branch --show-current")


def git_log(count: int = 5) -> str:
    """Show recent git log entries."""
    return _run_git(f"git log --oneline -n {count}")


def git_diff() -> str:
    """Show current uncommitted changes."""
    return _run_git("git diff")


def git_create_pr(title: str, body: str, base: str = "main") -> str:
    """Create a pull request using the GitHub API.

    Requires GITHUB_TOKEN and GITHUB_REPO to be configured.
    """
    if not GITHUB_TOKEN:
        return "Error: GITHUB_TOKEN not configured. Set it in agent_v4/.env"
    if not GITHUB_REPO:
        return "Error: GITHUB_REPO not configured. Set it in agent_v4/.env (e.g. owner/repo)"

    branch = _run_git("git branch --show-current").strip()
    if not branch or "Error" in branch:
        return f"Error: Could not determine current branch: {branch}"

    # Push first
    push_result = git_push(branch)
    if "error" in push_result.lower() and "Everything up-to-date" not in push_result:
        return f"Error pushing branch: {push_result}"

    # Create PR via GitHub API
    try:
        import urllib.request
        import urllib.error

        url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls"
        data = json.dumps({
            "title": title,
            "body": body,
            "head": branch,
            "base": base,
        }).encode()

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            pr_url = result.get("html_url", "unknown")
            pr_number = result.get("number", "unknown")
            return f"PR #{pr_number} created: {pr_url}"

    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode() if exc.fp else str(exc)
        return f"GitHub API error ({exc.code}): {error_body}"
    except Exception as exc:
        return f"Error creating PR: {exc}"


# ---------------------------------------------------------------------------
# Tool definitions for the agent
# ---------------------------------------------------------------------------

GITHUB_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "git_create_branch",
        "description": "Create and switch to a new git branch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch_name": {"type": "string", "description": "Name of the new branch"},
            },
            "required": ["branch_name"],
        },
    },
    {
        "name": "git_commit",
        "description": "Stage all changes and commit with a message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Commit message"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "git_push",
        "description": "Push the current branch to origin.",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch_name": {"type": "string", "description": "Branch to push (optional, defaults to current)", "default": ""},
            },
            "required": [],
        },
    },
    {
        "name": "git_create_pr",
        "description": "Create a GitHub pull request from the current branch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "PR title"},
                "body": {"type": "string", "description": "PR description"},
                "base": {"type": "string", "description": "Base branch (default: main)", "default": "main"},
            },
            "required": ["title", "body"],
        },
    },
    {
        "name": "git_current_branch",
        "description": "Show the current git branch name.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "git_log",
        "description": "Show recent git log entries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of entries (default 5)", "default": 5},
            },
            "required": [],
        },
    },
    {
        "name": "git_diff",
        "description": "Show current uncommitted changes.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

GITHUB_TOOLS: dict[str, Any] = {
    "git_create_branch": git_create_branch,
    "git_commit": git_commit,
    "git_push": git_push,
    "git_create_pr": git_create_pr,
    "git_current_branch": git_current_branch,
    "git_log": git_log,
    "git_diff": git_diff,
}
