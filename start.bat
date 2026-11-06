@echo off
REM Bam dup de chay du an. Moi logic nam trong run.py; file nay chi tao venv Windows lan dau.
REM (.venv la venv Linux tao tu WSL, Windows khong dung duoc -> dung .venv-win)
cd /d "%~dp0"
if not exist ".venv-win\Scripts\python.exe" (
    echo Tao moi truong ao .venv-win lan dau...
    python -m venv .venv-win || goto :fail
)
".venv-win\Scripts\python.exe" run.py %*
if errorlevel 1 goto :fail
exit /b 0

:fail
pause
exit /b 1
