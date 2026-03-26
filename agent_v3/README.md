# Cornerstone AI Agent v3 — Full-Featured Autonomous

A fully autonomous local AI agent powered by Claude (Anthropic) with
**streaming responses**, **automatic key rotation with exponential backoff**,
**cost tracking**, **model switching**, **undo/rollback**, **persistent sessions**,
**a plugin system**, **expanded safety**, and a **browser-based Web UI**.

---

## What's New in v3 (vs v2)

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Streaming responses** | Text appears word-by-word in real time instead of waiting for the full response |
| 2 | **Expanded safety blocklist** | 25+ dangerous patterns blocked (including `rm -rf .`, `chmod 777`, `curl\|bash`, path traversal). Safety checks on `write_file`, `delete_file`, and `patch_file` — not just `run_command` |
| 3 | **Persistent sessions** | Save/load conversation history. Resume where you left off with `resume <file>` |
| 4 | **Exponential backoff** | Rate-limited keys use increasing cooldowns (60s → 120s → 240s...) capped at 5 min |
| 5 | **patch_file tool** | Edit specific sections of a file instead of rewriting the whole thing |
| 6 | **Auto project context** | On startup, the agent reads your README and file structure so it already knows the codebase |
| 7 | **Cost tracking** | Track input/output tokens and estimated USD cost per model. Type `cost` to see |
| 8 | **Undo/rollback** | Agent auto-commits before changes. Type `undo` to revert the last action via git |
| 9 | **Web UI** | Browser-based chat interface with WebSocket (FastAPI + HTML) |
| 10 | **Plugin system** | Drop `.py` files in `agent_v3/plugins/` to add custom tools |
| 11 | **Multi-model support** | Switch between Opus (powerful), Sonnet (fast), Haiku (cheap) mid-session |

---

## Installation

```bash
pip install anthropic python-dotenv rich fastapi uvicorn websockets
```

---

## Configuration

```bash
cp agent_v3/.env.example agent_v3/.env
```

Edit `agent_v3/.env`:

```env
ANTHROPIC_API_KEY_1=sk-ant-your-first-key
ANTHROPIC_API_KEY_2=sk-ant-your-second-key
WORKSPACE=./backend
DEFAULT_MODEL=sonnet
MAX_TOKENS=8096
```

---

## Running — CLI Mode

From the repo root:

```bash
python -m agent_v3.main
```

### CLI Commands

| Command | What it does |
|---------|-------------|
| `exit` / `quit` | End session (saves log automatically) |
| `keys` | Show API key stats dashboard |
| `cost` | Show token usage and estimated cost |
| `model opus` | Switch to Claude Opus (most powerful) |
| `model sonnet` | Switch to Claude Sonnet (fast, default) |
| `model haiku` | Switch to Claude Haiku (cheapest) |
| `undo` | Revert the last agent change via git |
| `sessions` | List all saved sessions |
| `resume <file>` | Resume a saved session |
| `clear` | Clear conversation history |

---

## Running — Web UI Mode

```bash
uvicorn agent_v3.web:app --port 8080
```

Then open http://localhost:8080 in your browser. You get:
- Real-time chat with the agent
- Model selector dropdown (Opus / Sonnet / Haiku)
- Cost and Keys buttons
- Tool call and result panels
- Blocked command alerts

---

## Available Tools (9 built-in)

| Tool | Description |
|------|-------------|
| `read_file` | Read a file's contents |
| `write_file` | Write content to a file (creates parents) |
| `patch_file` | Replace a specific section of an existing file |
| `delete_file` | Delete a file |
| `list_files` | Recursively list files in a directory |
| `create_directory` | Create a directory and parents |
| `run_command` | Run a shell command (60s timeout) |
| `search_in_files` | Search for text patterns across files |
| `git_status` | Show git status and diff stats |

---

## Plugin System

Create a `.py` file in `agent_v3/plugins/`:

```python
# agent_v3/plugins/hello.py

TOOL_DEF = {
    "name": "hello",
    "description": "Say hello to someone.",
    "input_schema": {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
}

def tool_func(name: str) -> str:
    return f"Hello, {name}!"
```

The plugin is loaded automatically on startup.

---

## Safety Features

### Blocked Commands (run_command)

Patterns including: `rm -rf /`, `rm -rf .`, `rm -rf *`, `format`, `mkfs`,
`dd if=`, `shutdown`, `reboot`, `DROP DATABASE`, `DROP TABLE`, `TRUNCATE TABLE`,
fork bomb, `curl | bash`, `wget | bash`, `chmod 777`, `cat /etc/shadow`, and more.

### Blocked Paths (write_file / delete_file / patch_file)

Path traversal (`..`), system directories (`/etc/`, `/usr/`, `/bin/`, etc.),
SSH keys (`~/.ssh`), and `.env` files are all blocked.

### Autonomous Execution

All tool calls execute automatically — no `y/n` prompts. Blocked actions
are silently rejected and the agent is told why.

---

## Cost Tracking

Token usage and estimated cost are tracked per model:

```
Total requests: 12
Input tokens:   45,230
Output tokens:  8,450
Estimated cost: $0.2614

Per model:
  sonnet: 10 calls, 40,230+7,450 tokens, $0.2325
  opus:    2 calls,  5,000+1,000 tokens, $0.1500
```

---

## Example Session (CLI)

```
╭─ Welcome ─────────────────────────────────────────────╮
│ Cornerstone AI Agent v3 — Full-Featured Autonomous    │
│ Workspace: /home/user/northstar-platform/backend      │
│ API Keys loaded: 2                                    │
│ Model: claude-sonnet-4-5-20250514                     │
│ Fully autonomous — executes tools without approval.   │
│ ...                                                   │
╰───────────────────────────────────────────────────────╯

You > Show me the main FastAPI app

Using API key #1 of 2 | Model: claude-sonnet-4-5-20250514

Cornerstone AI: I'll read the main application file to show you...

╭─ Executing ───────────────────────────────────────────╮
│ Tool: read_file                                       │
│ filepath: app/main.py                                 │
╰───────────────────────────────────────────────────────╯

Cornerstone AI: Here's the main FastAPI application...

You > model opus
Switched to opus (claude-opus-4-5)

You > cost
╭─ Token Usage & Cost ──────────────────────────────────╮
│ Total requests: 2                                     │
│ Input tokens:   12,450                                │
│ Output tokens:  1,230                                 │
│ Estimated cost: $0.0559                               │
╰───────────────────────────────────────────────────────╯

You > exit
Session log saved to: agent_v3/logs/session_2026_03_24_22_30_00.json
Goodbye!
```

---

## Project Structure

```
agent_v3/
├── __init__.py         # Package marker
├── main.py             # CLI entry point
├── web.py              # Web UI (FastAPI + WebSocket)
├── session.py          # Claude API interaction with streaming
├── tools.py            # 9 tool implementations + plugin loader
├── safety.py           # Expanded blocklist + path safety
├── config.py           # Multi-key, multi-model .env loader
├── token_manager.py    # Key rotation with exponential backoff
├── history.py          # Persistent session save/load
├── cost_tracker.py     # Token usage & cost tracking
├── plugins/            # Drop-in custom tools
│   └── __init__.py
├── templates/
│   └── index.html      # Web UI template
├── logs/               # Session logs (auto-created)
├── .env.example        # Configuration template
└── README.md           # This file
```
