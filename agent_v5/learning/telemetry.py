"""Telemetry tracker — per-session cost, latency, and token tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TelemetryTracker:
    """Tracks per-session usage metrics."""

    session_start: float = field(default_factory=time.time)
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    total_queries: int = 0
    total_tool_calls: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    models_used: set[str] = field(default_factory=set)
    engines_used: set[str] = field(default_factory=set)

    def record(
        self,
        *,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        tool_calls: int = 0,
        model: str = "",
        engine: str = "",
    ) -> None:
        self.total_tokens_in += tokens_in
        self.total_tokens_out += tokens_out
        self.total_cost_usd += cost_usd
        self.total_queries += 1
        self.total_tool_calls += tool_calls
        if latency_ms > 0:
            self.latencies_ms.append(latency_ms)
        if model:
            self.models_used.add(model)
        if engine:
            self.engines_used.add(engine)

    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return sum(self.latencies_ms) / len(self.latencies_ms)

    @property
    def session_duration_s(self) -> float:
        return time.time() - self.session_start

    def summary(self) -> dict[str, Any]:
        return {
            "session_duration_s": round(self.session_duration_s, 1),
            "total_queries": self.total_queries,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_tokens": self.total_tokens_in + self.total_tokens_out,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "total_tool_calls": self.total_tool_calls,
            "models_used": sorted(self.models_used),
            "engines_used": sorted(self.engines_used),
        }
