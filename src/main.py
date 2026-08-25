from __future__ import annotations

import os
import socket
from multiprocessing import freeze_support
from pathlib import Path

from fastapi.responses import FileResponse, Response
from nicegui import app, native, ui

from config import assets_dir, cache_dir, get_settings, native_enabled
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
    ui.run(
        title='Delphin Eye',
        favicon=str(assets / 'favicon.ico'),
        native=native_window,
        window_size=WINDOW_SIZE if native_window else None,
        # Desktop app, not a server: no auto-reload, no browser tab, loopback
        # only so the UI is never exposed on the local network, and quiet logs.
        reload=False,
        show=False,
        host='127.0.0.1',
        port=None if native_window else _pick_port(),
        # DELPHIN_LOG_LEVEL=info surfaces access logs when diagnosing a build.
        uvicorn_logging_level=os.environ.get('DELPHIN_LOG_LEVEL', 'warning'),
    )


if __name__ == '__main__':
    freeze_support()
    main()
