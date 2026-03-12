from __future__ import annotations

import asyncio
import json
import mimetypes
import random
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from app.config import Settings
from app.models import GeneratedAsset, GeneratorOutput, StylePreset


class ComfyUIClientError(RuntimeError):
    pass


class ComfyUIClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not self.settings.comfyui_base_url:
            raise ComfyUIClientError("COMFYUI_BASE_URL is required when GENERATION_BACKEND=comfyui.")

    async def generate(self, style: StylePreset, input_image: bytes, job_id: str, filename: str) -> GeneratorOutput:
        uploaded_filename = await self._upload_input_image(job_id, filename, input_image)
        prompt = self._build_prompt(style, uploaded_filename)
        prompt_id = await self._submit_prompt(prompt)
        history = await self._wait_for_history(prompt_id)
        images = await self._download_output_images(history)
        if not images:
            raise ComfyUIClientError("ComfyUI completed but returned no images.")
        return GeneratorOutput(prompt_id=prompt_id, assets=images[: style.output_count])

    async def _upload_input_image(self, job_id: str, filename: str, content: bytes) -> str:
        safe_name = f"{job_id}-{Path(filename).name or 'input.jpg'}"
        files = {"image": (safe_name, BytesIO(content), mimetypes.guess_type(safe_name)[0] or "image/jpeg")}
        data = {"type": "input", "overwrite": "true"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.settings.comfyui_base_url.rstrip('/')}/upload/image",
                files=files,
                data=data,
            )
            response.raise_for_status()
        return safe_name

    def _build_prompt(self, style: StylePreset, input_filename: str) -> dict[str, Any]:
        template_path = self.settings.comfyui_workflow_template
        if not template_path.exists():
            raise ComfyUIClientError(
                f"Workflow template was not found at {template_path}. Export an API workflow from ComfyUI first."
            )

        with template_path.open("r", encoding="utf-8") as handle:
            template = json.load(handle)

        placeholders = {
            "{{PROMPT}}": style.prompt_template,
            "{{NEGATIVE_PROMPT}}": style.negative_prompt,
            "{{INPUT_IMAGE}}": input_filename,
            "{{WIDTH}}": str(style.width),
            "{{HEIGHT}}": str(style.height),
            "{{OUTPUT_COUNT}}": str(style.output_count),
            "{{SEED}}": str(random.randint(1, 2_147_483_647)),
            "{{CLIENT_ID}}": self.settings.comfyui_client_id,
            "{{STYLE_NAME}}": style.name,
        }
        return self._replace_placeholders(deepcopy(template), placeholders)

    def _replace_placeholders(self, value: Any, placeholders: dict[str, str]) -> Any:
        if isinstance(value, str):
            rendered = value
            for placeholder, replacement in placeholders.items():
                rendered = rendered.replace(placeholder, replacement)
            if rendered.isdigit() and any(token in value for token in placeholders):
                return int(rendered)
            return rendered
        if isinstance(value, list):
            return [self._replace_placeholders(item, placeholders) for item in value]
        if isinstance(value, dict):
            return {key: self._replace_placeholders(item, placeholders) for key, item in value.items()}
        return value

    async def _submit_prompt(self, prompt: dict[str, Any]) -> str:
        payload = {"prompt": prompt, "client_id": self.settings.comfyui_client_id or str(uuid4())}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.settings.comfyui_base_url.rstrip('/')}/prompt", json=payload)
            response.raise_for_status()
        body = response.json()
        prompt_id = body.get("prompt_id")
        if not prompt_id:
            raise ComfyUIClientError("ComfyUI did not return a prompt_id.")
        return prompt_id

    async def _wait_for_history(self, prompt_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            while True:
                response = await client.get(f"{self.settings.comfyui_base_url.rstrip('/')}/history/{prompt_id}")
                response.raise_for_status()
                body = response.json()
                if body:
                    return body
                await asyncio.sleep(self.settings.comfyui_poll_seconds)

    async def _download_output_images(self, history: dict[str, Any]) -> list[GeneratedAsset]:
        prompt_data = next(iter(history.values()), {})
        outputs = prompt_data.get("outputs", {})
        image_specs: list[dict[str, Any]] = []
        for node_output in outputs.values():
            image_specs.extend(node_output.get("images", []))

        if not image_specs:
            return []

        assets: list[GeneratedAsset] = []
        async with httpx.AsyncClient(timeout=60) as client:
            for spec in image_specs:
                params = {
                    "filename": spec.get("filename"),
                    "subfolder": spec.get("subfolder", ""),
                    "type": spec.get("type", "output"),
                }
                response = await client.get(f"{self.settings.comfyui_base_url.rstrip('/')}/view", params=params)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "image/png")
                extension = mimetypes.guess_extension(content_type) or ".png"
                assets.append(
                    GeneratedAsset(
                        content=response.content,
                        content_type=content_type,
                        extension=extension,
                        seed=spec.get("seed"),
                        width=spec.get("width") or spec.get("image_width"),
                        height=spec.get("height") or spec.get("image_height"),
                    )
                )
        return assets
