@echo off
rem Erstellt die Windows-Version "Predict Endpoint.exe" im Ordner dist\.
rem
rem Voraussetzung: Python 3 von https://www.python.org (mit "tcl/tk and IDLE",
rem ist in der Standardinstallation enthalten).
rem Aufruf: Doppelklick auf build_app.bat oder in der Eingabeaufforderung: build_app.bat
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
    echo Fehler: Kein Python 3 gefunden. Bitte von https://www.python.org/downloads/windows/ installieren
    echo und dabei "Add python.exe to PATH" ankreuzen.
    pause
    exit /b 1
)

%PY% -c "import tkinter" >nul 2>nul
if errorlevel 1 (
    echo Fehler: Tkinter fehlt. Bitte Python neu installieren und "tcl/tk and IDLE" auswaehlen.
    pause
    exit /b 1
)

for /f "delims=" %%v in ('%PY% --version') do echo Verwende %%v

if not exist .venv (
    %PY% -m venv .venv
)
call .venv\Scripts\activate.bat

python -m pip install --upgrade pip >nul
pip install -r requirements.txt -r requirements-build-windows.txt
if errorlevel 1 (
    echo Fehler bei der Installation der Abhaengigkeiten.
    pause
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --noconfirm --clean predict_endpoint.spec
if errorlevel 1 (
    echo Fehler beim Erstellen der EXE.
    pause
    exit /b 1
)

echo.
echo Fertig: %cd%\dist\Predict Endpoint.exe
echo Koeffizienten und Intercepts sind in die EXE eingebaut.
echo Die EXE kann an einen beliebigen Ort kopiert werden.
pause
