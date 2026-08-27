from __future__ import annotations

from pathlib import Path

from nicegui import ui

from config import get_settings
from config.settings import ModelEntry
from models.app_state import AppState
from services.export_service import ExportService

_CUSTOM_ID = 'custom'


class SettingsDialog:
    def __init__(self, state: AppState) -> None:
        self._state = state
        self._settings = get_settings()

        initial_id = self._current_model_id()

        with ui.dialog() as self.dialog, ui.card().style('min-width: 540px;'):
            ui.label('Paramètres').classes('app-title')

            self._model_select = (
                ui.select(
                    options=self._build_model_options(),
                    value=initial_id,
                    label='Modèle',
                    on_change=self._on_model_change,
                )
                .props('outlined dense')
                .classes('w-full')
            )

            self._model_path_input = (
                ui.input('Chemin du modèle (.pt)', value=str(self._settings.model_path))
                .props('outlined dense')
                .classes('w-full')
            )
            self._model_path_input.set_visibility(initial_id == _CUSTOM_ID)

            self._mode_select = (
                ui.select(
                    options={'yolo': 'YOLO · rapide', 'sahi': 'SAHI · découpé (lent, précis sur grandes images)'},
                    value=self._settings.inference_mode,
                    label='Mode de détection',
                )
                .props('outlined dense')
                .classes('w-full')
            )

            self._imgsz_input = (
                ui.number('Taille inférence (px)', value=self._settings.inference_imgsz,
                          min=320, max=1536, step=32)
                .props('outlined dense')
                .classes('w-full')
            )
            self._conf_input = (
                ui.number('Seuil de confiance', value=self._settings.inference_conf,
                          min=0.05, max=0.95, step=0.05)
                .props('outlined dense')
                .classes('w-full')
            )
            self._margin_input = (
                ui.number('Marge de recadrage (px)', value=self._settings.crop_margin,
                          min=0, max=500, step=10)
                .props('outlined dense')
                .classes('w-full')
            )

            ui.separator().style('margin: 12px 0 8px;')
            ui.label("Aperçu de l'export").style(
                'font-size: 0.78rem; font-weight: 600; color: var(--color-text); margin-bottom: 4px;'
            )
            self._preview = ui.html('').style('font-size: 0.8rem;')

            with ui.row().classes('w-full justify-end').style('margin-top: 16px;'):
                ui.button('Annuler', on_click=self.dialog.close, color=None) \
                    .props('flat no-caps').classes('app-ghost')
                ui.button('Enregistrer', on_click=self._save).props('no-caps unelevated')

    def _build_model_options(self) -> dict[str, str]:
        options: dict[str, str] = {}
        for entry in self._settings.model_catalog:
            label = entry.name
            if entry.recommended:
                label += ' ★'
            options[entry.id] = label
        options[_CUSTOM_ID] = 'Modèle personnalisé…'
        return options

    def _current_model_id(self) -> str:
        if self._settings.model_id:
            return self._settings.model_id
        current = self._settings.model_path.resolve()
        for entry in self._settings.model_catalog:
            if entry.path.resolve() == current:
                return entry.id
        return _CUSTOM_ID

    def _on_model_change(self, e) -> None:
        selected_id = e.value
        is_custom = selected_id == _CUSTOM_ID
        self._model_path_input.set_visibility(is_custom)
        if not is_custom:
            entry = self._find_entry(selected_id)
            if entry:
                self._imgsz_input.value = entry.imgsz

    def _find_entry(self, model_id: str) -> ModelEntry | None:
        return next((m for m in self._settings.model_catalog if m.id == model_id), None)

    def _save(self) -> None:
        selected_id = self._model_select.value
        if selected_id == _CUSTOM_ID:
            self._settings.model_path = Path(str(self._model_path_input.value))
            self._settings.model_id = ''
        else:
            entry = self._find_entry(selected_id)
            if entry:
                self._settings.model_path = entry.path
                self._settings.model_id = entry.id

        self._settings.inference_mode = self._mode_select.value
        self._settings.inference_imgsz = int(self._imgsz_input.value or 640)
        self._settings.inference_conf = float(self._conf_input.value or 0.25)
        self._settings.crop_margin = int(self._margin_input.value or 100)
        self._settings.save_user_overrides()
        self._state.prediction.reset_model()
        ui.notify('Paramètres enregistrés.', type='positive')
        self.dialog.close()

    def _update_preview(self) -> None:
        folder = self._state.queue.folder
        if folder is None:
            self._preview.content = (
                '<span style="color: var(--color-muted); font-style: italic;">'
                'Aucun dossier sélectionné.'
                '</span>'
            )
            return

        triees = ExportService.compute_triees_path(folder)
        corrections = ExportService.compute_corrections_path(folder)

        detected = sum(1 for img in self._state.images if img.will_export)
        modified = sum(1 for img in self._state.images if img.status.value == 'modified')

        self._preview.content = (
            '<div style="font-family: ui-monospace, monospace; line-height: 1.9; '
            'background: var(--color-surface-muted); border-radius: 8px; padding: 10px 14px;">'
            f'<div>📁 <strong>{triees.name}/</strong></div>'
            '<div style="margin-left: 20px; color: var(--color-muted);">'
            f'└─ {detected} image{"s" if detected != 1 else ""} avec ailerons détectés'
            '</div>'
            '<div style="margin-top: 6px;">📁 <strong>{corr}/</strong></div>'
            '<div style="margin-left: 20px; color: var(--color-muted);">'
            f'└─ {modified} image{"s" if modified != 1 else ""} modifiée{"s" if modified != 1 else ""} manuellement'
            '<br>'
            '<span style="margin-left: 0;">└─ labels YOLO (.txt) inclus</span>'
            '</div>'
            '</div>'
        ).replace('{corr}', corrections.name)

    def open(self) -> None:
        self._update_preview()
        self.dialog.open()