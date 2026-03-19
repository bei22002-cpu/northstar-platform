# Cornerstone AI Agent

A local AI agent powered by Claude (Anthropic) that can autonomously read,
write, edit, and manage files and run terminal commands inside the
Cornerstone project workspace — with a **human approval gate** before every
action.

---

## Features

- **8 built-in tools**: read/write/delete files, list files, create
  directories, run shell commands, search code, and check git status.
- **Human-in-the-loop**: Every tool invocation requires explicit `y/n`
  approval before execution.
- **Dangerous command blocking**: Commands matching known destructive
  patterns (e.g. `rm -rf /`, `DROP DATABASE`) are blocked automatically.
- **Session logging**: Every conversation is saved as a timestamped JSON
  file in `agent/logs/`.
- **Rich terminal UI**: Styled prompts, panels, and Markdown rendering
  powered by the `rich` library.

---

## Installation

```bash
pip install anthropic python-dotenv rich
```

---

## Configuration

1. Copy the example environment file:

   ```bash
   cp agent/.env.example agent/.env
   ```

2. Edit `agent/.env` and add your Anthropic API key:

   ```
   ANTHROPIC_API_KEY=sk-ant-...
   WORKSPACE=./backend
   ```

   `WORKSPACE` defaults to `./backend` if not set.

---

## Usage

From the **repository root**, run:

```bash
python -m agent.main
```

You will see a welcome banner and a prompt. Type a natural-language
request and the agent will plan and execute it, asking for your approval
at each step.

Type `exit` or `quit` (or press `Ctrl+C`) to end the session. The path to
the session log file will be displayed on exit.

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

The following patterns are blocked and will **never** execute, even if you
approve them:

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

You must type **y** to approve. Anything else denies the action, and the
agent is informed that the user declined.

---

## Example Interaction

```
You > Show me all Python files in the project

╭─ AI wants to perform an action ───────────────────────╮
│ Tool: list_files                                       │
│ directory: .                                           │
╰────────────────────────────────────────────────────────╯
Approve? (y/n): y

╭─ Cornerstone AI ──────────────────────────────────────╮
│ Here are all the Python files in the workspace:        │
│                                                        │
│ app/main.py                                            │
│ app/models.py                                          │
│ ...                                                    │
╰────────────────────────────────────────────────────────╯
```

---

## Project Structure

```
agent/
├── __init__.py      # Package marker
├── main.py          # CLI entry point & input loop
├── tools.py         # 8 tool implementations + schema definitions
├── safety.py        # Blocked-command list & approval gate
├── config.py        # .env loader & validation
├── session.py       # Anthropic API interaction & tool-use loop
├── history.py       # In-memory message history & JSON log saving
├── .env.example     # Example environment variables
└── README.md        # This file
```
