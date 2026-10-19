@echo off
REM Local build (optional - GitHub builds every release automatically)
cd /d "%~dp0"
py -m pip install --upgrade pyinstaller && py build.py
pause
