from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field as PydanticField, model_validator
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


class AvatarProfile(BaseModel):
    id: str
    name: str
    role: str
    tone: str
    summary: str
    system_prompt: str
    memory: list[str] = PydanticField(default_factory=list)
    starter_messages: list[str] = PydanticField(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatMemoryState(BaseModel):
    summary: str = ""
    known_facts: list[str] = PydanticField(default_factory=list)
    relationship_state: str = ""
    active_topics: list[str] = PydanticField(default_factory=list)
    last_updated: datetime | None = None


class ChatSessionSnapshot(BaseModel):
    session_id: str
    avatar_id: str
    avatar_name: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessage] = PydanticField(default_factory=list)
    memory: ChatMemoryState = PydanticField(default_factory=ChatMemoryState)


class ChatRequest(BaseModel):
    avatar_id: str
    messages: list[ChatMessage] = PydanticField(default_factory=list)
    message: str | None = None
    session_id: str | None = None
    temperature: float = PydanticField(default=0.7, ge=0.0, le=2.0)
    history_limit: int = PydanticField(default=12, ge=1, le=24)

    @model_validator(mode="after")
    def validate_input(self) -> "ChatRequest":
        if not self.messages and not self.message:
            raise ValueError("Provide either 'message' or 'messages' for chat.")
        return self


class ChatResponse(BaseModel):
    avatar_id: str
    avatar_name: str
    reply: str
    session_id: str | None = None
    session: ChatSessionSnapshot | None = None


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class JobSource(str, Enum):
    web = "web"
    telegram_webapp = "telegram_webapp"


class QueueTier(str, Enum):
    free = "free"
    premium = "premium"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StylePreset(BaseModel):
    id: str
    name: str
    description: str
    prompt_template: str
    negative_prompt: str = ""
    preview_image: str
    enabled: bool = True
    width: int = 1024
    height: int = 1024
    output_count: int = 4
    tags: list[str] = PydanticField(default_factory=list)


class StyleCard(BaseModel):
    id: str
    name: str
    description: str
    preview_image: str
    enabled: bool
    tags: list[str]


class FaceProfile(SQLModel, table=True):
    id: str = SQLField(default_factory=lambda: str(uuid4()), primary_key=True)
    guest_session_id: str | None = SQLField(default=None, index=True)
    telegram_user_id: int | None = SQLField(default=None, index=True)
    label: str
    image_key: str
    preview_key: str | None = None
    created_at: datetime = SQLField(default_factory=utc_now, index=True)
    updated_at: datetime = SQLField(default_factory=utc_now)


class FaceProfileResponse(BaseModel):
    id: str
    label: str
    image_url: str
    preview_url: str | None = None
    created_at: datetime
    updated_at: datetime


class FaceProfileListResponse(BaseModel):
    items: list[FaceProfileResponse]


class GenerationJob(SQLModel, table=True):
    id: str = SQLField(default_factory=lambda: str(uuid4()), primary_key=True)
    status: str = SQLField(default=JobStatus.queued.value, index=True)
    source: str = SQLField(index=True)
    guest_session_id: str | None = SQLField(default=None, index=True)
    telegram_user_id: int | None = SQLField(default=None, index=True)
    style_id: str = SQLField(index=True)
    input_image_key: str
    input_preview_key: str | None = None
    error_message: str | None = SQLField(default=None)
    comfy_prompt_id: str | None = SQLField(default=None)
    created_at: datetime = SQLField(default_factory=utc_now, index=True)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class GenerationResult(SQLModel, table=True):
    id: int | None = SQLField(default=None, primary_key=True)
    job_id: str = SQLField(foreign_key="generationjob.id", index=True)
    image_index: int = SQLField(default=0, index=True)
    image_key: str
    thumb_key: str
    seed: int | None = None
    width: int | None = None
    height: int | None = None
    created_at: datetime = SQLField(default_factory=utc_now)


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    poll_url: str
    result_url: str
    guest_session_id: str | None = None
    queue_tier: QueueTier = QueueTier.free
    queue_position: int | None = None
    jobs_ahead: int = 0
    estimated_wait_seconds: int = 0
    user_pending_jobs: int = 0
    max_pending_per_user: int = 0


class ResultAssetResponse(BaseModel):
    index: int
    image_url: str
    thumb_url: str
    seed: int | None = None
    width: int | None = None
    height: int | None = None


class JobDetailResponse(BaseModel):
    job_id: str
    status: JobStatus
    source: JobSource
    style_id: str
    guest_session_id: str | None = None
    telegram_user_id: int | None = None
    input_image_url: str
    input_preview_url: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    queue_tier: QueueTier = QueueTier.free
    queue_position: int | None = None
    jobs_ahead: int = 0
    estimated_wait_seconds: int = 0
    user_pending_jobs: int = 0
    max_pending_per_user: int = 0
    results: list[ResultAssetResponse] = PydanticField(default_factory=list)


class JobResultsResponse(BaseModel):
    job_id: str
    status: JobStatus
    items: list[ResultAssetResponse]


class JobListResponse(BaseModel):
    items: list[JobDetailResponse]


class GeneratedAsset(BaseModel):
    content: bytes
    content_type: str
    extension: str
    seed: int | None = None
    width: int | None = None
    height: int | None = None


class GeneratorOutput(BaseModel):
    prompt_id: str | None = None
    assets: list[GeneratedAsset]
