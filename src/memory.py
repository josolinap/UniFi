"""Persistent memory for the autonomous agent across GitHub Actions runs."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MEMORY_FILENAME = "agent_memory.json"
MAX_LOG_ENTRIES = 50


def _memory_path() -> Path:
    """Resolve the memory file path lazily (honours working directory changes in tests)."""
    return Path(MEMORY_FILENAME)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_memory() -> dict[str, Any]:
    """Load agent memory from disk. Returns empty state if not found."""
    memory_file = _memory_path()
    if memory_file.exists():
        try:
            data = json.loads(memory_file.read_text(encoding="utf-8"))
            logger.info(f"Memory loaded: cycle #{data.get('cycle_count', 0)}, {len(data.get('log', []))} log entries")
            return data
        except Exception as e:
            logger.warning(f"Failed to read memory file, starting fresh: {e}")

    return {
        "cycle_count": 0,
        "created_at": _now(),
        "goals": [
            "Explore the current n8n instance and understand what workflows exist.",
            "Create a health-check workflow that pings external services.",
            "Build a self-monitor workflow that alerts on failures.",
        ],
        "created_workflow_ids": [],
        "log": [],
        "last_updated": _now(),
    }


def save_memory(memory: dict[str, Any]) -> None:
    """Save agent memory to disk."""
    memory["last_updated"] = _now()
    # Keep log trimmed
    if len(memory.get("log", [])) > MAX_LOG_ENTRIES:
        memory["log"] = memory["log"][-MAX_LOG_ENTRIES:]
    _memory_path().write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Memory saved: cycle #{memory.get('cycle_count', 0)}")


def append_log(memory: dict[str, Any], entry: dict[str, Any]) -> None:
    """Append a log entry to memory (in-place)."""
    entry["ts"] = _now()
    memory.setdefault("log", []).append(entry)


def summarise_memory(memory: dict[str, Any]) -> str:
    """Return a compact text summary for injection into LLM context."""
    lines = [
        f"=== AGENT MEMORY (Cycle #{memory.get('cycle_count', 0)}) ===",
        f"Created: {memory.get('created_at', 'unknown')}",
        f"Last updated: {memory.get('last_updated', 'unknown')}",
        "",
        "CURRENT GOALS:",
    ]
    for i, g in enumerate(memory.get("goals", []), 1):
        lines.append(f"  {i}. {g}")

    recent = memory.get("log", [])[-10:]
    if recent:
        lines.append("")
        lines.append("RECENT ACTIONS (last 10):")
        for entry in recent:
            lines.append(f"  [{entry.get('ts', '')[:19]}] {entry.get('summary', '')}")

    wf_ids = memory.get("created_workflow_ids", [])
    if wf_ids:
        lines.append("")
        lines.append(f"WORKFLOWS I CREATED: {', '.join(str(x) for x in wf_ids)}")

    return "\n".join(lines)
