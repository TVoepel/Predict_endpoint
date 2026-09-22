#!/usr/bin/env python3
"""Kommandozeilen-Variante von Schritt 2: Vorhersagen für alle CSVs in input_csv/ berechnen.

Verhalten wie das ursprüngliche Skript; der Projektordner ist der Ordner,
in dem dieses Skript liegt.
"""

from pathlib import Path

from predict_app.core import Project


def main() -> None:
    Project(Path(__file__).resolve().parent).run_predictions(log=print)


if __name__ == "__main__":
    main()
