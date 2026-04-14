from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from random import Random
from typing import Callable


class ImageStatus(str, Enum):
    PENDING = 'pending'
    VALIDATED = 'validated'
    REJECTED = 'rejected'
    MANUAL_EDIT = 'manual_edit'
    PROCESSED = 'processed'


STATUS_ICON = {
    ImageStatus.PENDING: '?',
    ImageStatus.VALIDATED: '✓',
    ImageStatus.REJECTED: '✗',
    ImageStatus.MANUAL_EDIT: 'M',
    ImageStatus.PROCESSED: '•',
}

STATUS_COLOR = {
    ImageStatus.PENDING: 'orange-6',
    ImageStatus.VALIDATED: 'positive',
    ImageStatus.REJECTED: 'negative',
    ImageStatus.MANUAL_EDIT: 'purple',
    ImageStatus.PROCESSED: 'primary',
}


@dataclass(slots=True)
class Detection:
    id: int
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float


@dataclass(slots=True)
class ImageRecord:
    filename: str
    fake_source_path: str
    preview_url: str
    status: ImageStatus
    notes: str
    detections: list[Detection] = field(default_factory=list)


class DashboardState:
    """Shared state container with an observer pattern for component refresh."""

    def __init__(self, images: list[ImageRecord]) -> None:
        self.images = images
        self.current_index = 0
        self.selected_detection_index: int | None = 0 if images and images[0].detections else None
        self.processed_images = 0
        self.total_images = len(images)
        self.detection_running = False
        self._listeners: list[Callable[[], None]] = []

    @property
    def current_image(self) -> ImageRecord:
        return self.images[self.current_index]

    def subscribe(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def notify(self) -> None:
        for listener in self._listeners:
            listener()

    def select_image(self, index: int) -> None:
        if 0 <= index < len(self.images):
            self.current_index = index
            self.selected_detection_index = 0 if self.current_image.detections else None
            self.notify()

    def next_image(self) -> None:
        self.select_image(min(self.current_index + 1, len(self.images) - 1))

    def previous_image(self) -> None:
        self.select_image(max(self.current_index - 1, 0))

    def validate_current(self) -> None:
        self.current_image.status = ImageStatus.VALIDATED
        self.notify()

    def reject_current(self) -> None:
        self.current_image.status = ImageStatus.REJECTED
        self.notify()

    def update_notes(self, notes: str) -> None:
        self.current_image.notes = notes
        self.notify()

    def select_detection(self, index: int | None) -> None:
        if index is None:
            self.selected_detection_index = None
        elif 0 <= index < len(self.current_image.detections):
            self.selected_detection_index = index
        self.notify()

    def delete_selected_detection(self) -> None:
        if self.selected_detection_index is None:
            return
        detections = self.current_image.detections
        if 0 <= self.selected_detection_index < len(detections):
            detections.pop(self.selected_detection_index)
            self.current_image.status = ImageStatus.MANUAL_EDIT
            if not detections:
                self.selected_detection_index = None
            else:
                self.selected_detection_index = min(self.selected_detection_index, len(detections) - 1)
            self.notify()

    def add_mock_detection(self) -> None:
        detections = self.current_image.detections
        new_id = max((det.id for det in detections), default=0) + 1
        # Keep generated boxes inside a 1280x720 mock frame.
        offset = 20 * new_id
        detections.append(
            Detection(
                id=new_id,
                x1=min(120 + offset, 980),
                y1=min(80 + offset, 500),
                x2=min(360 + offset, 1220),
                y2=min(260 + offset, 680),
                confidence=0.77,
            )
        )
        self.selected_detection_index = len(detections) - 1
        self.current_image.status = ImageStatus.MANUAL_EDIT
        self.notify()

    def start_detection_run(self) -> None:
        self.processed_images = 0
        self.detection_running = True
        self.notify()

    def step_detection(self) -> None:
        if not self.detection_running:
            return
        self.processed_images = min(self.processed_images + 4, self.total_images)
        if self.processed_images >= self.total_images:
            self.detection_running = False
        self.notify()


def build_mock_images(total_images: int = 120, preview_url: str = '/assets/placeholder.JPG') -> list[ImageRecord]:
    rng = Random(7)
    images: list[ImageRecord] = []

    for idx in range(1, total_images + 1):
        filename = f'img_{idx:03}.jpg'
        status = [
            ImageStatus.PENDING,
            ImageStatus.VALIDATED,
            ImageStatus.REJECTED,
            ImageStatus.MANUAL_EDIT,
        ][idx % 4]

        detections: list[Detection] = []
        for det_id in range(1, rng.randint(1, 4) + 1):
            x1 = rng.randint(80, 780)
            y1 = rng.randint(60, 320)
            width = rng.randint(180, 320)
            height = rng.randint(120, 220)
            detections.append(
                Detection(
                    id=det_id,
                    x1=x1,
                    y1=y1,
                    x2=min(x1 + width, 1260),
                    y2=min(y1 + height, 700),
                    confidence=round(rng.uniform(0.71, 0.98), 2),
                )
            )

        images.append(
            ImageRecord(
                filename=filename,
                fake_source_path=f'/mock_dataset/campaign_2026/day_01/{filename}',
                preview_url=preview_url,
                status=status,
                notes='No user notes yet.' if idx % 5 else 'Check light reflections near the dorsal fin.',
                detections=detections,
            )
        )

    return images

