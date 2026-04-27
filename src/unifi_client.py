"""UniFi API client for multi-site network management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import httpx

from .config import get_settings


class DeviceState(Enum):
    ONLINE = "1"
    OFFLINE = "0"
    UNKNOWN = "unknown"


@dataclass
class UniFiDevice:
    """Represents a UniFi network device."""

    mac: str
    name: str
    type: str
    model: str
    state: DeviceState
    uptime: int
    ip_address: str
    version: str
    site_name: str
    channel: Optional[int] = None
    channel_width: Optional[int] = None
    tx_bytes: int = 0
    rx_bytes: int = 0
    tx_power: Optional[int] = None
    signal: Optional[int] = None
    cg_name: Optional[str] = None
    cg_mac: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], site_name: str) -> "UniFiDevice":
        """Create UniFiDevice from API response dict."""
        state_str = data.get("state", "0")
        try:
            state = DeviceState(state_str)
        except ValueError:
            state = DeviceState.UNKNOWN

        return cls(
            mac=data.get("mac", ""),
            name=data.get("name", data.get("mac", "Unknown")),
            type=data.get("type", "unknown"),
            model=data.get("model", "unknown"),
            state=state,
            uptime=data.get("uptime", 0),
            ip_address=data.get("ip", ""),
            version=data.get("version", ""),
            site_name=site_name,
            channel=data.get("channel"),
            channel_width=data.get("channel_width"),
            tx_bytes=data.get("tx_bytes", 0),
            rx_bytes=data.get("rx_bytes", 0),
            tx_power=data.get("tx_power"),
            signal=data.get("signal"),
            cg_name=data.get("cg_name"),
            cg_mac=data.get("cg_mac"),
        )

    def is_online(self) -> bool:
        """Check if device is online."""
        return self.state == DeviceState.ONLINE

    @property
    def uptime_formatted(self) -> str:
        """Format uptime as human-readable string."""
        seconds = self.uptime
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60

        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"


@dataclass
class UniFiClient:
    """Client for interacting with UniFi Network API."""

    _settings = get_settings()
    _client: httpx.Client = field(init=False)
    _headers: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        """Initialize HTTP client and headers."""
        api_type = self._settings.unifi_api_type
        base_url = self._settings.unifi_base_url

        if api_type == "cloud-ea":
            base_url = "https://api.ui.com"
        elif api_type == "local":
            if not base_url or base_url == "https://api.ui.com":
                base_url = "https://unifi.ui.com/proxy/network/api"

        self._client = httpx.Client(
            base_url=base_url,
            timeout=30.0,
            verify=True,
            follow_redirects=True,
        )
        api_key = self._settings.unifi_api_key
        self._headers = self._build_headers(api_key)

    def _build_headers(self, api_key: str) -> dict[str, str]:
        """Build headers with proper auth based on endpoint."""
        base_url = self._settings.unifi_base_url
        if "api.ui.com" in base_url or "unifi.ui.com" in base_url:
            return {
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        else:
            return {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

    def __enter__(self) -> "UniFiClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self._client.close()

    def get_sites(self) -> list[dict[str, Any]]:
        """Get all accessible sites."""
        # Try Site Manager cloud API
        response = self._client.get("/ea/sites", headers=self._headers)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    def get_all_devices(self) -> list[dict[str, Any]]:
        """Get all devices across all sites."""
        response = self._client.get("/ea/devices", headers=self._headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        return []

    def get_site_devices(self, site_id: str) -> list[UniFiDevice]:
        """Get all devices in a site."""
        response = self._client.get(
            f"/ea/sites/{site_id}/devices",
            headers=self._headers,
        )
        response.raise_for_status()
        data = response.json()

        site_name = self._get_site_name(site_id)
        devices = [
            UniFiDevice.from_dict(d, site_name) for d in data.get("data", [])
        ]
        return devices

    def get_site_clients(self, site_id: str) -> list[dict[str, Any]]:
        """Get all clients in a site."""
        response = self._client.get(
            f"/v1/sites/{site_id}/clients",
            headers=self._headers,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    def get_site_alerts(self, site_id: str) -> list[dict[str, Any]]:
        """Get alerts in a site."""
        response = self._client.get(
            f"/v1/sites/{site_id}/alarms",
            headers=self._headers,
        )
        if response.status_code != 200:
            return []
        data = response.json()
        return data.get("data", [])

    def get_network_health(self, site_id: str) -> dict[str, Any]:
        """Get network health metrics for a site."""
        response = self._client.get(
            f"/v1/sites/{site_id}/health",
            headers=self._headers,
        )
        if response.status_code != 200:
            return {}
        data = response.json()
        return data.get("data", {})

    def get_all_sites_data(self) -> dict[str, Any]:
        """Get comprehensive data for all sites."""
        sites = []
        devices = []
        raw_response = {}

        # Try Site Manager cloud API /ea/sites
        try:
            response = self._client.get("/ea/sites", headers=self._headers)
            if response.status_code == 200:
                data = response.json()
                sites = data.get("data", [])
                raw_response["ea/sites"] = data
        except Exception as e:
            raw_response["ea/sites"] = {"error": str(e)}

        # Try /ea/devices (may require specific site)
        try:
            response = self._client.get("/ea/devices", headers=self._headers)
            if response.status_code == 200:
                data = response.json()
                devices = data.get("data", [])
                raw_response["ea/devices"] = data
        except Exception as e:
            raw_response["ea/devices"] = {"error": str(e)}

        result = {
            "sites": [], 
            "total_devices": len(devices), 
            "total_clients": 0,
            "raw_response": raw_response,
            "api_key_set": bool(self._settings.unifi_api_key),
        }

        # If no sites but have devices, create a placeholder
        if not sites and devices:
            site_data = {
                "id": "default",
                "name": "My Network",
                "desc": "All devices",
                "devices": devices,
                "devices_online": sum(1 for d in devices if d.get("state") == "1"),
                "devices_total": len(devices),
                "clients": 0,
                "alerts": [],
            }
            result["sites"].append(site_data)
            return result

        # Even if empty, provide placeholder
        if not result["sites"]:
            result["sites"].append({
                "id": "placeholder",
                "name": "UniFi Site Manager",
                "desc": "API connected - no data (UDM not linked)",
                "devices": [],
                "devices_online": 0,
                "devices_total": 0,
                "clients": 0,
                "alerts": [],
            })

        return result

    def _get_site_name(self, site_id: str) -> str:
        """Get site name by ID."""
        sites = self.get_sites()
        for site in sites:
            site_id_match = site.get("id") or site.get("_id")
            if site_id_match == site_id:
                return site.get("name", "Unknown")
        return "Unknown"

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()


def get_network_summary() -> str:
    """Get a formatted summary of the network status."""
    with UniFiClient() as client:
        data = client.get_all_sites_data()

    if not data.get("sites"):
        return "WARNING: No UniFi data found.\n\nPossible issues:\n- Your UDM Pro may not be connected to Site Manager\n- No sites configured yet\n- API key needs console association\n\nCheck: https://unifi.ui.com"

    lines = ["<b>Network Status</b>", ""]

    for site in data["sites"]:
        name = site.get("name", "Unknown")
        devices_online = site.get("devices_online", 0)
        devices_total = site.get("devices_total", 0)
        clients = site.get("clients", 0)

        status_emoji = "[OK]" if devices_online == devices_total else "[WARN]"
        lines.append(f"{status_emoji} {name}")
        lines.append(f"   Devices: {devices_online}/{devices_total} online")
        lines.append(f"   Clients: {clients}")

        offline = []
        for d in site.get("devices", []):
            if isinstance(d, dict):
                if d.get("state") != "1":
                    offline.append(d.get("name", "Unknown"))
            elif hasattr(d, 'is_online') and not d.is_online():
                offline.append(d.name)
        if offline:
            lines.append(f"   ⚠️ Offline: {', '.join(offline)}")
        lines.append("")

    lines.append(
        f"Total: {data['total_devices']} devices, {data['total_clients']} clients"
    )

    return "\n".join(lines)