import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings


ROOT_DIR = Path(__file__).resolve().parents[2]


async def _fake_generate_reply(**_: object) -> str:
    return "Start with one visible persona card and a small memory block."


def test_chat_endpoint_creates_and_returns_session(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AVATAR_DIR", str(ROOT_DIR / "data" / "avatars"))
    monkeypatch.setenv("CHAT_SESSION_DIR", str(tmp_path / "chat_sessions"))
    get_settings.cache_clear()

    import app.main as app_main

    app_main = importlib.reload(app_main)
    monkeypatch.setattr(app_main, "generate_reply", _fake_generate_reply)

    with TestClient(app_main.app) as client:
        response = client.post(
            "/api/chat",
            json={
                "avatar_id": "guide",
                "message": "I am building a local avatar AI MVP in FastAPI.",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["reply"] == "Start with one visible persona card and a small memory block."
        assert body["session_id"]
        assert body["session"]["avatar_id"] == "guide"
        assert any("local avatar ai" in item.lower() for item in body["session"]["memory"]["known_facts"])

        session_response = client.get(f"/api/chat/sessions/guide/{body['session_id']}")

        assert session_response.status_code == 200
        session_body = session_response.json()
        assert len(session_body["messages"]) == 2
        assert session_body["messages"][0]["role"] == "user"
        assert session_body["messages"][1]["role"] == "assistant"
