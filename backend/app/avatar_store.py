from pathlib import Path

import yaml

from app.models import AvatarProfile


class AvatarNotFoundError(FileNotFoundError):
    pass


def _avatar_file(avatar_dir: Path, avatar_id: str) -> Path:
    return avatar_dir / f"{avatar_id}.yaml"


def list_avatars(avatar_dir: Path) -> list[AvatarProfile]:
    avatars: list[AvatarProfile] = []
    for path in sorted(avatar_dir.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            avatars.append(AvatarProfile.model_validate(yaml.safe_load(handle)))
    return avatars


def load_avatar(avatar_dir: Path, avatar_id: str) -> AvatarProfile:
    path = _avatar_file(avatar_dir, avatar_id)
    if not path.exists():
        raise AvatarNotFoundError(f"Avatar '{avatar_id}' was not found.")

    with path.open("r", encoding="utf-8") as handle:
        return AvatarProfile.model_validate(yaml.safe_load(handle))
