import pytest

from app.telegram_account import as_entity_ref, as_public_username, normalize_username


def test_normalize_username_strips_at_sign() -> None:
    assert normalize_username("@avatar_ai_top") == "avatar_ai_top"


def test_as_public_username_returns_none_for_blank() -> None:
    assert as_public_username("   ") is None


def test_as_entity_ref_returns_telegram_handle() -> None:
    assert as_entity_ref("ai_ava_666_bot") == "@ai_ava_666_bot"


def test_normalize_username_rejects_empty() -> None:
    with pytest.raises(ValueError):
        normalize_username("   ")
