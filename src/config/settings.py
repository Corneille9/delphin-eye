from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ModelEntry:
    id: str
    name: str
    path: Path
    imgsz: int
    recommended: bool = False


@dataclass
class Settings:
    project_root: Path = PROJECT_ROOT
    model_path: Path = PROJECT_ROOT / 'output' / 'models' / 'default' / 'weights' / 'best.pt'
    database_path: Path = PROJECT_ROOT / 'src' / 'database' / 'app.db'

    supported_formats: tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.webp')
    inference_imgsz: int = 640
    inference_conf: float = 0.25
    inference_overlap: float = 0.2
    inference_mode: str = 'yolo'
    crop_margin: int = 200

    user_config_path: Path = PROJECT_ROOT / 'config' / 'user_settings.json'
    inference_config_path: Path = PROJECT_ROOT / 'config' / 'inference.yaml'

    model_catalog: list[ModelEntry] = field(default_factory=list, repr=False)

    _overridable_fields: tuple[str, ...] = field(
        default=('model_path', 'inference_imgsz', 'inference_conf', 'inference_overlap', 'inference_mode', 'crop_margin'),
        repr=False,
    )

    def load_inference_config(self) -> None:
        if not self.inference_config_path.exists():
            return
        import yaml
        try:
            data = yaml.safe_load(self.inference_config_path.read_text(encoding='utf-8')) or {}
        except Exception:
            return
        inference = data.get('inference', {})
        if 'mode' in inference:
            self.inference_mode = str(inference['mode'])
        if 'overlap' in inference:
            self.inference_overlap = float(inference['overlap'])
        self.model_catalog = [
            ModelEntry(
                id=m['id'],
                name=m['name'],
                path=self.project_root / m['path'],
                imgsz=int(m.get('imgsz', 640)),
                recommended=bool(m.get('recommended', False)),
            )
            for m in data.get('models', [])
        ]

    def ensure_directories(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

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
            current = getattr(self, key, None)
            if current is None:
                continue
            if isinstance(current, Path):
                setattr(self, key, Path(value))
            else:
                setattr(self, key, type(current)(value))

    def save_user_overrides(self, keys: Iterable[str] | None = None) -> None:
        keys = tuple(keys) if keys is not None else self._overridable_fields
        payload: dict[str, object] = {}
        for key in keys:
            value = getattr(self, key, None)
            if value is None:
                continue
            payload[key] = str(value) if isinstance(value, Path) else value
        self.user_config_path.parent.mkdir(parents=True, exist_ok=True)
        self.user_config_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8'
        )


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings()
        _SETTINGS.load_inference_config()
        _SETTINGS.load_user_overrides()
        _SETTINGS.ensure_directories()
    return _SETTINGS
