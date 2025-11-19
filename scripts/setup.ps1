# Setup script for MillPresenter
Write-Host "Setting up MillPresenter Environment..."

# Check for Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}
Write-Host "Found $pythonVersion"

# Create venv if it doesn't exist
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

# Activate venv
Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..."
pip install --upgrade pip
pip install -e .

Write-Host "Setup complete! Run 'scripts/run.ps1' to start the app."
