from __future__ import annotations

from nicegui import events, ui

from src.components.action_toolbar import ActionToolbar
from src.components.image_viewer import ImageViewer
from src.components.sidebar import Sidebar
from src.components.status_panel import StatusPanel
from src.components.topbar import TopBar
from src.models.mock_data import DashboardState, build_mock_images


def register_dashboard_page() -> None:
    @ui.page('/')
    def dashboard_page() -> None:
        state = DashboardState(build_mock_images(total_images=180))

        def on_select_folder() -> None:
            ui.notify('Mock mode: folder selection is simulated.')

        timer_ref: dict[str, ui.timer] = {}

        def on_run_detection() -> None:
            state.start_detection_run()
            timer_ref['timer'].active = True

        def on_export() -> None:
            ui.notify(f'Mock export completed for {state.total_images} images.', type='positive')

        def tick_detection() -> None:
            state.step_detection()
            if not state.detection_running:
                timer_ref['timer'].active = False

        with ui.column().classes('w-full h-screen bg-slate-100 p-3 gap-3'):
            TopBar(state, on_select_folder=on_select_folder, on_run_detection=on_run_detection, on_export=on_export)

            with ui.row().classes('w-full flex-1 gap-3 no-wrap'):
                Sidebar(state)

                with ui.column().classes('flex-1 h-full gap-3'):
                    ImageViewer(state)
                    ActionToolbar(state)

                StatusPanel(state)

        timer_ref['timer'] = ui.timer(0.08, tick_detection, active=False)

        def on_key(event: events.KeyEventArguments) -> None:
            if event.action.keydown:
                if event.key.arrow_left:
                    state.previous_image()
                elif event.key.arrow_right:
                    state.next_image()
                elif event.key.enter:
                    state.validate_current()
                elif event.key.delete:
                    state.delete_selected_detection()
                elif event.key.a:
                    state.add_mock_detection()

        ui.keyboard(on_key=on_key)

