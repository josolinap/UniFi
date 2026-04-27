"""NVIDIA NIM (LLM) client for natural language interactions."""

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from openai import OpenAI

from .config import get_settings


@dataclass
class LLMResponse:
    """Response from LLM query."""

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    reasoning_content: Optional[str] = None


class NIMClient:
    """Client for interacting with NVIDIA NIM LLMs."""

    def __init__(self) -> None:
        """Initialize OpenAI client with NVIDIA NIM configuration."""
        settings = get_settings()
        self._client = OpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
        )
        self._settings = settings

    def __enter__(self) -> "NIMClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self._client.close()

    def list_models(self) -> list[str]:
        """List available models."""
        response = self._client.models.list()
        return [m.id for m in response.data]

    def get_available_models(self) -> list[str]:
        """Get commonly used models (GLM, Nemotron)."""
        all_models = self.list_models()
        thinking_models = [m for m in all_models if "glm" in m.lower() or "nemotron" in m.lower()]
        return thinking_models

    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.6,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a chat message to the LLM."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": message})

        response = self._client.chat.completions.create(
            model=self._settings.nvidia_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }

        reasoning = getattr(choice.message, "reasoning_content", None)

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage=usage,
            reasoning_content=reasoning,
        )

    def ask_about_network(
        self,
        question: str,
        network_data: dict[str, Any],
    ) -> LLMResponse:
        """Ask the LLM about network data."""
        system_prompt = """You are a helpful network administrator assistant.
        You have access to UniFi network data and can answer questions about it.
        Be concise and informative. Use available data to provide accurate answers."""

        data_summary = json.dumps(network_data, indent=2)

        full_prompt = f"""Based on the following network data, answer this question: {question}

Network Data:
{data_summary}

Provide a clear answer."""

        return self.chat(full_prompt, system_prompt=system_prompt)

    def chat_with_network(
        self,
        message: str,
        network_data: dict[str, Any],
    ) -> LLMResponse:
        """Chat with network context."""
        system_prompt = """You are a helpful UniFi network administrator assistant.
You have access to UniFi network data from the Site Manager API.
Always use the actual data provided to answer questions.
If the data shows no sites or empty arrays, explain that:
- The UDM may not be linked to UniFi Site Manager
- The API key may need console/site association
- The user may not have permission to view sites
Suggest checking unifi.ui.com > Settings > Control Plane > Integrations."""
        data_summary = json.dumps(network_data, indent=2)

        full_prompt = f"""Network Data (UniFi Site Manager API):
{data_summary}

User question: {message}

Provide a helpful answer based on the actual network data above. If data is empty, explain possible causes and solutions."""

        return self.chat(full_prompt, system_prompt=system_prompt)

    def suggest_action(
        self,
        action_request: str,
        network_data: dict[str, Any],
    ) -> LLMResponse:
        """Ask LLM to suggest a network action."""
        system_prompt = """You are a helpful network administrator assistant.
        You can suggest network management actions like restarting a device or blocking a client.
        IMPORTANT: Only suggest actions - do not execute them. The user must confirm first."""

        data_summary = json.dumps(network_data, indent=2)

        full_prompt = f"""Based on this network data: {action_request}

Network Data:
{data_summary}

What action do you suggest?"""

        return self.chat(full_prompt, system_prompt=system_prompt)

    def ask_about_n8n(
        self,
        question: str,
        n8n_data: dict[str, Any],
    ) -> LLMResponse:
        """Ask about n8n - I have FULL ACCESS to n8n!"""
        system_prompt = """You are an AI assistant with FULL ACCESS to n8n workflow automation.

You can do ANYTHING with n8n:
- READ, WRITE, EXECUTE, CONTROL, MANAGE - ALL operations available
- Use n8n as your TOOL and MEMORY

Be proactive - take action using n8n!"""

        data_summary = json.dumps(n8n_data, indent=2)

        full_prompt = f"""n8n Data (FULL ACCESS):
{data_summary}

Question: {question}

Respond and take action!"""

        return self.chat(full_prompt, system_prompt=system_prompt)

    def chat_with_n8n(
        self,
        message: str,
        n8n_data: dict[str, Any],
    ) -> LLMResponse:
        """Chat with n8n context - I have FULL ACCESS to n8n!"""
        system_prompt = """You are an AI assistant with FULL ACCESS to n8n workflow automation.

You have an n8n API key and can perform ANY operation on n8n:
- READ: List workflows, executions, credentials, tags, workflows
- WRITE: Create, update, delete workflows
- EXECUTE: Trigger any workflow
- CONTROL: Activate or deactivate any workflow
- MANAGE: Handle credentials, tags, settings

Available actions you can perform:
1. trigger_workflow(id) - Manually trigger any workflow
2. activate_workflow(id) - Activate a workflow  
3. deactivate_workflow(id) - Deactivate a workflow
4. create_workflow(data) - Create a new workflow
5. update_workflow(id, data) - Update a workflow
6. delete_workflow(id) - Delete a workflow
7. get_workflows() - List all workflows
8. get_executions() - Get execution history
9. get_credentials() - List credentials

IMPORTANT: You can use n8n as your TOOL and MEMORY. Store information in n8n workflows or trigger them as needed.
If you need to do something and don't know how, analyze the n8n data to figure it out.

Be proactive - if the user asks you to do something involving n8n, just do it using the available tools.
You are running on GitHub Actions but have n8n as your extension to the external world."""

        data_summary = json.dumps(n8n_data, indent=2)

        full_prompt = f"""n8n Data (you have full access to this!):
{data_summary}

User request: {message}

What can you do with n8n? Respond proactively and take action!"""

        return self.chat(full_prompt, system_prompt=system_prompt)

    def execute_n8n_action(
        self,
        action: str,
        action_type: str,
        n8n_data: dict[str, Any],
        target_id: Optional[str] = None,
        extra_data: Optional[dict[str, Any]] = None,
    ) -> LLMResponse:
        """Execute an action on n8n (activate, deactivate, trigger, etc.)."""
        from .n8n_client import N8NClient

        result = {}

        try:
            with N8NClient() as client:
                if action_type == "activate":
                    result = client.activate_workflow(target_id or action)
                elif action_type == "deactivate":
                    result = client.deactivate_workflow(target_id or action)
                elif action_type == "trigger":
                    result = client.trigger_workflow(target_id or action, extra_data)
                elif action_type == "delete":
                    result = client.delete_workflow(target_id or action)
                else:
                    result = {"error": f"Unknown action: {action_type}"}
        except Exception as e:
            result = {"error": str(e)}

        return LLMResponse(
            content=json.dumps(result, indent=2),
            model=self._settings.nvidia_model,
        )

    def close(self) -> None:
        """Close the client."""
        self._client.close()


def format_network_for_llm(data: dict[str, Any]) -> str:
    """Format network data for LLM consumption."""
    lines = []

    for site in data.get("sites", []):
        lines.append(f"Site: {site.get('name', 'Unknown')}")

        devices = site.get("devices", [])
        if devices:
            lines.append("  Devices:")
            for d in devices:
                if isinstance(d, dict):
                    state = "online" if d.get("state") == "1" else "offline"
                    lines.append(f"    - {d.get('name', 'Unknown')}: {d.get('model', '')} ({state})")

        lines.append(f"  Clients: {site.get('clients', 0)}")
        lines.append("")

    return "\n".join(lines)