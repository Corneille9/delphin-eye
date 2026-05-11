from __future__ import annotations

import json
import uuid
from typing import Any

from nicegui import ui

from models.app_state import AppState
from models.entities import DetectionSource


KONVA_CDN = 'https://unpkg.com/konva@9/konva.min.js'


CANVAS_JS = r"""
window.DolphinCanvas = (function() {
    const state = {
        stage: null, layer: null, imageLayer: null, imageNode: null,
        transformer: null, boxes: new Map(), scale: 1, mode: 'select',
        draft: null, draftStart: null, selectedId: null,
        emit: null, containerId: null,
    };

    function resizeStage() {
        const host = document.getElementById(state.containerId);
        if (!host || !state.stage) return;
        state.stage.width(host.clientWidth);
        state.stage.height(host.clientHeight);
        state.stage.batchDraw();
    }

    function init(containerId, emit) {
        state.containerId = containerId;
        state.emit = emit;
        const host = document.getElementById(containerId);
        if (!host) return;
        host.innerHTML = '';
        state.stage = new Konva.Stage({
            container: containerId,
            width: host.clientWidth,
            height: host.clientHeight,
            draggable: false,
        });
        state.imageLayer = new Konva.Layer();
        state.layer = new Konva.Layer();
        state.stage.add(state.imageLayer);
        state.stage.add(state.layer);
        state.transformer = new Konva.Transformer({
            rotateEnabled: false,
            anchorStroke: '#2563EB',
            anchorFill: '#ffffff',
            anchorSize: 10,
            borderStroke: '#2563EB',
            borderDash: [4, 2],
        });
        state.layer.add(state.transformer);

        // Zoom
        state.stage.on('wheel', (e) => {
            e.evt.preventDefault();
            const oldScale = state.stage.scaleX();
            const pointer = state.stage.getPointerPosition();
            if (!pointer) return;
            const mousePointTo = {
                x: (pointer.x - state.stage.x()) / oldScale,
                y: (pointer.y - state.stage.y()) / oldScale,
            };
            const direction = e.evt.deltaY > 0 ? -1 : 1;
            const factor = 1.12;
            const newScale = direction > 0 ? oldScale * factor : oldScale / factor;
            const clamped = Math.max(0.1, Math.min(8, newScale));
            state.stage.scale({x: clamped, y: clamped});
            state.stage.position({
                x: pointer.x - mousePointTo.x * clamped,
                y: pointer.y - mousePointTo.y * clamped,
            });
            state.scale = clamped;
            state.stage.batchDraw();
        });

        // Pan (space + drag or middle button)
        let panning = false, lastPos = null, spaceHeld = false;
        document.addEventListener('keydown', (e) => { if (e.code === 'Space') spaceHeld = true; });
        document.addEventListener('keyup',   (e) => { if (e.code === 'Space') spaceHeld = false; });

        state.stage.on('mousedown touchstart', (e) => {
            if (state.mode === 'add') {
                const pos = getImagePos();
                if (!pos) return;
                state.draftStart = pos;
                state.draft = new Konva.Rect({
                    x: pos.x, y: pos.y, width: 1, height: 1,
                    stroke: '#F59E0B', strokeWidth: 2, dash: [6, 4],
                    strokeScaleEnabled: false,
                });
                state.layer.add(state.draft);
                return;
            }
            if (spaceHeld || e.evt.button === 1) {
                panning = true;
                lastPos = state.stage.getPointerPosition();
                e.evt.preventDefault();
                return;
            }
            if (e.target === state.stage || e.target === state.imageNode) {
                selectBox(null);
            }
        });

        state.stage.on('mousemove touchmove', () => {
            if (state.mode === 'add' && state.draft && state.draftStart) {
                const pos = getImagePos();
                if (!pos) return;
                const x = Math.min(pos.x, state.draftStart.x);
                const y = Math.min(pos.y, state.draftStart.y);
                state.draft.x(x);
                state.draft.y(y);
                state.draft.width(Math.abs(pos.x - state.draftStart.x));
                state.draft.height(Math.abs(pos.y - state.draftStart.y));
                state.layer.batchDraw();
                return;
            }
            if (panning) {
                const pos = state.stage.getPointerPosition();
                if (!pos || !lastPos) return;
                state.stage.x(state.stage.x() + pos.x - lastPos.x);
                state.stage.y(state.stage.y() + pos.y - lastPos.y);
                lastPos = pos;
                state.stage.batchDraw();
            }
        });

        state.stage.on('mouseup touchend', () => {
            if (state.mode === 'add' && state.draft) {
                const w = state.draft.width(), h = state.draft.height();
                const x = state.draft.x(), y = state.draft.y();
                state.draft.destroy();
                state.draft = null;
                state.draftStart = null;
                state.mode = 'select';
                if (w > 5 && h > 5) {
                    state.emit('canvas_add', {x1: x, y1: y, x2: x + w, y2: y + h});
                }
                state.layer.batchDraw();
                return;
            }
            panning = false;
            lastPos = null;
        });

        // Use ResizeObserver for reliable resize handling
        if (typeof ResizeObserver !== 'undefined') {
            new ResizeObserver(resizeStage).observe(host);
        } else {
            window.addEventListener('resize', resizeStage);
        }
    }

    function getImagePos() {
        const pointer = state.stage.getPointerPosition();
        if (!pointer) return null;
        return {
            x: (pointer.x - state.stage.x()) / state.stage.scaleX(),
            y: (pointer.y - state.stage.y()) / state.stage.scaleY(),
        };
    }

    // Destroy both the rect AND its label to avoid ghost labels on image switch
    function clearBoxes() {
        state.boxes.forEach((b) => {
            if (b._label) b._label.destroy();
            b.destroy();
        });
        state.boxes.clear();
        state.transformer.nodes([]);
    }

    function renderImage(data) {
        if (!state.stage) return;
        clearBoxes();
        if (state.imageNode) { state.imageNode.destroy(); state.imageNode = null; }
        if (!data || !data.url) {
            state.imageLayer.draw();
            state.layer.draw();
            return;
        }
        const img = new Image();
        img.onload = () => {
            state.imageNode = new Konva.Image({
                x: 0, y: 0,
                image: img,
                width: img.width,
                height: img.height,
                listening: true,
            });
            state.imageLayer.add(state.imageNode);
            fitToStage(img.width, img.height);
            (data.detections || []).forEach(addBox);
            if (data.selectedId != null) selectBox(data.selectedId);
            state.imageLayer.draw();
            state.layer.draw();
        };
        img.onerror = () => { state.imageLayer.draw(); };
        img.src = data.url + '?t=' + Date.now();
    }

    function fitToStage(w, h) {
        const host = document.getElementById(state.containerId);
        if (!host) return;
        const sw = host.clientWidth, sh = host.clientHeight;
        const scale = Math.min(sw / w, sh / h) * 0.97;
        state.stage.scale({x: scale, y: scale});
        state.stage.position({x: (sw - w * scale) / 2, y: (sh - h * scale) / 2});
        state.scale = scale;
        state.stage.batchDraw();
    }

    function addBox(det) {
        const isManual = det.source === 'manual';
        const color = isManual ? '#16A34A' : '#2563EB';
        const rect = new Konva.Rect({
            x: det.x1, y: det.y1,
            width: det.x2 - det.x1,
            height: det.y2 - det.y1,
            stroke: color,
            strokeWidth: 2,
            strokeScaleEnabled: false,
            draggable: true,
            name: 'bbox',
            id: 'bbox_' + det.local_id,
        });
        rect._detId = det.local_id;

        const conf = ((det.confidence || 1) * 100).toFixed(0);
        const label = new Konva.Label({x: det.x1, y: Math.max(0, det.y1 - 20)});
        label.add(new Konva.Tag({fill: color, cornerRadius: 3, opacity: 0.88}));
        label.add(new Konva.Text({
            text: '#' + det.local_id + '  ' + conf + '%',
            padding: 3,
            fill: '#ffffff',
            fontSize: 11,
            fontFamily: 'ui-monospace, monospace',
        }));
        label.scale({x: 1 / state.stage.scaleX(), y: 1 / state.stage.scaleY()});
        rect._label = label;

        rect.on('click tap', () => selectBox(det.local_id));
        rect.on('dragmove', () => {
            if (rect._label) {
                rect._label.x(rect.x());
                rect._label.y(Math.max(0, rect.y() - 20 / state.stage.scaleY()));
            }
        });
        rect.on('dragend', () => emitUpdate(rect));
        rect.on('transformend', () => {
            rect.width(rect.width() * rect.scaleX());
            rect.height(rect.height() * rect.scaleY());
            rect.scaleX(1);
            rect.scaleY(1);
            emitUpdate(rect);
        });

        state.layer.add(rect);
        state.layer.add(label);
        state.boxes.set(det.local_id, rect);
    }

    function emitUpdate(rect) {
        const payload = {
            local_id: rect._detId,
            x1: rect.x(), y1: rect.y(),
            x2: rect.x() + rect.width(), y2: rect.y() + rect.height(),
        };
        if (rect._label) {
            rect._label.x(payload.x1);
            rect._label.y(Math.max(0, payload.y1 - 20 / state.stage.scaleY()));
        }
        state.layer.batchDraw();
        state.emit('canvas_update', payload);
    }

    function selectBox(localId) {
        state.selectedId = localId;
        if (localId == null) {
            state.transformer.nodes([]);
        } else {
            const box = state.boxes.get(localId);
            if (box) state.transformer.nodes([box]);
        }
        state.layer.batchDraw();
        state.emit('canvas_select', {local_id: localId});
    }

    function setMode(mode) { state.mode = mode; }

    function deleteSelected() {
        if (state.selectedId == null) return;
        state.emit('canvas_delete', {local_id: state.selectedId});
    }

    function resetView() {
        if (state.imageNode) fitToStage(state.imageNode.width(), state.imageNode.height());
    }

    return {init, renderImage, setMode, deleteSelected, resetView, selectBox};
})();
"""


class CanvasView:
    def __init__(self, state: AppState, image_url_builder) -> None:
        self.state = state
        self._image_url = image_url_builder
        self._container_id = f'dolphin-canvas-{uuid.uuid4().hex[:8]}'
        self._initialized = False

        ui.add_head_html(f'<script src="{KONVA_CDN}"></script>')
        ui.add_head_html(f'<script>{CANVAS_JS}</script>')

        # Outer wrapper: flex column so _host grows via flex: 1.
        # position: relative enables absolute-positioned overlays.
        with ui.element('div').style(
            'flex: 1; min-height: 0; '
            'display: flex; flex-direction: column; '
            'position: relative; '
            'background: #0b1120; '
            'overflow: hidden;'
        ):
            # Konva host: grows to fill all remaining space in the flex column
            self._host = ui.element('div').style(
                'flex: 1; min-height: 300px;'
            ).props(f'id={self._container_id}')

            # ── Filename overlay (top-left, non-interactive) ─────────────
            with ui.element('div').style(
                'position: absolute; top: 10px; left: 10px; z-index: 5; '
                'pointer-events: none; max-width: 55%;'
            ):
                self.title_label = ui.label('').style(
                    'background: rgba(0,0,0,0.52); '
                    'color: rgba(255,255,255,0.88); '
                    'padding: 4px 12px; '
                    'border-radius: 6px; '
                    'font-size: 0.79rem; '
                    'font-weight: 500; '
                    'overflow: hidden; '
                    'text-overflow: ellipsis; '
                    'white-space: nowrap; '
                    'display: block;'
                )

            # ── Controls overlay (top-right) ─────────────────────────────
            with ui.element('div').style(
                'position: absolute; top: 8px; right: 8px; z-index: 5; '
                'display: flex; gap: 4px;'
            ):
                ui.button(icon='center_focus_strong', on_click=self._reset_view) \
                    .props('flat round dense') \
                    .style(
                        'background: rgba(255,255,255,0.12) !important; '
                        'color: rgba(255,255,255,0.75) !important;'
                    ) \
                    .tooltip('Recadrer')

            # ── Hint overlay (bottom-center, non-interactive) ────────────
            with ui.element('div').style(
                'position: absolute; bottom: 8px; left: 50%; '
                'transform: translateX(-50%); '
                'z-index: 5; pointer-events: none;'
            ):
                ui.label(
                    'Clic · sélectionner    Molette · zoomer    Espace+glisser · déplacer'
                ).style(
                    'background: rgba(0,0,0,0.38); '
                    'color: rgba(255,255,255,0.45); '
                    'padding: 3px 12px; '
                    'border-radius: 6px; '
                    'font-size: 0.7rem; '
                    'white-space: nowrap; '
                    'letter-spacing: 0.01em; '
                    'display: block;'
                )

        ui.on('canvas_select', self._on_select)
        ui.on('canvas_update', self._on_update)
        ui.on('canvas_delete', self._on_delete)
        ui.on('canvas_add', self._on_add)

        state.subscribe(self.refresh)
        ui.timer(0.2, self._bootstrap, once=True)

    def _bootstrap(self) -> None:
        ui.run_javascript(
            f"window.DolphinCanvas.init('{self._container_id}', "
            f"(name, payload) => window.emitEvent(name, payload));"
        )
        self._initialized = True
        self.refresh()

    def _build_payload(self) -> dict[str, Any]:
        image = self.state.current_image
        if image is None:
            return {'url': None, 'detections': [], 'selectedId': None}
        selected = None
        if (
            self.state.selected_detection_index is not None
            and 0 <= self.state.selected_detection_index < len(image.detections)
        ):
            selected = image.detections[self.state.selected_detection_index].local_id
        return {
            'url': self._image_url(image.id),
            'detections': [
                {
                    'local_id': d.local_id,
                    'x1': d.x1, 'y1': d.y1, 'x2': d.x2, 'y2': d.y2,
                    'confidence': d.confidence,
                    'source': (
                        d.source.value if isinstance(d.source, DetectionSource) else str(d.source)
                    ),
                }
                for d in image.detections
            ],
            'selectedId': selected,
        }

    def refresh(self) -> None:
        if not self._initialized:
            return
        image = self.state.current_image
        self.title_label.text = image.filename if image else ''
        payload = json.dumps(self._build_payload())
        ui.run_javascript(f'window.DolphinCanvas.renderImage({payload});')

    def start_add_mode(self) -> None:
        if self.state.current_image is None:
            return
        ui.run_javascript("window.DolphinCanvas.setMode('add');")
        ui.notify('Mode dessin - tracez une bbox sur l\'image.', type='info', timeout=2500)

    def delete_selected(self) -> None:
        ui.run_javascript('window.DolphinCanvas.deleteSelected();')

    def _reset_view(self) -> None:
        ui.run_javascript('window.DolphinCanvas.resetView();')

    # ── JS → Python events ───────────────────────────────────────────────────

    def _extract(self, event) -> dict:
        args = getattr(event, 'args', event)
        if isinstance(args, list) and args:
            args = args[0]
        return args if isinstance(args, dict) else {}

    def _on_select(self, event) -> None:
        data = self._extract(event)
        local_id = data.get('local_id')
        image = self.state.current_image
        if image is None:
            return
        if local_id is None:
            self.state.select_detection(None)
            return
        for idx, d in enumerate(image.detections):
            if d.local_id == local_id:
                self.state.select_detection(idx)
                return

    def _on_update(self, event) -> None:
        data = self._extract(event)
        if 'local_id' not in data:
            return
        self.state.update_detection_box(
            int(data['local_id']),
            float(data['x1']), float(data['y1']),
            float(data['x2']), float(data['y2']),
        )

    def _on_delete(self, event) -> None:
        data = self._extract(event)
        if 'local_id' in data:
            self.state.delete_detection(int(data['local_id']))

    def _on_add(self, event) -> None:
        data = self._extract(event)
        self.state.add_manual_detection(
            float(data.get('x1', 0)), float(data.get('y1', 0)),
            float(data.get('x2', 0)), float(data.get('y2', 0)),
        )
