"""py2app-Setup zum Erstellen der macOS-App.

    python3 setup.py py2app

Das Ergebnis liegt danach in dist/Predict Endpoint.app
"""

from pathlib import Path

from setuptools import setup

from predict_app import __version__
from predict_app.core import SETTINGS

HERE = Path(__file__).resolve().parent

# Koeffizienten und Intercepts werden in die App eingebaut (Contents/Resources),
# damit sie ohne weitere Einrichtung überall läuft.
COEFF_FILES = []
for _, coeff_name, intercept_name, _ in SETTINGS:
    for name in (coeff_name, intercept_name):
        if (HERE / name).is_file():
            COEFF_FILES.append(str(HERE / name))

APP = ["main.py"]
DATA_FILES: list = []
OPTIONS = {
    "argv_emulation": False,
    "packages": ["predict_app", "customtkinter", "darkdetect"],
    "includes": ["tkinter"],
    "resources": COEFF_FILES,
    "plist": {
        "CFBundleName": "Predict Endpoint",
        "CFBundleDisplayName": "Predict Endpoint",
        "CFBundleIdentifier": "de.voepel.predict-endpoint",
        "CFBundleVersion": __version__,
        "CFBundleShortVersionString": __version__,
        "NSHumanReadableCopyright": "",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
}

setup(
    name="Predict Endpoint",
    version=__version__,
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
