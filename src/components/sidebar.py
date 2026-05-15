from __future__ import annotations

from nicegui import ui

from models.app_state import AppState
from models.entities import ImageRecord, ImageStatus, STATUS_LABEL_FR


def _dot_cls(image: ImageRecord) -> str:
    if not image.has_detections:
        return 'status-dot status-dot-none'
    if image.status == ImageStatus.MODIFIED:
        return 'status-dot status-dot-manual_edit'
    return 'status-dot status-dot-detected'


class Sidebar:
    def __init__(self, state: AppState) -> None:
        self.state = state

        with ui.element('div').classes('app-surface').style(
            'width: 256px; flex-shrink: 0; display: flex; flex-direction: column; overflow: hidden;'
        ):
            with ui.element('div').style(
                'padding: 12px 14px 10px; border-bottom: 1px solid var(--color-border); flex-shrink: 0;'
            ):
                with ui.row().classes('items-center justify-between w-full no-wrap').style('margin-bottom: 8px;'):
                    ui.label("File d'attente").classes('app-title')
                    self.counter_label = ui.label('0 / 0').classes('app-caption').style(
                        'background: #F1F5F9; padding: 2px 8px; border-radius: 999px;'
                    )

                self.filter = ui.select(
                    options={
                        'all':      'Toutes les images',
                        'pending':  'En attente',
                        'detected': 'Détectées',
                        'modified': 'Modifiées',
                    },
                    value='all',
                    on_change=lambda _: self.refresh(),
                ).props('dense outlined').style('width: 100%;')

            self.list_container = ui.scroll_area().style('flex: 1; min-height: 0;')

        state.subscribe(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        total = self.state.total
        idx = self.state.current_index + 1 if total else 0
        self.counter_label.text = f'{idx} / {total}'

        active_filter = self.filter.value if hasattr(self, 'filter') else 'all'

        self.list_container.clear()
        with self.list_container:
            with ui.element('div').style('padding: 6px 8px; display: flex; flex-direction: column; gap: 2px;'):
                visible = [
                    (i, img) for i, img in enumerate(self.state.images)
                    if active_filter == 'all' or img.status.value == active_filter
                ]

                if not visible:
                    ui.label('Aucune image').classes('app-muted').style(
                        'padding: 16px 8px; text-align: center;'
                    )
                    return

                for index, image in visible:
                    is_active = index == self.state.current_index
                    dot = _dot_cls(image)
                    tip = STATUS_LABEL_FR.get(image.status, image.status.value)

                    row = ui.element('div').classes(
                        'app-queue-item' + (' active' if is_active else '')
                    )
                    row.on('click', lambda _e, i=index: self.state.select_image(i))

                    with row:
                        ui.html(f'<span class="{dot}" title="{tip}"></span>')
                        ui.label(image.filename).style(
                            'flex: 1; min-width: 0; overflow: hidden; '
                            'text-overflow: ellipsis; white-space: nowrap;'
                        )
                        ui.label(str(index + 1)).classes('app-caption').style(
                            'flex-shrink: 0; min-width: 18px; text-align: right;'
                        )
