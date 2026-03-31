# Cornerstone AI Agent v5 — Jarvis Edition

A production-grade local-first AI agent framework inspired by [OpenJarvis](https://github.com/open-jarvis/OpenJarvis).

## Architecture

Five core primitives:

| Primitive | Description |
|-----------|-------------|
| **Intelligence** | Hardware detection, model catalog, engine recommendation |
| **Engine** | Multi-backend inference — Ollama (local), Anthropic (cloud), OpenAI-compatible (vLLM, SGLang, LM Studio) |
| **Agents** | Pluggable agent types — Simple, Orchestrator (tool loop), ReAct (reasoning) |
| **Memory** | Persistent retrieval — SQLite/FTS5, ChromaDB vectors, Hybrid (RRF fusion) |
| **Learning** | Trace capture, telemetry, cost/token tracking |

Supporting systems: Tools, Sandbox, Safety, History, Server (OpenAI-compatible API), CLI.

## Quick Start

```bash
# 1. Install dependencies
pip install anthropic python-dotenv rich

# 2. Configure
cp agent_v5/.env.example agent_v5/.env
# Edit .env with your API key(s)

# 3. Run interactive mode
python -m agent_v5.main

# Or use subcommands:
python -m agent_v5.main init          # Detect hardware
python -m agent_v5.main doctor        # Run diagnostics
python -m agent_v5.main ask "hello"   # Single query
python -m agent_v5.main serve         # Start API server
python -m agent_v5.main memory index ./src  # Index a directory
python -m agent_v5.main stats         # Show usage stats
```

## Engine Backends

### Ollama (Local)
```bash
ollama serve
ollama pull llama3.2
python -m agent_v5.main --agent simple
```

### Anthropic (Cloud)
Set `ANTHROPIC_API_KEY_1` in `.env`. Supports up to 10 keys with automatic rotation.

### OpenAI-Compatible
Works with vLLM, SGLang, LM Studio, or OpenAI. Set `OPENAI_API_KEY` and optionally `OPENAI_BASE_URL`.

## Agent Types

- **simple** — Single-turn, no tools. Fast responses.
- **orchestrator** — Multi-turn with tool-calling loop (up to 25 turns). Default.
- **react** — Thought-Action-Observation reasoning loop (up to 15 turns).

## Memory Backends

- **sqlite** — Zero-dependency full-text search via SQLite FTS5 (default)
- **vector** — Dense vector retrieval via ChromaDB (`pip install chromadb`)
- **hybrid** — RRF fusion of both sparse and dense retrieval

## API Server

OpenAI-compatible endpoint:

```bash
python -m agent_v5.main serve --port 8000

# Then use any OpenAI client:
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-sonnet-4-20250514", "messages": [{"role": "user", "content": "Hello"}]}'
```

## Tools

| Tool | Description |
|------|-------------|
| `list_files` | List directory contents |
| `read_file` | Read file contents |
| `write_file` | Write/create files |
| `delete_file` | Delete files |
| `search_files` | Search for patterns in files |
| `run_command` | Execute shell commands (with safety checks) |
| `web_search` | Search the web via DuckDuckGo |
| `calculator` | Safe math expression evaluation |
| `run_python` | Execute Python code in sandboxed subprocess |

## File Structure

```
agent_v5/
├── __init__.py          # Package exports
├── types.py             # Core data types
├── registry.py          # Registry pattern for plugins
├── config.py            # Hardware detection, environment config
├── safety.py            # Command blocking, path protection
├── history.py           # Conversation history management
├── cli.py               # CLI commands
├── main.py              # Entry point
├── .env.example         # Environment template
├── engine/
│   ├── base.py          # Abstract inference engine
│   ├── ollama.py        # Ollama backend
│   ├── anthropic_engine.py  # Anthropic backend with key rotation
│   ├── openai_compat.py # OpenAI-compatible backend
│   └── discovery.py     # Engine discovery and fallback
├── agents/
│   ├── base.py          # Abstract agent base
│   ├── simple.py        # Single-turn agent
│   ├── orchestrator.py  # Multi-turn tool-calling agent
│   └── react.py         # ReAct reasoning agent
├── memory/
│   ├── base.py          # Abstract memory backend
│   ├── sqlite_backend.py # SQLite FTS5 backend
│   ├── vector_backend.py # ChromaDB vector backend
│   ├── hybrid.py        # Hybrid RRF fusion
│   ├── chunking.py      # Document chunking
│   ├── ingest.py        # File/directory ingestion
│   └── context.py       # Memory context injection
├── tools/
│   ├── base.py          # Abstract tool base
│   ├── filesystem.py    # File operations
│   ├── terminal.py      # Shell commands
│   ├── web.py           # Web search
│   └── calculator.py    # Math evaluation
├── learning/
│   ├── traces.py        # Trace capture and analysis
│   └── telemetry.py     # Per-session telemetry
├── sandbox/
│   └── runner.py        # Sandboxed Python execution
└── server/
    └── api.py           # OpenAI-compatible API server
```
