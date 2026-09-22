#!/bin/bash
# Erstellt die macOS-App "Predict Endpoint.app" im Ordner dist/.
#
# Voraussetzung: Python 3 von https://www.python.org (enthält Tkinter).
# Aufruf:   ./build_app.sh
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

if ! "$PYTHON" -c "import tkinter" 2>/dev/null; then
    echo "Fehler: Tkinter fehlt in $PYTHON. Bitte Python 3 von python.org installieren." >&2
    exit 1
fi

if [ ! -d .venv ]; then
    "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install --upgrade pip >/dev/null
pip install -r requirements-build.txt

rm -rf build dist
python setup.py py2app

echo
echo "Fertig: $(pwd)/dist/Predict Endpoint.app"
echo "Die App in einen Ordner legen, der auch die Koeffizienten-Dateien enthält,"
echo "oder den Projektordner in der App über „Wählen…“ auswählen."
