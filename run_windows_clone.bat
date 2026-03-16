@echo off
setlocal

set "SCRIPT_URL=https://raw.githubusercontent.com/JuanRRaFdez/VtesProxi/main/scripts/windows/clone_and_run.ps1"
set "SCRIPT_PATH=%TEMP%\VtesProxi_clone_and_run.ps1"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing '%SCRIPT_URL%' -OutFile '%SCRIPT_PATH%'; & '%SCRIPT_PATH%'"
