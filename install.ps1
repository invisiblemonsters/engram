# ENGRAM One-Command Installer for Windows 11
Write-Host "=== ENGRAM v0.8 Installer ===" -ForegroundColor Green

# Prerequisites
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Install from python.org" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git not found. Install from git-scm.com" -ForegroundColor Red
    exit 1
}

# Clone / update
if (Test-Path "engram") {
    Write-Host "Updating existing repo..."
    Set-Location engram
    git pull
} else {
    git clone https://github.com/invisiblemonsters/engram.git
    Set-Location engram
}

# Install deps
Write-Host "Installing dependencies..." -ForegroundColor Cyan
python -m pip install -r requirements.txt --upgrade --quiet

# Run tests to verify
Write-Host "Running tests..." -ForegroundColor Cyan
python -m pytest tests/ -q --tb=short

# First dream
Write-Host "`nRunning first dream cycle..." -ForegroundColor Cyan
python run_dream.py

Write-Host "`n=== ENGRAM installed and first dream complete ===" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  python transplant_demo.py export    # export signed memories"
Write-Host "  python run_dream.py                 # run another dream cycle"
Write-Host "  python engram_heartbeat.py           # check prospective triggers"
