#!/bin/bash
# Erstellt die macOS-App "Predict Endpoint.app" im Ordner dist/.
#
# Voraussetzung: ein Python 3 mit Tkinter, z. B. von https://www.python.org
# oder per Homebrew:  brew install python-tk
#
# Aufruf:   ./build_app.sh
# Optional: PYTHON=/pfad/zu/python3 ./build_app.sh
set -euo pipefail

cd "$(dirname "$0")"

has_tk() {
    [ -x "$1" ] && "$1" -c "import tkinter" >/dev/null 2>&1
}

# Kandidaten in dieser Reihenfolge prüfen, den ersten mit Tkinter verwenden.
CANDIDATES=(
    "${PYTHON:-}"
    "$(command -v python3 || true)"
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3
    /opt/homebrew/bin/python3
    /usr/local/bin/python3
)

PY=""
for c in "${CANDIDATES[@]}"; do
    [ -n "$c" ] || continue
    if has_tk "$c"; then
        PY="$c"
        break
    fi
done

if [ -z "$PY" ]; then
    cat >&2 <<'MSG'
Fehler: Kein Python 3 mit Tkinter gefunden.

Abhilfe (eine der beiden Möglichkeiten):
  1. Python 3 von https://www.python.org/downloads/macos/ installieren
     (enthält Tkinter), danach dieses Skript erneut starten.
  2. Homebrew:  brew install python-tk
     danach dieses Skript erneut starten.

Alternativ den Interpreter direkt angeben:
  PYTHON=/pfad/zu/python3 ./build_app.sh
MSG
    exit 1
fi

echo "Verwende Python: $PY ($("$PY" --version))"

# Venv neu anlegen, wenn sie mit einem anderen Python erstellt wurde.
if [ -d .venv ] && ! has_tk .venv/bin/python; then
    echo "Vorhandene .venv hat kein Tkinter – wird neu erstellt."
    rm -rf .venv
fi
if [ ! -d .venv ]; then
    "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install --upgrade pip >/dev/null
pip install -r requirements-build.txt

rm -rf build dist
python setup.py py2app

echo
echo "Fertig: $(pwd)/dist/Predict Endpoint.app"
echo "Koeffizienten und Intercepts sind in die App eingebaut."
echo "Die App kann an einen beliebigen Ort verschoben werden, z. B. /Applications."
