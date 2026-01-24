from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from services.cache import read_cache, write_cache
from services.dify_client import DifyClient
from models.schemas import Payload


load_dotenv(override=False)


def jst_today():
    tz = ZoneInfo(os.getenv("TZ", "Asia/Tokyo"))
    return datetime.now(tz).date()


def normalize_url(u: str) -> str:
    try:
        p = urlparse(u)
        if p.scheme not in ("http", "https") or not p.netloc:
            return u
        # remove tracking params
        qs_pairs = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
        qs = urlencode(qs_pairs)
        path = p.path[:-1] if p.path.endswith("/") else p.path
        return urlunparse((p.scheme, p.netloc, path, p.params, qs, p.fragment))
    except Exception:
        return u


def coerce_items(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for it in items or []:
        title = (it.get("title") or "").strip()
        url = (it.get("url") or "").strip()
        gist = (it.get("gist") or it.get("summary") or "").strip()
        source = (it.get("source") or it.get("host") or "").strip()
        if not title or not url:
            continue
        url_n = normalize_url(url)
        if url_n in seen:
            continue
        seen.add(url_n)
        parsed = urlparse(url_n)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        out.append({
            "title": title,
            "url": url_n,
            "gist": gist[:300],
            "source": source or parsed.netloc,
        })
    return out


def fetch_payload(force: bool = False) -> dict:
    today = jst_today()
    if not force:
        cached = read_cache(today)
        if cached:
            return cached

    client = DifyClient()
    raw = client.run_workflow(inputs={})
    tech = coerce_items(raw.get("tech"))[:5]
    side = coerce_items(raw.get("side"))[:5]
    qiita = coerce_items(raw.get("qiita"))[:10]
    payload = {
        "date": today.isoformat(),
        "tech": tech,
        "side": side,
        "qiita": qiita,
    }
    # strict validation
    _ = Payload.model_validate(payload)
    write_cache(today, payload)
    return payload


def render_card(item: dict):
    title = item.get("title", "")
    url = item.get("url", "")
    gist = item.get("gist", "")
    source = item.get("source", "")
    st.markdown(
        f"<div style='border:1px solid #1f2937;border-radius:8px;padding:10px;margin-bottom:10px;background:#111827'>"
        f"<div style='display:flex;justify-content:space-between;align-items:baseline'>"
        f"<a href='{url}' target='_blank' rel='noreferrer' style='font-weight:600;color:#60a5fa;text-decoration:none'>{title}</a>"
        f"<span style='font-size:12px;color:#9ca3af;margin-left:8px'>{source}</span>"
        f"</div>"
        f"<div style='margin-top:6px;color:#d1d5db;line-height:1.5'>{gist}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="AI Trend Dashboard", layout="wide")
st.markdown("""
<style>
  .stApp { background-color: #0b0c10; color: #e5e7eb; }
  h1,h2,h3 { color: #e5e7eb; }
  .stButton>button { background:#111827; color:#e5e7eb; border:1px solid #374151; }
</style>
""", unsafe_allow_html=True)

st.title("AI Trend Dashboard")

col_left, col_right = st.columns([2, 1])

with st.sidebar:
    st.subheader("操作")
    force = st.button("更新 (Force)")
    st.caption("同日内のキャッシュを無視して再取得します")

error_placeholder = st.empty()

try:
    data = fetch_payload(force=force)
    last_updated = datetime.now(ZoneInfo(os.getenv("TZ", "Asia/Tokyo"))).strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"最終更新: {last_updated}")

    with col_left:
        st.subheader("AI 最新技術（5件）")
        if data.get("tech"):
            for it in data["tech"]:
                render_card(it)
        else:
            st.write("データがありません")

        st.subheader("AI 副業（5件）")
        if data.get("side"):
            for it in data["side"]:
                render_card(it)
        else:
            st.write("データがありません")

    with col_right:
        st.subheader("Qiita 人気（10件）")
        if data.get("qiita"):
            for it in data["qiita"]:
                render_card(it)
        else:
            st.write("データがありません")

except ValidationError as ve:
    error_placeholder.error(f"スキーマ検証に失敗しました: {ve}")
except Exception as e:
    error_placeholder.error(f"エラーが発生しました: {e}")

