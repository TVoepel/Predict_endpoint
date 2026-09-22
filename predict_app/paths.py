"""Ermittlung des Standard-Projektordners und Speichern der Einstellungen."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "Predict Endpoint"


def is_frozen_app() -> bool:
    """True, wenn das Programm als gebündelte .app (py2app) läuft."""
    return bool(getattr(sys, "frozen", False)) or "RESOURCEPATH" in os.environ


def app_bundle_dir() -> Path | None:
    """Ordner, in dem die .app liegt (nur im gebündelten Zustand)."""
    if not is_frozen_app():
        return None
    exe = Path(sys.executable).resolve()
    # <Ordner>/<Name>.app/Contents/MacOS/python
    for parent in exe.parents:
        if parent.suffix == ".app":
            return parent.parent
    return None


def repo_dir() -> Path:
    """Ordner mit den Quelldateien (bei Start aus dem Quellcode)."""
    return Path(__file__).resolve().parent.parent


def bundled_coefficient_dir() -> Path:
    """Ordner mit den in die App eingebauten Koeffizienten-Dateien.

    * gebündelte App: Contents/Resources der .app
    * Start aus dem Quellcode: der Repository-Ordner
    """
    resource_path = os.environ.get("RESOURCEPATH")
    if resource_path and Path(resource_path).is_dir():
        return Path(resource_path)
    return repo_dir()


def documents_project_dir() -> Path:
    return Path.home() / "Documents" / APP_NAME


def default_project_dir() -> Path:
    """Standard-Projektordner.

    * gebündelte App in einem normalen Ordner: der Ordner, in dem die .app liegt
    * gebündelte App in /Applications (oder einem nicht beschreibbaren Ordner):
      ~/Documents/Predict Endpoint
    * Start aus dem Quellcode: der Repository-Ordner
    """
    bundle = app_bundle_dir()
    if bundle is not None:
        in_applications = any(
            str(bundle).startswith(prefix)
            for prefix in ("/Applications", str(Path.home() / "Applications"))
        )
        if in_applications or not os.access(bundle, os.W_OK):
            return documents_project_dir()
        return bundle
    return repo_dir()


def config_file() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "predict_endpoint"
    return base / "config.json"


def load_config() -> dict:
    try:
        with open(config_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(data: dict) -> None:
    path = config_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
