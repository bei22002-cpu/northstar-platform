"""Trace capture and analysis — records every agent interaction."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, List, Optional

from agent_v5.config import TRACES_PATH
from agent_v5.types import Trace


class TraceStore:
    """Append-only store for interaction traces."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or TRACES_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def new_trace(self, query: str, **kwargs: Any) -> Trace:
        """Create a new trace with a unique ID."""
        return Trace(
            trace_id=uuid.uuid4().hex[:12],
            query=query,
            **kwargs,
        )

    def save(self, trace: Trace) -> None:
        """Append a completed trace to the store."""
        entry = {
            "trace_id": trace.trace_id,
            "query": trace.query,
            "agent_type": trace.agent_type,
            "engine_id": trace.engine_id,
            "model": trace.model,
            "start_time": trace.start_time,
            "end_time": trace.end_time,
            "tokens_in": trace.tokens_in,
            "tokens_out": trace.tokens_out,
            "latency_ms": trace.latency_ms,
            "tool_calls": trace.tool_calls,
            "memory_hits": trace.memory_hits,
            "result_length": len(trace.result),
            "error": trace.error,
            "cost_usd": trace.cost_usd,
        }
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass

    def load_all(self) -> List[dict[str, Any]]:
        """Load all traces from the store."""
        if not self._path.exists():
            return []
        traces: List[dict[str, Any]] = []
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        traces.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
        return traces

    def clear(self) -> None:
        """Clear all traces."""
        try:
            self._path.write_text("")
        except OSError:
            pass


class TraceAnalyzer:
    """Compute statistics from accumulated traces."""

    def __init__(self, store: TraceStore) -> None:
        self._store = store

    def summary(self) -> dict[str, Any]:
        """Return aggregate statistics."""
        traces = self._store.load_all()
        if not traces:
            return {
                "total_queries": 0,
                "total_tokens_in": 0,
                "total_tokens_out": 0,
                "total_cost_usd": 0.0,
                "avg_latency_ms": 0.0,
                "total_tool_calls": 0,
                "error_count": 0,
                "models_used": [],
                "engines_used": [],
            }

        total_in = sum(t.get("tokens_in", 0) for t in traces)
        total_out = sum(t.get("tokens_out", 0) for t in traces)
        total_cost = sum(t.get("cost_usd", 0) for t in traces)
        latencies = [t.get("latency_ms", 0) for t in traces if t.get("latency_ms", 0) > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        tool_calls = sum(len(t.get("tool_calls", [])) for t in traces)
        errors = sum(1 for t in traces if t.get("error"))
        models = list(set(t.get("model", "") for t in traces if t.get("model")))
        engines = list(set(t.get("engine_id", "") for t in traces if t.get("engine_id")))

        return {
            "total_queries": len(traces),
            "total_tokens_in": total_in,
            "total_tokens_out": total_out,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(avg_latency, 1),
            "total_tool_calls": tool_calls,
            "error_count": errors,
            "models_used": models,
            "engines_used": engines,
        }
