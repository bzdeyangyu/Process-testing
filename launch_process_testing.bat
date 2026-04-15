@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0process_testing_launcher.py"
) else (
    python "%~dp0process_testing_launcher.py"
)
exit /b %errorlevel%
