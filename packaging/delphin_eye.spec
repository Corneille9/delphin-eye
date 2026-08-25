# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Delphin Eye desktop app.

Ships only what an end user needs to run detections: the app code, the web
assets, the inference config and the model weights referenced by it. Training
notebooks, the dataset, the *last.pt* checkpoints and the GPU-only half of
PyTorch are deliberately left out.

Build with:  pyinstaller packaging/delphin_eye.spec --noconfirm
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / 'src'

APP_NAME = 'DelphinEye'
ICON_ICO = SRC / 'assets' / 'favicon.ico'

datas = [
    (str(SRC / 'assets'), 'assets'),
    (str(ROOT / 'config' / 'inference.yaml'), 'config'),
]

# Model weights: only the best.pt files, which are the ones config/inference.yaml
# points at. last.pt are training checkpoints the app never loads.
for weights in sorted((ROOT / 'output' / 'models' / 'saved').rglob('best.pt')):
    datas.append((str(weights), str(weights.parent.relative_to(ROOT))))

binaries = []
hiddenimports = []

# These packages resolve resources and submodules at runtime, so static analysis
# alone misses part of what they need.
for package in ('nicegui', 'ultralytics', 'sahi', 'webview'):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

hiddenimports += [
    'uvicorn.lifespan.on',
    'uvicorn.loops.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets.auto',
]

excludes = [
    # GPU-only PyTorch toolchain: inference runs on CPU.
    'triton',
    # Training and notebook tooling (notebooks/, requirements-dev.txt).
    'IPython', 'ipykernel', 'jupyter', 'jupyter_client', 'jupyter_core',
    'notebook', 'nbconvert', 'nbformat', 'jedi', 'debugpy', 'pytest',
    # The window comes from the system webview; no extra GUI toolkit is bundled.
    'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
    # PyGObject cannot be frozen reliably: its PyInstaller hook drags in the
    # whole GI stack and WebKit spawns helper processes with absolute paths.
    # On Linux the package depends on python3-gi instead - see main.py.
    'gi', 'cairo',
]

a = Analysis(
    [str(SRC / 'main.py')],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_ICO) if ICON_ICO.exists() else None,
)

# onedir rather than onefile: a ~500 MB onefile has to unpack itself on every
# launch, which costs 20-30 s before the window shows up.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

# BUNDLE only produces something on macOS; it is a no-op elsewhere.
app = BUNDLE(
    coll,
    name=f'{APP_NAME}.app',
    icon=str(ICON_ICO) if ICON_ICO.exists() else None,
    bundle_identifier='io.delphin.eye',
    info_plist={
        'CFBundleName': 'Delphin Eye',
        'CFBundleDisplayName': 'Delphin Eye',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
    },
)
