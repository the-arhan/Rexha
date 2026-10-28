# PowerShell launcher for Rexha Desktop Assistant
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Starting Rexha Desktop Assistant...    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Launch through canonical python module entry point
python -m rexha @args
