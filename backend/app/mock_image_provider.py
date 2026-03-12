from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from app.image_models import ProviderImageResult, ProviderRenderRequest


async def render_mock_images(
    request: ProviderRenderRequest,
) -> list[ProviderImageResult]:
    request.output_dir.mkdir(parents=True, exist_ok=True)
    results: list[ProviderImageResult] = []
    source = Image.open(request.source_image_path).convert("RGB")

    for index in range(request.variations):
        image = _render_variant(source, request, index)
        file_name = f"avatar-{index + 1:02d}.png"
        output_path = request.output_dir / file_name
        image.save(output_path, format="PNG")
        results.append(
            ProviderImageResult(
                file_name=file_name,
                relative_path=str(
                    Path("generated", request.job_id, file_name).as_posix(),
                ),
            ),
        )

    return results


def _render_variant(
    source: Image.Image,
    request: ProviderRenderRequest,
    index: int,
) -> Image.Image:
    canvas_size = (1024, 1024)
    base = ImageOps.fit(source, canvas_size, method=Image.Resampling.LANCZOS)
    blurred = base.filter(ImageFilter.GaussianBlur(radius=18))
    overlay = Image.new("RGBA", canvas_size, _overlay_rgba(request.style.accent_color, index))
    canvas = Image.alpha_composite(blurred.convert("RGBA"), overlay)

    portrait = ImageOps.fit(source, (640, 640), method=Image.Resampling.LANCZOS)
    portrait = portrait.filter(ImageFilter.GaussianBlur(radius=max(0, index - 1)))
    portrait = _rounded_card(portrait, radius=42)
    canvas.alpha_composite(portrait, (192, 152))

    band = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(band)
    draw.rounded_rectangle((120, 72, 904, 144), radius=24, fill=(15, 23, 42, 220))
    draw.rounded_rectangle((120, 840, 904, 952), radius=32, fill=(15, 23, 42, 200))
    draw.text((154, 95), request.style.name.upper(), fill=(248, 250, 252, 255))
    draw.text((154, 864), _subtitle(request, index), fill=(226, 232, 240, 255))
    draw.text((154, 905), f"Mock render {index + 1}/{request.variations}", fill=(148, 163, 184, 255))

    canvas = Image.alpha_composite(canvas, band)
    return canvas.convert("RGB")


def _rounded_card(portrait: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", portrait.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, portrait.width, portrait.height), radius=radius, fill=255)
    card = Image.new("RGBA", portrait.size, (255, 255, 255, 0))
    card.paste(portrait, (0, 0))
    card.putalpha(mask)
    return card


def _overlay_rgba(accent_color: str, index: int) -> tuple[int, int, int, int]:
    red, green, blue = _hex_to_rgb(accent_color)
    alpha = min(150 + index * 18, 210)
    return red, green, blue, alpha


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    normalized = value.lstrip("#")
    if len(normalized) != 6:
        return 51, 65, 85
    return tuple(int(normalized[i : i + 2], 16) for i in (0, 2, 4))


def _subtitle(request: ProviderRenderRequest, index: int) -> str:
    prompt = request.prompt.strip()
    if len(prompt) > 72:
        prompt = f"{prompt[:69]}..."
    return f"{prompt} | variation {index + 1}"
