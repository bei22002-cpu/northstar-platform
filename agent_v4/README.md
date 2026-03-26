# Cornerstone AI Agent v4

A fully autonomous local AI agent powered by Claude with **RAG codebase search**,
**multi-agent orchestration**, **GitHub integration**, **auto test generation**,
**persistent memory**, **linting integration**, **Slack bot**, and **custom system prompts**
— on top of all v3 features (streaming, cost tracking, safety, key rotation, etc.).

---

## What's New in v4 (vs v3)

| # | Feature | Description |
|---|---------|-------------|
| 1 | **RAG / Codebase Indexing** | On startup, indexes all files into a TF-IDF search index. The agent can search semantically (e.g. "find the auth middleware") |
| 2 | **Multi-Agent Orchestration** | Spawn up to 5 worker agents that execute tasks in parallel. Great for refactoring multiple files simultaneously |
| 3 | **GitHub Integration** | Create branches, commit, push, and open pull requests directly from the agent |
| 4 | **Auto Test Generation** | Generate pytest test skeletons for any Python file and run them automatically |
| 5 | **Persistent Memory** | Store project facts and preferences that persist across all sessions |
| 8 | **Linting & Type Checking** | Auto-runs ruff/flake8/mypy after code changes. Auto-detects installed linters |
| 9 | **Slack Bot** | Run the agent as a Slack bot — mention it in channels or DM it directly |
| 11 | **Custom System Prompts** | Customize the agent's personality via env var or `system_prompt.txt` file |

Plus all v3 features: streaming responses, expanded safety (25+ patterns), persistent
sessions, exponential backoff, patch_file tool, auto project context, cost tracking,
undo/rollback, web UI, plugin system, and multi-model support.

---

## Installation

```bash
pip install anthropic python-dotenv rich fastapi uvicorn websockets
```

Optional (for Slack bot):
```bash
pip install slack-bolt
```

---

## Configuration

```bash
cp agent_v4/.env.example agent_v4/.env
```

Edit `agent_v4/.env` — at minimum set your API key(s):

```env
ANTHROPIC_API_KEY_1=sk-ant-your-key-here
WORKSPACE=./backend
```

See `.env.example` for all options including GitHub token, Slack tokens, and linter config.

### Custom System Prompt

Option A — Environment variable:
```env
SYSTEM_PROMPT=You are a DevOps expert specializing in Kubernetes...
```

Option B — File (create `agent_v4/system_prompt.txt`):
```
You are a senior frontend engineer specializing in React and TypeScript.
Always suggest component-based architecture.
```

---

## Running — CLI Mode

```bash
python -m agent_v4.main
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `exit` / `quit` | End session |
| `keys` | API key stats dashboard |
| `cost` | Token usage and estimated cost |
| `model opus/sonnet/haiku` | Switch model mid-session |
| `undo` | Revert last agent change |
| `sessions` | List saved sessions |
| `resume <file>` | Resume a saved session |
| `memory` | Show persistent memories |
| `reindex` | Re-index codebase for RAG |
| `clear` | Clear conversation history |

---

## Running — Web UI Mode

```bash
uvicorn agent_v4.web:app --port 8080
```

Open http://localhost:8080 — features model selector, cost/keys/memory buttons, tool call panels, and real-time chat.

---

## Running — Slack Bot Mode

1. Create a Slack app at https://api.slack.com/apps
2. Enable Socket Mode and add scopes: `app_mentions:read`, `chat:write`, `im:history`
3. Set `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` in `.env`
4. Run:

```bash
python -m agent_v4.main --slack
```

Mention the bot in any channel or DM it directly. Commands in DM: `cost`, `clear`, `model <name>`.

---

## All Available Tools (22+)

### Core Tools (9)
| Tool | Description |
|------|-------------|
| `read_file` | Read file contents |
| `write_file` | Write content to a file |
| `patch_file` | Edit a specific section of a file |
| `delete_file` | Delete a file |
| `list_files` | List files recursively |
| `create_directory` | Create directories |
| `run_command` | Run shell commands (60s timeout) |
| `search_in_files` | Text pattern search |
| `git_status` | Git status + diff stats |

### RAG Tools (1)
| Tool | Description |
|------|-------------|
| `search_codebase` | Semantic search over indexed codebase |

### Memory Tools (3)
| Tool | Description |
|------|-------------|
| `remember` | Store a fact for future sessions |
| `recall` | Retrieve a stored fact |
| `search_memory` | Search memories by keyword |

### GitHub Tools (7)
| Tool | Description |
|------|-------------|
| `git_create_branch` | Create and switch to a new branch |
| `git_commit` | Stage and commit changes |
| `git_push` | Push to remote |
| `git_create_pr` | Create a GitHub pull request |
| `git_current_branch` | Show current branch |
| `git_log` | Recent commit history |
| `git_diff` | Show uncommitted changes |

### Testing Tools (2)
| Tool | Description |
|------|-------------|
| `generate_tests` | Generate pytest test skeletons |
| `run_tests` | Run pytest and return results |

### Linting Tools (3)
| Tool | Description |
|------|-------------|
| `run_lint` | Run project linter |
| `run_typecheck` | Run type checker |
| `run_lint_file` | Lint a specific file |

### Multi-Agent (1)
| Tool | Description |
|------|-------------|
| `run_parallel_tasks` | Spawn parallel worker agents |

### Plugins
Drop `.py` files in `agent_v4/plugins/` — see `plugins/__init__.py` for the format.

---

## Project Structure

```
agent_v4/
├── __init__.py             # Package marker
├── main.py                 # CLI entry point
├── web.py                  # Web UI (FastAPI + WebSocket)
├── session.py              # Agent loop with streaming
├── tools.py                # All tool implementations + dispatcher
├── safety.py               # Expanded blocklist + path protection
├── config.py               # Multi-key, multi-model config + custom prompts
├── token_manager.py        # Key rotation with exponential backoff
├── history.py              # Session save/load
├── cost_tracker.py         # Token usage & cost tracking
├── rag.py                  # TF-IDF codebase indexing & search
├── memory.py               # Persistent knowledge base
├── github_integration.py   # GitHub API (branches, commits, PRs)
├── test_generator.py       # Auto test generation + runner
├── linter.py               # Lint & typecheck integration
├── multi_agent.py          # Parallel worker orchestration
├── slack_bot.py            # Slack bot (Socket Mode)
├── plugins/                # Drop-in custom tools
│   └── __init__.py
├── templates/
│   └── index.html          # Web UI frontend
├── memory/                 # Persistent knowledge store
├── logs/                   # Session logs
├── .env.example            # Config template
└── README.md               # This file
```
