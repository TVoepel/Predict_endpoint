#!/usr/bin/env python3
"""Kommandozeile: nur die erste Zeile jeder Output-Datei in first_lines_summary.csv schreiben."""

from pathlib import Path

from predict_app.core import Project


def main() -> None:
    Project(Path(__file__).resolve().parent).build_first_lines_csv(log=print)


if __name__ == "__main__":
    main()
