@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
 echo No se encontro Python. Instala Python 3 desde python.org y activa "Add python to PATH".
 pause
 exit /b 1
)
echo Abriendo Que dirIA Bogota...
python server.py
pause
