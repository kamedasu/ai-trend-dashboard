from __future__ import annotations

import os
from typing import Any, Dict
import httpx


class DifyClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("DIFY_API_BASE") or "https://api.dify.ai").rstrip("/")
        self.api_key = api_key or os.getenv("DIFY_WORKFLOW_API_KEY")
        if not self.api_key:
            raise ValueError("DIFY_WORKFLOW_API_KEY is required")

    def run_workflow(self, inputs: Dict[str, Any] | None = None, user: str = "demo") -> Dict[str, Any]:
        url = f"{self.base_url}/v1/workflows/run"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "inputs": inputs or {},
            "response_mode": "blocking",
            "user": user,
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], dict):
                    return data["data"]
                if "outputs" in data and isinstance(data["outputs"], dict):
                    return data["outputs"]
            return data
