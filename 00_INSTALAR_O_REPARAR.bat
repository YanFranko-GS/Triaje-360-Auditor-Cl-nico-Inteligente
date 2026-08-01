@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
pushd "%~dp0"
if not exist "logs" mkdir "logs"
set "LOG=%~dp0logs\install.log"
>"%LOG%" echo KUTANLAB TRIaje 360 - INSTALACIÓN O REPARACIÓN
echo ========================================
echo KUTANLAB - INSTALAR O REPARAR
echo ========================================

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "VENV_MODE=crear"
if exist "%VENV_PY%" (
  "%VENV_PY%" --version >>"%LOG%" 2>&1
  if not errorlevel 1 goto :run_install
  echo El entorno virtual existe, pero su Python no funciona. Se intentará repararlo sin borrarlo.
  set "VENV_MODE=reparar"
)

set "PY_EXE="
set "PY_ARG="
where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12)" >nul 2>&1
  if not errorlevel 1 set "PY_EXE=py"& set "PY_ARG=-3.12"
  if not defined PY_EXE py -3.11 -c "import sys; assert sys.version_info[:2] == (3,11)" >nul 2>&1
  if not defined PY_EXE if not errorlevel 1 set "PY_EXE=py"& set "PY_ARG=-3.11"
)
if not defined PY_EXE if defined TRIAJE_PYTHON if exist "%TRIAJE_PYTHON%" set "PY_EXE=%TRIAJE_PYTHON%"
if not defined PY_EXE if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" set "PY_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not defined PY_EXE (
  echo ERROR: No se encontró Python 3.12 ni 3.11 compatible.
  echo Instale Python 3.12 o 3.11 sin requerir permisos de administrador.
  goto :error
)

echo Preparando .venv con "%PY_EXE%" %PY_ARG% ^(modo: !VENV_MODE!^)...
if /I "!VENV_MODE!"=="reparar" (
  "%PY_EXE%" %PY_ARG% -m venv --upgrade "%~dp0.venv" >>"%LOG%" 2>&1
) else (
  "%PY_EXE%" %PY_ARG% -m venv "%~dp0.venv" >>"%LOG%" 2>&1
)
if errorlevel 1 (
  echo ERROR: No se pudo crear .venv. Consulte "%LOG%".
  goto :error
)

:run_install
"%VENV_PY%" "%~dp0scripts\windows_launcher.py" install --log "%LOG%"
if errorlevel 1 goto :error
echo.
echo INSTALACIÓN COMPLETADA
echo Log: "%LOG%"
goto :success

:error
echo.
echo INSTALACIÓN NO COMPLETADA. Causa y detalles: "%LOG%"
if not defined KUTANLAB_MENU pause
popd
exit /b 1

:success
if not defined KUTANLAB_MENU pause
popd
exit /b 0
