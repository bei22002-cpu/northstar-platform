"""Dream distillation — deep memory consolidation for KAIROS mode.

Inspired by Claude Code's KAIROS ``/dream`` command.  While the basic
``memory.distill()`` in memory.py does simple LLM-based consolidation,
dream distillation goes further:

1. **Cross-reference** — finds connections between memories that share
   entities (files, functions, error patterns).
2. **Temporal decay** — older memories lose importance unless they've been
   frequently accessed.
3. **Insight synthesis** — generates *new* high-level insights from
   clusters of related memories (e.g. "this project prefers tabs over
   spaces" from multiple formatting observations).
4. **Prune stale** — removes memories that are outdated or superseded.
5. **Report** — writes a dream report summarising what was learned.

Dream distillation is triggered automatically by KAIROS at intervals
(every N goals) and at the end of a run.  It can also be triggered
manually via ``/kairos dream``.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from rich.console import Console

console = Console()

_REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")


def run_dream(
    create_message_fn: Any,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
) -> str:
    """Run a full dream distillation cycle.

    Steps:
    1. Load all memories
    2. Apply temporal decay to importance scores
    3. Cluster related memories by shared entities
    4. Ask the LLM to consolidate clusters and generate insights
    5. Replace old memories with consolidated set
    6. Write a dream report

    Returns a status string.
    """
    from agent_v2.memory import memory_store

    all_memories = memory_store.get_all()
    if len(all_memories) < 5:
        return "Not enough memories to dream (need at least 5)."

    original_count = len(all_memories)
    console.print(
        f"[magenta]Dream distillation starting with {original_count} memories...[/magenta]"
    )

    # Step 1: Apply temporal decay
    _apply_temporal_decay(all_memories)

    # Step 2: Cluster related memories
    clusters = _cluster_memories(all_memories)
    console.print(
        f"[dim]Found {len(clusters)} memory cluster(s)[/dim]"
    )

    # Step 3: LLM consolidation
    try:
        consolidated = _llm_consolidate(
            all_memories, clusters, create_message_fn, model, max_tokens
        )
    except Exception as exc:
        return f"Dream distillation LLM call failed: {exc}"

    if not consolidated:
        return "Dream distillation produced no usable output."

    # Step 4: Replace memories
    old_count = memory_store.count
    memory_store.clear()
    for mem in consolidated:
        memory_store.add(
            content=mem.get("content", ""),
            memory_type=mem.get("type", "fact"),
            tags=mem.get("tags", []) + ["dreamed"],
            importance=mem.get("importance", 0.5),
        )

    new_count = memory_store.count

    # Step 5: Write dream report
    report_path = _write_dream_report(
        original_count, new_count, clusters, consolidated
    )

    result = (
        f"Dream distillation complete: {old_count} -> {new_count} memories "
        f"({len(clusters)} clusters processed). Report: {report_path}"
    )
    console.print(f"[magenta]{result}[/magenta]")
    return result


# ---------------------------------------------------------------------------
# Temporal decay
# ---------------------------------------------------------------------------

def _apply_temporal_decay(memories: list[dict[str, Any]]) -> None:
    """Reduce importance of old, infrequently accessed memories.

    Memories lose importance over time unless they've been accessed
    recently.  The decay formula:

        new_importance = importance * decay_factor

    Where decay_factor depends on age and access frequency.
    """
    now = time.time()
    for mem in memories:
        age_days = (now - mem.get("created_at", now)) / 86400
        access_count = mem.get("access_count", 0)
        last_accessed = mem.get("last_accessed")

        # Base decay: lose 5% per day, min 0.3x multiplier
        age_decay = max(0.3, 1.0 - (age_days * 0.05))

        # Access boost: each access adds 0.05, up to 0.5 bonus
        access_boost = min(0.5, access_count * 0.05)

        # Recency boost: recently accessed memories decay slower
        recency_boost = 0.0
        if last_accessed:
            days_since_access = (now - last_accessed) / 86400
            recency_boost = max(0.0, 0.3 - (days_since_access * 0.05))

        decay_factor = age_decay + access_boost + recency_boost
        decay_factor = min(1.5, max(0.1, decay_factor))  # clamp

        old_importance = mem.get("importance", 0.5)
        mem["importance"] = min(1.0, max(0.05, old_importance * decay_factor))


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

def _cluster_memories(
    memories: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """Group related memories into clusters based on shared entities.

    Uses simple keyword/entity overlap: file paths, error patterns,
    function names, and tags.
    """
    # Extract entities from each memory
    entity_map: list[tuple[set[str], dict[str, Any]]] = []
    for mem in memories:
        entities = _extract_entities(mem)
        entity_map.append((entities, mem))

    # Greedy clustering: merge memories that share entities
    clusters: list[list[dict[str, Any]]] = []
    used: set[int] = set()

    for i, (entities_i, mem_i) in enumerate(entity_map):
        if i in used:
            continue
        cluster = [mem_i]
        used.add(i)

        for j, (entities_j, mem_j) in enumerate(entity_map):
            if j in used:
                continue
            # Merge if they share at least 1 meaningful entity
            overlap = entities_i & entities_j
            if overlap:
                cluster.append(mem_j)
                used.add(j)
                entities_i = entities_i | entities_j  # expand cluster entities

        clusters.append(cluster)

    # Sort clusters by size (largest first)
    clusters.sort(key=len, reverse=True)
    return clusters


def _extract_entities(mem: dict[str, Any]) -> set[str]:
    """Extract meaningful entities from a memory for clustering."""
    entities: set[str] = set()
    content = mem.get("content", "").lower()

    # File paths
    file_matches = re.findall(
        r"[\w./\\-]+\.(?:py|js|ts|json|yaml|yml|toml|md|html|css|sql)\b",
        content,
    )
    entities.update(file_matches)

    # Function/class names (camelCase or snake_case identifiers)
    ident_matches = re.findall(r"\b[a-z_][a-z0-9_]{3,}\b", content)
    # Only keep longer identifiers to avoid noise
    entities.update(w for w in ident_matches if len(w) > 5)

    # Tags
    for tag in mem.get("tags", []):
        entities.add(tag.lower())

    # Memory type
    entities.add(mem.get("type", "fact"))

    return entities


# ---------------------------------------------------------------------------
# LLM consolidation
# ---------------------------------------------------------------------------

def _llm_consolidate(
    all_memories: list[dict[str, Any]],
    clusters: list[list[dict[str, Any]]],
    create_message_fn: Any,
    model: str,
    max_tokens: int,
) -> list[dict[str, Any]]:
    """Use an LLM to consolidate memory clusters and generate insights."""

    # Build a summary of clusters for the LLM
    cluster_text_parts: list[str] = []
    for i, cluster in enumerate(clusters[:20]):  # cap at 20 clusters
        lines = [f"### Cluster {i + 1} ({len(cluster)} memories)"]
        for mem in cluster[:10]:  # cap at 10 per cluster
            mtype = mem.get("type", "fact")
            content = mem.get("content", "")[:200]
            importance = mem.get("importance", 0.5)
            tags = mem.get("tags", [])
            lines.append(
                f"- [{mtype}] (imp={importance:.2f}, tags={tags}) {content}"
            )
        cluster_text_parts.append("\n".join(lines))

    cluster_text = "\n\n".join(cluster_text_parts)

    system_prompt = (
        "You are a dream distillation engine for an AI agent's memory system. "
        "Your job is to consolidate and improve the agent's memories.\n\n"
        "Given clusters of related memories, you must:\n"
        "1. MERGE duplicate or very similar memories into single entries\n"
        "2. REMOVE outdated information superseded by newer memories\n"
        "3. SYNTHESIZE high-level insights from clusters of related facts "
        "(e.g., patterns, conventions, recurring issues)\n"
        "4. BOOST importance of frequently referenced, cross-cutting facts\n"
        "5. PRUNE low-value memories (trivial file references, etc.)\n\n"
        "Output a JSON array of consolidated memories. Each entry:\n"
        '{"content": "...", "type": "fact|decision|error|context|user|insight", '
        '"tags": [...], "importance": 0.0-1.0}\n\n'
        "The new type 'insight' is for synthesized knowledge not in any single "
        "original memory.\n\n"
        "Be aggressive about consolidation. Fewer, higher-quality memories "
        "are better. Aim for 30-60%% reduction in count while preserving "
        "all critical information.\n\n"
        "IMPORTANT: Output ONLY the JSON array, no other text."
    )

    response = create_message_fn(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": (
                f"Consolidate these {len(all_memories)} memories "
                f"across {len(clusters)} clusters:\n\n{cluster_text}"
            ),
        }],
    )

    # Extract text
    response_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            response_text += block.text

    # Parse JSON
    json_text = _extract_json_array(response_text)
    if not json_text:
        return []

    try:
        result = json.loads(json_text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    return []


def _extract_json_array(text: str) -> str | None:
    """Extract a JSON array from text that might contain markdown fences."""
    text = text.strip()
    if text.startswith("["):
        return text

    match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
    if match:
        return match.group(1)

    match = re.search(r"(\[[\s\S]*\])", text)
    if match:
        return match.group(1)

    return None


# ---------------------------------------------------------------------------
# Dream report
# ---------------------------------------------------------------------------

def _write_dream_report(
    original_count: int,
    new_count: int,
    clusters: list[list[dict[str, Any]]],
    consolidated: list[dict[str, Any]],
) -> str:
    """Write a dream distillation report."""
    os.makedirs(_REPORT_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = f"dream_{ts}.md"
    filepath = os.path.join(_REPORT_DIR, filename)

    # Count insights
    insights = [m for m in consolidated if m.get("type") == "insight"]
    high_importance = [m for m in consolidated if m.get("importance", 0) >= 0.8]

    content = (
        f"# Dream Distillation Report\n\n"
        f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**Memories before:** {original_count}\n"
        f"**Memories after:** {new_count}\n"
        f"**Reduction:** {original_count - new_count} "
        f"({((original_count - new_count) / max(1, original_count)) * 100:.0f}%%)\n"
        f"**Clusters processed:** {len(clusters)}\n"
        f"**Insights generated:** {len(insights)}\n"
        f"**High-importance memories:** {len(high_importance)}\n\n"
    )

    if insights:
        content += "## New Insights\n\n"
        for ins in insights:
            content += f"- {ins.get('content', '')}\n"
        content += "\n"

    if high_importance:
        content += "## High-Importance Memories\n\n"
        for mem in high_importance[:10]:
            content += (
                f"- [{mem.get('type', 'fact')}] {mem.get('content', '')[:150]}\n"
            )
        content += "\n"

    content += (
        "## Cluster Summary\n\n"
        f"| Cluster | Size | Sample |\n"
        f"|---------|------|--------|\n"
    )
    for i, cluster in enumerate(clusters[:15]):
        sample = cluster[0].get("content", "")[:60] if cluster else ""
        content += f"| {i + 1} | {len(cluster)} | {sample} |\n"

    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(content)

    return filepath
