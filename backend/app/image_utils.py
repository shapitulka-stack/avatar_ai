from io import BytesIO
from pathlib import Path

from PIL import Image


def create_thumbnail(content: bytes, size: tuple[int, int] = (512, 512), image_format: str = "WEBP") -> bytes:
    with Image.open(BytesIO(content)) as image:
        converted = image.convert("RGB")
        converted.thumbnail(size)
        buffer = BytesIO()
        converted.save(buffer, format=image_format, quality=88)
        return buffer.getvalue()


def normalize_extension(filename: str | None, content_type: str | None) -> str:
    suffix = Path(filename or "upload.jpg").suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix

    if content_type == "image/png":
        return ".png"
    if content_type == "image/webp":
        return ".webp"
    return ".jpg"
