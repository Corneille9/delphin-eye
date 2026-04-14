from __future__ import annotations

from typing import Callable

from nicegui import ui

from models.app_state import AppState


class ActionToolbar:
    def __init__(
        self,
        state: AppState,
        on_add_box: Callable[[], None],
        on_delete_box: Callable[[], None],
    ) -> None:
        self.state = state

        with ui.element('div').classes('app-surface w-full').style('padding: 8px 12px;'):
            with ui.row().classes('w-full items-center gap-2 no-wrap'):
                ui.button('Precedente', icon='chevron_left', on_click=state.previous_image) \
                    .props('flat no-caps').classes('app-outline').tooltip('Fleche gauche')
                ui.button('Suivante', icon='chevron_right', on_click=state.next_image) \
                    .props('flat no-caps').classes('app-outline').tooltip('Fleche droite')
                ui.separator().props('vertical')
                ui.button('Valider', icon='check', on_click=state.validate_current) \
                    .props('no-caps').style(
                        'background: var(--color-validation); color: white;'
                    ).tooltip('Entree')
                ui.button('Rejeter', icon='close', on_click=state.reject_current) \
                    .props('no-caps').style(
                        'background: var(--color-danger); color: white;'
                    ).tooltip('R')
                ui.separator().props('vertical')
                ui.button('Ajouter bbox', icon='add_box', on_click=on_add_box) \
                    .props('flat no-caps').classes('app-outline').tooltip('A')
                ui.button('Supprimer bbox', icon='delete', on_click=on_delete_box) \
                    .props('flat no-caps').classes('app-outline').tooltip('Suppr')
