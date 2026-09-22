#!/bin/bash
# Doppelklick-Starter für macOS, falls die App nicht gebaut wurde.
# Startet die Oberfläche direkt aus dem Quellcode mit dem installierten python3.
cd "$(dirname "$0")"
exec python3 main.py
