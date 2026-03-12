from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

from app.config import Settings


def _clean_username(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip().lstrip("@")
    return candidate or None


def build_mini_app_url(
    settings: Settings,
    *,
    style_id: str | None = None,
    job_id: str | None = None,
) -> str:
    base_url = settings.public_telegram_webapp_url
    query: dict[str, str] = {}
    if job_id:
        query["job"] = job_id
    if style_id:
        query["style"] = style_id
    if not query:
        return base_url
    return f"{base_url}?{urlencode(query)}"


def build_direct_mini_app_link(
    settings: Settings,
    *,
    style_id: str | None = None,
    job_id: str | None = None,
) -> str | None:
    username = _clean_username(settings.telegram_bot_username)
    if not username:
        return None

    start_param = encode_start_param(style_id=style_id, job_id=job_id)
    short_name = _clean_username(settings.telegram_mini_app_short_name)
    if short_name:
        base_url = f"https://t.me/{username}/{short_name}"
        if not start_param:
            return base_url
        return f"{base_url}?startapp={quote(start_param, safe='')}"

    if not start_param:
        return None
    return f"https://t.me/{username}?startapp={quote(start_param, safe='')}"


def encode_start_param(*, style_id: str | None = None, job_id: str | None = None) -> str | None:
    if job_id:
        return f"job-{job_id}"
    if style_id:
        return f"style-{style_id}"
    return None


def build_keyboard_button_payload(
    settings: Settings,
    *,
    text: str,
    style_id: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    direct_link = build_direct_mini_app_link(settings, style_id=style_id, job_id=job_id)
    if direct_link:
        return {"text": text, "url": direct_link}
    return {"text": text, "web_app": {"url": build_mini_app_url(settings, style_id=style_id, job_id=job_id)}}
