#!/usr/bin/env python3
"""Kommandozeilen-Variante von Schritt 3: alle Output-Dateien in eine sortierte CSV überführen."""

from pathlib import Path

from predict_app.core import Project


def main() -> None:
    Project(Path(__file__).resolve().parent).build_sorted_csv(log=print)


if __name__ == "__main__":
    main()
