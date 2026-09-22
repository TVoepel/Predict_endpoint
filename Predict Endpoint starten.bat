@echo off
rem Doppelklick-Starter fuer Windows, falls die EXE nicht gebaut wurde.
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw main.py) || (python main.py)
