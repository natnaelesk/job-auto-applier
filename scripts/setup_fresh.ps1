# Fresh clone setup (Windows)
#
# Creates .venv, installs deps, copies profile templates and .env if missing.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/setup_fresh.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/setup_fresh.ps1 -WithApplyHq
#   powershell -ExecutionPolicy Bypass -File scripts/setup_fresh.ps1 -SkipPlaywright

param(
    [switch]$WithApplyHq,
    [switch]$SkipPlaywright
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "==> Job Auto-Applier fresh setup" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Install Python 3.11+ and add it to PATH." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path .venv)) {
    Write-Host "==> Creating .venv"
    python -m venv .venv
}

$py = ".\.venv\Scripts\python.exe"
Write-Host "==> Installing requirements"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt

if (-not $SkipPlaywright) {
    Write-Host "==> Installing Playwright browsers (firefox + chromium)"
    & $py -m playwright install firefox chromium
} else {
    Write-Host "==> Skipping Playwright browsers (-SkipPlaywright)"
}

$copies = @(
    @("profile\about_me.example.md", "profile\about_me.md"),
    @("profile\master_cv.example.md", "profile\master_cv.md"),
    @("profile\answers.example.md", "profile\answers.md"),
    @(".env.example", ".env")
)
foreach ($pair in $copies) {
    $src, $dst = $pair
    if ((Test-Path $src) -and -not (Test-Path $dst)) {
        Copy-Item $src $dst
        Write-Host "==> Created $dst (edit this file)"
    } elseif (Test-Path $dst) {
        Write-Host "==> Keep existing $dst"
    }
}

New-Item -ItemType Directory -Force -Path data, output\cvs, output\cvs\general, output\cvs\cover_letter, output\screenshots, profile\docs\uploads | Out-Null

if ($WithApplyHq) {
    Write-Host "==> Apply HQ Python deps"
    & $py -m pip install -r apply_hq\requirements.txt
    if ((Test-Path "apply_hq\.env.example") -and -not (Test-Path "apply_hq\.env")) {
        Copy-Item "apply_hq\.env.example" "apply_hq\.env"
        Write-Host "==> Created apply_hq\.env (edit this file)"
    }
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Host "==> Apply HQ frontend (npm ci)"
        Push-Location apply_hq\web
        npm ci
        Pop-Location
    } else {
        Write-Host "WARNING: npm not found — install Node.js 20+ for Apply HQ UI." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. Edit .env          (TELEGRAM_* and CURSOR_API_KEY — see ENV.md)"
Write-Host "  2. Edit profile\about_me.md , master_cv.md , answers.md"
Write-Host "  3. Run:  .\.venv\Scripts\python.exe src\main.py scan"
Write-Host "  4. Run:  .\.venv\Scripts\python.exe src\main.py ui"
if ($WithApplyHq) {
    Write-Host "  5. Apply HQ: edit apply_hq\.env then  cd apply_hq; ..\.venv\Scripts\python.exe run.py"
}
Write-Host ""
Write-Host "Full guide: SETUP.md   |   Secrets map: ENV.md"
