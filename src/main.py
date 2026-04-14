from __future__ import annotations

from pathlib import Path

from nicegui import app, ui

from src.pages.dashboard import register_dashboard_page

def main() -> None:
    base_dir = Path(__file__).resolve().parent
    app.add_static_files('/assets', str(base_dir / 'assets'))

    register_dashboard_page()
    ui.run(title='Dolphin Fin Sorter', reload=False)


if __name__ == '__main__':
    main()

