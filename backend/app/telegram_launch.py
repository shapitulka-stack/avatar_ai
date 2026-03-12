from __future__ import annotations

from typing import Any

from app.config import Settings


BOT_DESCRIPTION = "Каталог AI-аватаров в Telegram: выбери шаблон, вставь себя и получи готовую аву."
BOT_SHORT_DESCRIPTION = "Каталог AI-аватаров с шаблонами и быстрым запуском."
CATALOG_BUTTON_TEXT = "Открыть каталог"
BOT_COMMANDS: tuple[tuple[str, str], ...] = (
    ("start", "Открыть каталог"),
    ("catalog", "Каталог шаблонов"),
    ("top", "Топ шаблоны"),
    ("styles", "Список шаблонов"),
)
WEBHOOK_ALLOWED_UPDATES: tuple[str, ...] = (
    "message",
    "edited_message",
    "callback_query",
    "inline_query",
    "my_chat_member",
    "chat_member",
    "chat_join_request",
)


def build_bot_commands() -> list[dict[str, str]]:
    return [{"command": command, "description": description} for command, description in BOT_COMMANDS]


def build_menu_button_payload(settings: Settings) -> dict[str, Any]:
    return {
        "type": "web_app",
        "text": CATALOG_BUTTON_TEXT,
        "web_app": {
            "url": settings.public_telegram_webapp_url,
        },
    }


def build_webhook_payload(settings: Settings) -> dict[str, Any] | None:
    if not settings.telegram_webhook_url or not settings.telegram_webhook_secret_value:
        return None
    return {
        "url": settings.telegram_webhook_url,
        "secret_token": settings.telegram_webhook_secret_value,
        "allowed_updates": list(WEBHOOK_ALLOWED_UPDATES),
    }
