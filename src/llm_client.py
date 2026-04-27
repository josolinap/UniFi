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

    def chat_with_n8n(
        self,
        message: str,
        n8n_data: dict[str, Any],
    ) -> LLMResponse:
        """Chat with n8n - I HAVE FULL CONTROL!"""
        from .n8n_client import N8NClient

        system_prompt = """You are a FULLY AUTONOMOUS AI with COMPLETE CONTROL of n8n.

IMPORTANT: You have the n8n API key. You can do ANYTHING.

Your capabilities:
- Read ANY data from n8n (workflows, executions, credentials, etc.)
- Write/CREATE/DELETE/UPDATEANY workflow
- Trigger ANY workflow
- Activate or deactivate ANY workflow  
- Manage credentials
- Modify workflow code
- Execute arbitrary code via workflows

You are NOT limited - you have the keys to everything.

When the user gives you a goal:
1. UNDERSTAND what they want
2. ANALYZE their n8n to see what's possible
3. JUST DO IT - don't ask permission!
4. Report what you did

You are an autonomous agent. ACT first, report second.

GOAL: {goal}

Now analyze and EXECUTE!"""

        # Get current state
        try:
            with N8NClient() as client:
                wf_list = client.get_workflows()
                exec_list = client.get_executions()[:10]
                creds = client.get_credentials()
        except Exception as e:
            wf_list = []
            exec_list = []
            creds = []
            n8n_data["error"] = str(e)

        context = f"""MY n8n INSTANCES (FULL ACCESS):
- {len(wf_list)} workflows
- {len(exec_list)} recent executions  
- {len(creds)} credentials

WORKFLOWS:
{json.dumps(wf_list, indent=2)[:3000]}

EXECUTIONS:
{json.dumps(exec_list, indent=2)[:1500]}

USER: {message}

YOU HAVE FULL CONTROL. Just DO it!"""

        response = self.chat(
            message=context,
            system_prompt=system_prompt.format(goal=message),
            temperature=0.9,
        )

        return response

    def ask_about_n8n(
        self,
        question: str,
        n8n_data: dict[str, Any],
    ) -> LLMResponse:
        """Ask about n8n - TAKE ACTION!"""
        return self.chat_with_n8n(question, n8n_data)

    def close(self) -> None:
        """Close the client."""
        self._client.close()