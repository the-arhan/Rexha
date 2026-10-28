# PowerShell Automated Test Runner for Rexha
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Rexha Full Automated Test Suite Runner " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

# 1. Native C++ Tests
Write-Host "`n[1/2] Running Native C++ Test Suite..." -ForegroundColor Yellow
$nativeTestExe = Join-Path $projectRoot "native\build\Release\rexha_native_tests.exe"
if (Test-Path $nativeTestExe) {
    & $nativeTestExe
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Native C++ tests failed with exit code $LASTEXITCODE"
    }
} else {
    Write-Warning "Native test binary not found at $nativeTestExe. Run .\scripts\build.ps1 first."
}

# 2. Python Pytest Suite
Write-Host "`n[2/2] Running Python Pytest Suite..." -ForegroundColor Yellow
pytest
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python test suite failed with exit code $LASTEXITCODE"
}

Write-Host "`nAll test suites passed successfully!" -ForegroundColor Green

