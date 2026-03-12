import httpx

from app.config import Settings
from app.integrations.models import IntegrationStatus


class ServerService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def status(self) -> list[IntegrationStatus]:
        statuses = [await self._gpu_api_status(), self._gpu_ssh_status()]
        return statuses

    async def _gpu_api_status(self) -> IntegrationStatus:
        base_url = self.settings.gpu_api_base_url or self.settings.comfyui_base_url
        if not base_url:
            return IntegrationStatus(
                name="gpu_worker_api",
                configured=False,
                detail="Add GPU_API_BASE_URL or COMFYUI_BASE_URL to probe the image worker API.",
            )

        health_url = f"{base_url.rstrip('/')}{self.settings.gpu_health_path}"
        headers = {}
        if self.settings.gpu_api_key:
            headers["Authorization"] = f"Bearer {self.settings.gpu_api_key}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(health_url, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return IntegrationStatus(
                name="gpu_worker_api",
                configured=True,
                reachable=False,
                detail="GPU worker API is configured but could not be reached.",
                metadata={"error": str(exc), "health_url": health_url},
            )

        return IntegrationStatus(
            name="gpu_worker_api",
            configured=True,
            reachable=True,
            detail="GPU worker API is reachable.",
            metadata={"health_url": health_url},
        )

    def _gpu_ssh_status(self) -> IntegrationStatus:
        if not (self.settings.gpu_ssh_host and self.settings.gpu_ssh_user):
            return IntegrationStatus(
                name="gpu_worker_ssh",
                configured=False,
                detail="Add GPU_SSH_HOST and GPU_SSH_USER to track SSH access.",
            )

        return IntegrationStatus(
            name="gpu_worker_ssh",
            configured=True,
            detail="SSH coordinates are configured.",
            metadata={
                "host": self.settings.gpu_ssh_host,
                "user": self.settings.gpu_ssh_user,
                "port": str(self.settings.gpu_ssh_port),
            },
        )
