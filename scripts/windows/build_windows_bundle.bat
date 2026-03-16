@echo off
setlocal

set ROOT_DIR=%~dp0\..\..
cd /d %ROOT_DIR%

if not exist desktop\seed mkdir desktop\seed
if exist db.sqlite3 copy /Y db.sqlite3 desktop\seed\db.sqlite3 >nul
if exist media (
  robocopy media desktop\seed\media /E >nul
)

pyinstaller --noconfirm desktop\windows_launcher.spec
