from pydantic import BaseModel, Field


class IntegrationStatus(BaseModel):
    name: str
    configured: bool
    reachable: bool | None = None
    detail: str
    metadata: dict[str, str] = Field(default_factory=dict)
