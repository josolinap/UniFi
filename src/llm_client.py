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

    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.6,
        max_tokens: int = 1024,
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

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage=usage,
        )

    def ask_about_network(
        self,
        question: str,
        network_data: dict[str, Any],
    ) -> LLMResponse:
        """Ask the LLM about network data."""
        system_prompt = """You are a helpful network administrator assistant.
        You have access to UniFi network data and can answer questions about it.
        Be concise and informative. Use available data to provide accurate answers.
        If you don't have enough information to answer, say so."""

        data_summary = json.dumps(network_data, indent=2)

        full_prompt = f"""Based on the following network data, answer this question: {question}

Network Data:
{data_summary}

Provide a clear and concise answer."""

        return self.chat(full_prompt, system_prompt=system_prompt)

    def suggest_action(
        self,
        action_request: str,
        network_data: dict[str, Any],
    ) -> LLMResponse:
        """Ask LLM to suggest a network action."""
        system_prompt = """You are a helpful network administrator assistant.
        You can suggest network management actions like:
        - Restarting a device
        - Blocking a client
        - Enabling/disabling WiFi
        
        Based on the network data provided, suggest an appropriate action.
        Explain what the action will do and its potential impact.
        
        IMPORTANT: Only suggest actions - do not execute them. The user must confirm first."""

        data_summary = json.dumps(network_data, indent=2)

        full_prompt = f"""Based on this network data, {action_request}

Network Data:
{data_summary}

What action do you suggest? Explain clearly what it will do."""

        return self.chat(full_prompt, system_prompt=system_prompt)

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
                state = "online" if d.get("state") == "1" else "offline"
                lines.append(
                    f"    - {d.get('name', 'Unknown')}: {d.get('model', '')} ({state})"
                )

        clients = site.get("clients", 0)
        lines.append(f"  Clients: {clients}")

        alerts = site.get("alerts", [])
        if alerts:
            lines.append("  Recent Alerts:")
            for alert in alerts[-3:]:
                msg = alert.get("msg", alert.get("key", "Unknown"))
                lines.append(f"    - {msg}")

        lines.append("")

    return "\n".join(lines)