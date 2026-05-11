from __future__ import annotations

from pathlib import Path

from database import Repository, get_repository
from models.entities import Detection, DetectionSource, ImageRecord, ImageStatus


class PersistenceService:
    """Maps SQLite rows <-> domain entities."""

    def __init__(self, repository: Repository | None = None) -> None:
        self._repo = repository or get_repository()

    # -- images ----------------------------------------------------------

    def register_folder(self, folder: Path, files: list[Path]) -> list[ImageRecord]:
        folder_key = str(folder.resolve())
        existing = {row['absolute_path']: row for row in self._repo.list_images(folder_key)}

        new_records: list[dict] = []
        for path in files:
            abs_path = str(path.resolve())
            if abs_path in existing:
                continue
            new_records.append({'filename': path.name, 'absolute_path': abs_path})

        if new_records:
            self._repo.insert_images(folder_key, new_records)

        return self.list_folder(folder)

    def list_folder(self, folder: Path) -> list[ImageRecord]:
        folder_key = str(folder.resolve())
        rows = self._repo.list_images(folder_key)
        records: list[ImageRecord] = []
        for row in rows:
            detections_rows = self._repo.list_detections(row['id'])
            detections = [
                Detection(
                    local_id=d['local_id'],
                    x1=d['x1'],
                    y1=d['y1'],
                    x2=d['x2'],
                    y2=d['y2'],
                    confidence=d['confidence'],
                    source=DetectionSource(d['source']),
                    label=d['label'],
                )
                for d in detections_rows
            ]
            records.append(
                ImageRecord(
                    id=row['id'],
                    filename=row['filename'],
                    absolute_path=Path(row['absolute_path']),
                    folder=row['folder'],
                    order_index=row['order_index'],
                    status=ImageStatus(row['status']),
                    notes=row['notes'] or '',
                    width=row['width'],
                    height=row['height'],
                    detections=detections,
                )
            )
        return records

    def clear_folder(self, folder: Path) -> None:
        self._repo.clear_folder(str(folder.resolve()))

    def update_status(self, image: ImageRecord) -> None:
        self._repo.update_image_status(image.id, image.status.value)

    def update_notes(self, image: ImageRecord) -> None:
        self._repo.update_image_notes(image.id, image.notes)

    def update_dimensions(self, image: ImageRecord) -> None:
        if image.width is None or image.height is None:
            return
        self._repo.update_image_dimensions(image.id, image.width, image.height)

    def save_detections(self, image: ImageRecord) -> None:
        payload = [det.as_dict() for det in image.detections]
        self._repo.replace_detections(image.id, payload)

    # -- app state -------------------------------------------------------

    def set_state(self, key: str, value: str) -> None:
        self._repo.set_state(key, value)

    def get_state(self, key: str, default: str | None = None) -> str | None:
        return self._repo.get_state(key, default)
