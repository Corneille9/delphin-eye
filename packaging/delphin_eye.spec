# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Delphin Eye desktop app.

Ships only what an end user needs to run detections: the app code, the web
assets, the inference config and the model weights referenced by it. Training
notebooks, the dataset, the *last.pt* checkpoints and the GPU-only half of
PyTorch are deliberately left out.

Build with:  pyinstaller packaging/delphin_eye.spec --noconfirm
"""
import os
import re
import sys
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

# The app deliberately drives the system GTK/WebKit stack through the
# distribution's PyGObject. Shipping our own GLib makes the system libgobject
# resolve its symbols against the bundled (older) copy, which fails at startup
# with "undefined symbol: g_dir_unref" on any machine whose GLib is newer than
# the build runner's. These have to come from the system, as a matched set.
SYSTEM_ONLY_LIBS = (
    # GLib: shipping our own makes the system libgobject resolve against it
    # ("undefined symbol: g_dir_unref").
    'libglib-2.0', 'libgobject-2.0', 'libgio-2.0',
    'libgmodule-2.0', 'libgthread-2.0', 'libgirepository-1.0',
    # GLib links these; they have to match the GLib actually in use.
    'libffi', 'libpcre2-8', 'libbsd', 'libmd',
    # Mesa (drirc parsing) and fontconfig both link expat.
    'libexpat',
    # X11 and graphics: the system Mesa/EGL is linked against the system libX11.
    # A bundled copy shadows it and WebKit's compositor then dies with
    # "Could not create default EGL display: EGL_BAD_PARAMETER".
    'libX11.so', 'libXau', 'libXdmcp', 'libXext', 'libICE', 'libSM',
    'libEGL', 'libGL.so', 'libGLX', 'libGLdispatch', 'libgbm', 'libdrm',
    'libwayland-',
    # The GCC runtime. Mesa loads libLLVM for shader compilation, and the
    # system libLLVM needs a libstdc++ at least as new as the one it was built
    # against (GLIBCXX_3.4.32 on Ubuntu 24.04). The runner's copy is older, so
    # bundling it makes eglInitialize fail and the window stays blank. Nothing
    # we ship needs more than GLIBCXX_3.4.22 / GCC_4.3.0, which every
    # distribution recent enough to carry WebKitGTK 4.1 already provides.
    'libstdc++', 'libgcc_s',
)

# Libraries we knowingly ship unhashed. PyInstaller puts _internal on
# LD_LIBRARY_PATH, so anything listed here shadows the system copy for the
# whole GTK/WebKit/Mesa stack, in this process and in the WebKit subprocesses.
# The three blank-window bugs so far were all a library that did not belong
# here. This is not a proof of correctness: it only makes a NEW unhashed
# system library fail the build loudly instead of shipping a blank window.
KNOWN_UNHASHED_LIBS = frozenset({
    'libbz2.so.1.0', 'libcrypto.so.3', 'liblzma.so.5', 'libncursesw.so.6',
    'libpcre.so.3', 'libpython3.12.so.1.0', 'libreadline.so.8',
    'libsqlite3.so.0', 'libssl.so.3', 'libtinfo.so.6', 'libuuid.so.1',
    'libz.so.1',
})

# A PyInstaller-mangled name (libfoo.a1b2c3d4.so.1, libfoo-a1b2c3d4.so.1)
# carries a content hash, so it cannot collide with a system library.
HASHED_LIB = re.compile(r'[.-][0-9a-f]{8}\.(so|\d)')


def _unexpected_unhashed(binaries):
    """Unhashed libraries landing at the root of _internal.

    Only the root matters: that is the single directory PyInstaller puts on
    LD_LIBRARY_PATH. A library under a package directory (torch/lib/...) is
    found through its RPATH and shadows nothing.
    """
    seen = set()
    for entry in binaries:
        dest = entry[0]
        if os.path.dirname(dest):
            continue
        name = os.path.basename(dest)
        if '.so' in name and not HASHED_LIB.search(name):
            seen.add(name)
    return sorted(seen - KNOWN_UNHASHED_LIBS)


if sys.platform == 'linux':
    a.binaries = [
        entry for entry in a.binaries
        if not os.path.basename(entry[0]).startswith(SYSTEM_ONLY_LIBS)
    ]

    unexpected = [
        name for name in _unexpected_unhashed(a.binaries)
        if not name.startswith(('_', 'lib_'))
        and '.cpython-' not in name
    ]
    if unexpected:
        raise SystemExit(
            'Nouvelles bibliotheques non hachees dans le bundle :\n  '
            + '\n  '.join(unexpected)
            + '\n\nChacune masque la copie systeme pour GTK/WebKit/Mesa.'
              '\nSoit elle appartient a la pile systeme -> SYSTEM_ONLY_LIBS,'
              '\nsoit elle est inoffensive -> KNOWN_UNHASHED_LIBS.'
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
