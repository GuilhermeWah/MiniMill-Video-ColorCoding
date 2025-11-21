# Demo script: Runs detection then launches player
$ScriptDir = Split-Path $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path $ScriptDir -Parent

# Paths
$VideoPath = "$ProjectRoot\content\DSC_3310.MOV"
$ConfigPath = "$ProjectRoot\configs\sample.config.yaml"
$DetectionsPath = "$ProjectRoot\detections.jsonl"
$RoiMaskPath = "$ProjectRoot\content\roi_mask.png"

# Activate venv
if (Test-Path "$ProjectRoot\.venv\Scripts\Activate.ps1") {
    & "$ProjectRoot\.venv\Scripts\Activate.ps1"
}

# Set PYTHONPATH
$env:PYTHONPATH = "$ProjectRoot\src"

# 1. Run Detection
Write-Host "Step 1: Running Detection..." -ForegroundColor Cyan
python "$ScriptDir\run_detection.py" --input "$VideoPath" --output "$DetectionsPath" --config "$ConfigPath" --roi "$RoiMaskPath"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Detection failed!"
    exit 1
}

# 2. Run Player
Write-Host "Step 2: Launching Player..." -ForegroundColor Cyan
python -m mill_presenter.app --video "$VideoPath" --detections "$DetectionsPath" --config "$ConfigPath"
