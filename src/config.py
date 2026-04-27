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
    unifi_api_key: str = Field(default="", alias="UNIFI_API_KEY", description="UniFi API key from unifi.ui.com")
    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY", description="NVIDIA API key from build.nvidia.com")
    nvidia_model: str = Field(
        default="z-ai/glm-4.7",
        alias="NVIDIA_MODEL",
        description="NVIDIA NIM model (z-ai/glm-4.7, nvidia/llama-3.1-nemotron-nano-8b-v1, etc.)",
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


_project_root = Path(__file__).parent.parent
_env_example = _project_root / ".env.example"


def create_env_example() -> None:
    """Generate .env.example file from Settings fields."""
    lines = [
        "# Telegram Configuration",
        "TELEGRAM_BOT_TOKEN=",
        "TELEGRAM_OWNER_CHAT_ID=",
        "",
        "# UniFi Configuration",
        "UNIFI_API_KEY=",
        "# UNIFI_SITE_ID=  # Optional: specify site ID if needed",
        "",
        "# NVIDIA Configuration",
        "NVIDIA_API_KEY=",
        "# NVIDA_MODEL=nvidia/llama-3.1-nemotron-nano-8b-v1",
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
    if not settings.unifi_api_key:
        missing.append("UNIFI_API_KEY")
    if not settings.nvidia_api_key:
        missing.append("NVIDIA_API_KEY")

    return missing