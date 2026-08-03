# Fresh clone setup (Windows)

Creates .venv, installs deps, copies profile templates and .env if missing.

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

New-Item -ItemType Directory -Force -Path data, output\cvs, output\cvs\general, output\cvs\cover_letter, output\screenshots | Out-Null

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. Edit .env          (TELEGRAM_* and CURSOR_API_KEY)"
Write-Host "  2. Edit profile\about_me.md , master_cv.md , answers.md"
Write-Host "  3. Run:  .\.venv\Scripts\python.exe src\main.py scan"
Write-Host "  4. Run:  .\.venv\Scripts\python.exe src\main.py ui"
Write-Host ""
Write-Host "Full guide: SETUP.md"
