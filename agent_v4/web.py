"""Web UI for Cornerstone AI Agent v4.

Browser-based chat interface with FastAPI + WebSocket.
Run with: uvicorn agent_v4.web:app --port 8080
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from agent_v4.config import (
    API_KEYS, AVAILABLE_MODELS, MAX_TOKENS, WORKSPACE, get_system_prompt,
)
from agent_v4.cost_tracker import CostTracker
from agent_v4.history import SessionHistory
from agent_v4.memory import KnowledgeBase
from agent_v4.multi_agent import Orchestrator
from agent_v4.rag import CodebaseIndex
from agent_v4.safety import check_safety
from agent_v4.token_manager import TokenManager
from agent_v4.tools import TOOL_DEFINITIONS, execute_tool

import anthropic

app = FastAPI(title="Cornerstone AI Agent v4 — Web UI")

_HTML_PATH = os.path.join(os.path.dirname(__file__), "templates", "index.html")

# Shared codebase index (indexed once on first request)
_codebase_index = CodebaseIndex()


def _get_html() -> str:
    if os.path.isfile(_HTML_PATH):
        with open(_HTML_PATH, encoding="utf-8") as f:
            return f.read()
    return "<html><body><h1>Template not found</h1></body></html>"


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return _get_html()


@app.get("/api/status")
async def status() -> dict[str, Any]:
    return {
        "keys_loaded": len(API_KEYS),
        "workspace": WORKSPACE,
        "models": AVAILABLE_MODELS,
        "rag_indexed": _codebase_index.is_indexed,
        "rag_files": _codebase_index.file_count,
        "rag_chunks": _codebase_index.chunk_count,
    }


@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket) -> None:
    await ws.accept()

    history = SessionHistory()
    cost = CostTracker()
    knowledge = KnowledgeBase()
    token_manager = TokenManager(API_KEYS)
    current_model = AVAILABLE_MODELS.get("sonnet", "claude-sonnet-4-5-20250514")

    # Index codebase if not done yet
    if not _codebase_index.is_indexed:
        await ws.send_json({"type": "system", "text": "Indexing codebase..."})
        stats = await asyncio.to_thread(_codebase_index.index_workspace, WORKSPACE)
        import agent_v4
        agent_v4._shared_index = _codebase_index
        await ws.send_json({
            "type": "system",
            "text": f"Indexed {stats['files_indexed']} files ({stats['chunks_created']} chunks)",
        })

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "model_switch":
                model_key = msg.get("model", "sonnet")
                if model_key in AVAILABLE_MODELS:
                    current_model = AVAILABLE_MODELS[model_key]
                    await ws.send_json({
                        "type": "system",
                        "text": f"Switched to {model_key} ({current_model})",
                    })
                else:
                    await ws.send_json({
                        "type": "system",
                        "text": f"Unknown model: {model_key}",
                    })
                continue

            if msg.get("type") == "cost":
                await ws.send_json({"type": "cost", "text": cost.summary()})
                continue

            if msg.get("type") == "keys":
                await ws.send_json({
                    "type": "keys",
                    "stats": token_manager.get_stats(),
                })
                continue

            if msg.get("type") == "memory":
                memories = knowledge.list_all()
                text = "\n".join(
                    f"- {m['key']}: {m['value']}" for m in memories
                ) or "No memories stored."
                await ws.send_json({"type": "system", "text": text})
                continue

            # Regular chat message
            user_text = msg.get("text", "").strip()
            if not user_text:
                continue

            history.add_user(user_text)
            messages = history.get_messages()

            # Agent loop
            max_turns = 20
            for _ in range(max_turns):
                await ws.send_json({
                    "type": "status",
                    "text": f"Key #{token_manager.active_key_index}/{token_manager.total_keys} | {current_model}",
                })

                try:
                    response = await asyncio.to_thread(
                        token_manager.create_message,
                        model=current_model,
                        max_tokens=MAX_TOKENS,
                        system=get_system_prompt(),
                        tools=TOOL_DEFINITIONS,
                        messages=messages,
                    )
                except anthropic.BadRequestError:
                    history.clear()
                    history.add_user(user_text)
                    messages = history.get_messages()
                    response = await asyncio.to_thread(
                        token_manager.create_message,
                        model=current_model,
                        max_tokens=MAX_TOKENS,
                        system=get_system_prompt(),
                        tools=TOOL_DEFINITIONS,
                        messages=messages,
                    )

                if hasattr(response, "usage"):
                    cost.record(
                        current_model,
                        response.usage.input_tokens,
                        response.usage.output_tokens,
                    )

                history.add_assistant(response.content)
                messages = history.get_messages()

                for block in response.content:
                    if hasattr(block, "text"):
                        await ws.send_json({
                            "type": "assistant",
                            "text": block.text,
                        })

                if response.stop_reason == "end_turn":
                    await ws.send_json({"type": "done"})
                    break

                if response.stop_reason == "tool_use":
                    tool_results: list[dict[str, Any]] = []
                    for block in response.content:
                        if block.type != "tool_use":
                            continue

                        tool_name = block.name
                        tool_input = block.input

                        block_reason = check_safety(tool_name, tool_input)
                        if block_reason:
                            result = block_reason
                            await ws.send_json({
                                "type": "blocked",
                                "tool": tool_name,
                                "reason": block_reason,
                            })
                        elif tool_name == "run_parallel_tasks":
                            tasks = tool_input.get("tasks", [])
                            await ws.send_json({
                                "type": "system",
                                "text": f"Spawning {len(tasks)} worker agents...",
                            })
                            orchestrator = Orchestrator(
                                token_manager=token_manager,
                                cost_tracker=cost,
                                model=current_model,
                            )
                            worker_results = await asyncio.to_thread(
                                orchestrator.run_parallel, tasks
                            )
                            result = orchestrator.format_results(worker_results)
                            await ws.send_json({
                                "type": "tool_result",
                                "tool": tool_name,
                                "result": result[:3000],
                            })
                        else:
                            await ws.send_json({
                                "type": "tool_call",
                                "tool": tool_name,
                                "input": tool_input,
                            })
                            result = await asyncio.to_thread(
                                execute_tool, tool_name, tool_input
                            )
                            await ws.send_json({
                                "type": "tool_result",
                                "tool": tool_name,
                                "result": result[:2000] if len(result) > 2000 else result,
                            })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                    history.add_tool_results(tool_results)
                    messages = history.get_messages()
                else:
                    await ws.send_json({"type": "done"})
                    break

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await ws.send_json({"type": "error", "text": str(exc)})
        except Exception:
            pass
