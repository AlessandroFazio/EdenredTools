<#
  install.ps1  –  Edenred Tools CLI (Windows)

  • Ensures Python 3.10 (winget)
  • Creates project venv → installs Poetry → poetry install
  • Drops   %USERPROFILE%\.edenredtools\bin\edenredtools.cmd
    and places that folder on the user PATH
#>

[CmdletBinding()]
param (
    [switch] $Yes
)

Write-Host "=== Edenred Tools – Windows installer ===" -ForegroundColor Cyan

$ScriptDir   = Split-Path -LiteralPath $PSCommandPath -Parent
$ProjectRoot = Split-Path -LiteralPath $ScriptDir      -Parent

function Invoke-Step { param([scriptblock]$Cmd,[string]$Msg)
    Write-Host $Msg -ForegroundColor Yellow
    & $Cmd
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Msg" }
}

function Ensure-Python {
    if (-not (Get-Command python3.10 -ErrorAction SilentlyContinue)) {
        if (-not $Yes) {
            $resp = Read-Host "Python 3.10 not found. Install with winget? [Y/n]"
            if ($resp -match '^[nN]') { throw "Python required – aborting." }
        }
        Invoke-Step { winget install --id Python.Python.3.10 -e } "Installing Python 3.10…"
    }
}
Ensure-Python
$Py = (Get-Command python3.10).Source

# ── Virtual-environment ───────────────────────────────────────────────
$Venv = Join-Path $ProjectRoot ".venv"
if (Test-Path $Venv) {
    Write-Host "Removing existing venv…" -Fore Yellow
    Remove-Item -Recurse -Force $Venv
}
Invoke-Step { & $Py -m venv $Venv }              "Creating venv…"
$Env:Path = "$Venv\Scripts;$Env:Path"
Invoke-Step { pip install -U pip setuptools }    "Upgrading pip & setuptools…"
Invoke-Step { pip install poetry }               "Installing Poetry…"

Push-Location $ProjectRoot
Invoke-Step { poetry install } "Running poetry install…"
Pop-Location

# ── Launcher shim ────────────────────────────────────────────────────
$ShimDir = "$HOME\.edenredtools\bin"
$Shim    = Join-Path $ShimDir "edenredtools.cmd"
New-Item $ShimDir -ItemType Directory -Force | Out-Null

@"
@echo off
"%~dp0..\..\..\.\venv\Scripts\edenredtools.exe" %*
"@ | Set-Content -Path $Shim -Encoding ascii

# Add shim folder to user PATH if missing
if (-not ($Env:Path -split ';' | Where-Object { $_ -eq $ShimDir })) {
    Write-Host "Adding $ShimDir to user PATH…" -Fore Yellow
    $old = [Environment]::GetEnvironmentVariable('Path','User')
    [Environment]::SetEnvironmentVariable('Path', "$old;$ShimDir", 'User')
}

Write-Host "`nInstallation complete! Open a **new PowerShell** session and run 'edenredtools --help'." -ForegroundColor Green
