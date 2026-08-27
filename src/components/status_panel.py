from __future__ import annotations

from statistics import mean

from nicegui import ui

from models.app_state import AppState
from models.entities import (
    STATUS_BADGE_CLASS, STATUS_DOT_CLASS, STATUS_LABEL_FR, ImageStatus,
)


class StatusPanel:
    def __init__(self, state: AppState) -> None:
        self.state = state

        with ui.element('div').classes('app-pane app-pane-right app-hide-md'):
            with ui.element('div').classes('app-pane-header'):
                ui.label('Informations').classes('app-title')

            with ui.scroll_area().style('flex: 1; min-height: 0;'):
                with ui.element('div').style('padding: 12px 14px; display: flex; flex-direction: column; gap: 12px;'):
                    self.file_label = ui.label('').style(
                        'font-size: 0.82rem; font-weight: 600; color: var(--color-text); '
                        'word-break: break-all;'
                    )

                    # Status badge
                    with ui.element('div').style('display: flex; align-items: center; gap: 8px;'):
                        ui.label('Statut').classes('app-muted').style('flex-shrink: 0;')
                        self.status_badge = ui.html('')

                    ui.separator().style('margin: 0;')

                    # Detection stats
                    with ui.element('div').style('display: flex; flex-direction: column; gap: 4px;'):
                        ui.label('Détections').classes('app-title').style('font-size: 0.78rem;')
                        self.fin_count = ui.label('').classes('app-muted')
                        self.confidence = ui.label('').classes('app-caption')

                    ui.separator().style('margin: 0;')

                    # Queue distribution
                    with ui.element('div').style('display: flex; flex-direction: column; gap: 6px;'):
                        ui.label('Répartition').classes('app-title').style('font-size: 0.78rem;')
                        self.counts_container = ui.element('div').style(
                            'display: flex; flex-direction: column; gap: 4px;'
                        )

                    ui.separator().style('margin: 0;')

                    # Notes
                    with ui.element('div').style('display: flex; flex-direction: column; gap: 6px;'):
                        ui.label('Notes').classes('app-title').style('font-size: 0.78rem;')
                        self.notes = ui.textarea(
                            placeholder="Commentaires sur l'image…",
                            on_change=lambda e: self.state.update_notes(str(e.value or '')),
                        ).props('outlined autogrow dense').classes('w-full')

        state.subscribe(self.refresh)
        self.refresh()

    def _status_row(self, status: ImageStatus, label: str, value: int) -> None:
        with ui.row().classes('items-center gap-2 no-wrap'):
            ui.html(f'<span class="{STATUS_DOT_CLASS[status]}"></span>')
            ui.label(label).classes('app-muted').style('flex: 1;')
            ui.label(str(value)).style(
                'font-size: 0.79rem; font-weight: 600; color: var(--color-text);'
            )

    def refresh(self) -> None:
        image = self.state.current_image

        if image is None:
            self.file_label.text = 'Aucune image sélectionnée'
            self.status_badge.content = ''
            self.fin_count.text = ''
            self.confidence.text = ''
            self.counts_container.clear()
            self.notes.value = ''
            self.notes.update()
            return

        self.file_label.text = image.filename

        badge_cls = STATUS_BADGE_CLASS.get(image.status, 'app-badge')
        self.status_badge.content = (
            f'<span class="{badge_cls}">{STATUS_LABEL_FR.get(image.status, "")}</span>'
        )

        # The badge above already carries the status; these two lines add the
        # numbers it cannot.
        self.fin_count.text = f'Ailerons : {len(image.detections)}'
        if image.detections:
            avg = mean(d.confidence for d in image.detections)
            self.confidence.text = f'Confiance moyenne : {avg:.0%}'
        else:
            self.confidence.text = 'Confiance moyenne : —'

        counts = self.state.counts()

        self.counts_container.clear()
        with self.counts_container:
            self._status_row(ImageStatus.PENDING, 'En attente', counts[ImageStatus.PENDING])
            self._status_row(ImageStatus.DETECTED, 'Avec ailerons', counts[ImageStatus.DETECTED])
            self._status_row(ImageStatus.EMPTY, 'Sans aileron', counts[ImageStatus.EMPTY])
            self._status_row(ImageStatus.MODIFIED, 'Modifiées', counts[ImageStatus.MODIFIED])
            if counts[ImageStatus.FAILED]:
                self._status_row(ImageStatus.FAILED, 'En échec', counts[ImageStatus.FAILED])

        if self.notes.value != image.notes:
            self.notes.value = image.notes
            self.notes.update()
