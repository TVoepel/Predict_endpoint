"""py2app-Setup zum Erstellen der macOS-App.

    python3 setup.py py2app

Das Ergebnis liegt danach in dist/Predict Endpoint.app
"""

from setuptools import setup

from predict_app import __version__

APP = ["main.py"]
DATA_FILES: list = []
OPTIONS = {
    "argv_emulation": False,
    "packages": ["predict_app"],
    "includes": ["tkinter"],
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
