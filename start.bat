@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Zerthanadan qashu - server
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 server.py
) else (
  python server.py
)
echo.
echo Server toqtady. Python ornatylmaghan bolsa: https://www.python.org/downloads/ (Add to PATH belgisin qoi)
pause
