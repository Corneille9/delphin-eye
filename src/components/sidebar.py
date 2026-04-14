from __future__ import annotations

from nicegui import ui

from models.app_state import AppState
from models.entities import ImageStatus, STATUS_ICON, STATUS_LABEL_FR


class Sidebar:
    def __init__(self, state: AppState) -> None:
        self.state = state

        with ui.element('div').classes('app-surface').style(
            'width: 280px; height: 100%; display: flex; flex-direction: column;'
        ):
            with ui.element('div').style('padding: 12px 14px; border-bottom: 1px solid var(--color-border);'):
                ui.label('File d\'attente').classes('app-title')
                self.counter_label = ui.label('').classes('app-muted')

            self.filter = ui.select(
                options={
                    'all': 'Toutes',
                    'pending': 'En attente',
                    'validated': 'Validees',
                    'rejected': 'Rejetees',
                    'manual_edit': 'Modifiees',
                },
                value='all',
                on_change=lambda _e: self.refresh(),
            ).props('dense outlined').style('margin: 8px 14px;')

            self.list_container = ui.scroll_area().classes('flex-1').style('padding: 0 8px 12px 8px;')

        state.subscribe(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        total = self.state.total
        idx = self.state.current_index + 1 if total else 0
        self.counter_label.text = f'Image {idx} / {total}'

        self.list_container.clear()
        active_filter = self.filter.value if hasattr(self, 'filter') else 'all'

        with self.list_container:
            for index, image in enumerate(self.state.images):
                if active_filter != 'all' and image.status.value != active_filter:
                    continue
                is_active = index == self.state.current_index
                classes = 'app-queue-item'
                if is_active:
                    classes += ' active'
                row = ui.element('div').classes(classes)
                row.on('click', lambda _e, i=index: self.state.select_image(i))
                with row:
                    badge = STATUS_ICON.get(image.status, '?')
                    tooltip = STATUS_LABEL_FR.get(image.status, image.status.value)
                    ui.label(f'{index + 1:>3}.').style('color: var(--color-muted); min-width: 32px;')
                    ui.label(image.filename).style('flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;')
                    ui.label(badge).style(
                        'font-weight: 600; color: var(--color-primary);'
                    ).tooltip(tooltip)
