from __future__ import annotations

from pathlib import Path

from config import get_settings
from models.entities import ImageRecord
from services.persistence_service import PersistenceService


class ImageQueueService:
    """Scans a folder and keeps an ordered queue of images."""

    def __init__(self, persistence: PersistenceService) -> None:
        self._persistence = persistence
        self._settings = get_settings()
        self._folder: Path | None = None
        self._images: list[ImageRecord] = []

    @property
    def folder(self) -> Path | None:
        return self._folder

    @property
    def images(self) -> list[ImageRecord]:
        return self._images

    def load_folder(self, folder: Path) -> list[ImageRecord]:
        folder = folder.resolve()
        if not folder.is_dir():
            raise NotADirectoryError(str(folder))
        files = sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in self._settings.supported_formats
        )
        self._images = self._persistence.register_folder(folder, files)
        self._folder = folder
        return self._images

    def refresh(self) -> list[ImageRecord]:
        if self._folder is None:
            return []
        self._images = self._persistence.list_folder(self._folder)
        return self._images

    def clear(self) -> None:
        self._folder = None
        self._images = []

    def find_index(self, image_id: int) -> int | None:
        for idx, img in enumerate(self._images):
            if img.id == image_id:
                return idx
        return None
