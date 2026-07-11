# Start YOUR real Google Chrome with remote debugging so the apply agent
# can attach (fixes Google "This browser or app may not be secure").
#
# Playwright cannot attach to stock Firefox — use Chrome for Gmail/Google login.
# Your normal Firefox can stay open for everything else.
#
# Usage:
#   1. Close ALL Chrome windows first (required to reuse your profile).
#   2. powershell -ExecutionPolicy Bypass -File scripts\start_real_chrome.ps1
#   3. In the Chrome window that opens, sign into Google / LinkedIn if needed.
#   4. python src/main.py apply

param(
    [int]$Port = 9222,
    # Use your everyday Chrome profile (must close Chrome first).
    [switch]$UseDefaultProfile,
    # Dedicated profile folder (safer — won't lock your daily Chrome).
    [string]$UserDataDir = ""
)

$ErrorActionPreference = "Stop"

$chromeCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chrome) {
    Write-Host "Chrome not found. Install Google Chrome, or edit this script for Edge."
    exit 1
}

# Is something already listening on the debug port?
$listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listening) {
    Write-Host "Already debugging on port $Port — you can run: python src/main.py apply"
    exit 0
}

$chromeProcs = Get-Process -Name chrome -ErrorAction SilentlyContinue
if ($chromeProcs -and $UseDefaultProfile) {
    Write-Host "Close ALL Chrome windows first, then re-run with -UseDefaultProfile."
    Write-Host "Or omit -UseDefaultProfile to use a separate Job-Applier profile (safer)."
    exit 1
}

if (-not $UserDataDir) {
    if ($UseDefaultProfile) {
        $UserDataDir = Join-Path $env:LOCALAPPDATA "Google\Chrome\User Data"
    } else {
        $root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
        # scripts/ is under project root
        $projectRoot = Split-Path $PSScriptRoot -Parent
        $UserDataDir = Join-Path $projectRoot "data\chrome_cdp_profile"
    }
}

New-Item -ItemType Directory -Force -Path $UserDataDir | Out-Null

Write-Host "Starting real Chrome..."
Write-Host "  exe:     $chrome"
Write-Host "  profile: $UserDataDir"
Write-Host "  CDP:     http://127.0.0.1:$Port"
Write-Host ""
Write-Host "Sign into Google / LinkedIn in this window if asked, THEN run apply."

Start-Process -FilePath $chrome -ArgumentList @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$UserDataDir",
    "--no-first-run",
    "--no-default-browser-check",
    "https://mail.google.com"
)

Start-Sleep -Seconds 2
$ok = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($ok) {
    Write-Host "Ready. CDP is up on port $Port."
} else {
    Write-Host "Chrome started — wait a few seconds for CDP, then run apply."
}
