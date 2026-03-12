from pathlib import Path

import yaml

from app.models import StyleCard, StylePreset


class StyleNotFoundError(FileNotFoundError):
    pass


def list_styles(style_dir: Path) -> list[StylePreset]:
    styles: list[StylePreset] = []
    if not style_dir.exists():
        return styles

    for path in sorted(style_dir.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            styles.append(StylePreset.model_validate(yaml.safe_load(handle)))
    return styles


def get_style(style_dir: Path, style_id: str) -> StylePreset:
    path = style_dir / f"{style_id}.yaml"
    if not path.exists():
        raise StyleNotFoundError(f"Style '{style_id}' was not found.")

    with path.open("r", encoding="utf-8") as handle:
        return StylePreset.model_validate(yaml.safe_load(handle))


def public_styles(style_dir: Path) -> list[StyleCard]:
    return [
        StyleCard(
            id=style.id,
            name=style.name,
            description=style.description,
            preview_image=style.preview_image,
            enabled=style.enabled,
            tags=style.tags,
        )
        for style in list_styles(style_dir)
        if style.enabled
    ]
