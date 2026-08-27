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
from config import apply_theme, get_settings, native_active
from models.app_state import AppState
from services.export_service import ExportService
from services.image_queue_service import ImageQueueService
from services.persistence_service import PersistenceService
from services.prediction_service import BatchResult, PredictionService
from services.system_service import open_folder


async def _pick_folder_webview() -> str | None:
    """Folder picker of the embedded webview - no external tool required."""
    import webview
    from nicegui import app

    window = app.native.main_window
    if window is None:
        return None
    # FileDialog.FOLDER is a plain enum; the legacy webview.FOLDER_DIALOG is a
    # proxy object that cannot cross NiceGUI's process boundary.
    folder_dialog = getattr(webview, 'FileDialog', None)
    dialog_type = folder_dialog.FOLDER if folder_dialog is not None else 20
    result = await window.create_file_dialog(dialog_type)
    if not result:
        return None
    return result[0] if isinstance(result, (list, tuple)) else str(result)


def _pick_folder_system() -> str | None:
    import platform
    import subprocess

    if platform.system() == 'Linux':
        for cmd in (
                ['zenity', '--file-selection', '--directory', "--title=Choisir un dossier d'images"],
                ['kdialog', '--getexistingdirectory', Path.home().as_posix()],
        ):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    return result.stdout.strip() or None
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    try:
        folder = filedialog.askdirectory(title="Choisir un dossier d'images")
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

        _client = ui.context.client  # captured here so background callbacks can restore slot context

        settings_dialog = SettingsDialog(state)

        def manual_folder_dialog() -> None:
            with ui.dialog() as dialog, ui.card().style('min-width: 460px;'):
                ui.label('Chemin du dossier').classes('app-title').style('margin-bottom: 8px;')
                inp = (
                    ui.input('Chemin', value=str(state.queue.folder or ''))
                    .props('outlined dense')
                    .classes('w-full')
                )
                with ui.row().classes('w-full justify-end gap-2').style('margin-top: 12px;'):
                    ui.button('Annuler', on_click=dialog.close, color=None) \
                        .props('flat no-caps').classes('app-ghost')

                    def confirm() -> None:
                        path = Path(str(inp.value or '')).expanduser()
                        dialog.close()
                        _load_folder(path)

                    ui.button('Ouvrir', on_click=confirm).props('no-caps unelevated')
            dialog.open()

        def _load_folder(path: Path) -> None:
            if not path or not path.is_dir():
                ui.notify(f'Dossier introuvable : {path}', type='negative')
                return
            try:
                state.load_folder(path)
                ui.notify(f'{state.total} images chargées.', type='positive')
            except Exception as exc:
                ui.notify(f'Erreur : {exc}', type='negative')

        async def on_select_folder() -> None:
            if native_active():
                folder = await _pick_folder_webview()
                if folder:
                    _load_folder(Path(folder))
                return
            folder = _pick_folder_system()
            if folder:
                _load_folder(Path(folder))
            else:
                manual_folder_dialog()

        def on_reset_folder() -> None:
            state.reset_folder()
            ui.notify('Dossier réinitialisé.', type='info')

        def on_run_detection() -> None:
            if state.total == 0:
                ui.notify("Chargez d'abord un dossier.", type='warning')
                return
            if state.prediction.running:
                ui.notify('Détection déjà en cours.', type='info')
                return
            if not state.prediction.model_available():
                ui.notify(f'Modèle YOLO introuvable : {settings.model_path}', type='negative')
                return

            # Nothing left to analyse means the user is asking for a re-run.
            force_all = not state.detection_targets()
            if force_all and not state.detection_targets(force_all=True):
                ui.notify(
                    'Toutes les images ont été modifiées à la main : rien à réanalyser.',
                    type='info',
                )
                return

            def on_update() -> None:
                state.notify()

            def on_finished(result: BatchResult) -> None:
                state.notify()
                with _client:
                    _report_detection(result)

            count = state.run_detection(on_update, on_finished, force_all=force_all)
            verb = 'Réanalyse' if force_all else 'Analyse'
            ui.notify(f'{verb} de {count} image(s) en cours…', type='info')

        def _report_detection(result: BatchResult) -> None:
            """Say what actually happened - including when nothing worked."""
            if result.error and not result.analysed:
                ui.notify(
                    f'La détection a échoué : {result.error}',
                    type='negative',
                    multi_line=True,
                    timeout=0,
                    close_button='Fermer',
                )
                return

            fins = result.detections
            summary = (
                f'{result.analysed} image(s) analysée(s), '
                f'{fins} aileron{"s" if fins > 1 else ""} détecté{"s" if fins > 1 else ""}.'
            )
            if result.cancelled:
                summary = f'Détection interrompue — {summary}'
            if result.failed:
                ui.notify(
                    f'{summary} {result.failed} échec(s) — {result.error}',
                    type='warning',
                    multi_line=True,
                    timeout=0,
                    close_button='Fermer',
                )
                return
            ui.notify(summary, type='positive')

        def _open_folder(path: Path | None, missing: str) -> None:
            if path is None or not path.is_dir():
                ui.notify(missing, type='warning', multi_line=True)
                return
            if not open_folder(path):
                ui.notify(f"Impossible d'ouvrir {path}", type='negative', multi_line=True)

        def on_open_export_folder() -> None:
            triees = state.triees_dir
            if triees is None:
                ui.notify("Chargez d'abord un dossier.", type='warning')
                return
            _open_folder(
                triees,
                f"Aucun export pour l'instant : {triees} sera créé au premier export.",
            )

        # Built once: a dialog rebuilt at every export would pile up on the page.
        export_dirs: dict[str, Path | None] = {'triees': None, 'corrections': None}

        def _open_exported(key: str) -> None:
            export_dialog.close()
            _open_folder(export_dirs[key], 'Dossier introuvable.')

        with ui.dialog() as export_dialog, ui.card().style('min-width: 460px;'):
            ui.label('Export terminé').classes('app-title')
            export_summary = ui.label().classes('app-muted').style(
                'white-space: pre-line; word-break: break-all;'
            )
            with ui.row().classes('w-full justify-end gap-2').style('margin-top: 12px;'):
                ui.button('Fermer', on_click=export_dialog.close, color=None) \
                    .props('flat no-caps').classes('app-ghost')
                corrections_btn = (
                    ui.button('Ouvrir les corrections',
                              on_click=lambda: _open_exported('corrections'), color=None)
                    .props('no-caps flat dense padding="6px 14px"')
                    .classes('app-outline')
                )
                ui.button('Ouvrir le dossier', icon='folder_open',
                          on_click=lambda: _open_exported('triees')) \
                    .props('no-caps unelevated')

        def _report_export(summary: dict) -> None:
            triees = Path(summary['triees_dir']) if summary['triees_dir'] else None
            corrections = Path(summary['corrections_dir']) if summary['corrections'] else None
            export_dirs['triees'] = triees
            export_dirs['corrections'] = corrections

            lines = [f"{summary['exported']} image(s) exportée(s) → {triees}"]
            if corrections:
                lines.append(f"{summary['corrections']} correction(s) → {corrections}")
            if summary.get('uncropped'):
                lines.append(
                    f"{summary['uncropped']} image(s) copiée(s) sans recadrage — "
                    f"{summary.get('warning', '')}"
                )
            corrections_btn.set_visibility(corrections is not None)
            export_summary.text = '\n'.join(lines)
            export_dialog.open()

        def on_export() -> None:
            if state.export_running or state.prediction.running:
                return
            detected = sum(1 for img in state.images if img.will_export)
            if detected == 0:
                ui.notify('Aucune image avec ailerons détectés à exporter.', type='warning')
                return

            def on_done(summary: dict) -> None:
                with _client:
                    if 'error' in summary:
                        ui.notify(
                            f"Erreur export : {summary['error']}",
                            type='negative',
                            multi_line=True,
                            timeout=0,
                            close_button='Fermer',
                        )
                        return
                    _report_export(summary)

            state.run_export_async(on_done)

        with ui.element('div').classes('app-shell'):
            TopBar(
                state,
                on_select_folder=on_select_folder,
                on_reset_folder=on_reset_folder,
                on_run_detection=on_run_detection,
                on_export=on_export,
                on_open_export_folder=on_open_export_folder,
                on_open_settings=settings_dialog.open,
            )

            with ui.element('div').classes('app-body'):
                Sidebar(state)

                with ui.element('div').classes('app-pane app-pane-main'):
                    canvas = CanvasView(state, image_url_builder=image_url_builder)
                    ActionToolbar(
                        state,
                        on_add_box=canvas.start_add_mode,
                        on_delete_box=canvas.delete_selected,
                        is_add_mode=lambda: canvas.add_mode,
                    )

                StatusPanel(state)

        def on_key(event: events.KeyEventArguments) -> None:
            if not event.action.keydown:
                return
            if event.key.arrow_left:
                state.previous_image()
            elif event.key.arrow_right:
                state.next_image()
            elif event.key.delete:
                canvas.delete_selected()
            elif event.key.escape:
                canvas.cancel_add_mode()
                state.select_detection(None)
            elif str(getattr(event.key, 'name', '')).lower() == 'a':
                canvas.start_add_mode()

        # 'button' is left out of the default ignore list on purpose: clicking a
        # toolbar arrow leaves the focus on it, and the shortcuts would then stay
        # dead until the user clicked somewhere else.
        ui.keyboard(on_key=on_key, ignore=['input', 'select', 'textarea'])
