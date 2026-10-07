@echo off
setlocal
cd /d "%~dp0"
title AIRT - demo scan (safe, offline)
set "PYEXE="
where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE ( where py >nul 2>nul && set "PYEXE=py" )
if not defined PYEXE (
  echo.
  echo  [x] Python 3 not found.
  echo      Install it from https://www.python.org/downloads/
  echo      and TICK the box "Add python.exe to PATH" during setup.
  echo.
  pause
  exit /b 1
)
echo.
echo  AIRT demo - attacking the built-in offline simulator (no network, no API key)
echo  ------------------------------------------------------------------------
echo.
%PYEXE% -m airt demo --mutate-all
echo.
echo  Reports (.html and .json) were written to:
echo  %CD%
echo.
echo  Open the .html file in your browser to see the report.
pause
