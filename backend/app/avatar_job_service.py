from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from app.avatar_job_store import AvatarJobStore
from app.avatar_style_store import AvatarStyleNotFoundError, load_avatar_style, list_avatar_styles
from app.config import Settings
from app.image_models import (
    AvatarJob,
    AvatarJobImage,
    AvatarStyle,
    AvatarStyleSummary,
    ProviderRenderRequest,
    StoredAvatarJob,
)
from app.image_provider import ImageProviderError, build_image_provider


class AvatarJobService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = AvatarJobStore(settings.job_db_path)

    def list_styles(self) -> list[AvatarStyleSummary]:
        styles = list_avatar_styles(self.settings.avatar_style_dir)
        return [
            AvatarStyleSummary(
                id=style.id,
                name=style.name,
                summary=style.summary,
                accent_color=style.accent_color,
                tags=style.tags,
                sample_caption=style.sample_caption,
            )
            for style in styles
        ]

    def list_jobs(self, limit: int = 20) -> list[AvatarJob]:
        return [self._to_public_job(job) for job in self.store.list_jobs(limit)]

    def get_job(self, job_id: str) -> AvatarJob:
        job = self.store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Avatar job '{job_id}' was not found.")
        return self._to_public_job(job)

    async def create_job(
        self,
        *,
        style_id: str,
        source_file_name: str,
        source_bytes: bytes,
        prompt_override: str | None,
        variations: int,
        requester_channel: str,
        requester_id: str | None,
    ) -> AvatarJob:
        if not source_bytes:
            raise HTTPException(status_code=400, detail="Upload an image before creating a job.")

        if len(source_bytes) > self.settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"Uploads are limited to {self.settings.max_upload_size_mb} MB.",
            )

        if variations < 1 or variations > 6:
            raise HTTPException(status_code=400, detail="Variations must be between 1 and 6.")

        try:
            style = load_avatar_style(self.settings.avatar_style_dir, style_id)
        except AvatarStyleNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        job_id = str(uuid4())
        extension = self._file_extension(source_file_name)
        relative_source_path = Path("uploads", job_id, f"source{extension}")
        source_path = self.settings.runtime_dir / relative_source_path
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(source_bytes)

        prompt_override = self._clean_text(prompt_override)
        resolved_prompt = self._compose_prompt(style, prompt_override)
        timestamp = self._timestamp()
        job = StoredAvatarJob(
            id=job_id,
            style_id=style.id,
            prompt_override=prompt_override,
            resolved_prompt=resolved_prompt,
            negative_prompt=style.negative_prompt,
            variations=variations,
            status="queued",
            source_image_path=relative_source_path.as_posix(),
            requester_channel=requester_channel,
            requester_id=requester_id,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.store.create_job(job)
        return self._to_public_job(job, style)

    async def process_job(self, job_id: str) -> None:
        stored_job = self.store.get_job(job_id)
        if stored_job is None:
            return

        try:
            style = load_avatar_style(self.settings.avatar_style_dir, stored_job.style_id)
        except AvatarStyleNotFoundError:
            self.store.update_status(
                job_id=job_id,
                status="failed",
                updated_at=self._timestamp(),
                error_message=f"Style '{stored_job.style_id}' is no longer available.",
            )
            return

        self.store.update_status(
            job_id=job_id,
            status="running",
            updated_at=self._timestamp(),
        )

        provider = build_image_provider(self.settings)
        source_path = self.settings.runtime_dir / stored_job.source_image_path
        output_dir = self.settings.generated_dir / stored_job.id
        request = ProviderRenderRequest(
            job_id=stored_job.id,
            style=style,
            prompt=stored_job.resolved_prompt,
            negative_prompt=stored_job.negative_prompt,
            source_image_path=source_path,
            output_dir=output_dir,
            variations=stored_job.variations,
        )

        try:
            results = await provider.generate(request)
        except ImageProviderError as exc:
            self.store.update_status(
                job_id=job_id,
                status="failed",
                updated_at=self._timestamp(),
                error_message=str(exc),
            )
            return
        except Exception as exc:  # pragma: no cover
            self.store.update_status(
                job_id=job_id,
                status="failed",
                updated_at=self._timestamp(),
                error_message=f"Unexpected render error: {exc}",
            )
            return

        self.store.replace_results(
            job_id=job_id,
            images=results,
            updated_at=self._timestamp(),
        )
        self.store.update_status(
            job_id=job_id,
            status="completed",
            updated_at=self._timestamp(),
        )

    def _to_public_job(
        self,
        job: StoredAvatarJob,
        style: AvatarStyle | None = None,
    ) -> AvatarJob:
        resolved_style = style or load_avatar_style(self.settings.avatar_style_dir, job.style_id)
        return AvatarJob(
            id=job.id,
            style_id=job.style_id,
            style_name=resolved_style.name,
            prompt_override=job.prompt_override,
            resolved_prompt=job.resolved_prompt,
            negative_prompt=job.negative_prompt,
            variations=job.variations,
            status=job.status,
            source_image_url=self._media_url(job.source_image_path),
            requester_channel=job.requester_channel,
            requester_id=job.requester_id,
            created_at=job.created_at,
            updated_at=job.updated_at,
            error_message=job.error_message,
            images=[
                AvatarJobImage(
                    file_name=image.file_name,
                    url=self._media_url(image.relative_path),
                )
                for image in job.images
            ],
        )

    def _compose_prompt(self, style: AvatarStyle, prompt_override: str | None) -> str:
        parts = [style.base_prompt.strip()]
        if prompt_override:
            parts.append(prompt_override.strip())
        return ", ".join(part for part in parts if part)

    def _media_url(self, relative_path: str) -> str:
        return f"/media/{relative_path.lstrip('/')}"

    def _file_extension(self, file_name: str) -> str:
        suffix = Path(file_name or "upload.jpg").suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            return suffix
        return ".jpg"

    def _clean_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()
