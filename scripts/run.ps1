# Run script for MillPresenter
$ScriptDir = Split-Path $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path $ScriptDir -Parent

# Activate venv
if (Test-Path "$ProjectRoot\.venv\Scripts\Activate.ps1") {
    & "$ProjectRoot\.venv\Scripts\Activate.ps1"
} else {
    Write-Warning "Virtual environment not found. Running with system Python."
}

# Set PYTHONPATH to include src
$env:PYTHONPATH = "$ProjectRoot\src"

# Run the app
python -m mill_presenter.app $args
