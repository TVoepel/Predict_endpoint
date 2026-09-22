# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Spezifikation für die Windows-Version (eine einzelne EXE).

    pyinstaller --noconfirm --clean predict_endpoint.spec

Ergebnis: dist/Predict Endpoint.exe
Koeffizienten, Intercepts, Logo und die CustomTkinter-Themes werden eingebettet.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

HERE = Path(SPECPATH).resolve()  # noqa: F821 – von PyInstaller gesetzt

datas = [(str(p), ".") for p in sorted(HERE.glob("coeff_*.csv"))]
datas += [(str(p), ".") for p in sorted(HERE.glob("intercept_*.txt"))]
datas += [
    (str(HERE / "assets" / "logo.png"), "."),
    (str(HERE / "assets" / "icon_256.png"), "."),
]
datas += collect_data_files("customtkinter")

icon = str(HERE / "assets" / "icon.ico") if sys.platform.startswith("win") else None

a = Analysis(
    [str(HERE / "main.py")],
    pathex=[str(HERE)],
    binaries=[],
    datas=datas,
    hiddenimports=["darkdetect", "PIL.ImageTk", "PIL._tkinter_finder"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["numpy", "matplotlib", "scipy", "pandas", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Predict Endpoint",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=icon,
)
