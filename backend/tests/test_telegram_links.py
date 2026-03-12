from app.config import Settings
from app.telegram_links import build_direct_mini_app_link, build_keyboard_button_payload, build_mini_app_url, encode_start_param


def test_build_mini_app_url_for_style() -> None:
    settings = Settings(telegram_webapp_url="https://example.com/studio")
    assert build_mini_app_url(settings, style_id="anime-neon") == "https://example.com/studio?style=anime-neon"


def test_build_direct_mini_app_link_for_style() -> None:
    settings = Settings(
        telegram_webapp_url="https://example.com/studio",
        telegram_bot_username="@avatar_test_bot",
        telegram_mini_app_short_name="catalog",
    )
    assert build_direct_mini_app_link(settings, style_id="anime-neon") == "https://t.me/avatar_test_bot/catalog?startapp=style-anime-neon"


def test_build_keyboard_button_payload_prefers_direct_link() -> None:
    settings = Settings(
        telegram_webapp_url="https://example.com/studio",
        telegram_bot_username="avatar_test_bot",
        telegram_mini_app_short_name="catalog",
    )
    payload = build_keyboard_button_payload(settings, text="Открыть", job_id="123")
    assert payload == {"text": "Открыть", "url": "https://t.me/avatar_test_bot/catalog?startapp=job-123"}


def test_encode_start_param_prefers_job() -> None:
    assert encode_start_param(style_id="anime-neon", job_id="abc123") == "job-abc123"


def test_build_direct_mini_app_link_falls_back_to_main_app_link() -> None:
    settings = Settings(
        telegram_webapp_url="https://example.com/studio",
        telegram_bot_username="avatar_test_bot",
        telegram_mini_app_short_name=None,
    )
    assert build_direct_mini_app_link(settings, style_id="anime-neon") == "https://t.me/avatar_test_bot?startapp=style-anime-neon"


def test_build_keyboard_button_payload_uses_webapp_without_start_param_if_no_short_name() -> None:
    settings = Settings(
        telegram_webapp_url="https://example.com/studio",
        telegram_bot_username="avatar_test_bot",
        telegram_mini_app_short_name=None,
    )
    payload = build_keyboard_button_payload(settings, text="Открыть каталог")
    assert payload == {"text": "Открыть каталог", "web_app": {"url": "https://example.com/studio"}}
