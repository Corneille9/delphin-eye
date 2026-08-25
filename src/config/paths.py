"""Filesystem layout for both the dev checkout and the frozen (PyInstaller) build.

In development everything stays inside the repository so ``python3 run.py`` keeps
working unchanged. Once frozen, read-only resources live in the bundle while
anything the app writes goes to the per-user data directory.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = 'DelphinEye'


def is_frozen() -> bool:
    return getattr(sys, 'frozen', False)


def resource_dir() -> Path:
    """Root of the read-only files shipped with the app (assets, config, weights)."""
    if is_frozen():
        return Path(getattr(sys, '_MEIPASS', Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[2]


def user_data_dir() -> Path:
    """Writable per-user directory. Falls back to the repo root in development."""
    if not is_frozen():
        return resource_dir()
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA') or Path.home() / 'AppData' / 'Roaming')
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share')
    return base / APP_NAME


def assets_dir() -> Path:
    """Static web assets (favicon, images) shipped with the app."""
    if is_frozen():
        return resource_dir() / 'assets'
    return resource_dir() / 'src' / 'assets'


def cache_dir() -> Path:
    """Regenerable files (canvas previews). Safe to delete at any time."""
    if is_frozen():
        return user_data_dir() / 'cache'
    return resource_dir() / 'output' / 'cache'


def native_enabled() -> bool:
    """Native webview window. On by default everywhere, dev included, so what we
    test locally is what the packaged app does.

    Set ``DELPHIN_NATIVE=0`` to fall back to serving the UI in a browser.
    """
    override = os.environ.get('DELPHIN_NATIVE')
    if override is not None:
        return override.strip().lower() not in ('', '0', 'false', 'no')
    return True
