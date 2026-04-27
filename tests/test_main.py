&lt;?xml version="1.0" encoding="UTF-8"?&gt;
"""Test suite for UniFi Network Monitor."""

import pytest
from unittest.mock import MagicMock, patch

from src.config import Settings


class TestConfig:
    """Tests for configuration."""

    def test_settings_defaults(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.nvidia_model == "nvidia/llama-3.1-nemotron-nano-8b-v1"
        assert settings.nvidia_base_url == "https://integrate.api.nvidia.com/nim/v1"
        assert settings.unifi_base_url == "https://unifi.ui.com"

    def test_settings_from_env(self, monkeypatch):
        """Test settings loading from environment."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_OWNER_CHAT_ID", "12345")
        monkeypatch.setenv("UNIFI_API_KEY", "test_key")
        monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")

        settings = Settings()
        assert settings.telegram_bot_token == "test_token"
        assert settings.telegram_owner_chat_id == "12345"
        assert settings.unifi_api_key == "test_key"
        assert settings.nvidia_api_key == "nvapi-test"


class TestUniFiClient:
    """Tests for UniFi API client."""

    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": []}
        return response

    def test_get_sites_empty(self, mock_response):
        """Test get_sites with empty response."""
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.get.return_value = mock_response

            from src.unifi_client import UniFiClient

            with UniFiClient() as client:
                sites = client.get_sites()

            assert sites == []

    def test_device_state_enum(self):
        """Test device state enum."""
        from src.unifi_client import DeviceState

        assert DeviceState.ONLINE.value == "1"
        assert DeviceState.OFFLINE.value == "0"


class TestLLMClient:
    """Tests for LLM client."""

    def test_format_network_for_llm(self):
        """Test network data formatting."""
        data = {
            "sites": [
                {
                    "name": "Home",
                    "devices": [
                        {"name": "AP1", "model": "U6-Pro", "state": "1"},
                        {"name": "AP2", "model": "U6-Pro", "state": "0"},
                    ],
                    "clients": 5,
                    "alerts": [],
                }
            ],
            "total_devices": 2,
            "total_clients": 5,
        }

        from src.llm_client import format_network_for_llm

        result = format_network_for_llm(data)
        assert "Site: Home" in result
        assert "AP1" in result
        assert "AP2" in result
        assert "Clients: 5" in result


class TestActions:
    """Tests for action management."""

    def test_pending_action_text(self):
        """Test pending action confirmation text."""
        from src.actions import ActionType, PendingAction

        action = PendingAction(
            action_type=ActionType.RESTART_DEVICE,
            target="aa:bb:cc:dd:ee:ff",
            site_id="site1",
        )

        text = action.to_confirmation_text()
        assert "aa:bb:cc:dd:ee:ff" in text

    def test_get_available_actions_text(self):
        """Test available actions text."""
        from src.actions import get_available_actions_text

        text = get_available_actions_text()
        assert "/restart" in text
        assert "/block" in text
        assert "/unblock" in text


class TestMain:
    """Tests for main module."""

    def test_main_help(self):
        """Test main help output."""
        with pytest.raises(SystemExit):
            from src.main import main

            main()