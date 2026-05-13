from __future__ import annotations

import time
from typing import Callable

from nicegui import events, ui

from models.app_state import AppState
from models.entities import DetectionSource, ImageRecord


class CanvasView:
    def __init__(self, state: AppState, image_url_builder: Callable[[int], str]) -> None:
        self.state = state
        self._image_url = image_url_builder
        self._draw_start: tuple[float, float] | None = None
        self._current_image_id: int | None = None
        self._last_move: float = 0.0

        with ui.element('div').style(
            'flex: 1; min-height: 0; '
            'display: flex; align-items: center; justify-content: center; '
            'position: relative; background: #0b1120; overflow: hidden;'
        ):
            self._img = (
                ui.interactive_image(
                    source='',
                    on_mouse=self._on_mouse,
                    events=['mousedown', 'mousemove', 'mouseup'],
                    sanitize=False,
                )
                .style('max-width: 100%; max-height: 100%;')
            )
            self._draft_layer = self._img.add_layer()

            with self._img:
                self.title_label = (
                    ui.label('')
                    .classes('absolute top-0 left-0 m-2')
                    .style(
                        'background: rgba(0,0,0,0.52); color: rgba(255,255,255,0.88); '
                        'padding: 4px 12px; border-radius: 6px; font-size: 0.79rem; '
                        'font-weight: 500; pointer-events: none; '
                        'max-width: 55%; overflow: hidden; '
                        'text-overflow: ellipsis; white-space: nowrap;'
                    )
                )

            self._empty_hint = (
                ui.label('Sélectionnez un dossier pour commencer')
                .style(
                    'position: absolute; color: rgba(255,255,255,0.22); '
                    'font-size: 0.9rem; pointer-events: none;'
                )
            )

        state.subscribe(self.refresh)
        self.refresh()

    # ── Scale helpers ──────────────────────────────────────────────────────────

    def _spx(self, target_screen_px: float, image: ImageRecord | None) -> float:
        """Convert a target screen-pixel size to SVG coordinate units.

        The SVG viewport matches the image's natural dimensions, so elements
        must be sized in image pixels. We assume the panel is ~800 CSS px wide
        to derive the conversion factor; the result looks reasonable across
        typical display widths (600–1200 px).
        """
        image_w = image.width if (image and image.width) else 1920
        return target_screen_px * image_w / 800.0

    # ── Mouse events ───────────────────────────────────────────────────────────

    def _on_mouse(self, e: events.MouseEventArguments) -> None:
        if e.type == 'mousedown':
            image = self.state.current_image
            if image is None:
                return
            idx = self._hit_test(e.image_x, e.image_y, image)
            if idx is not None:
                self.state.select_detection(idx)
            else:
                self.state.select_detection(None)
                self._draw_start = (e.image_x, e.image_y)

        elif e.type == 'mousemove':
            if self._draw_start:
                now = time.time()
                if now - self._last_move < 0.04:
                    return
                self._last_move = now
                x1 = min(self._draw_start[0], e.image_x)
                y1 = min(self._draw_start[1], e.image_y)
                w = abs(e.image_x - self._draw_start[0])
                h = abs(e.image_y - self._draw_start[1])
                self._draft_layer.content = (
                    f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{w:.1f}" height="{h:.1f}" '
                    f'fill="rgba(245,158,11,0.08)" stroke="#F59E0B" '
                    f'stroke-width="2" stroke-dasharray="8 4" '
                    f'vector-effect="non-scaling-stroke" '
                    f'pointer-events="none"/>'
                )

        elif e.type == 'mouseup':
            if self._draw_start:
                x1 = min(self._draw_start[0], e.image_x)
                y1 = min(self._draw_start[1], e.image_y)
                x2 = max(self._draw_start[0], e.image_x)
                y2 = max(self._draw_start[1], e.image_y)
                self._draw_start = None
                self._draft_layer.content = ''
                if x2 - x1 > 5 and y2 - y1 > 5:
                    self.state.add_manual_detection(x1, y1, x2, y2)

    def _hit_test(self, x: float, y: float, image: ImageRecord) -> int | None:
        """Return detection index if (x, y) falls inside a box, else None."""
        for idx, det in enumerate(image.detections):
            if det.x1 <= x <= det.x2 and det.y1 <= y <= det.y2:
                return idx
        return None

    # ── State refresh ──────────────────────────────────────────────────────────

    def refresh(self) -> None:
        image = self.state.current_image
        self.title_label.text = image.filename if image else ''
        self._empty_hint.set_visibility(image is None)

        if image is None:
            if self._current_image_id is not None:
                self._img.set_source('')
                self._img.content = ''
                self._draft_layer.content = ''
                self._current_image_id = None
            return

        if image.id != self._current_image_id:
            if image.width is None or image.height is None:
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(str(image.absolute_path)) as pil:
                        image.width, image.height = pil.size
                        self.state.persistence.update_dimensions(image)
                except Exception:
                    pass

            self._img.set_source(self._image_url(image.id))
            self._current_image_id = image.id
            self._draw_start = None
            self._draft_layer.content = ''

            style = 'max-width: 100%; max-height: 100%;'
            if image.width and image.height:
                style += f' aspect-ratio: {image.width} / {image.height};'
            self._img.style(style)

        self._img.content = self._build_svg(image)

    # ── SVG overlay ────────────────────────────────────────────────────────────

    def _build_svg(self, image: ImageRecord) -> str:
        if not image.detections:
            return ''

        # Box borders use vector-effect="non-scaling-stroke" so stroke-width
        # is always in screen pixels regardless of the image's natural size.
        # Label/text dimensions use _spx() to convert screen px → SVG units.
        px = lambda n: self._spx(n, image)
        fs = px(12)       # font-size  → 12 screen px
        lh = px(20)       # label height → 20 screen px
        pad = px(5)       # padding → 5 screen px

        selected_idx = self.state.selected_detection_index
        parts: list[str] = []

        for i, det in enumerate(image.detections):
            is_selected = (i == selected_idx)
            is_manual = (
                det.source == DetectionSource.MANUAL
                or (hasattr(det.source, 'value') and det.source.value == 'manual')
            )
            color = '#16A34A' if is_manual else '#2563EB'
            stroke = '#F59E0B' if is_selected else color
            stroke_w = 3 if is_selected else 2
            dash = 'stroke-dasharray="8 4"' if is_selected else ''

            conf = int((det.confidence or 1.0) * 100)
            lbl = f'#{det.local_id} {conf}%'
            lw = len(lbl) * fs * 0.63 + pad * 2

            x1, y1, x2, y2 = det.x1, det.y1, det.x2, det.y2
            w, h = x2 - x1, y2 - y1
            ly = max(0.0, y1 - lh - px(2))

            parts.append(
                f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{w:.1f}" height="{h:.1f}" '
                f'fill="none" stroke="{stroke}" stroke-width="{stroke_w}" {dash} '
                f'vector-effect="non-scaling-stroke" '
                f'pointer-events="none" rx="{px(2):.1f}"/>'
            )
            parts.append(
                f'<rect x="{x1:.1f}" y="{ly:.1f}" width="{lw:.1f}" height="{lh:.1f}" '
                f'fill="{color}" rx="{px(2):.1f}" opacity="0.88" pointer-events="none"/>'
            )
            parts.append(
                f'<text x="{x1 + pad:.1f}" y="{ly + lh - pad:.1f}" '
                f'font-size="{fs:.1f}" font-family="ui-monospace,monospace" '
                f'fill="white" pointer-events="none">{lbl}</text>'
            )

        return ''.join(parts)

    # ── Public API (called by ActionToolbar and keyboard shortcuts) ────────────

    def start_add_mode(self) -> None:
        if self.state.current_image is None:
            return
        ui.notify('Glissez directement sur l\'image pour ajouter un aileron.', type='info', timeout=2000)

    def delete_selected(self) -> None:
        image = self.state.current_image
        if image is None or self.state.selected_detection_index is None:
            return
        idx = self.state.selected_detection_index
        if 0 <= idx < len(image.detections):
            self.state.delete_detection(image.detections[idx].local_id)