"""n8n API client for workflow and execution management."""

from typing import Any, Optional

import httpx

from .config import get_settings


class N8NClient:
    """Client for interacting with n8n API."""

    def __init__(self) -> None:
        """Initialize n8n client."""
        settings = get_settings()
        self._base_url = settings.n8n_base_url.rstrip("/")
        self._api_key = settings.n8n_api_key
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=30.0,
            headers={
                "X-N8N-API-KEY": self._api_key,
                "Content-Type": "application/json",
            },
        )

    def __enter__(self) -> "N8NClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._client.close()

    def get_workflows(self) -> list[dict[str, Any]]:
        """Get all workflows."""
        response = self._client.get("/api/v1/workflows")
        response.raise_for_status()
        return response.json().get("data", [])

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Get a specific workflow."""
        response = self._client.get(f"/api/v1/workflows/{workflow_id}")
        response.raise_for_status()
        return response.json()

    def get_executions(self, workflow_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Get executions, optionally filtered by workflow."""
        params = {}
        if workflow_id:
            params["workflowId"] = workflow_id
        response = self._client.get("/api/v1/executions", params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def get_current_executions(self) -> list[dict[str, Any]]:
        """Get currently running executions."""
        response = self._client.get("/api/v1/executions/current")
        response.raise_for_status()
        return response.json().get("data", [])

    def trigger_workflow(self, workflow_id: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Trigger a workflow manually."""
        response = self._client.post(
            f"/api/v1/webhooks/{workflow_id}",
            json=data or {},
        )
        response.raise_for_status()
        return response.json()

    def get_tags(self) -> list[dict[str, Any]]:
        """Get all tags."""
        response = self._client.get("/api/v1/tags")
        response.raise_for_status()
        return response.json().get("data", [])

    def get_credentials(self) -> list[dict[str, Any]]:
        """Get all credentials."""
        response = self._client.get("/api/v1/credentials")
        response.raise_for_status()
        return response.json().get("data", [])

    def get_all_data(self) -> dict[str, Any]:
        """Get comprehensive n8n data."""
        result = {"status": "unknown", "workflows": [], "executions": [], "running": []}

        try:
            workflows = self.get_workflows()
            result["workflows"] = workflows
            result["workflow_count"] = len(workflows)
        except Exception as e:
            result["workflows_error"] = str(e)

        try:
            executions = self.get_executions()
            result["recent_executions"] = executions[:10]  # Last 10
            result["execution_count"] = len(executions)
        except Exception as e:
            result["executions_error"] = str(e)

        try:
            running = self.get_current_executions()
            result["running"] = running
            result["running_count"] = len(running)
        except Exception as e:
            result["running_error"] = str(e)

        if result.get("workflow_count", 0) > 0:
            result["status"] = "connected"

        return result


def get_n8n_summary() -> str:
    """Get a formatted summary of n8n status."""
    with N8NClient() as client:
        data = client.get_all_data()

    if data.get("status") != "connected":
        return f"ERROR: Cannot connect to n8n at {get_settings().n8n_base_url}\n\nCheck:\n- N8N_BASE_URL is correct\n- N8N_API_KEY is valid"

    lines = ["<b>n8n Status</b>", ""]
    lines.append(f"<b>Workflows:</b> {data.get('workflow_count', 0)}")
    lines.append(f"<b>Total Executions:</b> {data.get('execution_count', 0)}")
    lines.append(f"<b>Running:</b> {data.get('running_count', 0)}")
    lines.append("")

    # Show workflows
    for wf in data.get("workflows", [])[:5]:
        name = wf.get("name", "Unknown")
        active = "ACTIVE" if wf.get("active") else "inactive"
        lines.append(f"  - {name} [{active}]")

    return "\n".join(lines)