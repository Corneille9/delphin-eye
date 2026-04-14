from __future__ import annotations

from nicegui import events, ui

from src.models.mock_data import DashboardState


class ImageViewer:
    def __init__(self, state: DashboardState) -> None:
        self.state = state

        with ui.card().classes('w-full h-full rounded-xl bg-white shadow-sm p-3 gap-2'):
            with ui.row().classes('w-full items-center gap-3 no-wrap'):
                self.title = ui.label('').classes('text-base font-semibold text-slate-800')
                ui.space()
                ui.label('Zoom').classes('text-sm text-slate-600')
                self.zoom_slider = ui.slider(
                    min=0.7,
                    max=1.8,
                    value=1.0,
                    step=0.1,
                    on_change=lambda e: self._apply_zoom(float(e.value)),
                ).classes('w-36')

            with ui.row().classes('w-full items-center text-xs text-slate-500'):
                self.source_path = ui.label('')
                ui.space()
                self.hint = ui.label('Click a box to select it. Manual drawing area reserved for phase 2.')

            with ui.element('div').classes('w-full h-[calc(100vh-300px)] overflow-auto rounded-lg bg-slate-900 p-2'):
                self.viewer = ui.interactive_image(source='', on_mouse=self._on_mouse).classes('w-full rounded-lg')

        state.subscribe(self.refresh)
        self.refresh()

    def _on_mouse(self, event: events.MouseEventArguments) -> None:
        if event.type != 'click':
            return

        if event.image_x is None or event.image_y is None:
            return

        x = int(event.image_x)
        y = int(event.image_y)

        selected_index = None
        for index, det in enumerate(self.state.current_image.detections):
            if det.x1 <= x <= det.x2 and det.y1 <= y <= det.y2:
                selected_index = index
                break

        self.state.select_detection(selected_index)

    def _apply_zoom(self, zoom: float) -> None:
        width = int(100 * zoom)
        self.viewer.style(f'width: {width}%;')

    def _build_svg_overlay(self) -> str:
        image = self.state.current_image
        chunks: list[str] = []
        for index, det in enumerate(image.detections):
            is_selected = index == self.state.selected_detection_index
            stroke = '#2dd4bf' if is_selected else '#38bdf8'
            chunks.append(
                (
                    f"<rect x='{det.x1}' y='{det.y1}' width='{det.x2 - det.x1}' height='{det.y2 - det.y1}' "
                    f"fill='none' stroke='{stroke}' stroke-width='4' rx='6' />"
                )
            )
            chunks.append(
                (
                    f"<text x='{det.x1 + 10}' y='{max(det.y1 - 10, 20)}' fill='{stroke}' font-size='20' "
                    f"font-weight='bold'>fin {det.id} ({det.confidence:.2f})</text>"
                )
            )
        return ''.join(chunks)

    def refresh(self) -> None:
        image = self.state.current_image
        self.title.text = image.filename
        self.source_path.text = f'Source: {image.fake_source_path}'
        self.viewer.set_source(image.preview_url)
        self.viewer.content = self._build_svg_overlay()
        self.viewer.update()
