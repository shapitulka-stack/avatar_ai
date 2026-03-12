from typing import Protocol

from app.config import Settings
from app.image_models import ProviderImageResult, ProviderRenderRequest


class ImageProviderError(RuntimeError):
    pass


class ImageProvider(Protocol):
    async def generate(
        self,
        request: ProviderRenderRequest,
    ) -> list[ProviderImageResult]:
        ...


class MockImageProvider:
    async def generate(
        self,
        request: ProviderRenderRequest,
    ) -> list[ProviderImageResult]:
        from app.mock_image_provider import render_mock_images

        return await render_mock_images(request)


class RemoteImageProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate(
        self,
        request: ProviderRenderRequest,
    ) -> list[ProviderImageResult]:
        from app.remote_image_provider import render_remote_images

        return await render_remote_images(self.settings, request)


def build_image_provider(settings: Settings) -> ImageProvider:
    provider_name = settings.image_provider.lower().strip()
    if provider_name == "mock":
        return MockImageProvider()
    if provider_name == "remote":
        return RemoteImageProvider(settings)

    raise ImageProviderError(
        f"Unsupported IMAGE_PROVIDER '{settings.image_provider}'. "
        "Use 'mock' or 'remote'."
    )
