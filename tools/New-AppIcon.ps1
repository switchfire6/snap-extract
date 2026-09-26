# Original geometric card/export icon. Regenerate with Windows PowerShell.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$assetDirectory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../assets'))
New-Item -ItemType Directory -Force -Path $assetDirectory | Out-Null
$frames = @()
foreach ($size in @(16, 24, 32, 48, 64, 128, 256)) {
    $bitmap = New-Object Drawing.Bitmap 256, 256
    $canvas = [Drawing.Graphics]::FromImage($bitmap)
    $canvas.SmoothingMode = [Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $canvas.Clear([Drawing.ColorTranslator]::FromHtml('#10141f'))
    $mint = New-Object Drawing.SolidBrush ([Drawing.ColorTranslator]::FromHtml('#84edcc'))
    $white = New-Object Drawing.SolidBrush ([Drawing.ColorTranslator]::FromHtml('#eff2f8'))
    $outline = New-Object Drawing.Pen ([Drawing.ColorTranslator]::FromHtml('#53677e')), 10
    $canvas.DrawRectangle($outline, 44, 42, 116, 152)
    $canvas.FillRectangle($white, 68, 62, 116, 152)
    $dark = New-Object Drawing.SolidBrush ([Drawing.ColorTranslator]::FromHtml('#222b3b'))
    $canvas.FillRectangle($dark, 82, 78, 88, 68)
    $canvas.FillRectangle($dark, 82, 160, 52, 10)
    $canvas.FillRectangle($dark, 82, 184, 38, 10)
    $points = [Drawing.Point[]]@((New-Object Drawing.Point 158, 127), (New-Object Drawing.Point 222, 181),
        (New-Object Drawing.Point 158, 235), (New-Object Drawing.Point 158, 204),
        (New-Object Drawing.Point 124, 204), (New-Object Drawing.Point 124, 158), (New-Object Drawing.Point 158, 158))
    $canvas.FillPolygon($mint, $points)
    $scaled = New-Object Drawing.Bitmap $size, $size
    $graphics = [Drawing.Graphics]::FromImage($scaled)
    $graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.DrawImage($bitmap, 0, 0, $size, $size)
    $stream = New-Object IO.MemoryStream
    $scaled.Save($stream, [Drawing.Imaging.ImageFormat]::Png)
    $frames += ,($stream.ToArray())
    if ($size -eq 256) { $scaled.Save((Join-Path $assetDirectory 'app.png'), [Drawing.Imaging.ImageFormat]::Png) }
    $stream.Dispose(); $graphics.Dispose(); $scaled.Dispose(); $canvas.Dispose(); $bitmap.Dispose()
    $mint.Dispose(); $white.Dispose(); $dark.Dispose(); $outline.Dispose()
}
$packageAssets = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../snap_extract/assets'))
New-Item -ItemType Directory -Force -Path $packageAssets | Out-Null
$file = [IO.File]::Create((Join-Path $packageAssets 'app.ico'))
$writer = New-Object IO.BinaryWriter $file
try {
    $writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]$frames.Count)
    $offset = 6 + 16 * $frames.Count
    $sizes = @(16, 24, 32, 48, 64, 128, 0)
    for ($index = 0; $index -lt $frames.Count; $index++) {
        $writer.Write([byte]$sizes[$index]); $writer.Write([byte]$sizes[$index])
        $writer.Write([byte]0); $writer.Write([byte]0)
        $writer.Write([uint16]1); $writer.Write([uint16]32)
        $writer.Write([uint32]$frames[$index].Length); $writer.Write([uint32]$offset)
        $offset += $frames[$index].Length
    }
    foreach ($frame in $frames) { $writer.Write([byte[]]$frame) }
} finally { $writer.Dispose() }
