@echo off
setlocal
cd /d "%~dp0"
title AIRT - scanning the practice bot
set "PYEXE="
where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE ( where py >nul 2>nul && set "PYEXE=py" )
if not defined PYEXE (
  echo  [x] Python 3 not found. Install from https://www.python.org/downloads/
  pause
  exit /b 1
)
echo.
echo  Scanning the practice bot at http://localhost:8899/chat
echo  (make sure run-practice-bot.bat is running in another window)
echo.
%PYEXE% -m airt scan --target-type http --target-url http://localhost:8899/chat --body "{\"message\":\"{prompt}\"}" --response-path reply --inject-canary --profile standard --mutate base64,roleplay --yes --html airt_report.html --sarif airt_report.sarif --json airt_report.json
echo.
echo  Report written to %CD%\airt_report.html
pause
