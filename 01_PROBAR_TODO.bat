@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
pushd "%~dp0"
if not exist "logs" mkdir "logs"
set "LOG=%~dp0logs\smoke_test.log"
echo ========================================
echo KUTANLAB - PRUEBA COMPLETA
echo ========================================
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Falta .venv. Ejecute 00_INSTALAR_O_REPARAR.bat.
  >"%LOG%" echo ERROR: Falta .venv\Scripts\python.exe.
  goto :error
)
".venv\Scripts\python.exe" "scripts\windows_launcher.py" smoke --log "%LOG%"
if errorlevel 1 goto :error
echo Log: "%LOG%"
if not defined KUTANLAB_MENU pause
popd
exit /b 0
:error
echo PRUEBA NO COMPLETADA. Consulte "%LOG%".
if not defined KUTANLAB_MENU pause
popd
exit /b 1
