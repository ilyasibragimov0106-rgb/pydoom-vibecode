@echo off
rem Rebuild PYDOOM.exe (single file, no console window).
rem Requires: python, pygame, numpy, pyinstaller  (pip install pygame numpy pyinstaller)
cd /d "%~dp0"
python -m PyInstaller --onefile --windowed --clean --name PYDOOM main.py
echo.
echo Done. Executable: dist\PYDOOM.exe
