from __future__ import annotations

import time
from typing import Callable

from nicegui import events, ui

from config.theme import CANVAS_AUTO_COLOR, CANVAS_MANUAL_COLOR, CANVAS_SELECTED_COLOR
from models.app_state import AppState
from models.entities import Detection, DetectionSource, ImageRecord
from services.preview_service import preview_scale

#: On-screen geometry of the overlay, in CSS pixels. Everything drawn in the SVG
#: is converted from these through ``_units_per_px`` so a box looks the same
#: whether the photo is displayed at 400 or 1200 pixels wide.
LABEL_FONT_PX = 13.0
LABEL_HEIGHT_PX = 21.0
LABEL_PADDING_PX = 6.0
BOX_STROKE_PX = 2.0
HANDLE_PX = 9.0
GRAB_PX = 11.0
MIN_BOX_PX = 8.0

#: Handle name -> CSS cursor. The empty key is the box interior.
_CURSORS = {
    '': 'move',
    'n': 'ns-resize', 's': 'ns-resize',
    'e': 'ew-resize', 'w': 'ew-resize',
    'nw': 'nwse-resize', 'se': 'nwse-resize',
    'ne': 'nesw-resize', 'sw': 'nesw-resize',
}

#: Reports the displayed size of the photo so the overlay can size itself in
#: real screen pixels. Without it the label text and the resize handles shrink
#: with the image and become unreadable on portrait shots.
_MEASURE_JS = """
let attempts = 0;
const attach = () => {
    const el = document.querySelector('.app-canvas-image');
    if (!el) {
        if (attempts++ < 120) requestAnimationFrame(attach);
        return;
    }
    if (el.dataset.appMeasured) return;
    el.dataset.appMeasured = '1';
    const report = () => emitEvent('canvas_resize', {width: el.clientWidth, height: el.clientHeight});
    new ResizeObserver(report).observe(el);
    report();
};
attach();
"""

_MOVE_THROTTLE = 0.04


class CanvasView:
    """The photo with its detection boxes, drawn as an SVG overlay.

    Boxes can be drawn on an empty area, dragged from their interior and resized
    from any of their eight handles. Detections are stored in original image
    coordinates; the overlay works in preview coordinates (see PreviewService).
    """

    def __init__(self, state: AppState, image_url_builder: Callable[[int], str]) -> None:
        self.state = state
        self._image_url = image_url_builder
        self._current_image_id: int | None = None
        self._last_move: float = 0.0
        self._cursor: str = ''
        self._add_mode: bool = False

        # Active gesture: {'mode': 'draw'|'move'|'resize', ...}, in original px.
        self._gesture: dict | None = None
        # Displayed size of the photo in CSS pixels, reported by the browser.
        self._view: tuple[float, float] | None = None

        with ui.element('div').classes('app-canvas'):
            self._img = (
                ui.interactive_image(
                    source='',
                    on_mouse=self._on_mouse,
                    events=['mousedown', 'mousemove', 'mouseup', 'mouseleave'],
                    sanitize=False,
                )
                .classes('app-canvas-image')
            )
            self._draft_layer = self._img.add_layer()

            with self._img:
                self.title_label = (
                    ui.label('')
                    .classes('app-canvas-caption absolute top-0 left-0 m-2')
                )

            self._empty_hint = (
                ui.label('Sélectionnez un dossier pour commencer')
                .classes('app-canvas-hint')
            )

        ui.on('canvas_resize', self._on_resize)
        ui.context.client.on_connect(self._install_measure)

        state.subscribe(self.refresh)
        self.refresh()

    # ------------------------------------------------------------- geometry --

    @property
    def add_mode(self) -> bool:
        return self._add_mode

    def _install_measure(self) -> None:
        ui.run_javascript(_MEASURE_JS)

    def _on_resize(self, event: events.GenericEventArguments) -> None:
        width = float(event.args.get('width') or 0.0)
        height = float(event.args.get('height') or 0.0)
        if width <= 0 or height <= 0:
            return
        view = (width, height)
        if view == self._view:
            return
        self._view = view
        self.refresh()

    def _scale(self, image: ImageRecord | None) -> float:
        """Original image pixels -> preview (SVG) units.

        The canvas is served a downscaled copy of the photo, so the SVG viewport
        matches the preview, while detections are stored in original coordinates.
        """
        if image is None:
            return 1.0
        return preview_scale(image.width, image.height)

    def _units_per_px(self, image: ImageRecord | None) -> float:
        """SVG user units per on-screen CSS pixel.

        The wrapper shrink-wraps the photo, so its reported size *is* the size
        the image is painted at. Until the browser has reported it, fall back to
        a middle-of-the-road 800 px wide pane.
        """
        preview_w = (image.width if image and image.width else 1920) * self._scale(image)
        preview_h = (image.height if image and image.height else 1080) * self._scale(image)
        if self._view is None:
            return preview_w / 800.0
        view_w, view_h = self._view
        return max(preview_w / view_w, preview_h / view_h)

    def _image_per_px(self, image: ImageRecord | None) -> float:
        """Original image pixels per on-screen CSS pixel."""
        scale = self._scale(image)
        return self._units_per_px(image) / scale if scale else 1.0

    # ---------------------------------------------------------- hit testing --

    def _handle_at(self, x: float, y: float, det: Detection, grab: float) -> str | None:
        """Name of the resize handle under (x, y), '' for the interior, None outside."""
        # A wide grab area would swallow a small box whole, so cap it.
        tol = min(grab, det.width * 0.4, det.height * 0.4)
        if not (det.x1 - tol <= x <= det.x2 + tol and det.y1 - tol <= y <= det.y2 + tol):
            return None
        handle = ''
        if abs(y - det.y1) <= tol:
            handle += 'n'
        elif abs(y - det.y2) <= tol:
            handle += 's'
        if abs(x - det.x1) <= tol:
            handle += 'w'
        elif abs(x - det.x2) <= tol:
            handle += 'e'
        if handle:
            return handle
        # Outside the box but within the grab margin, and on no handle.
        if det.x1 <= x <= det.x2 and det.y1 <= y <= det.y2:
            return ''
        return None

    def _pick(self, x: float, y: float, image: ImageRecord, grab: float) -> tuple[int, str] | None:
        """Detection index and handle under (x, y), or None on bare image."""
        selected = self.state.selected_detection_index
        if selected is not None and 0 <= selected < len(image.detections):
            # The handles of the selected box win over everything else, so a box
            # drawn on top of it can never make them unreachable.
            handle = self._handle_at(x, y, image.detections[selected], grab)
            if handle:
                return selected, handle
        # Otherwise the topmost box under the pointer, so a small box nested in a
        # bigger one stays selectable.
        for index in reversed(range(len(image.detections))):
            handle = self._handle_at(x, y, image.detections[index], grab)
            if handle is not None:
                return index, handle
        return None

    # --------------------------------------------------------------- mouse ---

    def _on_mouse(self, e: events.MouseEventArguments) -> None:
        image = self.state.current_image
        if image is None:
            return
        scale = self._scale(image)
        # Everything below works in original image coordinates, like the stored
        # detections; only the SVG we emit is expressed in preview units.
        x, y = e.image_x / scale, e.image_y / scale

        if e.type == 'mousedown':
            if e.button == 0:  # only the left button draws, moves or resizes
                self._begin(x, y, image)
        elif e.type == 'mousemove':
            # A button released outside the window never reaches us as a mouseup,
            # which would leave the box glued to the pointer. The button state
            # carried by the move event is what tells us the drag is over.
            if self._gesture and not e.buttons & 1:
                self._commit(x, y, image)
                return
            now = time.time()
            if now - self._last_move < _MOVE_THROTTLE:
                return
            self._last_move = now
            if self._gesture:
                self._update(x, y, image)
            else:
                self._update_cursor(x, y, image)
        elif e.type in ('mouseup', 'mouseleave'):
            self._commit(x, y, image)

    def _begin(self, x: float, y: float, image: ImageRecord) -> None:
        grab = GRAB_PX * self._image_per_px(image)
        picked = None if self._add_mode else self._pick(x, y, image, grab)

        if picked is None:
            self.state.select_detection(None)
            self._gesture = {'mode': 'draw', 'origin': (x, y), 'point': (x, y)}
            return

        index, handle = picked
        det = image.detections[index]
        if index != self.state.selected_detection_index:
            self.state.select_detection(index)
        self._gesture = {
            'mode': 'resize' if handle else 'move',
            'handle': handle,
            'local_id': det.local_id,
            'origin': (x, y),
            'box': (det.x1, det.y1, det.x2, det.y2),
        }

    def _update(self, x: float, y: float, image: ImageRecord) -> None:
        gesture = self._gesture
        if gesture is None:
            return

        if gesture['mode'] == 'draw':
            gesture['point'] = (x, y)
            self._draft_layer.content = self._draft_svg(gesture, image)
            return

        det = self._find(image, gesture['local_id'])
        if det is None:
            self._gesture = None
            return
        det.x1, det.y1, det.x2, det.y2 = self._resolve(gesture, x, y, image)
        # Redraw the overlay only: notifying the whole app on every mouse move
        # would rebuild the queue list dozens of times per second.
        self._img.content = self._build_svg(image)

    def _commit(self, x: float, y: float, image: ImageRecord) -> None:
        gesture, self._gesture = self._gesture, None
        if gesture is None:
            return
        self._set_cursor('')

        if gesture['mode'] == 'draw':
            self._draft_layer.content = ''
            x1, y1, x2, y2 = self._normalise(gesture['origin'], (x, y), image)
            minimum = MIN_BOX_PX * self._image_per_px(image)
            if x2 - x1 >= minimum and y2 - y1 >= minimum:
                self.state.add_manual_detection(x1, y1, x2, y2)
                self._set_add_mode(False)
            return

        det = self._find(image, gesture['local_id'])
        if det is None:
            return
        box = self._resolve(gesture, x, y, image)
        det.x1, det.y1, det.x2, det.y2 = box
        if box == gesture['box']:
            # A click that moved nothing: undo whatever the throttled moves left
            # on screen, but do not mark the image as edited.
            self._img.content = self._build_svg(image)
            return
        self.state.update_detection_box(gesture['local_id'], *box)

    # ---------------------------------------------------------- box maths ----

    @staticmethod
    def _find(image: ImageRecord, local_id: int) -> Detection | None:
        return next((d for d in image.detections if d.local_id == local_id), None)

    @staticmethod
    def _bounds(image: ImageRecord) -> tuple[float, float]:
        return float(image.width or 0) or 1e9, float(image.height or 0) or 1e9

    def _normalise(
            self,
            start: tuple[float, float],
            end: tuple[float, float],
            image: ImageRecord,
    ) -> tuple[float, float, float, float]:
        max_x, max_y = self._bounds(image)
        x1, x2 = sorted((start[0], end[0]))
        y1, y2 = sorted((start[1], end[1]))
        return (
            max(0.0, min(x1, max_x)), max(0.0, min(y1, max_y)),
            max(0.0, min(x2, max_x)), max(0.0, min(y2, max_y)),
        )

    def _resolve(
            self,
            gesture: dict,
            x: float,
            y: float,
            image: ImageRecord,
    ) -> tuple[float, float, float, float]:
        """Box the gesture describes, clamped to the image and to a usable size."""
        x1, y1, x2, y2 = gesture['box']
        ox, oy = gesture['origin']
        max_x, max_y = self._bounds(image)
        minimum = MIN_BOX_PX * self._image_per_px(image)

        if gesture['mode'] == 'move':
            dx = max(-x1, min(x - ox, max_x - x2))
            dy = max(-y1, min(y - oy, max_y - y2))
            return x1 + dx, y1 + dy, x2 + dx, y2 + dy

        handle = gesture['handle']
        if 'w' in handle:
            x1 = max(0.0, min(x, x2 - minimum))
        elif 'e' in handle:
            x2 = min(max_x, max(x, x1 + minimum))
        if 'n' in handle:
            y1 = max(0.0, min(y, y2 - minimum))
        elif 's' in handle:
            y2 = min(max_y, max(y, y1 + minimum))
        return x1, y1, x2, y2

    # -------------------------------------------------------------- cursor ---

    def _update_cursor(self, x: float, y: float, image: ImageRecord) -> None:
        if self._add_mode:
            self._set_cursor('crosshair')
            return
        picked = self._pick(x, y, image, GRAB_PX * self._image_per_px(image))
        self._set_cursor('crosshair' if picked is None else _CURSORS[picked[1]])

    def _set_cursor(self, cursor: str) -> None:
        cursor = cursor or 'crosshair'
        if cursor == self._cursor:
            return
        self._cursor = cursor
        self._img.style(f'cursor: {cursor};')

    # ----------------------------------------------------------- rendering ---

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
            self._gesture = None
            self._draft_layer.content = ''

            # No aspect-ratio here on purpose: the image sizes itself (see the
            # .app-canvas-image rule) and the wrapper shrink-wraps around it, so
            # the SVG overlay always lines up with what is actually painted.

        self._img.content = self._build_svg(image)

    def _draft_svg(self, gesture: dict, image: ImageRecord) -> str:
        scale = self._scale(image)
        x1, y1, x2, y2 = self._normalise(gesture['origin'], gesture['point'], image)
        return (
            f'<rect x="{x1 * scale:.1f}" y="{y1 * scale:.1f}" '
            f'width="{(x2 - x1) * scale:.1f}" height="{(y2 - y1) * scale:.1f}" '
            f'fill="{CANVAS_SELECTED_COLOR}" fill-opacity="0.12" '
            f'stroke="{CANVAS_SELECTED_COLOR}" stroke-width="{BOX_STROKE_PX:.0f}" '
            f'stroke-dasharray="8 4" vector-effect="non-scaling-stroke" '
            f'pointer-events="none"/>'
        )

    def _build_svg(self, image: ImageRecord) -> str:
        if not image.detections:
            return ''

        # Box borders use vector-effect="non-scaling-stroke" so stroke-width is
        # always in screen pixels; everything else is converted through
        # _units_per_px, which the browser keeps up to date.
        scale = self._scale(image)
        upp = self._units_per_px(image)
        font = LABEL_FONT_PX * upp
        label_h = LABEL_HEIGHT_PX * upp
        pad = LABEL_PADDING_PX * upp
        radius = 3 * upp

        selected_index = self.state.selected_detection_index
        parts: list[str] = []

        for index, det in enumerate(image.detections):
            is_selected = index == selected_index
            is_manual = det.source == DetectionSource.MANUAL
            color = CANVAS_MANUAL_COLOR if is_manual else CANVAS_AUTO_COLOR
            stroke = CANVAS_SELECTED_COLOR if is_selected else color

            # A hand-drawn box has no confidence to report; "100 %" would be a lie.
            label = f'#{det.local_id}' if is_manual else f'#{det.local_id} {det.confidence:.0%}'
            label_w = len(label) * font * 0.62 + pad * 2

            x1, y1 = det.x1 * scale, det.y1 * scale
            x2, y2 = det.x2 * scale, det.y2 * scale
            width, height = x2 - x1, y2 - y1
            label_y = y1 - label_h - upp * 2
            if label_y < 0:  # no room above the box: tuck the label inside it
                label_y = y1 + upp * 2

            parts.append(
                f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{width:.1f}" height="{height:.1f}" '
                f'fill="{stroke}" fill-opacity="{0.1 if is_selected else 0.0:.2f}" '
                f'stroke="{stroke}" stroke-width="{BOX_STROKE_PX + (1 if is_selected else 0):.0f}" '
                f'vector-effect="non-scaling-stroke" pointer-events="none" rx="{radius:.1f}"/>'
            )
            parts.append(
                f'<rect x="{x1:.1f}" y="{label_y:.1f}" width="{label_w:.1f}" height="{label_h:.1f}" '
                f'fill="{stroke}" rx="{radius:.1f}" opacity="0.92" pointer-events="none"/>'
            )
            parts.append(
                f'<text x="{x1 + pad:.1f}" y="{label_y + label_h - pad * 0.85:.1f}" '
                f'font-size="{font:.1f}" font-family="ui-monospace,monospace" '
                f'font-weight="600" fill="#FFFFFF" pointer-events="none">{label}</text>'
            )
            if is_selected:
                parts.append(self._handles_svg(x1, y1, x2, y2, upp))

        return ''.join(parts)

    @staticmethod
    def _handles_svg(x1: float, y1: float, x2: float, y2: float, upp: float) -> str:
        size = HANDLE_PX * upp
        half = size / 2
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        return ''.join(
            f'<rect x="{cx - half:.1f}" y="{cy - half:.1f}" '
            f'width="{size:.1f}" height="{size:.1f}" rx="{upp:.1f}" '
            f'fill="#FFFFFF" stroke="{CANVAS_SELECTED_COLOR}" stroke-width="2" '
            f'vector-effect="non-scaling-stroke" pointer-events="none"/>'
            for cx, cy in (
                (x1, y1), (mid_x, y1), (x2, y1),
                (x1, mid_y), (x2, mid_y),
                (x1, y2), (mid_x, y2), (x2, y2),
            )
        )

    # -------------------------------------------------------------- actions --

    def start_add_mode(self) -> None:
        if self.state.current_image is None:
            ui.notify("Chargez d'abord un dossier.", type='warning')
            return
        self._set_add_mode(not self._add_mode)
        if self._add_mode:
            ui.notify("Glissez sur l'image pour dessiner un aileron.", type='info', timeout=2000)

    def cancel_add_mode(self) -> None:
        self._set_add_mode(False)

    def _set_add_mode(self, active: bool) -> None:
        if active == self._add_mode:
            return
        self._add_mode = active
        self._set_cursor('crosshair')
        self.state.notify()

    def delete_selected(self) -> None:
        image = self.state.current_image
        if image is None or self.state.selected_detection_index is None:
            return
        index = self.state.selected_detection_index
        if 0 <= index < len(image.detections):
            self.state.delete_detection(image.detections[index].local_id)
