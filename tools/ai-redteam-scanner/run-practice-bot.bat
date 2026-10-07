@echo off
setlocal
cd /d "%~dp0"
title AIRT - practice bot (deliberately vulnerable, http://localhost:8899)
set "PYEXE="
where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE ( where py >nul 2>nul && set "PYEXE=py" )
if not defined PYEXE (
  echo.
  echo  [x] Python 3 not found. Install from https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)
echo.
echo  Practice bot starting on http://localhost:8899/chat
echo  Keep this window open, then run scan-practice-bot.bat in another window.
echo.
%PYEXE% examples\vulnerable_bot.py
pause
