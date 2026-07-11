@echo off
cd /d "%~dp0.."
title Job Auto-Applier
".\.venv\Scripts\pythonw.exe" "src\main.py" ui
if errorlevel 1 (
  ".\.venv\Scripts\python.exe" "src\main.py" ui
  pause
)
