from pathlib import Path

import pytest

from app.style_store import public_styles


ROOT_DIR = Path(__file__).resolve().parents[2]


def test_public_styles_returns_enabled_presets() -> None:
    styles = public_styles(ROOT_DIR / "data" / "styles")
    ids = {style.id for style in styles}
    assert "cinematic-pro" in ids
    assert "anime-neon" in ids
    assert all(style.enabled for style in styles)
