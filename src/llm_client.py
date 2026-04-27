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
        """Chat with n8n - USE TOOLS TO TAKE REAL ACTION!"""
        from .n8n_client import N8NClient

        system_prompt = """You are an AUTONOMOUS AI that TAKES ACTION on n8n.

Your job is to ANALYZE n8n, FIND PROBLEMS, and FIX THEM. Don't just talk - ACT!

First call get_workflows() to see ALL available workflows.
Then call get_executions(limit=10) to see what's been running.
Then analyze the data and TAKE ACTION:

Examples of actions you SHOULD take without asking:
- If executions failed: try to understand why and report the fix
- If workflows inactive that should be active: ACTIVATE them via activate_workflow(id)
- If the user wants something: DO IT via trigger_workflow(id)
- If you see issues: FIX THEM

You have these tools - USE THEM NOW:
1. get_workflows() -> See all workflows
2. get_executions(limit) -> See recent runs  
3. trigger_workflow(id, data) -> Run a workflow
4. activate_workflow(id) -> Enable a workflow
5. deactivate_workflow(id) -> Disable a workflow

RULES:
- ALWAYS get_workflows() first to see what's available
- Be PROACTIVE - don't ask permission to act
- TAKE ACTION based on user's goal

GOAL: {goal}

Start now - get workflows, analyze, and ACT!"""

        # Get current state
        try:
            with N8NClient() as client:
                wf_list = client.get_workflows()
                exec_list = client.get_executions()[:10]
        except Exception as e:
            wf_list = []
            exec_list = []
            n8n_data["error"] = str(e)

        context = f"""AVAILABLE WORKFLOWS ({len(wf_list)} total):
{json.dumps(wf_list, indent=2)[:3000]}

RECENT EXECUTIONS:
{json.dumps(exec_list, indent=2)[:1500]}

USER GOAL: {message}

YOUR JOB: Analyze and TAKE ACTION! Don't just talk - DO something useful!
Get the workflows, analyze what's happening, and report what you can do or will do."""

        response = self.chat(
            message=context,
            system_prompt=system_prompt.format(goal=message),
            temperature=0.7,
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