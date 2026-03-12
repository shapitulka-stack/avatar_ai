from pathlib import Path

import yaml

from app.chat_session_store import append_message, get_or_create_chat_session, load_chat_session, refresh_memory, save_chat_session
from app.models import AvatarProfile


ROOT_DIR = Path(__file__).resolve().parents[2]


def _guide_avatar() -> AvatarProfile:
    payload = yaml.safe_load((ROOT_DIR / "data" / "avatars" / "guide.yaml").read_text(encoding="utf-8"))
    return AvatarProfile.model_validate(payload)


def test_chat_session_memory_persists_recent_context(tmp_path: Path) -> None:
    avatar = _guide_avatar()
    chat_dir = tmp_path / "chat_sessions"
    session = get_or_create_chat_session(chat_dir, avatar)

    append_message(session, "user", "I am building a local avatar AI MVP in FastAPI with memory blocks.")
    append_message(session, "assistant", "Keep the architecture small and make the memory visible in the UI.")
    refresh_memory(session, avatar)
    save_chat_session(chat_dir, session)

    loaded = load_chat_session(chat_dir, avatar.id, session.session_id)

    assert loaded.memory.summary.startswith("Current discussion")
    assert any("local avatar ai" in item.casefold() for item in loaded.memory.known_facts)
    assert "fastapi" in loaded.memory.active_topics
