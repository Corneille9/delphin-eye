from __future__ import annotations

import json
import shutil
from pathlib import Path

from config import get_settings
from models.entities import ImageRecord, ImageStatus


class ExportService:
    """Exports validated images, crops and JSON annotations."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def export_all(self, images: list[ImageRecord]) -> dict:
        s = self._settings
        s.ensure_directories()

        validated = [i for i in images if i.status == ImageStatus.VALIDATED]
        rejected = [i for i in images if i.status == ImageStatus.REJECTED]

        for img in validated:
            self._copy_image(img.absolute_path, s.validated_dir / img.filename)
            self._crop_fins(img)
        for img in rejected:
            self._copy_image(img.absolute_path, s.rejected_dir / img.filename)

        self._write_json(images, s.annotations_dir / 'results.json')

        return {
            'validated': len(validated),
            'rejected': len(rejected),
            'total': len(images),
            'output_dir': str(s.output_dir),
        }

    def _copy_image(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dst)
        except (shutil.SameFileError, FileNotFoundError):
            pass

    def _crop_fins(self, image: ImageRecord) -> None:
        if not image.detections:
            return
        try:
            from PIL import Image as PILImage
        except ImportError:
            return
        try:
            pil = PILImage.open(image.absolute_path)
        except (OSError, FileNotFoundError):
            return
        for det in image.detections:
            fin_dir = self._settings.crops_dir / f'fin_{det.local_id}'
            fin_dir.mkdir(parents=True, exist_ok=True)
            box = (int(det.x1), int(det.y1), int(det.x2), int(det.y2))
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            crop = pil.crop(box)
            stem = Path(image.filename).stem
            crop.save(fin_dir / f'{stem}_fin{det.local_id}.jpg', 'JPEG', quality=90)

    def _write_json(self, images: list[ImageRecord], target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                'image': img.filename,
                'path': str(img.absolute_path),
                'status': img.status.value,
                'notes': img.notes,
                'fins': [
                    {
                        'id': d.local_id,
                        'bbox': [d.x1, d.y1, d.x2, d.y2],
                        'confidence': d.confidence,
                        'source': d.source.value,
                        'label': d.label,
                    }
                    for d in img.detections
                ],
            }
            for img in images
        ]
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
