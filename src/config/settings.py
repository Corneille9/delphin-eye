from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    project_root: Path = PROJECT_ROOT
    model_path: Path = PROJECT_ROOT / 'output' / 'models' / 'default' / 'weights' / 'best.pt'
    database_path: Path = PROJECT_ROOT / 'src' / 'database' / 'app.db'
    output_dir: Path = PROJECT_ROOT / 'output'
    validated_dir: Path = PROJECT_ROOT / 'output' / 'validated_images'
    rejected_dir: Path = PROJECT_ROOT / 'output' / 'rejected'
    crops_dir: Path = PROJECT_ROOT / 'output' / 'cropped_fins'
    annotations_dir: Path = PROJECT_ROOT / 'output' / 'annotations'

    supported_formats: tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.webp')
    autosave_interval_seconds: int = 5
    max_image_side: int = 1600
    inference_imgsz: int = 640
    inference_conf: float = 0.25

    user_config_path: Path = PROJECT_ROOT / 'config' / 'user_settings.json'

    _overridable_fields: tuple[str, ...] = field(
        default=(
            'model_path',
            'output_dir',
            'validated_dir',
            'rejected_dir',
            'crops_dir',
            'annotations_dir',
            'autosave_interval_seconds',
            'inference_imgsz',
            'inference_conf',
        ),
        repr=False,
    )

    def ensure_directories(self) -> None:
        for path in (
                self.output_dir,
                self.validated_dir,
                self.rejected_dir,
                self.crops_dir,
                self.annotations_dir,
                self.database_path.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def model_available(self) -> bool:
        return self.model_path.exists()

    def load_user_overrides(self) -> None:
        if not self.user_config_path.exists():
            return
        try:
            data = json.loads(self.user_config_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return
        for key in self._overridable_fields:
            if key not in data:
                continue
            value = data[key]
            current = getattr(self, key)
            if isinstance(current, Path):
                setattr(self, key, Path(value))
            else:
                setattr(self, key, type(current)(value))

    def save_user_overrides(self, keys: Iterable[str] | None = None) -> None:
        keys = tuple(keys) if keys is not None else self._overridable_fields
        payload: dict[str, object] = {}
        for key in keys:
            value = getattr(self, key)
            payload[key] = str(value) if isinstance(value, Path) else value
        self.user_config_path.parent.mkdir(parents=True, exist_ok=True)
        self.user_config_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8'
        )

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data.pop('_overridable_fields', None)
        return {k: str(v) if isinstance(v, Path) else v for k, v in data.items()}


_SETTINGS: Settings | None = None


def get_settings() -> Settings | None:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings()
        _SETTINGS.load_user_overrides()
        _SETTINGS.ensure_directories()
    return _SETTINGS
