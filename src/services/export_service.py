from __future__ import annotations

import shutil
from pathlib import Path

from config import get_settings
from models.entities import ImageRecord, ImageStatus


class ExportService:
    """Exports detected images following the project arborescence.

    Output structure is derived from the selected input folder:
      <folder>_sauvegarde/  →  <folder>_triees/       (cropped + numbered)
                           →  <folder>_corrections/   (original + YOLO labels)

    If '_sauvegarde' is absent from the folder name, suffixes are appended.
    """

    def export_all(self, images: list[ImageRecord]) -> dict:
        detected = [img for img in images if img.detections]
        if not detected:
            return {'exported': 0, 'corrections': 0, 'triees_dir': '', 'corrections_dir': ''}

        settings = get_settings()
        folder = Path(detected[0].folder)
        triees_root = self.compute_triees_path(folder)
        corrections_root = self.compute_corrections_path(folder)

        exported = 0
        for img in detected:
            dst = triees_root / Path(img.absolute_path).relative_to(folder)
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                self._crop_and_annotate(img, dst, margin=settings.crop_margin)
                exported += 1
            except Exception:
                # Fallback: copy original if image processing fails
                try:
                    shutil.copy2(img.absolute_path, dst)
                    exported += 1
                except (shutil.SameFileError, FileNotFoundError, OSError):
                    pass

        corrections = 0
        for img in images:
            if img.status != ImageStatus.MODIFIED:
                continue
            dst = corrections_root / Path(img.absolute_path).relative_to(folder)
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(img.absolute_path, dst)
                if img.detections and img.width and img.height:
                    self._write_yolo_labels(img, dst.with_suffix('.txt'))
                corrections += 1
            except (shutil.SameFileError, FileNotFoundError, OSError):
                pass

        return {
            'exported': exported,
            'corrections': corrections,
            'triees_dir': str(triees_root),
            'corrections_dir': str(corrections_root),
        }

    @staticmethod
    def compute_triees_path(folder: Path) -> Path:
        name = folder.name
        new_name = name.replace('_sauvegarde', '_triees') if '_sauvegarde' in name else name + '_triees'
        return folder.parent / new_name

    @staticmethod
    def compute_corrections_path(folder: Path) -> Path:
        name = folder.name
        new_name = name.replace('_sauvegarde', '_corrections') if '_sauvegarde' in name else name + '_corrections'
        return folder.parent / new_name

    @staticmethod
    def _crop_and_annotate(img: ImageRecord, dst: Path, margin: int) -> None:
        """Crop the image to the union of all bboxes + margin, then number fins."""
        from PIL import Image as PILImage, ImageDraw

        pil = PILImage.open(img.absolute_path).convert('RGB')
        W, H = pil.size
        dets = img.detections

        # Union bounding box of all detections
        left = min(d.x1 for d in dets)
        top = min(d.y1 for d in dets)
        right = max(d.x2 for d in dets)
        bottom = max(d.y2 for d in dets)

        # Apply margin and clamp to image dimensions
        cx1 = max(0, int(left - margin))
        cy1 = max(0, int(top - margin))
        cx2 = min(W, int(right + margin))
        cy2 = min(H, int(bottom + margin))

        cropped = pil.crop((cx1, cy1, cx2, cy2))
        cW, cH = cropped.size

        # Number fins only when there are two or more
        if len(dets) > 1:
            draw = ImageDraw.Draw(cropped)
            font_size = max(20, int(cH * 0.05))
            font = ExportService._load_font(font_size)

            # Sort left-to-right by horizontal center
            sorted_dets = sorted(dets, key=lambda d: (d.x1 + d.x2) / 2)

            for num, det in enumerate(sorted_dets, start=1):
                # Translate bbox to cropped-image coordinates
                bx1 = det.x1 - cx1
                by1 = det.y1 - cy1
                bx2 = det.x2 - cx1

                label = str(num)
                tb = draw.textbbox((0, 0), label, font=font)
                tw = tb[2] - tb[0]
                th = tb[3] - tb[1]
                pad = max(3, font_size // 6)
                gap = max(6, font_size // 3)

                # Background: centered above the top edge of the bbox
                bg_w = tw + pad * 2
                bg_h = th + pad * 2
                bg_x1 = (bx1 + bx2) / 2 - bg_w / 2
                bg_y1 = by1 - gap - bg_h
                bg_x2 = bg_x1 + bg_w
                bg_y2 = bg_y1 + bg_h

                # Clamp to crop bounds
                if bg_x1 < 0:
                    bg_x1, bg_x2 = 0, bg_w
                if bg_x2 > cW:
                    bg_x1, bg_x2 = cW - bg_w, cW
                if bg_y1 < 0:
                    bg_y1, bg_y2 = 0, bg_h

                draw.rectangle(
                    [bg_x1, bg_y1, bg_x2, bg_y2],
                    fill='white',
                    outline='#222222',
                    width=1,
                )
                # Offset by tb origin so text is truly centered inside the background
                draw.text((bg_x1 + pad - tb[0], bg_y1 + pad - tb[1]), label, fill='#111111', font=font)

        cropped.save(dst, quality=92)

    @staticmethod
    def _load_font(size: int):
        from PIL import ImageFont
        candidates = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
            'C:/Windows/Fonts/arialbd.ttf',
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    @staticmethod
    def _write_yolo_labels(img: ImageRecord, path: Path) -> None:
        lines = []
        for det in img.detections:
            cx = (det.x1 + det.x2) / 2 / img.width
            cy = (det.y1 + det.y2) / 2 / img.height
            w = (det.x2 - det.x1) / img.width
            h = (det.y2 - det.y1) / img.height
            lines.append(f'0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}')
        path.write_text('\n'.join(lines), encoding='utf-8')
