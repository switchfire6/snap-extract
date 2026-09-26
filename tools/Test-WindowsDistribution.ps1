[CmdletBinding()]
param([switch]$PortableOnly)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$version = & python -c 'from snap_extract import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0) { throw 'Could not read application version. Run from the repository root.' }
$testRoot = Join-Path $root ('build/smoke/' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path "$testRoot/data/SnapExtract", "$testRoot/state" | Out-Null
$source = Join-Path $testRoot 'state/CollectionState.json'
@{ ServerState = @{ Cards = @(@{ CardDefId = 'Test0' }); Decks = @() } } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $source -Encoding UTF8
$cards = @{}
for ($index = 0; $index -lt 100; $index++) {
    $cardId = "Test$index"
    $cards[$cardId] = @{ card_id = $cardId; name = "Test card $index"; cost = 1; power = 2; ability = 'No ability.' }
}
@{ schema = 1; fetched_at = [DateTimeOffset]::UtcNow.ToString('o'); cards = $cards } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$testRoot/data/SnapExtract/catalog.json" -Encoding UTF8

function Test-App([string]$Executable) {
    $settings = Join-Path $testRoot 'data/SnapExtract/settings.json'
    @{ collection_path = $source } | ConvertTo-Json | Set-Content -LiteralPath $settings -Encoding UTF8
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $Executable
    $start.WorkingDirectory = $testRoot
    $start.UseShellExecute = $false
    $start.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden
    $start.EnvironmentVariables['LOCALAPPDATA'] = Join-Path $testRoot 'data'
    $process = [Diagnostics.Process]::Start($start)
    try {
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        $loaded = $false
        while ([DateTime]::UtcNow -lt $deadline -and -not $process.HasExited) {
            $preferences = Get-Content -LiteralPath $settings -Raw | ConvertFrom-Json
            if ($preferences.PSObject.Properties.Name -contains 'columns') { $loaded = $true; break }
            Start-Sleep -Milliseconds 100
        }
        if (-not $loaded) { throw "Packaged app did not load the offline fixture: $Executable" }
        if (-not $process.CloseMainWindow()) { throw 'Packaged app did not create its main window.' }
        if (-not $process.WaitForExit(10000) -or $process.ExitCode -ne 0) { throw 'Packaged app did not exit cleanly.' }
    } finally {
        if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() }
        $process.Dispose()
    }
}

$portable = Join-Path $testRoot 'Portable app'
Expand-Archive -LiteralPath "$root/dist/Snap-Extract-$version-Windows-x64.zip" -DestinationPath $portable
Test-App (Join-Path $portable 'Snap Extract.exe')
Write-Host 'Portable ZIP: offline collection loaded and app closed successfully.'
if ($PortableOnly) { return }

$registry = 'HKCU:/Software/Microsoft/Windows/CurrentVersion/Uninstall/{A230FA14-4B4A-42DC-B977-8616F778D75F}_is1'
$startLink = Join-Path ([Environment]::GetFolderPath('Programs')) 'Snap Extract.lnk'
$desktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Snap Extract.lnk'
if ((Test-Path -LiteralPath $registry) -or (Test-Path -LiteralPath $startLink) -or (Test-Path -LiteralPath $desktopLink)) {
    throw 'An existing Snap Extract install or shortcut was found. Run installer tests in a clean Windows account, or use -PortableOnly.'
}
$install = Join-Path $testRoot 'Installed app'
$setup = Join-Path $root "dist/Snap-Extract-$version-Setup.exe"
$arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/TASKS=desktopicon', ('/DIR="' + $install + '"'))
try {
    # Exercise install and upgrade with the same stable application identity.
    foreach ($attempt in 1..2) {
        $process = Start-Process -FilePath $setup -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw "Installer failed: $($process.ExitCode)" }
        foreach ($path in @($registry, $startLink, $desktopLink, "$install/THIRD_PARTY_LICENSES.txt")) {
            if (-not (Test-Path -LiteralPath $path)) { throw "Installation did not create $path" }
        }
        $shell = New-Object -ComObject WScript.Shell
        if ($shell.CreateShortcut($startLink).TargetPath -ne (Join-Path $install 'Snap Extract.exe')) {
            throw 'Start menu launcher has the wrong target.'
        }
        Test-App (Join-Path $install 'Snap Extract.exe')
        'User-owned export' | Set-Content -LiteralPath "$install/keep-my-export.txt" -Encoding UTF8
    }
} finally {
    $uninstaller = Join-Path $install 'unins000.exe'
    if (Test-Path -LiteralPath $uninstaller) {
        $process = Start-Process -FilePath $uninstaller -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -WindowStyle Hidden -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw "Uninstall failed: $($process.ExitCode)" }
    }
}
foreach ($path in @($registry, $startLink, $desktopLink, "$install/Snap Extract.exe")) {
    if (Test-Path -LiteralPath $path) { throw "Uninstall left behind $path" }
}
if (-not (Test-Path -LiteralPath "$install/keep-my-export.txt")) { throw 'Uninstall deleted a user export.' }
if (-not (Test-Path -LiteralPath "$testRoot/data/SnapExtract/settings.json")) { throw 'Uninstall deleted preferences.' }
Write-Host 'Installer: install, upgrade, shortcuts, offline launch and uninstall passed; user data preserved.'
