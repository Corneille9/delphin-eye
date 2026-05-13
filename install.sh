#!/usr/bin/env bash
set -e

PYTHON=${PYTHON:-python3}
VENV_DIR=".venv"

echo "==> Vérification de Python..."
if ! command -v "$PYTHON" &>/dev/null; then
    echo "Erreur : Python introuvable. Installez Python 3.10+ et relancez."
    exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "    Python $PY_VERSION détecté."

# Require Python >= 3.10
if "$PYTHON" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"; then
 :
else
    echo "Erreur : Python 3.10 ou supérieur requis (version actuelle : $PY_VERSION)."
    exit 1
fi

echo "==> Création du virtualenv dans $VENV_DIR..."
"$PYTHON" -m venv "$VENV_DIR"

echo "==> Installation des dépendances..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r requirements.txt --quiet

echo ""
echo "Installation terminée."
echo ""
echo "Pour lancer l'application :"
echo "    ./run.sh"
