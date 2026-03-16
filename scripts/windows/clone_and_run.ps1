$ErrorActionPreference = "Stop"

function ConvertTo-PlainText {
    param([Security.SecureString]$SecureValue)

    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function Read-RequiredValue {
    param([string]$Prompt)

    while ($true) {
        $value = Read-Host $Prompt
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value.Trim()
        }
    }
}

$repoUrl = "https://github.com/JuanRRaFdez/VtesProxi.git"
$installRoot = Join-Path $env:LOCALAPPDATA "WebVTES"
$repoDir = Join-Path $installRoot "repo"
$pythonExe = Join-Path $repoDir ".venv\Scripts\python.exe"
$portableDir = Join-Path $repoDir "portable_data"

New-Item -ItemType Directory -Force -Path $installRoot | Out-Null

if (-not (Test-Path (Join-Path $repoDir ".git"))) {
    if (Test-Path $repoDir) {
        Remove-Item -Recurse -Force $repoDir
    }
    git clone $repoUrl $repoDir
}

Set-Location $repoDir

if (-not (Test-Path $pythonExe)) {
    py -m venv .venv
}

& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r requirements.txt

$env:WEBVTES_PORTABLE_DIR = $portableDir

& $pythonExe manage.py migrate --settings webvtes.settings_desktop

$hasUsers = (& $pythonExe manage.py shell -c "from django.contrib.auth import get_user_model; print('1' if get_user_model().objects.exists() else '0')" --settings webvtes.settings_desktop).Trim()

if ($hasUsers -ne "1") {
    $username = Read-RequiredValue "Nombre de usuario inicial"
    $password = ConvertTo-PlainText (Read-Host "Clave inicial" -AsSecureString)
    & $pythonExe scripts/bootstrap_local_user.py --username $username --password $password --portable-dir $portableDir
}

& $pythonExe desktop/windows_launcher.py --portable-dir $portableDir
