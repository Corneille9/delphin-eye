from __future__ import annotations

from nicegui import ui

from models.app_state import AppState
from models.entities import STATUS_DOT_CLASS, STATUS_LABEL_FR, ImageStatus

FILTER_OPTIONS: dict[str, str] = {
    'all': 'Toutes les images',
    'pending': 'En attente',
    'detected': 'Avec ailerons',
    'empty': 'Sans aileron',
    'modified': 'Modifiées',
    'failed': 'En échec',
}

_SCROLL_ACTIVE_INTO_VIEW = (
    "const el = document.querySelector('.app-queue-item.active');"
    "if (el) el.scrollIntoView({block: 'nearest'});"
)


class Sidebar:
    def __init__(self, state: AppState) -> None:
        self.state = state
        self._last_index: int | None = None

        with ui.element('div').classes('app-pane app-pane-left'):
            with ui.element('div').classes('app-pane-header'):
                with ui.row().classes('items-center justify-between w-full no-wrap').style('margin-bottom: 8px;'):
                    ui.label("File d'attente").classes('app-title')
                    self.counter_label = ui.label('0 / 0').classes('app-caption').style(
                        'background: var(--color-surface-muted); '
                        'padding: 2px 8px; border-radius: 999px;'
                    )

                self.filter = ui.select(
                    options=FILTER_OPTIONS,
                    value=state.queue_filter,
                    on_change=lambda e: state.set_queue_filter(str(e.value)),
                ).props('dense outlined').style('width: 100%;')

            self.list_container = ui.scroll_area().style('flex: 1; min-height: 0;')

        state.subscribe(self.refresh)
        self.refresh()

    def _scroll_active_into_view(self) -> None:
        try:
            ui.run_javascript(_SCROLL_ACTIVE_INTO_VIEW)
        except Exception:
            # Refreshes coming from a background thread have no client context.
            # Those never move the selection, so nothing is lost by skipping.
            pass

    def refresh(self) -> None:
        visible = self.state.visible_indexes()
        current = self.state.current_index

        # Position within the filtered view, which is what the list shows.
        position = visible.index(current) + 1 if current in visible else 0
        self.counter_label.text = f'{position} / {len(visible)}'

        self.list_container.clear()
        with self.list_container:
            with ui.element('div').style('padding: 6px 8px; display: flex; flex-direction: column; gap: 2px;'):
                if not visible:
                    ui.label('Aucune image').classes('app-muted').style(
                        'padding: 16px 8px; text-align: center;'
                    )
                    return

                for index in visible:
                    image = self.state.images[index]
                    dot = STATUS_DOT_CLASS.get(
                        image.status, STATUS_DOT_CLASS[ImageStatus.PENDING]
                    )
                    tip = STATUS_LABEL_FR.get(image.status, image.status.value)
                    count = len(image.detections)

                    row = ui.element('div').classes(
                        'app-queue-item' + (' active' if index == current else '')
                    )
                    row.on('click', lambda _e, i=index: self.state.select_image(i))

                    with row:
                        ui.html(f'<span class="{dot}" title="{tip}"></span>')
                        ui.label(image.filename).style(
                            'flex: 1; min-width: 0; overflow: hidden; '
                            'text-overflow: ellipsis; white-space: nowrap;'
                        )
                        if count:
                            ui.label(str(count)).classes('app-queue-count').tooltip(
                                f'{count} aileron{"s" if count > 1 else ""}'
                            )
                        ui.label(str(index + 1)).classes('app-caption').style(
                            'flex-shrink: 0; min-width: 18px; text-align: right;'
                        )

        if current != self._last_index:
            self._last_index = current
            self._scroll_active_into_view()
