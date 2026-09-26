# =============================================================
# promote_model.ps1
# -----------------
# Promotes validated candidate artifacts from training/ into
# backend/model/, making them the live artifacts served by the
# FastAPI application.
#
# Source convention (notebook output):  training/<name>_1.pkl
# Target convention (API serving dir):  backend/model/<name>.pkl
#
# Each existing canonical artifact is backed up as <name>.pkl.bak
# before being overwritten, enabling one-step rollback via
# rollback_model.ps1.
#
# Usage (from project root):
#   .\scripts\promote_model.ps1
# =============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TrainingDir = Join-Path $PSScriptRoot "..\training"
$ModelDir    = Join-Path $PSScriptRoot "..\backend\model"

# Four artifact pairs: source suffix _1, target no suffix
$Artifacts = @(
    @{ Name = "model";     Src = "model_1.pkl";     Dst = "model.pkl"     },
    @{ Name = "scaler";    Src = "scaler_1.pkl";    Dst = "scaler.pkl"    },
    @{ Name = "features";  Src = "features_1.pkl";  Dst = "features.pkl"  },
    @{ Name = "threshold"; Src = "threshold_1.pkl"; Dst = "threshold.pkl" }
)

Write-Host ''
Write-Host '========================================'
Write-Host ' Fraud Detection - Model Promotion'
Write-Host '========================================'
Write-Host ''

# Validate all source artifacts exist before touching the target directory
foreach ($a in $Artifacts) {
    $src = Join-Path $TrainingDir $a.Src
    if (-not (Test-Path $src)) {
        Write-Error "Source artifact not found: $src. Run the notebook (Kernel > Restart and Run All) first."
        exit 1
    }
}

# Validate model_metadata.json exists
$MetaSrc = Join-Path $TrainingDir "model_metadata.json"
if (-not (Test-Path $MetaSrc)) {
    Write-Error "training/model_metadata.json not found. Run the notebook (Kernel > Restart and Run All) first."
    exit 1
}

Write-Host 'All source artifacts found. Promoting...'
Write-Host ''

# Promote each artifact
foreach ($a in $Artifacts) {
    $src = Join-Path $TrainingDir $a.Src
    $dst = Join-Path $ModelDir    $a.Dst
    $bak = "$dst.bak"

    # Back up the existing canonical artifact if present
    if (Test-Path $dst) {
        Copy-Item -Path $dst -Destination $bak -Force
        Write-Host "  Backed up : $($a.Dst) -> $($a.Dst).bak"
    }

    # Promote candidate to canonical
    Copy-Item -Path $src -Destination $dst -Force
    Write-Host "  Promoted  : training/$($a.Src) -> backend/model/$($a.Dst)"
}

# Promote metadata
$MetaDst = Join-Path $ModelDir "model_metadata.json"
Copy-Item -Path $MetaSrc -Destination $MetaDst -Force
Write-Host "  Promoted  : training/model_metadata.json -> backend/model/model_metadata.json"

Write-Host ''
Write-Host '========================================'
Write-Host ' Promotion complete.'
Write-Host '========================================'
Write-Host ''

# Display the promoted metadata for confirmation
Write-Host 'Promoted model metadata:'
Get-Content $MetaDst | Write-Host
Write-Host ''
Write-Host 'Next steps:'
Write-Host '  1. Restart the API to load the new artifacts:'
Write-Host '       uvicorn backend.api.index:app --reload --port 8000'
Write-Host '  2. Or rebuild and rerun the Docker container:'
Write-Host '       docker build -t fraud-detection-api .'
Write-Host '       docker run -p 8000:8000 fraud-detection-api'
Write-Host '  3. Send a smoke-test request to verify the API is healthy.'
Write-Host ''
