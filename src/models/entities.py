from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ImageStatus(str, Enum):
    PENDING  = 'pending'   # not yet run through the model
    DETECTED = 'detected'  # model found at least one fin
    MODIFIED = 'modified'  # user added or removed bboxes manually


# Graceful migration: old status values stored in the DB before the refactor.
STATUS_COMPAT: dict[str, ImageStatus] = {
    'validated':   ImageStatus.DETECTED,
    'rejected':    ImageStatus.PENDING,
    'processed':   ImageStatus.DETECTED,
    'manual_edit': ImageStatus.MODIFIED,
}


def parse_status(value: str) -> ImageStatus:
    try:
        return ImageStatus(value)
    except ValueError:
        return STATUS_COMPAT.get(value, ImageStatus.PENDING)


class DetectionSource(str, Enum):
    AUTO   = 'auto'
    MANUAL = 'manual'


STATUS_ICON: dict[ImageStatus, str] = {
    ImageStatus.PENDING:  '·',
    ImageStatus.DETECTED: '✓',
    ImageStatus.MODIFIED: 'M',
}

STATUS_LABEL_FR: dict[ImageStatus, str] = {
    ImageStatus.PENDING:  'En attente',
    ImageStatus.DETECTED: 'Analysée',
    ImageStatus.MODIFIED: 'Modifiée',
}

STATUS_BADGE_CLASS: dict[ImageStatus, str] = {
    ImageStatus.PENDING:  'app-badge app-badge-pending',
    ImageStatus.DETECTED: 'app-badge app-badge-validated',
    ImageStatus.MODIFIED: 'app-badge app-badge-manual',
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
