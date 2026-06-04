<#
PowerShell helper to create a virtual environment and install required Python packages.
Usage (PowerShell):
  .\install_deps.ps1

This script will create a `.venv` folder (if missing) and install packages into it.
#>

$ErrorActionPreference = 'Stop'

$venv = Join-Path -Path (Get-Location) -ChildPath '.venv'
if (-not (Test-Path $venv)) {
    Write-Host "Creating virtual environment in $venv..."
    python -m venv $venv
} else {
    Write-Host "Virtual environment already exists at $venv"
}

$py = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

& $py -m pip install --upgrade pip
& $py -m pip install Pillow click pyinstaller

Write-Host "Done. To use the environment run: . .\.venv\Scripts\Activate.ps1"
Write-Host "Then run: pip install -r requirements.txt  (if you add a requirements.txt)"
