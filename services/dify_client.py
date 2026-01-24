from __future__ import annotations

import os
import json
from typing import Any, Dict

import httpx


class DifyClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.base_url = (base_url or os.getenv("DIFY_API_BASE") or "https://api.dify.ai").rstrip("/")
        self.api_key = api_key or os.getenv("DIFY_WORKFLOW_API_KEY")
        if not self.api_key:
            raise ValueError("DIFY_WORKFLOW_API_KEY is required")

        # デバッグ用フラグ（環境変数 DIFY_DEBUG=1 でON）
        self.debug = os.getenv("DIFY_DEBUG", "1") == "1"

    # --- 内部ログ用 ---
    def _log(self, msg: str) -> None:
        if self.debug:
            print(f"[DifyClient] {msg}", flush=True)

    def run_workflow(
        self,
        inputs: Dict[str, Any] | None = None,
        user: str = "demo",
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/workflows/run"
        masked_key = f"{self.api_key[:6]}...{self.api_key[-4:]}" if self.api_key else "None"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "inputs": inputs or {},
            "response_mode": "blocking",
            "user": user,
        }

        # 送信前ログ
        self._log(f"POST {url}")
        self._log(f"Authorization: Bearer {masked_key}")
        self._log(f"Request payload: {json.dumps(payload, ensure_ascii=False)}")

        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(url, headers=headers, json=payload)
        except httpx.RequestError as e:
            self._log(f"RequestError: {repr(e)}")
            raise

        self._log(f"HTTP status: {resp.status_code}")
        # レスポンス本文（長すぎると困るので先頭2,000文字だけ）
        try:
            body_text = resp.text
        except Exception:
            body_text = "<resp.text 取得失敗>"
        self._log(f"Raw response text: {body_text[:2000]}")

        # ステータス異常ならここで例外＋ログ
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            self._log(f"HTTPStatusError: {repr(e)}")
            raise

        # JSONパース
        try:
            data = resp.json()
        except Exception as e:
            self._log(f"JSON decode error: {repr(e)}")
            raise

        self._log(f"Parsed JSON: {json.dumps(data, ensure_ascii=False)[:2000]}")

        # いろいろなレスポンスパターンを吸収
        if isinstance(data, dict):
            # Dify workflow の典型: {"data":{"outputs":{...}}}
            if "data" in data and isinstance(data["data"], dict):
                inner = data["data"]
                if "outputs" in inner and isinstance(inner["outputs"], dict):
                    self._log("Returning data['data']['outputs']")
                    return inner["outputs"]
                self._log("Returning data['data']")
                return inner
            # もしくは {"outputs":{...}}
            if "outputs" in data and isinstance(data["outputs"], dict):
                self._log("Returning data['outputs']")
                return data["outputs"]

        self._log("Returning raw data as-is (unexpected structure)")
        return data
