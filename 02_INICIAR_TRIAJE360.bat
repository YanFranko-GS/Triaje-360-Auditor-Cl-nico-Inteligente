@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
pushd "%~dp0"
if not exist "logs" mkdir "logs"
set "LOG=%~dp0logs\start.log"
echo ========================================
echo KUTANLAB - INICIAR TRIaje 360
echo ========================================
if exist ".venv\Scripts\python.exe" goto :start
echo No existe el entorno virtual.
choice /C SN /N /M "¿Desea ejecutar ahora Instalar o reparar? [S/N]: "
if errorlevel 2 goto :error
set "KUTANLAB_MENU=1"
call "00_INSTALAR_O_REPARAR.bat"
if errorlevel 1 goto :error
:start
".venv\Scripts\python.exe" "scripts\windows_launcher.py" start --log "%LOG%"
if errorlevel 1 goto :error
echo Log: "%LOG%"
if not defined KUTANLAB_MENU pause
popd
exit /b 0
:error
echo No se pudo iniciar TRIaje 360. Consulte "%LOG%".
if not defined KUTANLAB_MENU pause
popd
exit /b 1
