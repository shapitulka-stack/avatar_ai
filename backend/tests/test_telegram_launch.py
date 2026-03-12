from app.config import Settings
from app.telegram_launch import BOT_DESCRIPTION, BOT_SHORT_DESCRIPTION, build_bot_commands, build_menu_button_payload, build_webhook_payload


def test_build_bot_commands_includes_catalog() -> None:
    assert build_bot_commands() == [
        {"command": "start", "description": "Открыть каталог"},
        {"command": "catalog", "description": "Каталог шаблонов"},
        {"command": "top", "description": "Топ шаблоны"},
        {"command": "styles", "description": "Список шаблонов"},
    ]


def test_build_menu_button_payload_uses_public_webapp_url() -> None:
    settings = Settings(
        render_external_url="https://avatar-ai-ngas.onrender.com",
        frontend_base_url="https://avatar-ai-ngas.onrender.com",
        backend_base_url="https://avatar-ai-ngas.onrender.com",
        telegram_webapp_url="https://avatar-ai-ngas.onrender.com/studio",
    )
    assert build_menu_button_payload(settings) == {
        "type": "web_app",
        "text": "Открыть каталог",
        "web_app": {"url": "https://avatar-ai-ngas.onrender.com/studio"},
    }


def test_build_webhook_payload_uses_public_backend_url() -> None:
    settings = Settings(
        telegram_bot_token="123:abc",
        render_external_url="https://avatar-ai-ngas.onrender.com",
        backend_base_url="https://avatar-ai-ngas.onrender.com",
        frontend_base_url="https://avatar-ai-ngas.onrender.com",
    )
    payload = build_webhook_payload(settings)
    assert payload is not None
    assert payload["url"] == "https://avatar-ai-ngas.onrender.com/api/telegram/webhook"
    assert payload["secret_token"]
    assert "message" in payload["allowed_updates"]


def test_launch_copy_stays_short_and_russian() -> None:
    assert "Telegram" in BOT_DESCRIPTION
    assert "Каталог" in BOT_SHORT_DESCRIPTION
