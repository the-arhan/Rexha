# PowerShell Build Script for Rexha Native Core
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Rexha Native Core CMake Build Script   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

$buildDir = Join-Path $projectRoot "native\build"
$binDir = Join-Path $projectRoot "src\rexha\bin"

# 1. CMake Configuration
Write-Host "`n[1/3] Configuring CMake project..." -ForegroundColor Yellow
cmake -B native/build -S native -G "Visual Studio 17 2022" -A x64

# 2. CMake Build
Write-Host "`n[2/3] Compiling Release binaries..." -ForegroundColor Yellow
cmake --build native/build --config Release

# 3. Verify Output
Write-Host "`n[3/3] Verifying binary deployment..." -ForegroundColor Yellow
$coreExe = Join-Path $binDir "rexha_native_core.exe"
if (Test-Path $coreExe) {
    Write-Host "rexha_native_core.exe is ready at: $coreExe" -ForegroundColor Green
} else {
    Write-Error "Build output binary missing: $coreExe"
}

Write-Host "`nBuild succeeded! Run .\scripts\test.ps1 to run the test suites." -ForegroundColor Cyan

