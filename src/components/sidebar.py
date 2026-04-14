from __future__ import annotations

from nicegui import ui

from src.models.mock_data import DashboardState, STATUS_ICON


class Sidebar:
    def __init__(self, state: DashboardState) -> None:
        self.state = state

        with ui.card().classes('w-72 h-full rounded-xl bg-white shadow-sm'):
            ui.label('Image queue').classes('text-base font-semibold px-4 pt-3 text-slate-800')
            ui.separator()
            with ui.scroll_area().classes('w-full h-[calc(100vh-190px)] px-2 pb-2') as self.list_container:
                pass

        state.subscribe(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        self.list_container.clear()
        with self.list_container:
            for index, image in enumerate(self.state.images):
                icon = STATUS_ICON[image.status]
                is_active = index == self.state.current_index
                label = f'{image.filename}  {icon}'

                button = ui.button(label, on_click=lambda i=index: self.state.select_image(i)).props(
                    'flat no-caps align=left'
                )
                button.classes('w-full justify-start text-left rounded-lg')
                if is_active:
                    button.classes('bg-cyan-1 text-cyan-9')

