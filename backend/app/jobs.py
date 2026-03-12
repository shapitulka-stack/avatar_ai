from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlmodel import Session, select

from app.config import Settings
from app.image_utils import create_thumbnail, normalize_extension
from app.models import (
    GenerationJob,
    GenerationResult,
    JobCreateResponse,
    JobDetailResponse,
    JobResultsResponse,
    JobSource,
    JobStatus,
    QueueTier,
    ResultAssetResponse,
    StylePreset,
)
from app.storage import StorageError, get_storage


class JobValidationError(ValueError):
    pass


PENDING_JOB_STATUSES = (JobStatus.queued.value, JobStatus.running.value)


@dataclass(frozen=True)
class QueueSnapshot:
    positions: dict[str, int]
    pending_total: int
    pending_by_guest: dict[str, int]
    pending_by_telegram: dict[int, int]


@dataclass(frozen=True)
class QueueMetadata:
    queue_tier: QueueTier
    queue_position: int | None
    jobs_ahead: int
    estimated_wait_seconds: int
    user_pending_jobs: int
    max_pending_per_user: int


def ensure_image_upload(photo: UploadFile, content: bytes, settings: Settings) -> str:
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise JobValidationError("Only image uploads are supported.")
    if len(content) > settings.max_upload_bytes:
        raise JobValidationError(f"Image is too large. Max size is {settings.max_upload_bytes} bytes.")
    return normalize_extension(photo.filename, photo.content_type)


def ensure_identity(source: JobSource, guest_session_id: str | None, telegram_user_id: int | None) -> tuple[str | None, int | None]:
    if source == JobSource.telegram_webapp and not telegram_user_id:
        raise JobValidationError("Telegram jobs require validated Telegram init data.")
    if source == JobSource.web and not guest_session_id:
        guest_session_id = str(uuid4())
    return guest_session_id, telegram_user_id


def list_pending_jobs(session: Session) -> list[GenerationJob]:
    statement = (
        select(GenerationJob)
        .where(GenerationJob.status.in_(PENDING_JOB_STATUSES))
        .order_by(GenerationJob.created_at.asc())
    )
    return list(session.exec(statement))


def build_queue_snapshot(session: Session) -> QueueSnapshot:
    positions: dict[str, int] = {}
    pending_by_guest: dict[str, int] = {}
    pending_by_telegram: dict[int, int] = {}
    pending_jobs = list_pending_jobs(session)

    for index, pending_job in enumerate(pending_jobs, start=1):
        positions[pending_job.id] = index
        if pending_job.guest_session_id:
            pending_by_guest[pending_job.guest_session_id] = pending_by_guest.get(pending_job.guest_session_id, 0) + 1
        if pending_job.telegram_user_id is not None:
            pending_by_telegram[pending_job.telegram_user_id] = pending_by_telegram.get(pending_job.telegram_user_id, 0) + 1

    return QueueSnapshot(
        positions=positions,
        pending_total=len(pending_jobs),
        pending_by_guest=pending_by_guest,
        pending_by_telegram=pending_by_telegram,
    )


def pending_jobs_for_identity(
    queue_snapshot: QueueSnapshot,
    guest_session_id: str | None,
    telegram_user_id: int | None,
) -> int:
    if telegram_user_id is not None:
        return queue_snapshot.pending_by_telegram.get(telegram_user_id, 0)
    if guest_session_id:
        return queue_snapshot.pending_by_guest.get(guest_session_id, 0)
    return 0


def build_queue_metadata(settings: Settings, queue_snapshot: QueueSnapshot, job: GenerationJob) -> QueueMetadata:
    queue_position = queue_snapshot.positions.get(job.id)
    jobs_ahead = queue_position - 1 if queue_position is not None else 0
    estimated_wait_seconds = jobs_ahead * settings.queue_estimated_seconds_per_job if queue_position is not None else 0
    user_pending_jobs = pending_jobs_for_identity(queue_snapshot, job.guest_session_id, job.telegram_user_id)

    return QueueMetadata(
        queue_tier=QueueTier.free,
        queue_position=queue_position,
        jobs_ahead=jobs_ahead,
        estimated_wait_seconds=estimated_wait_seconds,
        user_pending_jobs=user_pending_jobs,
        max_pending_per_user=settings.queue_max_pending_per_user,
    )


def validate_queue_capacity(
    settings: Settings,
    queue_snapshot: QueueSnapshot,
    guest_session_id: str | None,
    telegram_user_id: int | None,
) -> None:
    user_pending_jobs = pending_jobs_for_identity(queue_snapshot, guest_session_id, telegram_user_id)
    if user_pending_jobs >= settings.queue_max_pending_per_user:
        raise JobValidationError(
            f"You already have {settings.queue_max_pending_per_user} active jobs in the free queue. Wait for one to finish before creating another."
        )

    if queue_snapshot.pending_total >= settings.queue_max_pending_total:
        raise JobValidationError("The free queue is full right now. Please try again in a few minutes.")


def create_job(
    session: Session,
    settings: Settings,
    photo: UploadFile,
    content: bytes,
    source: JobSource,
    style: StylePreset,
    guest_session_id: str | None,
    telegram_user_id: int | None,
) -> JobCreateResponse:
    extension = ensure_image_upload(photo, content, settings)
    guest_session_id, telegram_user_id = ensure_identity(source, guest_session_id, telegram_user_id)
    validate_queue_capacity(settings, build_queue_snapshot(session), guest_session_id, telegram_user_id)
    storage = get_storage(settings)
    job_id = str(uuid4())
    input_key = f"uploads/{job_id}/input{extension}"
    preview_key = f"uploads/{job_id}/preview.webp"

    try:
        storage.save_bytes(input_key, content, photo.content_type)
        storage.save_bytes(preview_key, create_thumbnail(content), "image/webp")
    except StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    job = GenerationJob(
        id=job_id,
        source=source.value,
        guest_session_id=guest_session_id,
        telegram_user_id=telegram_user_id,
        style_id=style.id,
        input_image_key=input_key,
        input_preview_key=preview_key,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    queue_metadata = build_queue_metadata(settings, build_queue_snapshot(session), job)

    return JobCreateResponse(
        job_id=job.id,
        status=JobStatus(job.status),
        poll_url=f"/api/jobs/{job.id}",
        result_url=f"/api/jobs/{job.id}/results",
        guest_session_id=guest_session_id,
        queue_tier=queue_metadata.queue_tier,
        queue_position=queue_metadata.queue_position,
        jobs_ahead=queue_metadata.jobs_ahead,
        estimated_wait_seconds=queue_metadata.estimated_wait_seconds,
        user_pending_jobs=queue_metadata.user_pending_jobs,
        max_pending_per_user=queue_metadata.max_pending_per_user,
    )


def get_job_or_404(session: Session, job_id: str) -> GenerationJob:
    job = session.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' was not found.")
    return job


def get_job_results(session: Session, job_id: str) -> list[GenerationResult]:
    statement = (
        select(GenerationResult)
        .where(GenerationResult.job_id == job_id)
        .order_by(GenerationResult.image_index.asc())
    )
    return list(session.exec(statement))


def build_file_url(key: str) -> str:
    return f"/api/files/{quote(key, safe='/')}"


def serialize_results(results: list[GenerationResult]) -> list[ResultAssetResponse]:
    return [
        ResultAssetResponse(
            index=result.image_index,
            image_url=build_file_url(result.image_key),
            thumb_url=build_file_url(result.thumb_key),
            seed=result.seed,
            width=result.width,
            height=result.height,
        )
        for result in results
    ]


def serialize_job(
    session: Session,
    settings: Settings,
    job: GenerationJob,
    queue_snapshot: QueueSnapshot | None = None,
) -> JobDetailResponse:
    results = get_job_results(session, job.id)
    snapshot = queue_snapshot or build_queue_snapshot(session)
    queue_metadata = build_queue_metadata(settings, snapshot, job)
    return JobDetailResponse(
        job_id=job.id,
        status=JobStatus(job.status),
        source=JobSource(job.source),
        style_id=job.style_id,
        guest_session_id=job.guest_session_id,
        telegram_user_id=job.telegram_user_id,
        input_image_url=build_file_url(job.input_image_key),
        input_preview_url=build_file_url(job.input_preview_key) if job.input_preview_key else None,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        queue_tier=queue_metadata.queue_tier,
        queue_position=queue_metadata.queue_position,
        jobs_ahead=queue_metadata.jobs_ahead,
        estimated_wait_seconds=queue_metadata.estimated_wait_seconds,
        user_pending_jobs=queue_metadata.user_pending_jobs,
        max_pending_per_user=queue_metadata.max_pending_per_user,
        results=serialize_results(results),
    )


def list_jobs_for_identity(
    session: Session,
    settings: Settings,
    guest_session_id: str | None = None,
    telegram_user_id: int | None = None,
) -> list[JobDetailResponse]:
    if telegram_user_id is not None:
        statement = select(GenerationJob).where(GenerationJob.telegram_user_id == telegram_user_id)
    elif guest_session_id:
        statement = select(GenerationJob).where(GenerationJob.guest_session_id == guest_session_id)
    else:
        raise HTTPException(status_code=400, detail="Provide a guest_session_id or valid Telegram init data.")

    statement = statement.order_by(GenerationJob.created_at.desc())
    jobs = list(session.exec(statement))
    queue_snapshot = build_queue_snapshot(session)
    return [serialize_job(session, settings, job, queue_snapshot) for job in jobs]


def serialize_job_results(session: Session, job: GenerationJob) -> JobResultsResponse:
    return JobResultsResponse(
        job_id=job.id,
        status=JobStatus(job.status),
        items=serialize_results(get_job_results(session, job.id)),
    )


def count_running_jobs(session: Session) -> int:
    statement = select(GenerationJob).where(GenerationJob.status == JobStatus.running.value)
    return len(list(session.exec(statement)))


def claim_next_queued_job(session: Session, settings: Settings) -> GenerationJob | None:
    if count_running_jobs(session) >= settings.queue_max_concurrent_jobs:
        return None

    statement = (
        select(GenerationJob)
        .where(GenerationJob.status == JobStatus.queued.value)
        .order_by(GenerationJob.created_at.asc())
    )
    job = session.exec(statement).first()
    if not job:
        return None
    job.status = JobStatus.running.value
    job.started_at = datetime.now(timezone.utc)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def store_job_results(
    session: Session,
    settings: Settings,
    job: GenerationJob,
    assets: list[Any],
    prompt_id: str | None,
) -> GenerationJob:
    storage = get_storage(settings)
    for index, asset in enumerate(assets):
        image_key = f"results/{job.id}/{index}{asset.extension}"
        thumb_key = f"thumbs/{job.id}/{index}.webp"
        storage.save_bytes(image_key, asset.content, asset.content_type)
        storage.save_bytes(thumb_key, create_thumbnail(asset.content), "image/webp")
        session.add(
            GenerationResult(
                job_id=job.id,
                image_index=index,
                image_key=image_key,
                thumb_key=thumb_key,
                seed=asset.seed,
                width=asset.width,
                height=asset.height,
            )
        )

    job.status = JobStatus.succeeded.value
    job.finished_at = datetime.now(timezone.utc)
    job.comfy_prompt_id = prompt_id
    job.error_message = None
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def fail_job(session: Session, job: GenerationJob, message: str) -> None:
    job.status = JobStatus.failed.value
    job.finished_at = datetime.now(timezone.utc)
    job.error_message = message
    session.add(job)
    session.commit()


def input_filename_for_job(job: GenerationJob) -> str:
    return Path(job.input_image_key).name
