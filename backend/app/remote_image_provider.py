import base64
import mimetypes
from pathlib import Path

import httpx

from app.config import Settings
from app.image_models import ProviderImageResult, ProviderRenderRequest
from app.image_provider import ImageProviderError


async def render_remote_images(
    settings: Settings,
    request: ProviderRenderRequest,
) -> list[ProviderImageResult]:
    if not settings.gpu_api_base_url:
        raise ImageProviderError(
            "GPU_API_BASE_URL must be configured when IMAGE_PROVIDER=remote.",
        )

    request.output_dir.mkdir(parents=True, exist_ok=True)
    endpoint = f"{settings.gpu_api_base_url.rstrip('/')}{settings.remote_image_generate_path}"
    headers = {}
    if settings.gpu_api_key:
        headers["Authorization"] = f"Bearer {settings.gpu_api_key}"

    source_bytes = request.source_image_path.read_bytes()
    files = {
        "reference_image": (
            request.source_image_path.name,
            source_bytes,
            mimetypes.guess_type(request.source_image_path.name)[0] or "application/octet-stream",
        ),
    }
    data = {
        "job_id": request.job_id,
        "style_id": request.style.id,
        "style_name": request.style.name,
        "prompt": request.prompt,
        "negative_prompt": request.negative_prompt,
        "variations": str(request.variations),
    }

    try:
        async with httpx.AsyncClient(timeout=settings.image_generation_timeout_seconds) as client:
            response = await client.post(endpoint, data=data, files=files, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ImageProviderError(
            f"Remote image provider returned {exc.response.status_code}.",
        ) from exc
    except httpx.HTTPError as exc:
        raise ImageProviderError("Could not reach the configured remote image provider.") from exc

    body = response.json()
    images = body.get("images")
    if not isinstance(images, list) or not images:
        raise ImageProviderError("Remote image provider returned no images.")

    results: list[ProviderImageResult] = []
    for index, image in enumerate(images, start=1):
        file_name = image.get("file_name") or f"avatar-{index:02d}.png"
        encoded = image.get("base64_data")
        if not isinstance(encoded, str):
            raise ImageProviderError("Remote image provider returned an invalid image payload.")

        output_path = request.output_dir / file_name
        output_path.write_bytes(base64.b64decode(encoded))
        results.append(
            ProviderImageResult(
                file_name=file_name,
                relative_path=str(
                    Path("generated", request.job_id, file_name).as_posix(),
                ),
            ),
        )

    return results
