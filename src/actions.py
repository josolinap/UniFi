"""Network actions with confirmation workflow."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx

from .config import get_settings


class ActionType(Enum):
    """Types of network actions."""

    RESTART_DEVICE = "restart_device"
    BLOCK_CLIENT = "block_client"
    UNBLOCK_CLIENT = "unblock_client"
    DISABLE_WIFI = "disable_wifi"
    ENABLE_WIFI = "enable_wifi"
    RESTART_AP = "restart_ap"


@dataclass
class PendingAction:
    """Represents a pending action awaiting confirmation."""

    action_type: ActionType
    target: str
    site_id: str
    extra_params: dict[str, Any] = field(default_factory=dict)
    chat_id: str = ""
    message_id: Optional[int] = None

    def to_confirmation_text(self) -> str:
        """Generate confirmation message text."""
        action_descriptions = {
            ActionType.RESTART_DEVICE: f"Restart device '{self.target}'?",
            ActionType.BLOCK_CLIENT: f"Block client '{self.target}'?",
            ActionType.UNBLOCK_CLIENT: f"Unblock client '{self.target}'?",
            ActionType.DISABLE_WIFI: f"Disable WiFi '{self.target}'?",
            ActionType.ENABLE_WIFI: f"Enable WiFi '{self.target}'?",
            ActionType.RESTART_AP: f"Restart AP '{self.target}'?",
        }
        return action_descriptions.get(
            self.action_type, f"Confirm action '{self.action_type.value}' on '{self.target}'?"
        )

    def to_execute_command(self) -> str:
        """Get command string for logging."""
        return f"/{self.action_type.value} {self.target}"


@dataclass
class ActionResult:
    """Result of a network action."""

    success: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class ActionManager:
    """Manages network actions with confirmation."""

    _settings = get_settings()
    _pending_actions: dict[str, PendingAction] = field(default_factory=dict)
    _client: httpx.Client = field(init=False)
    _headers: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        """Initialize HTTP client."""
        self._client = httpx.Client(
            base_url=self._settings.unifi_base_url,
            timeout=30.0,
            verify=True,
        )
        self._headers = {
            "Authorization": f"Bearer {self._settings.unifi_api_key}",
            "Content-Type": "application/json",
        }

    def request_action(
        self,
        action_type: ActionType,
        target: str,
        site_id: str,
        chat_id: str,
        message_id: Optional[int] = None,
        **extra_params: Any,
    ) -> PendingAction:
        """Request a network action (generates pending confirmation)."""
        action = PendingAction(
            action_type=action_type,
            target=target,
            site_id=site_id,
            chat_id=chat_id,
            message_id=message_id,
            extra_params=extra_params,
        )
        key = f"{chat_id}:{site_id}:{target}"
        self._pending_actions[key] = action
        return action

    def confirm_action(
        self,
        target: str,
        site_id: str,
        chat_id: str,
    ) -> ActionResult:
        """Execute a pending action after confirmation."""
        key = f"{chat_id}:{site_id}:{target}"
        action = self._pending_actions.pop(key, None)

        if not action:
            return ActionResult(
                success=False,
                message="No pending action found. Please request the action again.",
            )

        return self._execute_action(action)

    def cancel_action(
        self,
        target: str,
        site_id: str,
        chat_id: str,
    ) -> bool:
        """Cancel a pending action."""
        key = f"{chat_id}:{site_id}:{target}"
        if key in self._pending_actions:
            del self._pending_actions[key]
            return True
        return False

    def get_pending_action(
        self,
        target: str,
        site_id: str,
        chat_id: str,
    ) -> Optional[PendingAction]:
        """Get a pending action if exists."""
        key = f"{chat_id}:{site_id}:{target}"
        return self._pending_actions.get(key)

    def _execute_action(self, action: PendingAction) -> ActionResult:
        """Execute the actual network action."""
        site_id = action.site_id

        try:
            if action.action_type in (
                ActionType.RESTART_DEVICE,
                ActionType.RESTART_AP,
            ):
                return self._restart_device(site_id, action.target)
            elif action.action_type == ActionType.BLOCK_CLIENT:
                return self._block_client(site_id, action.target)
            elif action.action_type == ActionType.UNBLOCK_CLIENT:
                return self._unblock_client(site_id, action.target)
            elif action.action_type == ActionType.DISABLE_WIFI:
                return self._set_wifi_enabled(site_id, action.target, False)
            elif action.action_type == ActionType.ENABLE_WIFI:
                return self._set_wifi_enabled(site_id, action.target, True)
            else:
                return ActionResult(
                    success=False,
                    message=f"Unknown action type: {action.action_type}",
                )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Error executing action: {str(e)}",
            )

    def _restart_device(self, site_id: str, device_mac: str) -> ActionResult:
        """Restart a device by MAC address."""
        payload = {"cmd": "restart", "mac": device_mac}
        response = self._client.post(
            f"/api/s/{site_id}/cmd/devmgr",
            json=payload,
            headers=self._headers,
        )

        if response.status_code == 200:
            return ActionResult(
                success=True,
                message=f"Device restart command sent successfully.",
                details={"mac": device_mac},
            )
        else:
            return ActionResult(
                success=False,
                message=f"Failed to restart device: {response.text}",
            )

    def _block_client(self, site_id: str, client_mac: str) -> ActionResult:
        """Block a client by MAC address."""
        payload = {"mac": client_mac, "cmd": "block-sta"}
        response = self._client.post(
            f"/api/s/{site_id}/cmd/stamgr",
            json=payload,
            headers=self._headers,
        )

        if response.status_code == 200:
            return ActionResult(
                success=True,
                message=f"Client blocked successfully.",
                details={"mac": client_mac},
            )
        else:
            return ActionResult(
                success=False,
                message=f"Failed to block client: {response.text}",
            )

    def _unblock_client(self, site_id: str, client_mac: str) -> ActionResult:
        """Unblock a client by MAC address."""
        payload = {"mac": client_mac, "cmd": "unblock-sta"}
        response = self._client.post(
            f"/api/s/{site_id}/cmd/stamgr",
            json=payload,
            headers=self._headers,
        )

        if response.status_code == 200:
            return ActionResult(
                success=True,
                message=f"Client unblocked successfully.",
                details={"mac": client_mac},
            )
        else:
            return ActionResult(
                success=False,
                message=f"Failed to unblock client: {response.text}",
            )

    def _set_wifi_enabled(
        self,
        site_id: str,
        wlan_id: str,
        enabled: bool,
    ) -> ActionResult:
        """Enable or disable a WiFi network."""
        cmd = "enable" if enabled else "disable"
        payload = {"cmd": cmd, "wlan_id": wlan_id}
        response = self._client.post(
            f"/api/s/{site_id}/cmd/wconf",
            json=payload,
            headers=self._headers,
        )

        if response.status_code == 200:
            state = "enabled" if enabled else "disabled"
            return ActionResult(
                success=True,
                message=f"WiFi {state} successfully.",
                details={"wlan_id": wlan_id},
            )
        else:
            return ActionResult(
                success=False,
                message=f"Failed to update WiFi: {response.text}",
            )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()


def get_available_actions_text() -> str:
    """Get list of available action commands."""
    return """<b>Available Actions:</b>

/restart - Restart a device (requires MAC)
/block - Block a client (requires MAC)
/unblock - Unblock a client (requires MAC)
/wifi-on - Enable WiFi network
/wifi-off - Disable WiFi network

Example: /restart 11:22:33:44:55:66

Note: All actions require confirmation before execution."""