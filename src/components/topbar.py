from __future__ import annotations

from typing import Callable

from nicegui import ui

from src.models.mock_data import DashboardState


class TopBar:
    def __init__(
        self,
        state: DashboardState,
        on_select_folder: Callable[[], None],
        on_run_detection: Callable[[], None],
        on_export: Callable[[], None],
    ) -> None:
        self.state = state

        with ui.card().classes('w-full px-4 py-3 shadow-sm rounded-xl bg-white'):
            with ui.row().classes('w-full items-center gap-3 no-wrap'):
                ui.icon('water').classes('text-cyan-6 text-2xl')
                ui.label('Dolphin Fin Sorter').classes('text-xl font-semibold text-slate-800')
                ui.space()
                ui.button('Select folder', icon='folder_open', on_click=on_select_folder).props('outline no-caps')
                self.run_button = ui.button('Run detection', icon='play_arrow', on_click=on_run_detection).props(
                    'color=primary no-caps'
                )
                ui.button('Export results', icon='file_download', on_click=on_export).props('outline no-caps')

            with ui.row().classes('w-full items-center gap-3 mt-2'):
                self.progress = ui.linear_progress(value=0.0).classes('flex-1')
                self.progress_label = ui.label('Progress: 0 / 0').classes('text-sm text-slate-600')

        state.subscribe(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        total = max(self.state.total_images, 1)
        current = self.state.processed_images
        self.progress.value = current / total
        self.progress_label.text = f'Progress: {current} / {self.state.total_images}'

        if self.state.detection_running:
            self.run_button.disable()
        else:
            self.run_button.enable()

