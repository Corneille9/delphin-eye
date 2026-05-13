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

        with ui.element('div').style(
            'flex-shrink: 0; '
            'padding: 8px 14px; '
            'border-top: 1px solid var(--color-border); '
            'background: var(--color-surface);'
        ):
            with ui.row().classes('w-full items-center gap-2 no-wrap'):

                # ── Image info (left) ──────────────────────────────────
                with ui.element('div').style(
                    'flex: 0 1 220px; min-width: 0; '
                    'display: flex; flex-direction: column; justify-content: center;'
                ):
                    self.image_label = ui.label('Aucune image').style(
                        'font-size: 0.79rem; font-weight: 600; color: var(--color-text); '
                        'overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'
                    )
                    self.index_label = ui.label('').classes('app-caption')

                ui.space()

                # ── Navigation ─────────────────────────────────────────
                ui.button(icon='chevron_left', on_click=state.previous_image) \
                    .props('flat round dense') \
                    .classes('app-ghost') \
                    .tooltip('← Image précédente')

                ui.button(icon='chevron_right', on_click=state.next_image) \
                    .props('flat round dense') \
                    .classes('app-ghost') \
                    .tooltip('→ Image suivante')

                ui.element('div').classes('toolbar-sep')

                # ── BBox editing ───────────────────────────────────────
                ui.button('Ajouter aileron', icon='add_box', on_click=on_add_box) \
                    .props('flat no-caps dense padding="6px 12px"') \
                    .classes('app-outline') \
                    .tooltip('A · glissez sur l\'image pour dessiner')

                ui.button(icon='delete_outline', on_click=on_delete_box) \
                    .props('flat round dense') \
                    .classes('app-ghost') \
                    .tooltip('Suppr · supprimer l\'aileron sélectionné')

        state.subscribe(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        image = self.state.current_image
        if image is None:
            self.image_label.text = 'Aucune image'
            self.index_label.text = ''
        else:
            self.image_label.text = image.filename
            idx = self.state.current_index + 1
            total = self.state.total
            n = len(image.detections)
            det_str = f'  ·  {n} aileron{"s" if n > 1 else ""}' if n else '  ·  aucun aileron'
            self.index_label.text = f'Image {idx} / {total}{det_str}'
