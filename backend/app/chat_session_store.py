from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from uuid import uuid4

from app.models import AvatarProfile, ChatMemoryState, ChatMessage, ChatSessionSnapshot, utc_now


MAX_SESSION_MESSAGES = 24
MAX_MEMORY_FACTS = 6
MAX_ACTIVE_TOPICS = 4
TOPIC_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "avatar",
    "avatar_ai",
    "backend",
    "build",
    "built",
    "building",
    "chat",
    "code",
    "could",
    "does",
    "from",
    "have",
    "help",
    "into",
    "just",
    "like",
    "make",
    "need",
    "project",
    "should",
    "some",
    "that",
    "them",
    "there",
    "they",
    "this",
    "want",
    "what",
    "when",
    "with",
    "would",
    "аватар",
    "будет",
    "если",
    "есть",
    "как",
    "когда",
    "который",
    "можно",
    "надо",
    "нужно",
    "проект",
    "сделать",
    "сейчас",
    "тоже",
    "чтобы",
    "этот",
}
FACT_HINTS = (
    "i ",
    "i'm",
    "i am",
    "my ",
    "we ",
    "we're",
    "our ",
    "working on",
    "building",
    "trying to",
    "need ",
    "я ",
    "мой",
    "моя",
    "мои",
    "мы ",
    "наш",
    "наша",
    "делаю",
    "строю",
    "работаю",
    "нужен",
    "нужно",
)
TOKEN_PATTERN = re.compile(r"[0-9A-Za-zА-Яа-яЁё_-]{4,}")
WHITESPACE_PATTERN = re.compile(r"\s+")


class ChatSessionNotFoundError(FileNotFoundError):
    pass


def _normalize_text(value: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", value).strip()


def _truncate(value: str, limit: int = 140) -> str:
    compact = _normalize_text(value)
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1].rstrip()}..."


def _session_file(chat_session_dir: Path, avatar_id: str, session_id: str) -> Path:
    return chat_session_dir / avatar_id / f"{session_id}.json"


def save_chat_session(chat_session_dir: Path, session: ChatSessionSnapshot) -> ChatSessionSnapshot:
    path = _session_file(chat_session_dir, session.avatar_id, session.session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")
    return session


def load_chat_session(chat_session_dir: Path, avatar_id: str, session_id: str) -> ChatSessionSnapshot:
    path = _session_file(chat_session_dir, avatar_id, session_id)
    if not path.exists():
        raise ChatSessionNotFoundError(f"Chat session '{session_id}' was not found for avatar '{avatar_id}'.")
    return ChatSessionSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def get_or_create_chat_session(
    chat_session_dir: Path,
    avatar: AvatarProfile,
    session_id: str | None = None,
) -> ChatSessionSnapshot:
    if session_id:
        try:
            session = load_chat_session(chat_session_dir, avatar.id, session_id)
        except ChatSessionNotFoundError:
            session = ChatSessionSnapshot(
                session_id=session_id,
                avatar_id=avatar.id,
                avatar_name=avatar.name,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        else:
            session.avatar_name = avatar.name
            session.updated_at = utc_now()
        return save_chat_session(chat_session_dir, session)

    session = ChatSessionSnapshot(
        session_id=str(uuid4()),
        avatar_id=avatar.id,
        avatar_name=avatar.name,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    return save_chat_session(chat_session_dir, session)


def append_message(session: ChatSessionSnapshot, role: str, content: str) -> ChatSessionSnapshot:
    cleaned = _normalize_text(content)
    if not cleaned:
        return session

    session.messages.append(ChatMessage(role=role, content=cleaned))
    if len(session.messages) > MAX_SESSION_MESSAGES:
        session.messages = session.messages[-MAX_SESSION_MESSAGES:]
    session.updated_at = utc_now()
    return session


def refresh_memory(session: ChatSessionSnapshot, avatar: AvatarProfile) -> ChatSessionSnapshot:
    user_messages = [message.content for message in session.messages if message.role == "user"]
    assistant_messages = [message.content for message in session.messages if message.role == "assistant"]
    active_topics = _extract_active_topics(user_messages)

    session.memory = ChatMemoryState(
        summary=_build_summary(user_messages, assistant_messages),
        known_facts=_extract_known_facts(user_messages),
        relationship_state=_build_relationship_state(avatar, active_topics),
        active_topics=active_topics,
        last_updated=utc_now(),
    )
    session.updated_at = utc_now()
    return session


def _build_summary(user_messages: list[str], assistant_messages: list[str]) -> str:
    recent_user = [_truncate(message, 90) for message in user_messages[-2:] if _normalize_text(message)]
    if recent_user:
        prefix = "Current discussion" if len(recent_user) == 1 else "Recent discussion"
        return f"{prefix}: {'; '.join(recent_user)}"

    if assistant_messages:
        return f"Recent assistant guidance: {_truncate(assistant_messages[-1], 120)}"

    return ""


def _extract_known_facts(user_messages: list[str]) -> list[str]:
    facts: list[str] = []
    seen: set[str] = set()

    for message in user_messages:
        normalized = _normalize_text(message)
        if len(normalized) < 8 or len(normalized) > 180 or "?" in normalized:
            continue

        lowered = normalized.casefold()
        if not any(hint in lowered for hint in FACT_HINTS):
            continue

        if lowered in seen:
            continue

        seen.add(lowered)
        facts.append(_truncate(normalized, 120))

    return facts[-MAX_MEMORY_FACTS:]


def _extract_active_topics(user_messages: list[str]) -> list[str]:
    counts: Counter[str] = Counter()

    for message in user_messages[-6:]:
        for token in TOKEN_PATTERN.findall(message.casefold()):
            if token in TOPIC_STOPWORDS:
                continue
            counts[token] += 1

    topics = [token for token, _ in counts.most_common(MAX_ACTIVE_TOPICS)]
    return topics


def _build_relationship_state(avatar: AvatarProfile, active_topics: list[str]) -> str:
    tone = avatar.tone.rstrip(".")
    if active_topics:
        topic = active_topics[0].replace("_", " ")
        return f"{avatar.name} is helping with {topic} in a {tone.lower()} tone."
    return f"{avatar.name} is supporting the user in a {tone.lower()} tone."


