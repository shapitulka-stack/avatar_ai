import httpx
from fastapi import HTTPException

from app.config import Settings
from app.models import AvatarProfile, ChatMemoryState, ChatMessage


def _system_message(avatar: AvatarProfile, session_memory: ChatMemoryState | None = None) -> str:
    sections = [avatar.system_prompt.strip()]

    if avatar.summary:
        sections.append(f"Avatar summary:\n{avatar.summary.strip()}")

    if avatar.memory:
        base_memory = "\n".join(f"- {item}" for item in avatar.memory)
        sections.append(f"Avatar memory:\n{base_memory}")

    if session_memory:
        if session_memory.summary:
            sections.append(f"Session summary:\n{session_memory.summary.strip()}")
        if session_memory.known_facts:
            facts = "\n".join(f"- {item}" for item in session_memory.known_facts)
            sections.append(f"Known user/context facts:\n{facts}")
        if session_memory.relationship_state:
            sections.append(f"Relationship state:\n{session_memory.relationship_state.strip()}")
        if session_memory.active_topics:
            sections.append(f"Active topics:\n{', '.join(session_memory.active_topics)}")

    return "\n\n".join(section for section in sections if section)


async def generate_reply(
    settings: Settings,
    avatar: AvatarProfile,
    messages: list[ChatMessage],
    temperature: float,
    session_memory: ChatMemoryState | None = None,
) -> str:
    payload = {
        "model": settings.llm_model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": _system_message(avatar, session_memory)},
            *[message.model_dump() for message in messages],
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    endpoint = f"{settings.llm_base_url.rstrip('/')}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider returned {exc.response.status_code}.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not reach the configured LLM provider.",
        ) from exc

    body = response.json()
    try:
        return body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="LLM provider returned an unexpected response format.",
        ) from exc
