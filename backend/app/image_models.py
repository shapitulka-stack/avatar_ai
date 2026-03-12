from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


AvatarJobStatus = Literal["queued", "running", "completed", "failed"]


class AvatarStyle(BaseModel):
    id: str
    name: str
    summary: str
    base_prompt: str
    negative_prompt: str = ""
    accent_color: str = "#334155"
    tags: list[str] = Field(default_factory=list)
    sample_caption: str | None = None


class AvatarStyleSummary(BaseModel):
    id: str
    name: str
    summary: str
    accent_color: str
    tags: list[str] = Field(default_factory=list)
    sample_caption: str | None = None


class StoredAvatarJobImage(BaseModel):
    file_name: str
    relative_path: str


class StoredAvatarJob(BaseModel):
    id: str
    style_id: str
    prompt_override: str | None = None
    resolved_prompt: str
    negative_prompt: str
    variations: int
    status: AvatarJobStatus
    source_image_path: str
    requester_channel: str
    requester_id: str | None = None
    created_at: str
    updated_at: str
    error_message: str | None = None
    images: list[StoredAvatarJobImage] = Field(default_factory=list)


class AvatarJobImage(BaseModel):
    file_name: str
    url: str


class AvatarJob(BaseModel):
    id: str
    style_id: str
    style_name: str
    prompt_override: str | None = None
    resolved_prompt: str
    negative_prompt: str
    variations: int
    status: AvatarJobStatus
    source_image_url: str
    requester_channel: str
    requester_id: str | None = None
    created_at: str
    updated_at: str
    error_message: str | None = None
    images: list[AvatarJobImage] = Field(default_factory=list)


class ProviderRenderRequest(BaseModel):
    job_id: str
    style: AvatarStyle
    prompt: str
    negative_prompt: str
    source_image_path: Path
    output_dir: Path
    variations: int

    model_config = {"arbitrary_types_allowed": True}


class ProviderImageResult(BaseModel):
    file_name: str
    relative_path: str
