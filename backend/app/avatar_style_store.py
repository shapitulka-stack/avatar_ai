from pathlib import Path

import yaml

from app.image_models import AvatarStyle


class AvatarStyleNotFoundError(FileNotFoundError):
    pass


def _style_file(style_dir: Path, style_id: str) -> Path:
    return style_dir / f"{style_id}.yaml"


def list_avatar_styles(style_dir: Path) -> list[AvatarStyle]:
    styles: list[AvatarStyle] = []
    for path in sorted(style_dir.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            styles.append(AvatarStyle.model_validate(yaml.safe_load(handle)))
    return styles


def load_avatar_style(style_dir: Path, style_id: str) -> AvatarStyle:
    path = _style_file(style_dir, style_id)
    if not path.exists():
        raise AvatarStyleNotFoundError(f"Avatar style '{style_id}' was not found.")

    with path.open("r", encoding="utf-8") as handle:
        return AvatarStyle.model_validate(yaml.safe_load(handle))
