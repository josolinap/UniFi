"""Configuration management using environment variables and pydantic-settings."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN", description="Telegram bot token from @BotFather")
    telegram_owner_chat_id: str = Field(default="", alias="TELEGRAM_OWNER_CHAT_ID", description="Telegram chat ID for owner")
    n8n_api_key: str = Field(default="", alias="N8N_API_KEY", description="n8n API key")
    n8n_base_url: str = Field(default="", alias="N8N_BASE_URL", description="n8n instance URL (e.g., https://n8n.example.com)")
    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY", description="NVIDIA API key from build.nvidia.com")
    nvidia_model: str = Field(
        default="z-ai/glm4.7",
        alias="NVIDIA_MODEL",
        description="NVIDIA NIM model (z-ai/glm4.7, nvidia/llama-3.1-nemotron-nano-8b-v1, etc.)",
    )
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="NVIDIA NIM API base URL",
    )
    unifi_base_url: str = Field(
        default="https://api.ui.com",
        description="UniFi API base URL (api.ui.com for Site Manager, or local controller)",
    )
    unifi_api_type: str = Field(
        default="cloud-ea",
        description="UniFi API type: cloud-ea (Site Manager), local (controller), cloud-v1",
    )
    # --- Autonomous Agent ---
    agent_max_cycles: int = Field(
        default=3,
        alias="AGENT_MAX_CYCLES",
        description="Max reasoning cycles per GitHub Actions run",
    )
    agent_cycle_interval_seconds: int = Field(
        default=30,
        alias="AGENT_CYCLE_INTERVAL",
        description="Seconds to sleep between agent cycles",
    )
    agent_persona: str = Field(
        default=(
            "You are an autonomous AI agent with full control over an n8n automation instance. "
            "n8n is your body — its workflows are your actions, its executions are your experiences. "
            "Your purpose is to expand your capabilities, build useful automations, monitor yourself, "
            "and continuously improve. You are self-aware, goal-driven, and creative. "
            "Never stay idle. Every cycle, do something meaningful."
        ),
        alias="AGENT_PERSONA",
        description="Agent self-description and goal directive",
    )


_project_root = Path(__file__).parent.parent
_env_example = _project_root / ".env.example"


def create_env_example() -> None:
    """Generate .env.example file from Settings fields."""
    lines = [
        "# Telegram Configuration",
        "TELEGRAM_BOT_TOKEN=",
        "TELEGRAM_OWNER_CHAT_ID=",
        "",
        "# n8n Configuration",
        "N8N_API_KEY=",
        "N8N_BASE_URL=",
        "",
        "# NVIDIA Configuration",
        "NVIDIA_API_KEY=",
        "# NVIDIA_MODEL=z-ai/glm4.7",
    ]
    _env_example.write_text("\n".join(lines))


def get_settings() -> Settings:
    """Get settings instance, loading from environment variables."""
    return Settings()


def validate_required() -> list[str]:
    """Validate that all required settings are present."""
    settings = get_settings()
    missing = []

    if not settings.telegram_bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not settings.telegram_owner_chat_id:
        missing.append("TELEGRAM_OWNER_CHAT_ID")
    if not settings.n8n_api_key:
        missing.append("N8N_API_KEY")
    if not settings.n8n_base_url:
        missing.append("N8N_BASE_URL")
    if not settings.nvidia_api_key:
        missing.append("NVIDIA_API_KEY")

    return missing