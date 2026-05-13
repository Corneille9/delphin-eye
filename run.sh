#!/usr/bin/env bash
set -e

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "==> Installation non détectée, lancement de install.sh..."
    "$(dirname "$0")/install.sh"
fi

cd "$(dirname "$0")/src"
"../$VENV_DIR/bin/python" main.py
