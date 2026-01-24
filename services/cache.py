from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any


def get_cache_dir() -> Path:
    cache_dir = Path(os.getenv("CACHE_DIR", "/data/cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def daily_cache_path(d: date) -> Path:
    return get_cache_dir() / f"daily-{d.isoformat()}.json"


def read_cache(d: date) -> dict[str, Any] | None:
    p = daily_cache_path(d)
    if p.exists():
        try:
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def write_cache(d: date, data: dict[str, Any]) -> None:
    p = daily_cache_path(d)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(p)
