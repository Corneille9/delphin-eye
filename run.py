#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def setup():
    print("==> Création du virtualenv...")
    venv.create(VENV, with_pip=True)
    print("==> Installation des dépendances...")
    subprocess.check_call([PYTHON, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([PYTHON, "-m", "pip", "install", "-r", ROOT / "requirements.txt"])


if Path(sys.executable).resolve() != PYTHON.resolve():
    if not PYTHON.exists():
        setup()
    sys.exit(subprocess.call([PYTHON, __file__] + sys.argv[1:]))

os.chdir(ROOT / "src")
sys.path.insert(0, str(ROOT / "src"))
from main import main
main()
