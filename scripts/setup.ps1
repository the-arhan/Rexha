# PowerShell Environment Setup for Rexha Desktop Assistant
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Rexha Hybrid Environment Setup Script  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Check Python
Write-Host "`n[1/4] Checking Python environment..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python was not found in PATH. Please install Python 3.12+ (x64)."
}
$pyVer = python --version
Write-Host "Found: $pyVer ($($pythonCmd.Source))" -ForegroundColor Green

# 2. Install / Verify Python dependencies
Write-Host "`n[2/4] Installing Python requirements..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Write-Host "Python dependencies installed successfully." -ForegroundColor Green

# 3. Check CMake
Write-Host "`n[3/4] Checking CMake installation..." -ForegroundColor Yellow
$cmakeCmd = Get-Command cmake -ErrorAction SilentlyContinue
if (-not $cmakeCmd) {
    Write-Error "CMake was not found in PATH. Please install CMake 3.25+."
}
$cmakeVer = cmake --version | Select-Object -First 1
Write-Host "Found: $cmakeVer ($($cmakeCmd.Source))" -ForegroundColor Green

# 4. Check C++ Compiler (Visual Studio 2022)
Write-Host "`n[4/4] Detecting C++ Compiler (MSVC / Visual Studio)..." -ForegroundColor Yellow
$vswherePath = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vswherePath) {
    $vsPath = & $vswherePath -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($vsPath) {
        Write-Host "Found Visual Studio C++ Toolset at: $vsPath" -ForegroundColor Green
    } else {
        Write-Warning "Visual Studio C++ Build Tools not detected via vswhere."
    }
} else {
    Write-Warning "vswhere.exe not found at default location."
}

Write-Host "`nSetup complete! Next step: Run .\scripts\build.ps1 to build native components." -ForegroundColor Cyan

