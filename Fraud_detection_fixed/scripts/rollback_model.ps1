# =============================================================
# rollback_model.ps1
# ------------------
# Restores the previous canonical artifacts in backend/model/
# from their .bak copies created by promote_model.ps1.
#
# This undoes the most recent promotion. Only one generation of
# backup is kept; running rollback twice will produce an error
# on the second run (no .bak files remain).
#
# Usage (from project root):
#   .\scripts\rollback_model.ps1
# =============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ModelDir = Join-Path $PSScriptRoot "..\backend\model"

$Artifacts = @(
    @{ Dst = "model.pkl"     },
    @{ Dst = "scaler.pkl"    },
    @{ Dst = "features.pkl"  },
    @{ Dst = "threshold.pkl" }
)

Write-Host ''
Write-Host '========================================'
Write-Host ' Fraud Detection - Model Rollback'
Write-Host '========================================'
Write-Host ''

# Validate all .bak files exist before touching anything
$missingBaks = @()
foreach ($a in $Artifacts) {
    $bak = Join-Path $ModelDir "$($a.Dst).bak"
    if (-not (Test-Path $bak)) {
        $missingBaks += $bak
    }
}

if ($missingBaks.Count -gt 0) {
    Write-Host 'ERROR: The following backup files were not found:'
    foreach ($b in $missingBaks) { Write-Host "  $b" }
    Write-Host ''
    Write-Host 'No rollback was performed. Either no promotion has been run yet,'
    Write-Host 'or a rollback has already been applied.'
    exit 1
}

Write-Host 'All backup artifacts found. Rolling back...'
Write-Host ''

foreach ($a in $Artifacts) {
    $dst = Join-Path $ModelDir $a.Dst
    $bak = Join-Path $ModelDir "$($a.Dst).bak"

    # Restore .bak to canonical name
    Move-Item -Path $bak -Destination $dst -Force
    Write-Host "  Restored  : $($a.Dst).bak -> $($a.Dst)"
}

Write-Host ''
Write-Host '========================================'
Write-Host ' Rollback complete.'
Write-Host '========================================'
Write-Host ''
Write-Host 'Next steps:'
Write-Host '  1. Restart the API to load the restored artifacts:'
Write-Host '       uvicorn backend.api.index:app --reload --port 8000'
Write-Host '  2. Or rebuild and rerun the Docker container:'
Write-Host '       docker build -t fraud-detection-api .'
Write-Host '       docker run -p 8000:8000 fraud-detection-api'
Write-Host ''
