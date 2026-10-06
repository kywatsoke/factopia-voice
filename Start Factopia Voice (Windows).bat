@echo off
rem Starts Factopia Voice. The first run sets up Python and downloads the voice model.
title Factopia Voice
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
  echo First run: installing a small helper ^(uv^) that sets up Python for this app...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
  if errorlevel 1 (
    echo Could not install the helper. Check the internet connection and try again.
    pause
    exit /b 1
  )
)
echo Starting Factopia Voice ^(the first start can take a few minutes^)...
uv run --python 3.12 --no-project --with-requirements requirements.txt python -m factopia_voice
if errorlevel 1 (
  echo.
  echo Factopia Voice stopped with an error. Copy the text above if you need help.
  pause
)
