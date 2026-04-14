from __future__ import annotations

from pathlib import Path

from nicegui import events, ui

from components import (
    ActionToolbar,
    CanvasView,
    SettingsDialog,
    Sidebar,
    StatusPanel,
    TopBar,
)
from config import apply_theme, get_settings
from models.app_state import AppState
from services.export_service import ExportService
from services.image_queue_service import ImageQueueService
from services.persistence_service import PersistenceService
from services.prediction_service import PredictionService


def _pick_folder_native() -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    try:
        folder = filedialog.askdirectory(title='Choisir un dossier d\'images')
    finally:
        root.destroy()
    return folder or None


def _build_state() -> AppState:
    persistence = PersistenceService()
    queue = ImageQueueService(persistence)
    prediction = PredictionService(persistence)
    export = ExportService()
    return AppState(persistence, queue, prediction, export)


def register_dashboard_page(image_url_builder) -> None:
    @ui.page('/')
    def dashboard_page() -> None:
        settings = get_settings()
        apply_theme()
        state = _build_state()
        state.try_resume()

        settings_dialog = SettingsDialog()

        def manual_folder_dialog() -> None:
            with ui.dialog() as dialog, ui.card():
                ui.label('Entrer le chemin du dossier').classes('app-title')
                inp = ui.input('Chemin', value=str(state.queue.folder or '')) \
                    .props('outlined dense').classes('w-full').style('min-width: 420px;')
                with ui.row().classes('w-full justify-end'):
                    ui.button('Annuler', on_click=dialog.close).props('flat no-caps')
                    def confirm():
                        path = Path(str(inp.value or '')).expanduser()
                        dialog.close()
                        _load_folder(path)
                    ui.button('Ouvrir', on_click=confirm).props('no-caps').classes('app-primary')
            dialog.open()

        def _load_folder(path: Path) -> None:
            if not path or not path.is_dir():
                ui.notify(f'Dossier introuvable : {path}', type='negative')
                return
            try:
                state.load_folder(path)
                ui.notify(f'{state.total} images chargees.', type='positive')
            except Exception as exc:
                ui.notify(f'Erreur : {exc}', type='negative')

        def on_select_folder() -> None:
            folder = _pick_folder_native()
            if folder:
                _load_folder(Path(folder))
            else:
                manual_folder_dialog()

        def on_run_detection() -> None:
            if state.total == 0:
                ui.notify('Chargez d\'abord un dossier.', type='warning')
                return
            if not state.prediction.model_available():
                ui.notify(
                    f'Modele YOLO introuvable : {settings.model_path}',
                    type='negative',
                )
                return
            if state.prediction.running:
                ui.notify('Detection deja en cours.', type='info')
                return

            def on_update() -> None:
                state.notify()

            def on_finished(processed: int) -> None:
                state.queue.refresh()
                state.notify()
                ui.notify(f'Detection terminee : {processed} images traitees.', type='positive')

            ui.notify('Detection demarree en arriere-plan...', type='info')
            state.run_detection(on_update, on_finished)

        def on_export() -> None:
            if state.total == 0:
                ui.notify('Rien a exporter.', type='warning')
                return
            try:
                summary = state.export.export_all(state.images)
                ui.notify(
                    f"Export OK : {summary['validated']} validees, "
                    f"{summary['rejected']} rejetees - {summary['output_dir']}",
                    type='positive',
                )
            except Exception as exc:
                ui.notify(f'Erreur export : {exc}', type='negative')

        with ui.element('div').style(
            'width: 100%; height: 100vh; display: flex; flex-direction: column; gap: 10px; padding: 10px;'
        ):
            TopBar(
                state,
                on_select_folder=on_select_folder,
                on_run_detection=on_run_detection,
                on_export=on_export,
                on_open_settings=settings_dialog.open,
            )

            with ui.row().classes('no-wrap').style(
                'flex: 1; min-height: 0; gap: 10px; width: 100%;'
            ):
                Sidebar(state)
                with ui.element('div').style(
                    'flex: 1; display: flex; flex-direction: column; gap: 10px; min-width: 0; min-height: 0;'
                ):
                    canvas = CanvasView(state, image_url_builder=image_url_builder)
                    ActionToolbar(
                        state,
                        on_add_box=canvas.start_add_mode,
                        on_delete_box=canvas.delete_selected,
                    )
                StatusPanel(state)

        def on_key(event: events.KeyEventArguments) -> None:
            if not event.action.keydown:
                return
            if event.key.arrow_left:
                state.previous_image()
            elif event.key.arrow_right:
                state.next_image()
            elif event.key.enter:
                state.validate_current()
            elif event.key.delete:
                canvas.delete_selected()
            elif getattr(event.key, 'name', '') == 'a' or event.key == 'a':
                canvas.start_add_mode()
            elif getattr(event.key, 'name', '') == 'r' or event.key == 'r':
                state.reject_current()

        ui.keyboard(on_key=on_key)
