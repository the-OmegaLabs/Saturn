# Build-Wheel: package saturn (and its workspace asset packages) into wheels,
# verify the wheel contents, then smoke-test an install in a throwaway venv.
#
# Package split:
#   saturn              minimal framework (fonts/icons come from the two packages below)
#   saturn-fonts-cjk    CJK font assets
#   saturn-icons-material  Material icon assets
# Wheels contain no .glsl (embedded in saturn/renderer/_glsl.py by
# gen_glsl.py) and no test files.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File tools\build-wheel.ps1
# Switches:
#   -WheelOnly  build only the wheel for saturn (skip the .tar.gz sdist)
#   -NoClean    keep existing files in dist\ before building
#   -SkipSmoke  skip the temporary-venv install test (offline builds)

param(
    [switch]$WheelOnly,
    [switch]$NoClean,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$dist = Join-Path $root "dist"

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Action
    # Cmdlets leave $LASTEXITCODE untouched; only native commands set it.
    if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv was not found on PATH; install it from https://docs.astral.sh/uv/"
}

Invoke-Step "cleaning $dist" {
    if (-not $NoClean -and (Test-Path $dist)) {
        Remove-Item "$dist\*" -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Force -Path $dist | Out-Null
}

Invoke-Step "regenerating embedded GLSL (saturn/renderer/_glsl.py)" {
    uv run --no-sync python gen_glsl.py
}

foreach ($project in @("packages\saturn-fonts-cjk", "packages\saturn-icons-material")) {
    Invoke-Step "building workspace package $project" {
        uv build --wheel $project
    }
}

Invoke-Step "building saturn" {
    if ($WheelOnly) { uv build --wheel . } else { uv build . }
}

# The GL backend imports _glsl.py when the checkout .glsl files are absent and
# the Vulkan backend needs the committed SPIR-V blobs; a wheel missing any of
# that installs fine and crashes on first use, so verify before declaring done.
Invoke-Step "verifying wheel contents" {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $wheel = Get-ChildItem "$dist\saturn-*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $wheel) { throw "no saturn wheel found in $dist" }
    $zip = [System.IO.Compression.ZipFile]::OpenRead($wheel.FullName)
    try {
        $names = $zip.Entries.FullName
        $required = @(
            "saturn/renderer/_glsl.py",
            "saturn/renderer/vulkan_frag.spv",
            "saturn/renderer/vulkan_vert.spv",
            "saturn/assets/Inter-VariableFont_opsz,wght.woff2",
            "saturn/assets/Inter-Bold.woff2"
        )
        foreach ($entry in $required) {
            if ($names -notcontains $entry) { throw "wheel is missing required file: $entry" }
        }
        $forbidden = @($names | Where-Object { $_ -like "*.glsl" -or $_ -match "(^|/)test" })
        if ($forbidden.Count -gt 0) { throw "wheel ships non-runtime files: $($forbidden -join ', ')" }
        foreach ($prefix in @("saturn/web/static/", "saturn/_gen/")) {
            $count = @($names | Where-Object { $_ -like "$prefix*" }).Count
            if ($count -eq 0) { throw "wheel has no files under $prefix" }
        }
        Write-Host ("    {0} entries in {1:N2} MB" -f $names.Count, ($wheel.Length / 1MB))
    } finally {
        $zip.Dispose()
    }
}

if (-not $SkipSmoke) {
    Invoke-Step "smoke-testing the wheel in a temporary venv" {
        $venv = Join-Path $env:TEMP ("saturn-wheel-smoke-" + $PID)
        $python = Join-Path $venv "Scripts\python.exe"
        try {
            uv venv $venv
            uv pip install --python $python --find-links $dist "saturn==0.1.0"
            $check = @"
import importlib.metadata
assert importlib.metadata.version('saturn') == '0.1.0'
import saturn.renderer.gl   # installed wheel has no .glsl: exercises the embedded copy
try:
    import saturn.renderer.vulkan
except ImportError as error:
    assert 'saturn[vulkan]' in str(error), error
    print('optional vulkan hint OK')
else:
    print('vulkan package present')
print('wheel smoke OK')
"@
            $check | & $python -
            if ($LASTEXITCODE -ne 0) { throw "smoke test imports failed" }
        } finally {
            if (Test-Path $venv) { Remove-Item $venv -Recurse -Force -ErrorAction SilentlyContinue }
        }
    }
}

Write-Host ""
Write-Host "Artifacts in ${dist}:" -ForegroundColor Green
Get-ChildItem $dist -File | Where-Object { $_.Extension -in ".whl", ".gz" } |
    ForEach-Object { Write-Host ("  {0}  ({1:N2} MB)" -f $_.Name, ($_.Length / 1MB)) }
