from __future__ import annotations

from nicegui import ui

from src.models.mock_data import DashboardState


class ActionToolbar:
    def __init__(self, state: DashboardState) -> None:
        with ui.card().classes('w-full rounded-xl bg-white shadow-sm px-3 py-2'):
            with ui.row().classes('w-full items-center justify-between gap-2 no-wrap'):
                ui.button('Previous (←)', icon='chevron_left', on_click=state.previous_image).props('outline no-caps')
                ui.button('Next (→)', icon='chevron_right', on_click=state.next_image).props('outline no-caps')
                ui.separator().props('vertical').classes('h-8')
                ui.button('Validate (Enter)', icon='check', on_click=state.validate_current).props(
                    'color=positive no-caps'
                )
                ui.button('Reject', icon='close', on_click=state.reject_current).props('color=negative no-caps')
                ui.button('Add Box (A)', icon='add_box', on_click=state.add_mock_detection).props('outline no-caps')
                ui.button('Delete Box (Del)', icon='delete', on_click=state.delete_selected_detection).props(
                    'outline no-caps'
                )

