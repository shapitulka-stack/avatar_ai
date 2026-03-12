from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlmodel import Session, select

from app.image_utils import create_thumbnail, normalize_extension
from app.models import FaceProfile, FaceProfileResponse
from app.storage import StorageError, get_storage


class FaceProfileValidationError(ValueError):
    pass


def ensure_face_upload(photo: UploadFile, content: bytes, max_upload_bytes: int) -> str:
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise FaceProfileValidationError("Only image uploads are supported for face profiles.")
    if len(content) > max_upload_bytes:
        raise FaceProfileValidationError(f"Image is too large. Max size is {max_upload_bytes} bytes.")
    return normalize_extension(photo.filename, photo.content_type)


def _owner_prefix(guest_session_id: str | None, telegram_user_id: int | None) -> str:
    if telegram_user_id is not None:
        return f"tg-{telegram_user_id}"
    if guest_session_id:
        return guest_session_id
    raise FaceProfileValidationError("Face profiles require a guest_session_id or a Telegram user.")


def list_face_profiles(
    session: Session,
    guest_session_id: str | None,
    telegram_user_id: int | None,
) -> list[FaceProfile]:
    if telegram_user_id is not None:
        statement = select(FaceProfile).where(FaceProfile.telegram_user_id == telegram_user_id)
    elif guest_session_id:
        statement = select(FaceProfile).where(FaceProfile.guest_session_id == guest_session_id)
    else:
        raise HTTPException(status_code=400, detail="Provide a guest_session_id or valid Telegram init data.")

    statement = statement.order_by(FaceProfile.created_at.desc())
    return list(session.exec(statement))


def get_face_profile_or_404(
    session: Session,
    profile_id: str,
    guest_session_id: str | None,
    telegram_user_id: int | None,
) -> FaceProfile:
    profile = session.get(FaceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Face profile '{profile_id}' was not found.")

    if telegram_user_id is not None and profile.telegram_user_id == telegram_user_id:
        return profile
    if guest_session_id and profile.guest_session_id == guest_session_id:
        return profile

    raise HTTPException(status_code=404, detail=f"Face profile '{profile_id}' was not found.")


def create_face_profile(
    session: Session,
    settings,
    photo: UploadFile,
    content: bytes,
    label: str,
    guest_session_id: str | None,
    telegram_user_id: int | None,
) -> FaceProfile:
    extension = ensure_face_upload(photo, content, settings.max_upload_bytes)
    storage = get_storage(settings)
    profile_id = str(uuid4())
    owner_prefix = _owner_prefix(guest_session_id, telegram_user_id)
    image_key = f"face-profiles/{owner_prefix}/{profile_id}/face{extension}"
    preview_key = f"face-profiles/{owner_prefix}/{profile_id}/preview.webp"
    now = datetime.now(timezone.utc)

    try:
        storage.save_bytes(image_key, content, photo.content_type)
        storage.save_bytes(preview_key, create_thumbnail(content), "image/webp")
    except StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    profile = FaceProfile(
        id=profile_id,
        guest_session_id=guest_session_id,
        telegram_user_id=telegram_user_id,
        label=label.strip() or "My face",
        image_key=image_key,
        preview_key=preview_key,
        created_at=now,
        updated_at=now,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def build_face_profile_response(profile: FaceProfile) -> FaceProfileResponse:
    return FaceProfileResponse(
        id=profile.id,
        label=profile.label,
        image_url=f"/api/files/{profile.image_key}",
        preview_url=f"/api/files/{profile.preview_key}" if profile.preview_key else None,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
