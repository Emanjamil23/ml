"""
scripts/validate_model.py
-------------------------
Validates the promoted model artifacts in backend/model/ against
the same deterministic test split used during training.

Pipeline reproduced from training/Fraud_detection.ipynb:
  - Cells 1-2  : load Fraud.csv, fill NaN, drop missing target rows
  - Cell 4-5   : engineer_features (shared module), extract X / y
  - Cell 6     : train_test_split(test_size=0.20, random_state=42, stratify=y)
  - Cell 7     : scaler.transform(X_test)  [fit was done on X_train during training]

The promoted scaler.pkl is loaded and used to transform X_test — it is
NOT re-fitted here, preserving the exact scaling parameters from training.

Exit codes
----------
  0  All four metric thresholds passed.
  1  One or more thresholds failed.
  2  A required artifact or data file was not found.
"""

import sys
import warnings
import pathlib

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Resolve project root so the script can be run from any working directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Imports (all already in requirements.txt — no new packages)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from shared.features import engineer_features

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MODEL_DIR   = PROJECT_ROOT / "backend" / "model"
DATASET_PATH = PROJECT_ROOT / "training" / "Fraud.csv"

REQUIRED_ARTIFACTS = {
    "model":     MODEL_DIR / "model.pkl",
    "scaler":    MODEL_DIR / "scaler.pkl",
    "features":  MODEL_DIR / "features.pkl",
    "threshold": MODEL_DIR / "threshold.pkl",
}

# ---------------------------------------------------------------------------
# Validation thresholds (from fraud-ml-ops-plan.md)
# ---------------------------------------------------------------------------
THRESHOLDS = {
    "accuracy":  0.995,
    "precision": 0.85,
    "recall":    0.40,
    "f1":        0.55,
}

# ---------------------------------------------------------------------------
# Step 1: Check all artifacts and dataset are present
# ---------------------------------------------------------------------------
missing = []
for name, path in REQUIRED_ARTIFACTS.items():
    if not path.exists():
        missing.append(str(path))
if not DATASET_PATH.exists():
    missing.append(str(DATASET_PATH))

if missing:
    print("ERROR: The following required files were not found:")
    for m in missing:
        print(f"  {m}")
    print()
    print("Run scripts/promote_model.ps1 first to promote trained artifacts.")
    sys.exit(2)

# ---------------------------------------------------------------------------
# Step 2: Load promoted artifacts
# ---------------------------------------------------------------------------
print()
print("Loading promoted artifacts from backend/model/ ...")
model     = joblib.load(REQUIRED_ARTIFACTS["model"])
scaler    = joblib.load(REQUIRED_ARTIFACTS["scaler"])
features  = joblib.load(REQUIRED_ARTIFACTS["features"])
threshold = joblib.load(REQUIRED_ARTIFACTS["threshold"])
print(f"  model     : {type(model).__name__}  (n_estimators={model.n_estimators})")
print(f"  scaler    : {type(scaler).__name__}")
print(f"  features  : {len(features)} columns")
print(f"  threshold : {threshold}")

# ---------------------------------------------------------------------------
# Step 3: Reproduce the training data pipeline (cells 1-2 of notebook)
# ---------------------------------------------------------------------------
print()
print("Loading and cleaning Fraud.csv ...")
data = pd.read_csv(DATASET_PATH)

# Cell 2: fill numeric NaN with column median, drop rows with missing target
numeric_columns = data.select_dtypes(include=np.number).columns
for col in numeric_columns:
    data[col] = data[col].fillna(data[col].median())
data = data.dropna(subset=["isFraud"])
print(f"  Rows after cleaning: {len(data):,}")

# ---------------------------------------------------------------------------
# Step 4: Feature engineering (cells 4-5 of notebook)
# Reuse the promoted threshold — this is the value the model was trained with.
# ---------------------------------------------------------------------------
print()
print("Applying feature engineering (shared module, is_training=True) ...")
X = engineer_features(data, threshold, is_training=True)
y = data["isFraud"]

# Align column order with features.pkl (safety net, should already match)
X = X.reindex(columns=features, fill_value=0)

# ---------------------------------------------------------------------------
# Step 5: Reproduce the exact train/test split (cell 6 of notebook)
# MAX_ROWS = 500000; dataset is 29,999 rows so full dataset is used directly.
# ---------------------------------------------------------------------------
MAX_ROWS = 500_000
if len(X) > MAX_ROWS:
    X_sample, _, y_sample, _ = train_test_split(
        X, y, train_size=MAX_ROWS, random_state=42, stratify=y
    )
else:
    X_sample, y_sample = X, y

_, X_test, _, y_test = train_test_split(
    X_sample, y_sample,
    test_size=0.20,
    random_state=42,
    stratify=y_sample
)
print(f"  Test set size: {len(X_test):,} rows  ({y_test.sum()} fraud, {(y_test == 0).sum()} legitimate)")

# ---------------------------------------------------------------------------
# Step 6: Scale using the promoted scaler (transform only — not re-fitted)
# ---------------------------------------------------------------------------
X_test_scaled = scaler.transform(X_test)

# ---------------------------------------------------------------------------
# Step 7: Evaluate the promoted model
# ---------------------------------------------------------------------------
y_pred = model.predict(X_test_scaled)

metrics = {
    "accuracy":  accuracy_score(y_test, y_pred),
    "precision": precision_score(y_test, y_pred, zero_division=0),
    "recall":    recall_score(y_test, y_pred, zero_division=0),
    "f1":        f1_score(y_test, y_pred, zero_division=0),
}

# ---------------------------------------------------------------------------
# Step 8: Report results
# ---------------------------------------------------------------------------
print()
print("========================================")
print(" Validation Results")
print("========================================")
print(f"  {'Metric':<12}  {'Actual':>10}  {'Required':>10}  {'Result'}")
print(f"  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*6}")

all_passed = True
for metric, required in THRESHOLDS.items():
    actual = metrics[metric]
    passed = actual >= required
    if not passed:
        all_passed = False
    status = "PASS" if passed else "FAIL"
    flag   = "  <-- BELOW THRESHOLD" if not passed else ""
    print(f"  {metric:<12}  {actual:>10.6f}  {required:>10.3f}  {status}{flag}")

print()
if all_passed:
    print("  OVERALL: PASSED -- model is safe to promote.")
    print("========================================")
    print()
    sys.exit(0)
else:
    print("  OVERALL: FAILED -- do not promote this model.")
    print("  Retrain the model and re-run validation before promoting.")
    print("========================================")
    print()
    sys.exit(1)
