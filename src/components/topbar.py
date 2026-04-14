from __future__ import annotations

from typing import Callable

from nicegui import ui

from models.app_state import AppState


class TopBar:
    def __init__(
        self,
        state: AppState,
        on_select_folder: Callable[[], None],
        on_run_detection: Callable[[], None],
        on_export: Callable[[], None],
        on_open_settings: Callable[[], None],
    ) -> None:
        self.state = state

        with ui.element('div').classes('app-surface w-full').style('padding: 12px 16px;'):
            with ui.row().classes('w-full items-center gap-3 no-wrap'):
                ui.icon('waves').style('color: var(--color-primary); font-size: 1.6rem;')
                ui.label('Dolphin Fin Sorter').classes('app-title')
                self.folder_label = ui.label('Aucun dossier selectionne').classes('app-muted app-hide-md')
                ui.space()
                ui.button('Choisir dossier', icon='folder_open', on_click=on_select_folder) \
                    .props('no-caps flat').classes('app-outline')
                self.run_button = ui.button(
                    'Lancer detection', icon='play_arrow', on_click=on_run_detection
                ).props('no-caps').classes('app-primary')
                ui.button('Exporter resultats', icon='file_download', on_click=on_export) \
                    .props('no-caps flat').classes('app-outline')
                ui.button(icon='settings', on_click=on_open_settings) \
                    .props('flat round').tooltip('Parametres')

            with ui.row().classes('w-full items-center gap-3').style('margin-top: 8px;'):
                self.progress = ui.linear_progress(value=0.0, show_value=False).classes('flex-1')
                self.progress_label = ui.label('Progression : 0 / 0').classes('app-muted')

        state.subscribe(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        done, total = self.state.detection_progress
        if total <= 0:
            total = max(self.state.total, 1)
            done = sum(1 for i in self.state.images if i.status.value != 'pending')
        self.progress.value = done / total if total else 0.0
        self.progress_label.text = f'Progression : {done} / {total}'

        if self.state.queue.folder is None:
            self.folder_label.text = 'Aucun dossier selectionne'
        else:
            self.folder_label.text = f'Dossier : {self.state.queue.folder}'

        if self.state.prediction.running:
            self.run_button.props('loading')
        else:
            self.run_button.props(remove='loading')
