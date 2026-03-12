from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings, get_settings
from app.telegram_launch import BOT_DESCRIPTION, BOT_SHORT_DESCRIPTION, build_bot_commands, build_menu_button_payload, build_webhook_payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Telegram bot commands, descriptions, menu button, and webhook.")
    parser.add_argument("--external-url", help="Public HTTPS base URL, for example https://avatar-ai-ngas.onrender.com")
    parser.add_argument("--webapp-url", help="Public mini app URL. Defaults to <external-url>/studio when omitted.")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned configuration without calling Telegram.")
    return parser.parse_args()


def _resolve_settings(args: argparse.Namespace) -> Settings:
    current = get_settings()
    updates: dict[str, str] = {}
    if args.external_url:
        normalized_external_url = args.external_url.rstrip("/")
        updates["render_external_url"] = normalized_external_url
        updates["backend_base_url"] = normalized_external_url
        updates["frontend_base_url"] = normalized_external_url
        updates["telegram_webapp_url"] = args.webapp_url or f"{normalized_external_url}/studio"
    elif args.webapp_url:
        updates["telegram_webapp_url"] = args.webapp_url
    if not updates:
        return current
    return current.model_copy(update=updates)


def _call(api_base: str, method: str, payload: dict[str, object] | None = None) -> None:
    with httpx.Client(timeout=30) as client:
        response = client.post(f"{api_base}/{method}", json=payload or {})
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API call failed for {method}: {data}")


def main() -> None:
    args = _parse_args()
    settings = _resolve_settings(args)
    if not settings.telegram_bot_token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN before running sync_telegram_bot.py")

    api_base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
    actions: list[tuple[str, dict[str, object]]] = [
        ("setMyCommands", {"commands": build_bot_commands()}),
        ("setMyDescription", {"description": BOT_DESCRIPTION}),
        ("setMyShortDescription", {"short_description": BOT_SHORT_DESCRIPTION}),
        ("setChatMenuButton", {"menu_button": build_menu_button_payload(settings)}),
    ]
    webhook_payload = build_webhook_payload(settings)
    if webhook_payload is not None:
        actions.append(("setWebhook", webhook_payload))

    if args.dry_run:
        print(f"public_webapp_url={settings.public_telegram_webapp_url}")
        print(f"public_backend_base_url={settings.public_backend_base_url}")
        for method, payload in actions:
            print(f"{method}: {payload}")
        return

    for method, payload in actions:
        _call(api_base, method, payload)
        print(f"ok {method}")


if __name__ == "__main__":
    main()
