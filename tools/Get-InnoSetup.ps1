# Download a pinned compiler and install it only in the ignored build directory.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$toolDirectory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../build/tools'))
$compiler = Join-Path $toolDirectory 'InnoSetup/ISCC.exe'
if (-not (Test-Path -LiteralPath $compiler -PathType Leaf)) {
    New-Item -ItemType Directory -Force -Path $toolDirectory | Out-Null
    $download = Join-Path $toolDirectory 'innosetup-6.7.3.exe'
    $expected = '9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732'
    if (-not (Test-Path -LiteralPath $download) -or (Get-FileHash -LiteralPath $download).Hash -ne $expected) {
        Invoke-WebRequest -Uri 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe' -OutFile $download
    }
    if ((Get-FileHash -LiteralPath $download).Hash -ne $expected) {
        throw 'Inno Setup download checksum mismatch.'
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $download
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike '*O=Pyrsys B.V.*') {
        throw 'Inno Setup download does not have the expected valid publisher signature.'
    }
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/CURRENTUSER',
        '/NOICONS', '/TASKS=', ('/DIR="' + (Join-Path $toolDirectory 'InnoSetup') + '"'))
    $process = Start-Process -FilePath $download -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $compiler)) {
        throw 'Could not install the Inno Setup compiler.'
    }
}
$compiler
