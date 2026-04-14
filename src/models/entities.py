from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ImageStatus(str, Enum):
    PENDING = 'pending'
    VALIDATED = 'validated'
    REJECTED = 'rejected'
    MANUAL_EDIT = 'manual_edit'
    PROCESSED = 'processed'


class DetectionSource(str, Enum):
    AUTO = 'auto'
    MANUAL = 'manual'


STATUS_ICON = {
    ImageStatus.PENDING: '?',
    ImageStatus.VALIDATED: 'OK',
    ImageStatus.REJECTED: 'X',
    ImageStatus.MANUAL_EDIT: 'M',
    ImageStatus.PROCESSED: '.',
}


STATUS_LABEL_FR = {
    ImageStatus.PENDING: 'En attente',
    ImageStatus.VALIDATED: 'Validee',
    ImageStatus.REJECTED: 'Rejetee',
    ImageStatus.MANUAL_EDIT: 'Modifiee',
    ImageStatus.PROCESSED: 'Traitee',
}


STATUS_BADGE_CLASS = {
    ImageStatus.PENDING: 'app-badge app-badge-pending',
    ImageStatus.VALIDATED: 'app-badge app-badge-validated',
    ImageStatus.REJECTED: 'app-badge app-badge-rejected',
    ImageStatus.MANUAL_EDIT: 'app-badge app-badge-manual',
    ImageStatus.PROCESSED: 'app-badge app-badge-manual',
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
