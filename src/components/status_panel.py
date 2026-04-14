from __future__ import annotations

from statistics import mean

from nicegui import ui

from models.app_state import AppState
from models.entities import ImageStatus, STATUS_BADGE_CLASS, STATUS_LABEL_FR


class StatusPanel:
    def __init__(self, state: AppState) -> None:
        self.state = state

        with ui.element('div').classes('app-surface app-hide-md').style(
            'width: 320px; height: 100%; display: flex; flex-direction: column; padding: 14px;'
        ):
            ui.label('Informations image').classes('app-title')

            self.file_label = ui.label('').classes('app-muted').style('margin-top: 8px;')
            self.path_label = ui.label('').classes('app-muted').style('font-size: 0.75rem; word-break: break-all;')

            with ui.row().classes('items-center gap-2').style('margin-top: 10px;'):
                ui.label('Statut :').classes('app-muted')
                self.status_badge = ui.html('')

            self.fin_count = ui.label('').style('margin-top: 8px;')
            self.confidence = ui.label('').classes('app-muted')
            self.size_label = ui.label('').classes('app-muted')

            ui.separator().style('margin: 10px 0;')
            ui.label('Repartition').classes('app-title').style('font-size: 0.95rem;')
            self.counts_label = ui.label('').classes('app-muted')

            ui.separator().style('margin: 10px 0;')
            ui.label('Notes').classes('app-title').style('font-size: 0.95rem;')
            self.notes = ui.textarea(
                placeholder='Commentaires sur l\'image',
                on_change=lambda e: self.state.update_notes(str(e.value or '')),
            ).props('outlined autogrow dense').classes('w-full')

        state.subscribe(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        image = self.state.current_image
        if image is None:
            self.file_label.text = 'Aucune image'
            self.path_label.text = ''
            self.status_badge.content = ''
            self.fin_count.text = ''
            self.confidence.text = ''
            self.size_label.text = ''
            self.counts_label.text = ''
            self.notes.value = ''
            self.notes.update()
            return

        self.file_label.text = f'Fichier : {image.filename}'
        self.path_label.text = str(image.absolute_path)
        badge_class = STATUS_BADGE_CLASS.get(image.status, 'app-badge')
        self.status_badge.content = f'<span class="{badge_class}">{STATUS_LABEL_FR.get(image.status, "")}</span>'
        self.fin_count.text = f'Ailerons detectes : {len(image.detections)}'
        if image.detections:
            avg = mean(d.confidence for d in image.detections)
            self.confidence.text = f'Confiance moyenne : {avg:.2f}'
        else:
            self.confidence.text = 'Confiance moyenne : -'
        if image.width and image.height:
            self.size_label.text = f'Dimensions : {image.width} x {image.height}'
        else:
            self.size_label.text = 'Dimensions : inconnues'

        counts = self.state.counts()
        self.counts_label.text = (
            f'En attente : {counts.get(ImageStatus.PENDING, 0)}   '
            f'Validees : {counts.get(ImageStatus.VALIDATED, 0)}   '
            f'Rejetees : {counts.get(ImageStatus.REJECTED, 0)}   '
            f'Modifiees : {counts.get(ImageStatus.MANUAL_EDIT, 0)}'
        )
        if self.notes.value != image.notes:
            self.notes.value = image.notes
            self.notes.update()
