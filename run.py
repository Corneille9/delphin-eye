#!/usr/bin/env python3
import hashlib
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
REQUIREMENTS = ROOT / "requirements.txt"
HASH_FILE = VENV / ".requirements_hash"


def requirements_hash():
    return hashlib.md5(REQUIREMENTS.read_bytes()).hexdigest()


def install():
    subprocess.check_call([PYTHON, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([PYTHON, "-m", "pip", "install", "-r", REQUIREMENTS])
    HASH_FILE.write_text(requirements_hash())


def setup():
    print("Creating virtual environment...")
    venv.create(VENV, with_pip=True)
    print("Installing dependencies...")
    install()


def sync_if_changed():
    if not HASH_FILE.exists() or HASH_FILE.read_text() != requirements_hash():
        print("requirements.txt changed - updating dependencies...")
        install()


if os.environ.get("_DELPHIN_VENV") != "1":
    if not PYTHON.exists():
        setup()
    else:
        sync_if_changed()
    env = {**os.environ, "_DELPHIN_VENV": "1"}
    sys.exit(subprocess.call([PYTHON, __file__] + sys.argv[1:], env=env))

os.chdir(ROOT / "src")
sys.path.insert(0, str(ROOT / "src"))
from main import main

main()
