$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
# Keep unrelated development packages out of the app.
$buildPython = Join-Path $PSScriptRoot '.build-venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $buildPython)) {
    python -m venv .build-venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment.' }
}
& $buildPython -m pip install 'pyinstaller==6.22.2'
if ($LASTEXITCODE -ne 0) { throw 'Could not install PyInstaller.' }
& $buildPython -m PyInstaller --noconfirm --onefile --windowed --name 'Snap Extract' run_app.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
& $buildPython tools/package_distribution.py
if ($LASTEXITCODE -ne 0) { throw 'Distribution packaging failed.' }
