$ErrorActionPreference = "Stop"

$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $rootDir

New-Item -ItemType Directory -Force -Path "desktop/seed" | Out-Null
if (Test-Path "db.sqlite3") {
    Copy-Item "db.sqlite3" "desktop/seed/db.sqlite3" -Force
}
if (Test-Path "media") {
    New-Item -ItemType Directory -Force -Path "desktop/seed/media" | Out-Null
    Copy-Item "media/*" "desktop/seed/media" -Recurse -Force
}

pyinstaller --noconfirm desktop/windows_launcher.spec
