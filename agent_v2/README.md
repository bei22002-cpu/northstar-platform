# Cornerstone AI Agent v2 — Automatic Token Rotation

A local AI agent powered by Claude (Anthropic) that can autonomously read,
write, edit, and manage files and run terminal commands inside the
Cornerstone project workspace — with a **human approval gate** before every
action and **automatic API key rotation** for uninterrupted progress.

---

## What's New in v2

| Feature | v1 | v2 |
| --- | --- | --- |
| API keys | Single key | Up to 10 keys with auto-rotation |
| Rate limits | Agent stops | Seamlessly switches to next key |
| Invalid keys | Fatal error | Skipped automatically |
| Server errors (500/503/529) | Fatal error | Retries with next key |
| Key status dashboard | N/A | Type `keys` at the prompt |
| Session stats on exit | N/A | Shows per-key call/error counts |

### How Token Rotation Works

1. You provide multiple Anthropic API keys in `.env`
   (`ANTHROPIC_API_KEY_1`, `ANTHROPIC_API_KEY_2`, etc.)
2. The agent uses the first available key for each API call.
3. When a key hits a **rate limit (429)**, the agent marks it as
   cooling down (60s) and immediately retries with the next key.
4. **Server errors** (500, 503, 529) trigger a short 10s cooldown
   and rotation.
5. **Invalid keys** (401) are permanently skipped.
6. If **all keys** are on cooldown, the agent waits for the shortest
   cooldown to expire, then continues automatically.

This means the agent can keep working continuously across long coding
sessions without you ever needing to intervene for rate-limit issues.

---

## Installation

```bash
pip install anthropic python-dotenv rich
```

---

## Configuration

1. Copy the example environment file:

   ```bash
   cp agent_v2/.env.example agent_v2/.env
   ```

2. Edit `agent_v2/.env` and add your Anthropic API keys:

   ```env
   ANTHROPIC_API_KEY_1=sk-ant-key-one...
   ANTHROPIC_API_KEY_2=sk-ant-key-two...
   ANTHROPIC_API_KEY_3=sk-ant-key-three...
   WORKSPACE=./backend
   ```

   You can add up to 10 keys (`_1` through `_10`). More keys = longer
   uninterrupted sessions. Even a single key works (backward compatible
   with v1's `ANTHROPIC_API_KEY`).

---

## Usage

From the **repository root**, run:

```bash
python -m agent_v2.main
```

### Special Commands

| Command | Description |
| --- | --- |
| `keys` | Show a table of all API keys with call counts, errors, and cooldown status |
| `exit` / `quit` | End the session (saves log + shows final key stats) |
| `Ctrl+C` | Interrupt the session |

---

## Available Tools

| Tool              | Description                                         |
| ----------------- | --------------------------------------------------- |
| `write_file`      | Write content to a file (creates parent dirs)       |
| `read_file`       | Read and return a file's contents                   |
| `list_files`      | Recursively list files in a directory               |
| `run_command`     | Run a shell command (60 s timeout)                  |
| `delete_file`     | Delete a file                                       |
| `create_directory`| Create a directory (and parents)                    |
| `search_in_files` | Search for a text pattern across files (max 50 hits)|
| `git_status`      | Show `git status` and `git diff --stat`             |

---

## Safety Features

### Blocked Commands

The following patterns are blocked and will **never** execute:

- `rm -rf /`
- `format`
- `del /f /s /q C:\`
- `shutdown`
- `DROP DATABASE`
- `DROP TABLE`
- `:(){ :|:& };:` (fork bomb)

### Approval Gate

Before every tool call the agent displays a styled panel showing:

- The tool name
- All parameters (file content is shown as a character count)

You must type **y** to approve. Anything else denies the action.

---

## Example Session

```
╭─ Welcome ─────────────────────────────────────────────╮
│ Cornerstone AI Agent v2                                │
│ Workspace: /home/user/northstar-platform/backend       │
│ API Keys loaded: 3                                     │
│ Auto-rotates keys on rate limits for continuous ...     │
│ Type 'exit' or 'quit' to end the session.              │
│ Type 'keys' to see token status.                       │
╰────────────────────────────────────────────────────────╯

You > Add a health check endpoint

Using API key #1 of 3

╭─ Cornerstone AI ──────────────────────────────────────╮
│ I'll add a /health endpoint. Let me first read the     │
│ existing main.py to understand the current structure.   │
╰────────────────────────────────────────────────────────╯

╭─ AI wants to perform an action ───────────────────────╮
│ Tool: read_file                                        │
│ filepath: app/main.py                                  │
╰────────────────────────────────────────────────────────╯
Approve? (y/n): y

Key #1 rate-limited. Rotating to next key...
Using API key #2 of 3

╭─ Cornerstone AI ──────────────────────────────────────╮
│ Now I'll write the health check endpoint...            │
╰────────────────────────────────────────────────────────╯
...
```

---

## Project Structure

```
agent_v2/
├── __init__.py        # Package marker
├── main.py            # CLI entry point with key stats dashboard
├── tools.py           # 8 tool implementations + schema definitions
├── safety.py          # Blocked-command list & approval gate
├── config.py          # Multi-key .env loader & validation
├── token_manager.py   # Automatic API key rotation engine
├── session.py         # Claude API interaction with token rotation
├── history.py         # In-memory message history & JSON logging
├── .env.example       # Example multi-key environment config
└── README.md          # This file
```
