from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ImageStatus(str, Enum):
    PENDING = 'pending'  # never run through the model
    EMPTY = 'empty'  # analysed, model found nothing
    DETECTED = 'detected'  # analysed, model found at least one fin
    MODIFIED = 'modified'  # user added, moved or removed boxes
    FAILED = 'failed'  # analysis raised; the image was not analysed


#: Statuses that count as "the model has seen this image".
ANALYSED_STATUSES = (ImageStatus.EMPTY, ImageStatus.DETECTED, ImageStatus.MODIFIED)


# Graceful migration: status values stored by earlier versions.
STATUS_COMPAT: dict[str, ImageStatus] = {
    'validated': ImageStatus.DETECTED,
    'rejected': ImageStatus.PENDING,
    'processed': ImageStatus.DETECTED,
    'manual_edit': ImageStatus.MODIFIED,
}


def parse_status(value: str) -> ImageStatus:
    try:
        return ImageStatus(value)
    except ValueError:
        return STATUS_COMPAT.get(value, ImageStatus.PENDING)


def resolve_status(status: ImageStatus, detection_count: int) -> ImageStatus:
    """Reconcile a stored status with the boxes actually present.

    Builds before the status rework marked every analysed image DETECTED, even
    the ones the model found nothing on - and a bundling bug made that every
    image. Reading the two together repairs those rows on load.
    """
    if status in (ImageStatus.PENDING, ImageStatus.FAILED):
        return status
    if status == ImageStatus.MODIFIED:
        return status
    return ImageStatus.DETECTED if detection_count else ImageStatus.EMPTY


class DetectionSource(str, Enum):
    AUTO = 'auto'
    MANUAL = 'manual'


STATUS_LABEL_FR: dict[ImageStatus, str] = {
    ImageStatus.PENDING: 'En attente',
    ImageStatus.EMPTY: 'Analysée · aucun aileron',
    ImageStatus.DETECTED: 'Analysée · aileron détecté',
    ImageStatus.MODIFIED: 'Modifiée',
    ImageStatus.FAILED: "Échec de l'analyse",
}

STATUS_BADGE_CLASS: dict[ImageStatus, str] = {
    ImageStatus.PENDING: 'app-badge app-badge-pending',
    ImageStatus.EMPTY: 'app-badge app-badge-empty',
    ImageStatus.DETECTED: 'app-badge app-badge-detected',
    ImageStatus.MODIFIED: 'app-badge app-badge-manual',
    ImageStatus.FAILED: 'app-badge app-badge-failed',
}

STATUS_DOT_CLASS: dict[ImageStatus, str] = {
    ImageStatus.PENDING: 'status-dot status-dot-pending',
    ImageStatus.EMPTY: 'status-dot status-dot-empty',
    ImageStatus.DETECTED: 'status-dot status-dot-detected',
    ImageStatus.MODIFIED: 'status-dot status-dot-modified',
    ImageStatus.FAILED: 'status-dot status-dot-failed',
}


@dataclass
class Detection:
    local_id: int
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = 1.0
    source: DetectionSource = DetectionSource.AUTO
    label: str = 'dorsal_fin'

    def as_dict(self) -> dict:
        return {
            'local_id': self.local_id,
            'x1': float(self.x1),
            'y1': float(self.y1),
            'x2': float(self.x2),
            'y2': float(self.y2),
            'confidence': float(self.confidence),
            'source': self.source.value if isinstance(self.source, DetectionSource) else str(self.source),
            'label': self.label,
        }

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)


@dataclass
class ImageRecord:
    id: int
    filename: str
    absolute_path: Path
    folder: str
    order_index: int
    status: ImageStatus = ImageStatus.PENDING
    notes: str = ''
    width: int | None = None
    height: int | None = None
    detections: list[Detection] = field(default_factory=list)

    @property
    def has_detections(self) -> bool:
        return bool(self.detections)

    @property
    def will_export(self) -> bool:
        return self.has_detections
