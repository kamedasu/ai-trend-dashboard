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

    def _log(self, msg: str) -> None:
        if self.debug:
            print(f"[DifyClient] {msg}", flush=True)

    def run_workflow(
        self,
        inputs: Dict[str, Any] | None = None,
        user: str = "demo",
    ) -> Dict[str, Any]:
        """
        Dify Workflow を streaming mode で実行し、
        workflow_finished イベントの outputs を返す。
        """
        url = f"{self.base_url}/v1/workflows/run"
        masked_key = f"{self.api_key[:6]}...{self.api_key[-4:]}" if self.api_key else "None"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        payload: Dict[str, Any] = {
            "inputs": inputs or {},
            "response_mode": "streaming",
            "user": user,
        }

        self._log(f"POST {url}")
        self._log(f"Authorization: Bearer {masked_key}")
        self._log(f"Request payload: {json.dumps(payload, ensure_ascii=False)}")

        timeout = httpx.Timeout(
            connect=10.0,
            read=float(os.getenv("DIFY_READ_TIMEOUT", "300")),
            write=30.0,
            pool=10.0,
        )

        last_event: Dict[str, Any] | None = None

        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream("POST", url, headers=headers, json=payload) as resp:
                    self._log(f"HTTP status: {resp.status_code}")

                    try:
                        resp.raise_for_status()
                    except httpx.HTTPStatusError as e:
                        # エラー時は本文も確認する
                        try:
                            error_body = resp.read().decode("utf-8", errors="replace")
                        except Exception:
                            error_body = "<failed to read error body>"
                        self._log(f"HTTPStatusError body: {error_body[:2000]}")
                        raise e

                    for line in resp.iter_lines():
                        if not line:
                            continue

                        # httpx のバージョンや環境によって bytes の可能性もあるため吸収
                        if isinstance(line, bytes):
                            line = line.decode("utf-8", errors="replace")

                        # Dify の SSE は data: {...} 形式
                        if not line.startswith("data:"):
                            continue

                        data_str = line[len("data:"):].strip()
                        if not data_str or data_str == "[DONE]":
                            continue

                        try:
                            event = json.loads(data_str)
                        except Exception:
                            self._log(f"Failed to parse SSE line: {data_str[:500]}")
                            continue

                        last_event = event
                        event_name = event.get("event")
                        self._log(f"SSE event: {event_name}")

                        # 失敗イベント
                        if event_name in ("workflow_failed", "error"):
                            self._log(
                                f"Workflow failed event: {json.dumps(event, ensure_ascii=False)[:2000]}"
                            )
                            raise RuntimeError(f"Dify workflow failed: {event}")

                        # 完了イベント
                        if event_name == "workflow_finished":
                            self._log(
                                f"workflow_finished: {json.dumps(event, ensure_ascii=False)[:2000]}"
                            )

                            data = event.get("data")

                            # Dify streaming の典型:
                            # {
                            #   "event": "workflow_finished",
                            #   "data": {
                            #     "outputs": {
                            #       "tech": [...],
                            #       "side": [...],
                            #       "qiita": [...]
                            #     }
                            #   }
                            # }
                            if isinstance(data, dict):
                                outputs = data.get("outputs")
                                if isinstance(outputs, dict):
                                    return outputs

                            # 念のため別構造にも対応
                            outputs = event.get("outputs")
                            if isinstance(outputs, dict):
                                return outputs

                            # outputs がない場合は data 全体を返す
                            if isinstance(data, dict):
                                return data

                            return {}

        except httpx.RequestError as e:
            self._log(f"RequestError: {repr(e)}")
            raise

        # workflow_finished が来ないまま終了した場合
        self._log(f"Stream ended without workflow_finished. last_event={last_event}")
        raise RuntimeError("Dify stream ended without workflow_finished event.")
