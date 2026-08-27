from __future__ import annotations

import inspect
import os
from typing import Callable

from nicegui import ui

from models.app_state import AppState

LOGO_URL = '/assets/web-app-manifest-192x192.png'


class TopBar:
    def __init__(
            self,
            state: AppState,
            on_select_folder: Callable[[], None],
            on_reset_folder: Callable[[], None],
            on_run_detection: Callable[[], None],
            on_export: Callable[[], None],
            on_open_export_folder: Callable[[], None],
            on_open_settings: Callable[[], None],
    ) -> None:
        self.state = state
        self._on_select_folder = on_select_folder
        self._on_reset_folder = on_reset_folder

        with ui.element('div').classes('app-pane app-pane-top').style('padding: 10px 16px;'):
            with ui.row().classes('w-full items-center gap-3 no-wrap'):
                with ui.element('div').style(
                        'display: flex; align-items: center; gap: 8px; flex-shrink: 0;'
                ):
                    ui.image(LOGO_URL).props('no-spinner fit=contain').style(
                        'width: 26px; height: 26px; flex-shrink: 0;'
                    )
                    ui.label('Delphin Eye').classes('app-brand')

                self.folder_label = (
                    ui.label('Aucun dossier sélectionné')
                    .classes('app-muted app-hide-md')
                    .style(
                        'overflow: hidden; text-overflow: ellipsis; '
                        'white-space: nowrap; max-width: 280px;'
                    )
                )

                ui.space()

                with ui.element('div').classes('app-hide-md').style(
                        'display: flex; align-items: center; gap: 8px; flex-shrink: 0;'
                ):
                    self.progress = ui.linear_progress(value=0.0, show_value=False) \
                        .props('rounded') \
                        .style('width: 110px; height: 6px;')
                    self.progress_label = ui.label('0 / 0').classes('app-caption').style(
                        'white-space: nowrap; min-width: 44px; text-align: right;'
                    )

                self.folder_btn = (
                    ui.button('Dossier', icon='folder_open',
                              on_click=self._handle_folder_click, color=None)
                    .props('no-caps flat dense padding="6px 14px"')
                    .classes('app-outline')
                )

                self.run_button = ui.button(
                    'Détecter', icon='play_arrow', on_click=on_run_detection
                ).props('no-caps unelevated padding="7px 16px"')

                self.export_btn = (
                    ui.button('Exporter', icon='file_download', on_click=on_export, color=None)
                    .props('no-caps flat dense padding="6px 14px"')
                    .classes('app-outline')
                )

                self.open_export_btn = (
                    ui.button(icon='folder_open', on_click=on_open_export_folder, color=None)
                    .props('flat round dense')
                    .classes('app-ghost')
                )
                with self.open_export_btn:
                    self.open_export_tip = ui.tooltip('Ouvrir le dossier des images triées')

                ui.button(icon='settings', on_click=on_open_settings, color=None) \
                    .props('flat round dense') \
                    .classes('app-ghost') \
                    .tooltip('Paramètres')

        state.subscribe(self.refresh)
        self.refresh()

    async def _handle_folder_click(self) -> None:
        if self.state.queue.folder is None:
            result = self._on_select_folder()
            if inspect.isawaitable(result):
                await result
        else:
            self._on_reset_folder()

    def refresh(self) -> None:
        done, total = self.state.detection_progress
        if not self.state.prediction.running:
            # Between runs the bar shows how far the folder as a whole has got.
            done, total = self.state.analysed_count, self.state.total
        self.progress.value = done / total if total else 0.0
        self.progress_label.text = f'{done} / {total}'

        folder = self.state.queue.folder
        if folder is None:
            self.folder_label.text = 'Aucun dossier sélectionné'
            self.folder_btn.text = 'Dossier'
            self.folder_btn.props('icon=folder_open')
            self.folder_btn.classes(remove='app-ghost-danger', add='app-outline')
        else:
            name = os.path.basename(str(folder)) or str(folder)
            self.folder_label.text = name
            self.folder_btn.text = 'Réinitialiser'
            self.folder_btn.props('icon=folder_off')
            self.folder_btn.classes(remove='app-outline', add='app-ghost-danger')

        triees = self.state.triees_dir
        self.open_export_tip.text = (
            f'Ouvrir le dossier des images triées : {triees}' if triees
            else 'Ouvrir le dossier des images triées'
        )

        busy = self.state.prediction.running or self.state.export_running

        if self.state.prediction.running:
            self.run_button.props('loading')
        else:
            self.run_button.props(remove='loading')
        if busy:
            self.run_button.disable()
        else:
            self.run_button.enable()

        if self.state.export_running:
            self.export_btn.props('loading')
        else:
            self.export_btn.props(remove='loading')
        if busy:
            self.export_btn.disable()
        else:
            self.export_btn.enable()
