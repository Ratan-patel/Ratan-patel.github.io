@echo off
REM ══════════════════════════════════════════════════════════════════
REM  RatanSec OS — Windows par ek click start (native Python)
REM
REM  Zaroori: Python install hona chahiye (python.org/downloads) —
REM  installer me "Add python.exe to PATH" pe tick karna mat bhoolo.
REM
REM  Note: Is mode me AI chat + dashboard chalega; nmap/john jaise tools
REM  nahi milenge (un steps par "skipped" likha aayega). Poora Kali
REM  experience chahiye to WSL use karo:
REM      wsl --install -d kali-linux
REM  phir Kali terminal me: ./setup.sh --with-tools
REM ══════════════════════════════════════════════════════════════════

cd /d "%~dp0"

echo.
echo  === RatanSec OS (Windows) ===
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo  [!] Python nahi mila.
  echo      Install karo: https://www.python.org/downloads/
  echo      Installer me "Add python.exe to PATH" pe TICK zaroor karo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo  [1/3] Python environment bana raha hoon...
  python -m venv .venv || (echo  [!] venv fail hua & pause & exit /b 1)
)

echo  [2/3] Dependencies install kar raha hoon...
".venv\Scripts\python.exe" -m pip install -q --upgrade pip
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || (
  echo  [!] pip install fail hua - internet check karo & pause & exit /b 1
)

if not exist ".env" (
  echo  [3/3] .env banaya - Notepad me password aur AI key bhar do, save karke band karo.
  copy /y ".env.example" ".env" >nul
  start /wait notepad ".env"
)

echo.
echo  Dashboard start ho raha hai: http://localhost:8000
echo  Band karne ke liye: is window me Ctrl + C
echo.
start "" http://localhost:8000
".venv\Scripts\python.exe" -m app.webui

echo.
echo  Server band ho gaya.
pause
