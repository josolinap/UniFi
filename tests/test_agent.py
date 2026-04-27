"""Tests for the autonomous agent loop."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Memory module tests
# ---------------------------------------------------------------------------

def test_load_memory_defaults(tmp_path, monkeypatch):
    """load_memory returns a fresh state when no file exists."""
    monkeypatch.chdir(tmp_path)
    from src.memory import load_memory
    mem = load_memory()
    assert mem["cycle_count"] == 0
    assert len(mem["goals"]) > 0
    assert mem["created_workflow_ids"] == []


def test_save_and_reload_memory(tmp_path, monkeypatch):
    """Memory round-trips through save/load correctly."""
    monkeypatch.chdir(tmp_path)
    from src.memory import load_memory, save_memory
    mem = load_memory()
    mem["cycle_count"] = 7
    mem["goals"] = ["do something cool"]
    save_memory(mem)

    mem2 = load_memory()
    assert mem2["cycle_count"] == 7
    assert mem2["goals"] == ["do something cool"]


def test_append_log(tmp_path, monkeypatch):
    """append_log adds entries and summarise_memory reflects them."""
    monkeypatch.chdir(tmp_path)
    from src.memory import append_log, load_memory, summarise_memory
    mem = load_memory()
    append_log(mem, {"action": "create_workflow", "summary": "✅ Created workflow 'Test'"})
    summary = summarise_memory(mem)
    assert "Created workflow" in summary


# ---------------------------------------------------------------------------
# Agent cycle test (mocked LLM + mocked n8n)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_one_cycle_reflect(tmp_path, monkeypatch):
    """A full agent cycle with a 'reflect' action only — no real network calls."""
    monkeypatch.chdir(tmp_path)

    # Mock LLM response
    mock_llm_response = MagicMock()
    mock_llm_response.content = json.dumps({
        "reasoning": "Nothing to do yet, just reflecting.",
        "actions": [{"type": "reflect", "note": "I am alive and watching."}],
        "new_goals": ["Build a health-check workflow next cycle."],
    })

    # Mock n8n state
    mock_n8n_data = {
        "status": "connected",
        "workflows": [],
        "recent_executions": [],
        "running": [],
        "workflow_count": 0,
        "execution_count": 0,
        "running_count": 0,
    }

    with (
        patch("src.agent.NIMClient") as MockLLM,
        patch("src.agent.N8NClient") as MockN8N,
        patch("src.agent.send_telegram", new_callable=AsyncMock),
    ):
        # Setup NIMClient mock
        mock_llm_instance = MagicMock()
        mock_llm_instance.__enter__ = MagicMock(return_value=mock_llm_instance)
        mock_llm_instance.__exit__ = MagicMock(return_value=False)
        mock_llm_instance.agent_decide.return_value = mock_llm_response
        MockLLM.return_value = mock_llm_instance

        # Setup N8NClient mock
        mock_n8n_instance = MagicMock()
        mock_n8n_instance.__enter__ = MagicMock(return_value=mock_n8n_instance)
        mock_n8n_instance.__exit__ = MagicMock(return_value=False)
        mock_n8n_instance.get_all_data.return_value = mock_n8n_data
        MockN8N.return_value = mock_n8n_instance

        from src.agent import run_agent
        await run_agent(max_cycles=1, cycle_interval=0)

    # Memory should have been saved with cycle_count == 1
    from src.memory import load_memory
    mem = load_memory()
    assert mem["cycle_count"] == 1
    assert mem["goals"] == ["Build a health-check workflow next cycle."]
    assert any("alive" in entry.get("summary", "") for entry in mem["log"])
