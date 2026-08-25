from __future__ import annotations

from multiprocessing import freeze_support
from pathlib import Path

from fastapi.responses import FileResponse, Response
from nicegui import app, ui

from config import assets_dir, get_settings, native_enabled
from database import get_repository
from pages.dashboard import register_dashboard_page

WINDOW_SIZE = (1440, 900)

# Native window options must be set at import time: NiceGUI starts pywebview in a
# separate process and only picks up what is configured before ui.run().
app.native.window_args['resizable'] = True
app.native.window_args['min_size'] = (1024, 700)


def _build_image_url(image_id: int) -> str:
    return f'/api/image/{image_id}'


def _register_routes() -> None:
    repo = get_repository()

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
        return FileResponse(str(path))


def main() -> None:
    settings = get_settings()
    settings.ensure_directories()

    assets = assets_dir()
    app.add_static_files('/assets', str(assets))

    _register_routes()
    register_dashboard_page(image_url_builder=_build_image_url)

    native = native_enabled()
    ui.run(
        title='Delphin Eye',
        reload=False,
        favicon=str(assets / 'favicon.ico'),
        native=native,
        window_size=WINDOW_SIZE if native else None,
        show=not native,
    )


if __name__ == '__main__':
    freeze_support()
    main()
