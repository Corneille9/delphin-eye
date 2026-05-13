from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse, Response
from nicegui import app, ui

from config import get_settings
from database import get_repository
from pages.dashboard import register_dashboard_page


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

    base_dir = Path(__file__).resolve().parent
    app.add_static_files('/assets', str(base_dir / 'assets'))

    _register_routes()
    register_dashboard_page(image_url_builder=_build_image_url)

    ui.run(
        title='Delphin Eye',
        reload=False,
        favicon=str(base_dir / 'assets/favicon.ico'),
    )


if __name__ == '__main__':
    main()
