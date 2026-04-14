from __future__ import annotations

from pathlib import Path

from nicegui import ui

from config import get_settings


class SettingsDialog:
    def __init__(self) -> None:
        self.settings = get_settings()
        with ui.dialog() as self.dialog, ui.card().style('min-width: 520px;'):
            ui.label('Parametres').classes('app-title')
            self.model_input = ui.input(
                'Chemin du modele YOLO',
                value=str(self.settings.model_path),
            ).props('outlined dense').classes('w-full')
            self.output_input = ui.input(
                'Dossier de sortie',
                value=str(self.settings.output_dir),
            ).props('outlined dense').classes('w-full')
            self.imgsz_input = ui.number(
                'Taille inference (px)',
                value=self.settings.inference_imgsz,
                min=320, max=1536, step=32,
            ).props('outlined dense').classes('w-full')
            self.conf_input = ui.number(
                'Seuil de confiance',
                value=self.settings.inference_conf,
                min=0.05, max=0.95, step=0.05,
            ).props('outlined dense').classes('w-full')

            with ui.row().classes('w-full justify-end'):
                ui.button('Annuler', on_click=self.dialog.close).props('flat no-caps')
                ui.button('Enregistrer', on_click=self._save).props('no-caps').classes('app-primary')

    def _save(self) -> None:
        self.settings.model_path = Path(str(self.model_input.value))
        self.settings.output_dir = Path(str(self.output_input.value))
        self.settings.validated_dir = self.settings.output_dir / 'validated_images'
        self.settings.rejected_dir = self.settings.output_dir / 'rejected'
        self.settings.crops_dir = self.settings.output_dir / 'cropped_fins'
        self.settings.annotations_dir = self.settings.output_dir / 'annotations'
        self.settings.inference_imgsz = int(self.imgsz_input.value or 640)
        self.settings.inference_conf = float(self.conf_input.value or 0.25)
        self.settings.save_user_overrides()
        self.settings.ensure_directories()
        ui.notify('Parametres enregistres.', type='positive')
        self.dialog.close()

    def open(self) -> None:
        self.dialog.open()
