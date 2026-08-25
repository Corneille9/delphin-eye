from __future__ import annotations

import os
import socket
import sys
from multiprocessing import freeze_support
from pathlib import Path

from fastapi.responses import FileResponse, Response
from nicegui import app, native, ui

from config import assets_dir, cache_dir, get_settings, is_frozen, native_enabled
from database import get_repository
from pages.dashboard import register_dashboard_page
from services.preview_service import PreviewService

WINDOW_SIZE = (1440, 900)

# Native window options must be set at import time: NiceGUI starts pywebview in a
# separate process and only picks up what is configured before ui.run().
app.native.window_args['resizable'] = True
app.native.window_args['min_size'] = (1024, 700)


def _build_image_url(image_id: int) -> str:
    return f'/api/image/{image_id}'


def _register_routes() -> None:
    repo = get_repository()
    previews = PreviewService(cache_dir())

    @app.get('/api/image/{image_id}')
    def serve_image(image_id: int):
        with repo.transaction() as conn:
            row = conn.execute(
                'SELECT absolute_path FROM images WHERE id = ?', (image_id,)
            ).fetchone()
        if row is None:
            return Response(status_code=404)
        path = Path(row['absolute_path'])
        if not path.is_file():
            return Response(status_code=404)
        # The canvas gets a downscaled copy; the originals are only ever read
        # from disk by the prediction and export services.
        return FileResponse(str(previews.preview_path(image_id, path)))


SYSTEM_DIST_PACKAGES = '/usr/lib/python3/dist-packages'


def _use_system_pygobject() -> None:
    """Let a frozen Linux build import the distribution's PyGObject.

    `gi` is excluded from the bundle (see the spec), so the packaged app relies
    on python3-gi being installed - which the .deb declares as a dependency.
    Appended rather than prepended so bundled modules keep priority.
    """
    if not is_frozen() or sys.platform != 'linux':
        return
    if os.path.isdir(SYSTEM_DIST_PACKAGES) and SYSTEM_DIST_PACKAGES not in sys.path:
        sys.path.append(SYSTEM_DIST_PACKAGES)


def _native_backend_error() -> str | None:
    """Explain why the native window cannot start, or return None if it can.

    Only Linux is checked: Windows ships WebView2 and macOS ships WebKit, and a
    missing WebView2 runtime is the installer's job to fix, not something that
    can be detected by an import.
    """
    try:
        import webview  # noqa: F401
    except ImportError as exc:
        return f'pywebview is not installed ({exc})'
    if sys.platform != 'linux':
        return None
    _use_system_pygobject()
    try:
        from webview.platforms import gtk  # noqa: F401
    except Exception as exc:
        return (
            f'the GTK/WebKit libraries are missing ({type(exc).__name__}: {exc}). '
            'Install them with: sudo apt install python3-gi python3-gi-cairo '
            'gir1.2-webkit2-4.1'
        )
    return None


def _pick_port() -> int:
    """Never fail to start because something else already holds the port.

    In native mode NiceGUI scans 8000-8999 on its own, so we only have to cover
    the browser fallback: keep the familiar 8080 when it is free, scan otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(('127.0.0.1', 8080))
        except OSError:
            return native.find_open_port()
    return 8080


def main() -> None:
    settings = get_settings()
    settings.ensure_directories()

    assets = assets_dir()
    app.add_static_files('/assets', str(assets))

    _register_routes()
    register_dashboard_page(image_url_builder=_build_image_url)

    native_window = native_enabled()
    fell_back = False
    if native_window:
        reason = _native_backend_error()
        if reason:
            print(f'Native window unavailable: {reason}', file=sys.stderr)
            print('Falling back to the browser.', file=sys.stderr)
            native_window, fell_back = False, True

    ui.run(
        title='Delphin Eye',
        favicon=str(assets / 'favicon.ico'),
        native=native_window,
        window_size=WINDOW_SIZE if native_window else None,
        # Desktop app, not a server: no auto-reload, no browser tab, loopback
        # only so the UI is never exposed on the local network, and quiet logs.
        reload=False,
        show=fell_back,  # only pop a browser open when the native window failed
        host='127.0.0.1',
        port=None if native_window else _pick_port(),
        # DELPHIN_LOG_LEVEL=info surfaces access logs when diagnosing a build.
        uvicorn_logging_level=os.environ.get('DELPHIN_LOG_LEVEL', 'warning'),
    )


if __name__ == '__main__':
    freeze_support()
    main()
