"""Token usage and cost tracking across the session."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_v4.config import MODEL_COSTS


@dataclass
class CostTracker:
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0
    _per_model: dict[str, dict[str, int]] = field(default_factory=dict)

    def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.requests += 1
        if model not in self._per_model:
            self._per_model[model] = {"input": 0, "output": 0, "requests": 0}
        self._per_model[model]["input"] += input_tokens
        self._per_model[model]["output"] += output_tokens
        self._per_model[model]["requests"] += 1

    @property
    def total_cost(self) -> float:
        cost = 0.0
        for model, usage in self._per_model.items():
            rates = MODEL_COSTS.get(model, {"input": 3.0, "output": 15.0})
            cost += (usage["input"] / 1_000_000) * rates["input"]
            cost += (usage["output"] / 1_000_000) * rates["output"]
        return cost

    def summary(self) -> str:
        lines = [
            f"Total requests: {self.requests}",
            f"Input tokens:   {self.input_tokens:,}",
            f"Output tokens:  {self.output_tokens:,}",
            f"Estimated cost: ${self.total_cost:.4f}",
        ]
        if len(self._per_model) > 1:
            lines.append("\nPer model:")
            for model, usage in self._per_model.items():
                rates = MODEL_COSTS.get(model, {"input": 3.0, "output": 15.0})
                model_cost = ((usage["input"] / 1_000_000) * rates["input"] +
                              (usage["output"] / 1_000_000) * rates["output"])
                short_name = model.split("-")[1] if "-" in model else model
                lines.append(f"  {short_name}: {usage['requests']} calls, "
                             f"{usage['input']:,}+{usage['output']:,} tokens, "
                             f"${model_cost:.4f}")
        return "\n".join(lines)
