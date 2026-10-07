@echo off
setlocal
cd /d "%~dp0"
title AIRT - web console (http://localhost:8765)
set "PYEXE="
where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE ( where py >nul 2>nul && set "PYEXE=py" )
if not defined PYEXE (
  echo.
  echo  [x] Python 3 not found. Install from https://www.python.org/downloads/
  echo      and tick "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)
echo.
echo  AIRT web console is starting at  http://localhost:8765
echo  Remote targets are ENABLED - only scan systems you have written permission for.
echo  Keep this window open. Press Ctrl+C to stop.
echo.
timeout /t 2 >nul
start "" http://localhost:8765
%PYEXE% -m airt serve --port 8765 --allow-remote
pause
