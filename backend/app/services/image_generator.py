from __future__ import annotations

import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageOps

from app.comfy_client import ComfyUIClient
from app.config import Settings
from app.models import GeneratedAsset, GeneratorOutput, StylePreset


class AvatarGeneratorError(RuntimeError):
    pass


class MockAvatarGenerator:
    async def generate(self, style: StylePreset, input_image: bytes, job_id: str) -> GeneratorOutput:
        assets: list[GeneratedAsset] = []
        seeds = [random.randint(100000, 999999) for _ in range(style.output_count)]

        with Image.open(BytesIO(input_image)) as original:
            base = ImageOps.fit(original.convert("RGB"), (style.width, style.height))
            for index, seed in enumerate(seeds, start=1):
                framed = base.copy()
                overlay = Image.new("RGBA", framed.size, (18 + index * 12, 48 + index * 10, 94 + index * 8, 72))
                composed = Image.alpha_composite(framed.convert("RGBA"), overlay)
                drawer = ImageDraw.Draw(composed)
                drawer.rounded_rectangle((32, style.height - 220, style.width - 32, style.height - 32), radius=28, fill=(12, 16, 24, 190))
                drawer.text((64, style.height - 188), style.name, fill=(255, 255, 255, 255))
                drawer.text((64, style.height - 128), f"variant {index}", fill=(217, 231, 255, 255))
                drawer.text((64, style.height - 76), f"seed {seed}", fill=(171, 196, 230, 255))
                buffer = BytesIO()
                composed.convert("RGB").save(buffer, format="PNG")
                assets.append(
                    GeneratedAsset(
                        content=buffer.getvalue(),
                        content_type="image/png",
                        extension=".png",
                        seed=seed,
                        width=style.width,
                        height=style.height,
                    )
                )

        return GeneratorOutput(prompt_id=f"mock-{job_id}", assets=assets)


class AvatarGenerator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate(self, style: StylePreset, input_image: bytes, job_id: str, filename: str) -> GeneratorOutput:
        backend = self.settings.generation_backend.lower()
        if backend == "mock":
            return await MockAvatarGenerator().generate(style, input_image, job_id)
        if backend == "comfyui":
            client = ComfyUIClient(self.settings)
            return await client.generate(style, input_image, job_id, filename)
        raise AvatarGeneratorError(f"Unsupported generation backend: {self.settings.generation_backend}")
