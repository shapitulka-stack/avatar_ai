from __future__ import annotations

from telethon.tl.types import ChatAdminRights


def normalize_username(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("Username cannot be empty.")
    return candidate.lstrip("@")


def as_public_username(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    return normalize_username(candidate)


def as_entity_ref(value: str) -> str:
    username = normalize_username(value)
    return f"@{username}"


def channel_admin_rights() -> ChatAdminRights:
    return ChatAdminRights(
        change_info=True,
        post_messages=True,
        edit_messages=True,
        delete_messages=True,
        invite_users=True,
        pin_messages=True,
        manage_call=False,
        anonymous=False,
        add_admins=False,
        manage_topics=False,
        other=True,
    )
