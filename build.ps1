[CmdletBinding()]
param(
    [string]$Python = 'python',
    [string]$IsccPath = '',
    [switch]$PortableOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Push-Location -LiteralPath $PSScriptRoot
try {
    & $Python -c "import sys, struct; assert sys.platform == 'win32' and sys.version_info >= (3, 13) and struct.calcsize('P') == 8, 'Build with current 64-bit Python 3.13+ (including Tcl/Tk).'"
    if ($LASTEXITCODE -ne 0) { throw 'A current 64-bit Python 3.13+ installation is required.' }
    if (-not $PortableOnly -and -not $IsccPath) {
        $IsccPath = & "$PSScriptRoot/tools/Get-InnoSetup.ps1"
    }
    if (-not $PortableOnly -and -not (Test-Path -LiteralPath $IsccPath -PathType Leaf)) {
        throw 'Inno Setup compiler not found. Supply -IsccPath or use -PortableOnly.'
    }
    # A dedicated environment prevents unrelated developer packages being bundled.
    & $Python -m venv .build-venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment.' }
    $buildPython = Join-Path $PSScriptRoot '.build-venv/Scripts/python.exe'
    & $buildPython -m pip install --upgrade pip setuptools
    if ($LASTEXITCODE -ne 0) { throw 'Could not update pip.' }
    & $buildPython -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Could not install build dependencies.' }
    & $buildPython tools/windows_assets.py
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate Windows version information.' }
    & $buildPython -m PyInstaller --noconfirm --clean --onedir --windowed --noupx `
        --name 'Snap Extract' --specpath build --icon "$PSScriptRoot/snap_extract/assets/app.ico" `
        --version-file "$PSScriptRoot/build/version-info.txt" --collect-data snap_extract run_app.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    & $buildPython tools/package_distribution.py
    if ($LASTEXITCODE -ne 0) { throw 'Distribution packaging failed.' }
    if (-not $PortableOnly) {
        $appVersion = & $buildPython -c 'from snap_extract import __version__; print(__version__)'
        if ($LASTEXITCODE -ne 0) { throw 'Could not read application version.' }
        & $IsccPath /Qp "/DAppVersion=$appVersion" installer/SnapExtract.iss
        if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
        & $buildPython tools/package_distribution.py --checksums --installer
    } else {
        & $buildPython tools/package_distribution.py --checksums
    }
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate checksums.' }
} finally {
    Pop-Location
}
