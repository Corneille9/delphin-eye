from __future__ import annotations

from statistics import mean

from nicegui import ui

from src.models.mock_data import DashboardState, STATUS_COLOR


class StatusPanel:
    def __init__(self, state: DashboardState) -> None:
        self.state = state

        with ui.card().classes('w-80 h-full rounded-xl bg-white shadow-sm p-3 gap-3'):
            ui.label('Metadata').classes('text-base font-semibold text-slate-800')
            self.file_label = ui.label('').classes('text-sm text-slate-700')
            self.status_badge = ui.badge('pending')
            self.fin_count_label = ui.label('').classes('text-sm text-slate-700')
            self.confidence_label = ui.label('').classes('text-sm text-slate-700')
            self.notes = ui.textarea(label='Notes', value='', on_change=lambda e: self.state.update_notes(str(e.value))).props(
                'outlined autogrow'
            ).classes('w-full')

        state.subscribe(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        image = self.state.current_image
        self.file_label.text = f'File: {image.filename}'

        self.status_badge.text = image.status.value
        self.status_badge.props(f'color={STATUS_COLOR[image.status]}')

        self.fin_count_label.text = f'Detected fins: {len(image.detections)}'
        if image.detections:
            avg = mean(det.confidence for det in image.detections)
            self.confidence_label.text = f'Average confidence: {avg:.2f}'
        else:
            self.confidence_label.text = 'Average confidence: n/a'

        self.notes.value = image.notes
        self.notes.update()

