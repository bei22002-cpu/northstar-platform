"""KAIROS mode — fully autonomous overnight agent with task queue.

Inspired by the leaked Claude Code KAIROS autonomous mode.  KAIROS
(Knowledge-Augmented Iterative Reasoning Over Sessions) runs a queue of
user-defined goals without interaction, writing progress reports and
consolidating memory via dream distillation when the queue is empty.

Features
--------
- **Task queue** — define goals up-front; KAIROS works through them one
  by one, fully autonomously.
- **Progress reporting** — writes a timestamped report file after each
  goal so you can check progress in the morning.
- **Budget guards** — hard limits on total API calls, wall-clock time,
  and per-goal iteration caps to prevent runaway spending.
- **Dream distillation** — when the queue is drained (or on schedule),
  KAIROS consolidates all memories accumulated during the run.
- **Resume** — persists queue state to disk so it can pick up where it
  left off after a crash or restart.
- **Hook integration** — fires ``SessionStart`` / ``SessionEnd`` and
  per-goal hooks so external tooling can observe progress.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_QUEUE_FILE = os.path.join(_DATA_DIR, "kairos_queue.json")
_REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")

# ---------------------------------------------------------------------------
# Budget defaults
# ---------------------------------------------------------------------------

DEFAULT_MAX_API_CALLS = 200          # hard cap on total API calls per run
DEFAULT_MAX_WALL_CLOCK_SECS = 7200   # 2 hours default
DEFAULT_MAX_TURNS_PER_GOAL = 30      # iterations per single goal
DEFAULT_DREAM_AFTER_GOALS = 5        # trigger dream distillation every N goals


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class GoalStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Goal:
    """A single autonomous goal in the KAIROS queue."""
    description: str
    context: str = ""
    status: GoalStatus = GoalStatus.PENDING
    result: str = ""
    turns_used: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Goal":
        d = dict(d)  # shallow copy
        d["status"] = GoalStatus(d.get("status", "pending"))
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class KairosState:
    """Persisted state for a KAIROS run."""
    goals: list[Goal] = field(default_factory=list)
    total_api_calls: int = 0
    total_goals_completed: int = 0
    total_goals_failed: int = 0
    run_started_at: float | None = None
    run_finished_at: float | None = None
    dreams_performed: int = 0
    max_api_calls: int = DEFAULT_MAX_API_CALLS
    max_wall_clock_secs: int = DEFAULT_MAX_WALL_CLOCK_SECS
    max_turns_per_goal: int = DEFAULT_MAX_TURNS_PER_GOAL

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["goals"] = [g.to_dict() for g in self.goals]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "KairosState":
        d = dict(d)
        goals_raw = d.pop("goals", [])
        goals = [Goal.from_dict(g) for g in goals_raw]
        # Only keep known fields
        known = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in known}
        state = cls(**filtered)
        state.goals = goals
        return state


# ---------------------------------------------------------------------------
# Queue persistence
# ---------------------------------------------------------------------------

def _save_state(state: KairosState) -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_QUEUE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state.to_dict(), fh, indent=2, default=str)


def _load_state() -> KairosState:
    if os.path.isfile(_QUEUE_FILE):
        try:
            with open(_QUEUE_FILE, "r", encoding="utf-8") as fh:
                return KairosState.from_dict(json.load(fh))
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    return KairosState()


def get_state() -> KairosState:
    """Public accessor for the current KAIROS state."""
    return _load_state()


# ---------------------------------------------------------------------------
# Queue management (user-facing)
# ---------------------------------------------------------------------------

def add_goal(description: str, context: str = "") -> Goal:
    """Add a goal to the KAIROS queue."""
    state = _load_state()
    goal = Goal(description=description, context=context)
    state.goals.append(goal)
    _save_state(state)
    console.print(f"[green]Goal added:[/green] {description[:120]}")
    return goal


def remove_goal(index: int) -> bool:
    """Remove a pending goal by index (0-based)."""
    state = _load_state()
    pending = [g for g in state.goals if g.status == GoalStatus.PENDING]
    if 0 <= index < len(pending):
        state.goals.remove(pending[index])
        _save_state(state)
        console.print(f"[yellow]Goal removed:[/yellow] {pending[index].description[:80]}")
        return True
    return False


def clear_queue() -> int:
    """Remove all pending goals. Returns count removed."""
    state = _load_state()
    before = len(state.goals)
    state.goals = [g for g in state.goals if g.status != GoalStatus.PENDING]
    _save_state(state)
    removed = before - len(state.goals)
    console.print(f"[yellow]Cleared {removed} pending goal(s).[/yellow]")
    return removed


def reset_state() -> None:
    """Full reset — wipe all goals and counters."""
    _save_state(KairosState())
    console.print("[yellow]KAIROS state fully reset.[/yellow]")


# ---------------------------------------------------------------------------
# Progress reporting
# ---------------------------------------------------------------------------

def _write_report(state: KairosState, goal: Goal, report_text: str) -> str:
    """Write a progress report for a completed/failed goal."""
    os.makedirs(_REPORT_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    status_tag = goal.status.value
    filename = f"kairos_{ts}_{status_tag}.md"
    filepath = os.path.join(_REPORT_DIR, filename)

    elapsed = ""
    if goal.started_at and goal.finished_at:
        secs = goal.finished_at - goal.started_at
        mins = secs / 60
        elapsed = f"{mins:.1f} minutes"

    content = (
        f"# KAIROS Report — {status_tag.upper()}\n\n"
        f"**Goal:** {goal.description}\n\n"
        f"**Status:** {status_tag}\n"
        f"**Turns used:** {goal.turns_used}\n"
        f"**Time elapsed:** {elapsed}\n"
        f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"## Result\n\n{report_text}\n\n"
        f"---\n"
        f"## Run Stats\n\n"
        f"- Total API calls this run: {state.total_api_calls}\n"
        f"- Goals completed: {state.total_goals_completed}\n"
        f"- Goals failed: {state.total_goals_failed}\n"
        f"- Dreams performed: {state.dreams_performed}\n"
    )
    if goal.error:
        content += f"\n## Error\n\n```\n{goal.error}\n```\n"

    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(content)

    return filepath


# ---------------------------------------------------------------------------
# Core KAIROS engine
# ---------------------------------------------------------------------------

def _run_goal(
    goal: Goal,
    state: KairosState,
    create_message_fn: Any,
    tools: list[dict[str, Any]],
    execute_tool_fn: Any,
    model: str,
    max_tokens: int,
) -> str:
    """Execute a single goal autonomously.

    Uses the same sub-agent pattern as subagent.py but with KAIROS-specific
    system prompt and higher turn limits.
    """
    from agent_v2.safety import is_blocked
    from agent_v2.hooks import fire_pre_tool_use, fire_post_tool_use
    from agent_v2.permissions import permissions
    from agent_v2.memory import memory_store, extract_facts_from_turn

    goal.status = GoalStatus.IN_PROGRESS
    goal.started_at = time.time()
    _save_state(state)

    kairos_system = (
        "You are Cornerstone AI running in KAIROS autonomous mode. "
        "You are working through a queue of goals without human supervision. "
        "Complete the current goal thoroughly and report your results.\n\n"
        "## Rules\n"
        "- Work autonomously — do not ask for user input.\n"
        "- Be thorough but efficient — minimize unnecessary API calls.\n"
        "- If you encounter an error, try to fix it yourself.\n"
        "- If a goal is truly impossible, explain why and move on.\n"
        "- Always verify your work before declaring completion.\n"
        "- Write clean, production-quality code.\n"
        "- After completing the task, provide a clear summary of what you did.\n\n"
        "## Current Goal\n"
        f"{goal.description}\n"
    )
    if goal.context:
        kairos_system += f"\n## Additional Context\n{goal.context}\n"

    # Inject memory context
    memory_context = memory_store.get_context_block(query=goal.description)
    if memory_context:
        kairos_system += f"\n\n{memory_context}"

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": f"Execute this goal: {goal.description}"},
    ]

    collected_output: list[str] = []
    turns = 0

    while turns < state.max_turns_per_goal:
        # Budget check
        if state.total_api_calls >= state.max_api_calls:
            collected_output.append(
                "[KAIROS] API call budget exhausted. Stopping goal."
            )
            goal.error = "API call budget exhausted"
            break

        # Wall-clock check
        if state.run_started_at:
            elapsed = time.time() - state.run_started_at
            if elapsed > state.max_wall_clock_secs:
                collected_output.append(
                    "[KAIROS] Wall-clock time limit reached. Stopping goal."
                )
                goal.error = "Wall-clock time limit reached"
                break

        turns += 1
        state.total_api_calls += 1
        goal.turns_used = turns

        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "system": kairos_system,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            response = create_message_fn(**kwargs)
        except Exception as exc:
            err = f"[KAIROS] API error on turn {turns}: {exc}"
            console.print(f"[red]{err}[/red]")
            collected_output.append(err)
            goal.error = str(exc)

            # If history is too large, try trimming
            if "prompt is too long" in str(exc) or "too many tokens" in str(exc).lower():
                if len(messages) > 3:
                    messages = [messages[0]] + messages[-2:]
                    console.print("[yellow][KAIROS] Trimmed history, retrying...[/yellow]")
                    continue
            break

        # Serialize assistant response
        assistant_content = _make_serializable(response.content)
        messages.append({"role": "assistant", "content": assistant_content})

        # Collect text output
        assistant_text = ""
        for block in response.content:
            if hasattr(block, "text") and block.text:
                assistant_text += block.text
                collected_output.append(block.text)

        # Extract facts for memory
        try:
            facts = extract_facts_from_turn(goal.description, assistant_text)
            for fact in facts:
                memory_store.add(
                    content=fact["content"],
                    memory_type=fact["type"],
                    tags=fact.get("tags", []) + ["kairos"],
                    importance=fact.get("importance", 0.5),
                )
        except Exception:
            pass

        # Check for tool use
        tool_use_blocks = [
            b for b in response.content if getattr(b, "type", None) == "tool_use"
        ]

        if not tool_use_blocks:
            break

        if execute_tool_fn is None:
            collected_output.append("[KAIROS] No tool executor — stopping.")
            break

        # Execute tools
        tool_results: list[dict[str, Any]] = []
        for block in tool_use_blocks:
            tool_name = block.name
            tool_input = block.input

            try:
                # Permission check
                allowed, reason = permissions.check_tool_call(tool_name, tool_input)
                if not allowed:
                    result = f"PERMISSION DENIED: {reason}"
                elif tool_name == "run_command" and is_blocked(
                    tool_input.get("command", "")
                ):
                    result = "BLOCKED: Dangerous command blocked in KAIROS mode."
                else:
                    # Fire hooks
                    pre_result = fire_pre_tool_use(tool_name, tool_input)
                    if pre_result["blocked"]:
                        result = f"BLOCKED by hook: {pre_result['reason']}"
                    else:
                        tool_input = pre_result["tool_input"]
                        result = execute_tool_fn(tool_name, tool_input)
                        result = fire_post_tool_use(tool_name, tool_input, result)

            except Exception as exc:
                result = f"[KAIROS] Tool error ({tool_name}): {exc}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

            console.print(
                f"[dim]  [KAIROS] {tool_name} -> "
                f"{str(result)[:100]}{'...' if len(str(result)) > 100 else ''}[/dim]"
            )

        messages.append({"role": "user", "content": tool_results})

        if response.stop_reason != "tool_use":
            break

        # Save state periodically
        _save_state(state)

    # Finalize
    goal.finished_at = time.time()
    final_output = "\n\n".join(collected_output)

    # Cap output
    if len(final_output) > 50_000:
        final_output = final_output[:50_000] + "\n\n... (output truncated)"

    goal.result = final_output[:5000]  # store abbreviated result in state

    if not goal.error:
        goal.status = GoalStatus.COMPLETED
        state.total_goals_completed += 1
    else:
        goal.status = GoalStatus.FAILED
        state.total_goals_failed += 1

    _save_state(state)
    return final_output


def run_kairos(
    create_message_fn: Any,
    tools: list[dict[str, Any]],
    execute_tool_fn: Any,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 8096,
    dream_after: int = DEFAULT_DREAM_AFTER_GOALS,
) -> str:
    """Run the full KAIROS autonomous loop.

    Processes all pending goals in the queue, writing progress reports
    and performing dream distillation at intervals.

    Parameters
    ----------
    create_message_fn : callable
        TokenManager's ``create_message`` method.
    tools : list
        Tool definitions for the agent.
    execute_tool_fn : callable
        Tool executor function.
    model : str
        Model to use (defaults to Sonnet for cost efficiency).
    max_tokens : int
        Max tokens per API response.
    dream_after : int
        Trigger dream distillation every N completed goals.

    Returns
    -------
    str
        Summary of the KAIROS run.
    """
    from agent_v2.hooks import fire_simple
    from agent_v2.memory import memory_store

    state = _load_state()

    pending = [g for g in state.goals if g.status == GoalStatus.PENDING]
    if not pending:
        return "No pending goals in the KAIROS queue. Add goals with /kairos add <goal>"

    state.run_started_at = time.time()
    _save_state(state)

    console.print(
        Panel(
            f"[bold]Goals in queue:[/bold] {len(pending)}\n"
            f"[bold]API call budget:[/bold] {state.max_api_calls}\n"
            f"[bold]Time limit:[/bold] {state.max_wall_clock_secs // 60} minutes\n"
            f"[bold]Max turns/goal:[/bold] {state.max_turns_per_goal}\n"
            f"[bold]Dream after:[/bold] every {dream_after} goals",
            title="KAIROS Mode — Starting Autonomous Run",
            border_style="bright_magenta",
        )
    )

    fire_simple("SessionStart")
    goals_processed = 0
    reports: list[str] = []

    for goal in state.goals:
        if goal.status != GoalStatus.PENDING:
            continue

        # Budget checks
        if state.total_api_calls >= state.max_api_calls:
            console.print("[red][KAIROS] API budget exhausted. Stopping run.[/red]")
            goal.status = GoalStatus.SKIPPED
            goal.error = "Skipped — API budget exhausted"
            _save_state(state)
            continue

        if state.run_started_at:
            elapsed = time.time() - state.run_started_at
            if elapsed > state.max_wall_clock_secs:
                console.print("[red][KAIROS] Time limit reached. Stopping run.[/red]")
                goal.status = GoalStatus.SKIPPED
                goal.error = "Skipped — time limit reached"
                _save_state(state)
                continue

        console.print(
            Panel(
                f"[bold]{goal.description}[/bold]",
                title=f"KAIROS — Goal {goals_processed + 1}/{len(pending)}",
                border_style="cyan",
            )
        )

        try:
            result_text = _run_goal(
                goal=goal,
                state=state,
                create_message_fn=create_message_fn,
                tools=tools,
                execute_tool_fn=execute_tool_fn,
                model=model,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            goal.status = GoalStatus.FAILED
            goal.finished_at = time.time()
            goal.error = str(exc)
            state.total_goals_failed += 1
            result_text = f"Unhandled error: {exc}"
            _save_state(state)

        # Write progress report
        report_path = _write_report(state, goal, result_text)
        reports.append(report_path)
        console.print(
            f"[dim]Report written: {report_path}[/dim]"
        )

        goals_processed += 1

        # Dream distillation at intervals
        if dream_after > 0 and goals_processed % dream_after == 0:
            console.print("[magenta][KAIROS] Triggering dream distillation...[/magenta]")
            try:
                from agent_v2.dream import run_dream
                dream_result = run_dream(create_message_fn, model=model)
                state.dreams_performed += 1
                _save_state(state)
                console.print(f"[magenta]{dream_result}[/magenta]")
            except Exception as exc:
                console.print(f"[yellow]Dream distillation failed: {exc}[/yellow]")

    # Final dream distillation
    if goals_processed > 0:
        console.print("[magenta][KAIROS] Final dream distillation...[/magenta]")
        try:
            from agent_v2.dream import run_dream
            dream_result = run_dream(create_message_fn, model=model)
            state.dreams_performed += 1
            _save_state(state)
            console.print(f"[magenta]{dream_result}[/magenta]")
        except Exception as exc:
            console.print(f"[yellow]Final dream distillation failed: {exc}[/yellow]")

    state.run_finished_at = time.time()
    _save_state(state)

    fire_simple("SessionEnd")

    # Build summary
    total_time = ""
    if state.run_started_at and state.run_finished_at:
        secs = state.run_finished_at - state.run_started_at
        mins = secs / 60
        total_time = f"{mins:.1f} minutes"

    summary = (
        f"KAIROS run complete.\n"
        f"  Goals processed: {goals_processed}\n"
        f"  Completed: {state.total_goals_completed}\n"
        f"  Failed: {state.total_goals_failed}\n"
        f"  API calls: {state.total_api_calls}\n"
        f"  Dreams: {state.dreams_performed}\n"
        f"  Total time: {total_time}\n"
        f"  Reports: {', '.join(os.path.basename(r) for r in reports)}"
    )

    console.print(
        Panel(summary, title="KAIROS Run Complete", border_style="bright_green")
    )

    return summary


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_queue() -> None:
    """Print the current KAIROS queue status."""
    state = _load_state()
    if not state.goals:
        console.print("[dim]KAIROS queue is empty. Add goals with /kairos add <goal>[/dim]")
        return

    table = Table(title="KAIROS Goal Queue")
    table.add_column("#", style="bold")
    table.add_column("Status", style="cyan")
    table.add_column("Goal")
    table.add_column("Turns", justify="right")
    table.add_column("Result", style="dim")

    for i, goal in enumerate(state.goals):
        status_style = {
            GoalStatus.PENDING: "[yellow]pending[/yellow]",
            GoalStatus.IN_PROGRESS: "[blue]running[/blue]",
            GoalStatus.COMPLETED: "[green]done[/green]",
            GoalStatus.FAILED: "[red]failed[/red]",
            GoalStatus.SKIPPED: "[dim]skipped[/dim]",
        }.get(goal.status, goal.status.value)

        table.add_row(
            str(i),
            status_style,
            goal.description[:80],
            str(goal.turns_used),
            (goal.result[:60] + "..." if len(goal.result) > 60 else goal.result)
            if goal.result else "",
        )

    console.print(table)

    # Show stats
    console.print(
        f"\n[dim]Total API calls: {state.total_api_calls} | "
        f"Completed: {state.total_goals_completed} | "
        f"Failed: {state.total_goals_failed} | "
        f"Dreams: {state.dreams_performed}[/dim]"
    )


def print_config() -> None:
    """Print current KAIROS configuration."""
    state = _load_state()
    console.print(Panel(
        f"Max API calls: {state.max_api_calls}\n"
        f"Max wall-clock time: {state.max_wall_clock_secs // 60} minutes\n"
        f"Max turns per goal: {state.max_turns_per_goal}\n"
        f"Dream after every: {DEFAULT_DREAM_AFTER_GOALS} goals",
        title="KAIROS Configuration",
        border_style="magenta",
    ))


def set_budget(
    max_api_calls: int | None = None,
    max_wall_clock_mins: int | None = None,
    max_turns_per_goal: int | None = None,
) -> None:
    """Update KAIROS budget limits."""
    state = _load_state()
    if max_api_calls is not None:
        state.max_api_calls = max(1, max_api_calls)
    if max_wall_clock_mins is not None:
        state.max_wall_clock_secs = max(60, max_wall_clock_mins * 60)
    if max_turns_per_goal is not None:
        state.max_turns_per_goal = max(1, max_turns_per_goal)
    _save_state(state)
    console.print("[green]KAIROS budget updated.[/green]")
    print_config()


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _make_serializable(obj: Any) -> Any:
    """Recursively convert API objects to plain dicts/lists for JSON."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    return obj
