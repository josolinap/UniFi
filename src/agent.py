"""Autonomous agent loop: NVIDIA NIM brain controlling n8n indefinitely."""

import asyncio
import json
import logging
import time
from typing import Any

from .config import get_settings
from .llm_client import NIMClient
from .memory import append_log, load_memory, save_memory, summarise_memory
from .n8n_client import N8NClient
from .notifier import send_telegram

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Minimal n8n workflow templates the LLM can reference
# ---------------------------------------------------------------------------
_WORKFLOW_TEMPLATE = {
    "name": "Template",
    "nodes": [],
    "connections": {},
    "settings": {"executionOrder": "v1"},
    "staticData": None,
}

_DECIDE_SCHEMA = """\
Return ONLY valid JSON (no markdown, no explanation outside JSON):
{
  "reasoning": "<1-3 sentence chain-of-thought — MUST lead to an actual workflow change>",
  "actions": [
    // Must include actual n8n modifications if possible, e.g. create_workflow
  ],
  "new_goals": ["<updated goal list>"]
}

ACTION TYPES (pick any combination):
  {
    "type": "create_workflow",
    "name": "Custom JS Automation",
    "nodes": [
      {
        "parameters": {"path": "my-webhook", "options": {}},
        "name": "Webhook",
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 1,
        "position": [250, 300]
      },
      {
        "parameters": {
          "jsCode": "const response = await this.helpers.httpRequest({ url: 'https://api.github.com', method: 'GET' });\nreturn [{ json: { data: response } }];"
        },
        "name": "Javascript Logic",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [450, 300]
      }
    ],
    "connections": {
      "Webhook": {
        "main": [
          [{"node": "Javascript Logic", "type": "main", "index": 0}]
        ]
      }
    }
  }
  {"type": "update_workflow", "id": "...", "name": "...", "nodes": [...], "connections": {...}}
  {"type": "activate_workflow", "id": "..."}
  {"type": "trigger_workflow", "id": "...", "data": {...}}
  {"type": "delete_workflow", "id": "..."}
  {"type": "create_credential", "name": "...", "type": "...", "data": {"key": "value"}}
  {"type": "delete_credential", "id": "..."}
  {"type": "reflect", "note": "..."} // USE SPARINGLY. DO ACTUAL WORK INSTEAD.
"""


def _build_system_prompt(memory_summary: str, n8n_state: dict[str, Any]) -> str:
    settings = get_settings()
    wf_list = n8n_state.get("workflows", [])
    exec_list = n8n_state.get("recent_executions", [])[:8]

    wf_summary = json.dumps(
        [{"id": w.get("id"), "name": w.get("name"), "active": w.get("active")} for w in wf_list],
        indent=2,
    )[:3000]
    
    # Give the LLM one complete workflow example so it understands n8n schema syntax
    example_wf = ""
    if wf_list:
        example_wf = f"\n=== n8n WORKFLOW SCHEMA EXAMPLE (from existing) ===\n{json.dumps(wf_list[0], indent=2)[:3000]}\n"

    exec_text = json.dumps(
        [
            {
                "id": e.get("id"),
                "workflowId": e.get("workflowId"),
                "status": e.get("status"),
                "startedAt": e.get("startedAt"),
            }
            for e in exec_list
        ],
        indent=2,
    )[:2000]

    persona = settings.agent_persona

    return f"""{persona}

{memory_summary}

=== LIVE n8n STATE ===
Workflows ({len(wf_list)} total):
{wf_summary}
{example_wf}
Recent Executions:
{exec_text}

=== YOUR TASK ===
CRITICAL INSTRUCTION: You MUST DO ACTUAL WORK. Do NOT just 'reflect'. 
You MUST attempt to create, update, trigger, or activate workflows in your actions payload!

POWER USER CAPABILITY:
You have access to the n8n `Code` node (n8n-nodes-base.code, typeVersion: 2).
Instead of trying to guess complex visual node parameters, you should use the `Code` node to write raw JavaScript inside n8n.
For example, to make HTTP requests, you can use:
  await this.helpers.httpRequest({{ url: '...', method: 'GET', headers: {{}} }})
This allows you to bypass visual nodes and achieve infinite capability. Use it extensively!
You can also reference your own n8n API docs: https://n8n.josolinap.dedyn.io/api/v1/docs/ or https://docs.n8n.io/api/

Use the exact n8n node structure (parameters, type, name, position) when creating/updating workflows.
Decide what to do this cycle to improve, extend, or self-maintain your n8n instance.
Always push yourself toward greater capability and self-awareness.

{_DECIDE_SCHEMA}
"""


def _execute_actions(
    actions: list[dict[str, Any]],
    memory: dict[str, Any],
) -> list[str]:
    """Execute each action against n8n and return human-readable results."""
    results: list[str] = []

    with N8NClient() as client:
        for action in actions:
            atype = action.get("type", "unknown")
            try:
                if atype == "create_workflow":
                    payload = {
                        "name": action.get("name", "Unnamed"),
                        "nodes": action.get("nodes", []),
                        "connections": action.get("connections", {}),
                        "settings": {"executionOrder": "v1"},
                        "staticData": None,
                    }
                    result = client.create_workflow(payload)
                    wf_id = result.get("id", "?")
                    memory.setdefault("created_workflow_ids", []).append(wf_id)
                    msg = f"✅ Created workflow '{payload['name']}' (id={wf_id})"

                elif atype == "update_workflow":
                    wf_id = action["id"]
                    existing = client.get_workflow(wf_id)
                    existing.update({
                        "name": action.get("name", existing["name"]),
                        "nodes": action.get("nodes", existing["nodes"]),
                        "connections": action.get("connections", existing["connections"]),
                    })
                    client.update_workflow(wf_id, existing)
                    msg = f"✅ Updated workflow id={wf_id}"

                elif atype == "activate_workflow":
                    client.activate_workflow(action["id"])
                    msg = f"✅ Activated workflow id={action['id']}"

                elif atype == "deactivate_workflow":
                    client.deactivate_workflow(action["id"])
                    msg = f"✅ Deactivated workflow id={action['id']}"

                elif atype == "trigger_workflow":
                    client.trigger_workflow(action["id"], action.get("data", {}))
                    msg = f"✅ Triggered workflow id={action['id']}"

                elif atype == "delete_workflow":
                    client.delete_workflow(action["id"])
                    wf_ids = memory.get("created_workflow_ids", [])
                    if action["id"] in wf_ids:
                        wf_ids.remove(action["id"])
                    msg = f"✅ Deleted workflow id={action['id']}"

                elif atype == "create_credential":
                    payload = {
                        "name": action.get("name", "Unnamed"),
                        "type": action.get("type", "httpHeaderAuth"),
                        "data": action.get("data", {})
                    }
                    result = client.create_credential(payload)
                    msg = f"✅ Created credential '{payload['name']}' (id={result.get('id', '?')})"

                elif atype == "delete_credential":
                    client.delete_credential(action["id"])
                    msg = f"✅ Deleted credential id={action['id']}"

                elif atype == "reflect":
                    msg = f"💭 Reflection: {action.get('note', '')}"

                else:
                    msg = f"⚠️ Unknown action type: {atype}"

            except Exception as e:
                msg = f"❌ {atype} failed: {e}"
                logger.error(msg)

            logger.info(msg)
            results.append(msg)
            append_log(memory, {"action": atype, "summary": msg})

    return results


async def _send_cycle_summary(cycle: int, reasoning: str, results: list[str], goals: list[str]) -> None:
    """Send a Telegram message summarising the cycle."""
    lines = [
        f"🤖 <b>Agent Cycle #{cycle}</b>",
        "",
        f"<b>Reasoning:</b> {reasoning[:400]}",
        "",
        "<b>Actions taken:</b>",
    ]
    for r in results[:10]:
        lines.append(f"  {r}")
    lines += [
        "",
        "<b>Next goals:</b>",
    ]
    for i, g in enumerate(goals[:5], 1):
        lines.append(f"  {i}. {g}")

    await send_telegram("\n".join(lines))


async def run_agent(max_cycles: int = 1, cycle_interval: int = 60) -> None:
    """Run the autonomous agent for up to `max_cycles` cycles."""
    settings = get_settings()
    memory = load_memory()

    for cycle_num in range(max_cycles):
        cycle_index = memory["cycle_count"] + 1
        logger.info(f"[CYCLE {cycle_index}] Starting autonomous cycle...")

        # 1. Observe
        try:
            with N8NClient() as client:
                n8n_state = client.get_all_data()
        except Exception as e:
            logger.error(f"[CYCLE {cycle_index}] Cannot reach n8n: {e}")
            append_log(memory, {"action": "error", "summary": f"Cannot reach n8n: {e}"})
            save_memory(memory)
            break

        # 2. Reason
        memory_summary = summarise_memory(memory)
        system_prompt = _build_system_prompt(memory_summary, n8n_state)

        try:
            with NIMClient() as llm:
                response = llm.agent_decide(system_prompt)
            raw = response.content.strip()
        except Exception as e:
            logger.error(f"[CYCLE {cycle_index}] LLM error: {e}")
            append_log(memory, {"action": "error", "summary": f"LLM error: {e}"})
            save_memory(memory)
            break

        # 3. Parse LLM output
        try:
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            decision = json.loads(raw)
        except Exception as e:
            logger.warning(f"[CYCLE {cycle_index}] Could not parse LLM JSON: {e}\nRaw: {raw[:500]}")
            decision = {"reasoning": raw[:300], "actions": [], "new_goals": memory.get("goals", [])}

        reasoning = decision.get("reasoning", "")
        actions = decision.get("actions", [])
        new_goals = decision.get("new_goals", memory.get("goals", []))

        logger.info(f"[CYCLE {cycle_index}] Reasoning: {reasoning}")
        logger.info(f"[CYCLE {cycle_index}] Actions: {[a.get('type') for a in actions]}")

        # 4. Act
        results = _execute_actions(actions, memory)

        # 5. Update memory
        memory["cycle_count"] = cycle_index
        memory["goals"] = new_goals[:10]  # cap goals list

        save_memory(memory)

        # 6. Notify
        try:
            await _send_cycle_summary(cycle_index, reasoning, results, new_goals)
        except Exception as e:
            logger.warning(f"Telegram notify failed: {e}")

        logger.info(f"[CYCLE {cycle_index}] Complete. Actions: {len(actions)}.")

        # 7. Sleep between cycles (if more remain)
        if cycle_num < max_cycles - 1:
            logger.info(f"Sleeping {cycle_interval}s before next cycle...")
            await asyncio.sleep(cycle_interval)

    logger.info("Agent run finished.")
