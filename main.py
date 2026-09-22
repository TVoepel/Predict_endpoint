#!/usr/bin/env python3
"""Startpunkt der App: python3 main.py

Verwendet die moderne Oberfläche (CustomTkinter). Ist das Paket nicht
installiert, startet die klassische Tkinter-Oberfläche.
"""

import sys


def main() -> None:
    try:
        from predict_app.gui import main as run
    except ImportError as exc:
        print(f"Hinweis: CustomTkinter nicht verfügbar ({exc}); "
              "starte klassische Oberfläche.\n"
              "Installation: python3 -m pip install -r requirements.txt", file=sys.stderr)
        from predict_app.gui_classic import main as run
    run()


if __name__ == "__main__":
    main()
