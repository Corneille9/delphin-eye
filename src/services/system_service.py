"""Handing a path back to the desktop environment."""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

# PyInstaller points these at _internal; a file manager inheriting them would
# load our bundled libraries and fail to start. The bootloader keeps the
# original value in <NAME>_ORIG when there was one.
_LOADER_VARS = ('LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH', 'DYLD_FRAMEWORK_PATH')

_LINUX_OPENERS = (['xdg-open'], ['gio', 'open'], ['nautilus'], ['dolphin'], ['thunar'], ['nemo'])


def desktop_env() -> dict[str, str]:
    env = dict(os.environ)
    for name in _LOADER_VARS:
        original = env.pop(f'{name}_ORIG', '')
        if original:
            env[name] = original
        else:
            env.pop(name, None)
    return env


def open_folder(path: Path | str) -> bool:
    """Open a folder in the system file manager. False when it cannot be done."""
    target = Path(path)
    if not target.is_dir():
        return False

    system = platform.system()
    if system == 'Windows':
        try:
            os.startfile(str(target))  # type: ignore[attr-defined]
        except OSError:
            return False
        return True

    commands = [['open']] if system == 'Darwin' else list(_LINUX_OPENERS)
    for command in commands:
        try:
            subprocess.Popen(
                command + [str(target)],
                env=desktop_env(),
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, ValueError):
            continue
        return True
    return False
