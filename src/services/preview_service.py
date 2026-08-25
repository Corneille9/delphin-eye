"""Downscaled previews for the canvas.

The source photographs are 20 MP DSLR files: pushing them through the local HTTP
server means ~4 MB and ~80 MB of decoded pixels per image, which the embedded
webview struggles to render. The canvas never needs more than screen resolution,
so it gets a cached, downscaled copy instead. Detections stay in original image
coordinates - only the display layer is scaled, via ``preview_scale``.
"""
from __future__ import annotations

from pathlib import Path

# Longest edge of the preview, in pixels. Comfortably above the canvas size on a
# 4K screen while keeping each preview around 200 KB.
PREVIEW_MAX_EDGE = 1600


def preview_scale(width: int | None, height: int | None) -> float:
    """Factor to convert original image coordinates into preview coordinates."""
    longest = max(width or 0, height or 0)
    if longest <= 0 or longest <= PREVIEW_MAX_EDGE:
        return 1.0
    return PREVIEW_MAX_EDGE / longest


class PreviewService:
    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir

    def preview_path(self, image_id: int, source: Path) -> Path:
        """Return a downscaled copy of *source*, generating it once and caching it.

        Falls back to the original file if the image cannot be processed.
        """
        try:
            stat = source.stat()
        except OSError:
            return source

        target = self._cache_dir / f'{image_id}-{int(stat.st_mtime)}-{PREVIEW_MAX_EDGE}.jpg'
        if target.exists():
            return target

        try:
            from PIL import Image

            with Image.open(source) as img:
                if max(img.size) <= PREVIEW_MAX_EDGE:
                    return source
                # draft() lets libjpeg decode straight to a smaller size instead
                # of unpacking all 20 MP first.
                img.draft('RGB', (PREVIEW_MAX_EDGE, PREVIEW_MAX_EDGE))
                img = img.convert('RGB')
                img.thumbnail((PREVIEW_MAX_EDGE, PREVIEW_MAX_EDGE), Image.LANCZOS)
                self._cache_dir.mkdir(parents=True, exist_ok=True)
                img.save(target, 'JPEG', quality=85, optimize=True)
        except Exception:
            return source
        return target

    def clear(self) -> None:
        if not self._cache_dir.is_dir():
            return
        for entry in self._cache_dir.glob(f'*-{PREVIEW_MAX_EDGE}.jpg'):
            entry.unlink(missing_ok=True)
