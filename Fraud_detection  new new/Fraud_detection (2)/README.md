# Financial Fraud Detection System

A machine learning project that detects potentially fraudulent financial transactions in real time using a tuned **Random Forest** classification model, served via a **FastAPI** serverless API on Vercel and presented with a clean, lightweight HTML/CSS/JavaScript frontend.

---

## 📁 Project Structure

```text
Fraud-Detection-System/
│
├── frontend/
│   ├── index.html          # Form UI to enter transaction details
│   ├── style.css           # Clean, minimalist styling (centered card layout)
│   └── script.js           # Handles form submission, fetch() request, and UI updates
│
├── backend/
│   ├── api/
│   │   └── index.py        # FastAPI application with /predict endpoint
│   ├── model/
│   │   ├── model.pkl       # Trained Random Forest classifier
│   │   ├── scaler.pkl      # StandardScaler instance for feature normalization
│   │   └── features.pkl    # List of engineered feature names in exact order
│   └── requirements.txt    # Python dependencies for the backend
│
├── training/
│   ├── Fraud_detection.ipynb  # Data exploration, feature engineering, and model training
│   └── Fraud.csv              # Financial transaction dataset (PaySim synthetic data)
│
├── Dockerfile              # Docker containerization configuration
├── .gitignore              # Ignored files (virtualenvs, cache, credentials)
└── README.md               # Project documentation
```

---

## 🚀 Live API Endpoint

- **Endpoint URL**: `https://fraud-detection-api-jade.vercel.app/predict`
- **Method**: `POST`
- **Header**: `Content-Type: application/json`

### Sample Request Payload:
```json
{
  "step": 1,
  "type": "PAYMENT",
  "amount": 9839.64,
  "oldbalanceOrg": 170136.0,
  "newbalanceOrig": 160296.36,
  "oldbalanceDest": 0.0,
  "newbalanceDest": 0.0
}
```

### Sample Response:
```json
{
  "prediction": 0,
  "result": "Legitimate Transaction"
}
```
*(If fraudulent, `prediction` is `1` and `result` is `"Fraudulent Transaction"`)*

---

## 🌐 Deploying to Vercel

The project includes `vercel.json` for instant, zero-configuration deployment on Vercel:

### Option 1 — Zero-Config Git Deployment (Recommended)
1. Push this repository to your GitHub account.
2. In **[Vercel](https://vercel.com/)**, click **Add New...** > **Project** and import your repository.
3. Keep default settings (Root Directory as `./`) — the included `vercel.json` automatically routes `/` to `frontend/index.html` and serves all assets.
4. Click **Deploy**. Your app will be live and functional immediately!

### Option 2 — Set Root Directory to `frontend`
1. Go to your project in Vercel > **Settings** > **General**.
2. Under **Root Directory**, click **Edit**, type `frontend`, and click **Save**.
3. Go to **Deployments** > click `...` on the latest deployment > **Redeploy**.

> **Backend Note**: The frontend is pre-connected to the live production backend API (`https://fraud-detection-api-jade.vercel.app/predict`), which has open CORS enabled. You do not need to deploy a separate backend.

---


### 1. Run the Backend (FastAPI)

Make sure you have Python installed, then install dependencies and start the Uvicorn dev server:

```powershell
pip install -r backend/requirements.txt
uvicorn backend.api.index:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000`. You can test it via interactive Swagger docs at `http://127.0.0.1:8000/docs`.

### 2. Run the Frontend

Open `frontend/index.html` directly in any web browser, or launch a simple local server:

```powershell
cd frontend
python -m http.server 3000
```

Then visit `http://localhost:3000` in your browser.

---

## 🐳 Running with Docker

```bash
# Build the Docker image
docker build -t fraud-detection-api .

# Run the container
docker run -p 8000:8000 fraud-detection-api
```

---

## 📊 Model Information

- **Algorithm**: `RandomForestClassifier(n_estimators=50, class_weight="balanced", random_state=42)`
- **Key Engineered Features**: `origin_balance_change`, `destination_balance_change`, `large_transaction`, `origin_balance_empty`, `destination_balance_empty`, one-hot encoded transaction types.
- **Dataset**: PaySim synthetic financial mobile transactions.

---

## 🤖 Model Retraining and Promotion (IBM Bob Workflow)

The training-to-serving lifecycle is managed through IBM Bob. A developer does
not manually copy model files — they run the workflow below, which uses Bob's
**Fraud ML Ops** custom mode and the **promote-model** skill to enforce a
mandatory validation gate before any artifacts reach the serving layer.

### Updated Project Structure

```text
├── shared/
│   ├── __init__.py             # Package marker
│   └── features.py             # Single source of truth for feature engineering
│
├── scripts/
│   ├── validate_model.py       # Validation gate — evaluates promoted artifacts
│   ├── promote_model.ps1       # Promotes training/_1.pkl artifacts to backend/model/
│   └── rollback_model.ps1      # Restores previous .bak artifacts (one generation)
│
├── training/
│   ├── model_1.pkl             # Candidate model (notebook output, not committed)
│   ├── scaler_1.pkl            # Candidate scaler (not committed)
│   ├── features_1.pkl          # Candidate feature list (not committed)
│   ├── threshold_1.pkl         # Candidate large_transaction threshold (not committed)
│   └── model_metadata.json     # Training metrics and artifact metadata (not committed)
│
├── backend/model/
│   ├── model.pkl               # Live promoted model
│   ├── scaler.pkl              # Live promoted scaler
│   ├── features.pkl            # Live promoted feature list
│   ├── threshold.pkl           # Live promoted threshold
│   └── model_metadata.json     # Metadata for the currently promoted model
│
└── .bob/
    ├── custom_modes.yaml       # Fraud ML Ops mode definition
    └── skills/promote-model/
        └── SKILL.md            # 6-step promotion skill
```

### Validation Thresholds

The validation gate (`scripts/validate_model.py`) evaluates the promoted model
against the same deterministic test split used during training
(`test_size=0.20, random_state=42`). Promotion is blocked if any threshold fails.

| Metric    | Required | Last Validated |
|-----------|----------|---------------|
| Accuracy  | >= 0.995 | 0.9985        |
| Precision | >= 0.850 | 1.0000        |
| Recall    | >= 0.400 | 0.4706        |
| F1 Score  | >= 0.550 | 0.6400        |

### Normal Workflow: Retrain → Validate → Promote → Verify

**1. Retrain** — open `training/Fraud_detection.ipynb`, run
**Kernel > Restart & Run All**. Candidate artifacts are saved to `training/`.

**2. Validate** — run the validation gate directly, or let Bob run it:

```powershell
python scripts/validate_model.py
```

Exit code `0` = pass. Exit code `1` = one or more thresholds failed; do not promote.

**3. Promote** — run the promotion script, or let Bob run it:

```powershell
.\scripts\promote_model.ps1
```

This backs up the current `backend/model/*.pkl` as `*.pkl.bak`, then copies
the `training/*_1.pkl` candidates to their canonical names in `backend/model/`.

**4. Restart the API** to load the new artifacts:

```powershell
uvicorn backend.api.index:app --reload --port 8000
```

**5. Rollback** (if needed) — restores all `.bak` files in one command:

```powershell
.\scripts\rollback_model.ps1
```

One generation of backup is kept. Restart the API after rollback.

### IBM Bob Integration

Open Bob and switch to the **Fraud ML Ops** mode, then type `promote model`
(or `/promote-model`). Bob activates the **promote-model** skill and walks
through all six steps:

1. Pre-flight: confirm notebook was run
2. Validation gate: runs `validate_model.py` — **hard stop on failure, no bypass**
3. Promote: runs `promote_model.ps1` with developer confirmation
4. Verify: checks artifact files and re-runs validation on promoted artifacts
5. Restart: provides the correct API restart command
6. Summary: displays promotion record from `model_metadata.json` and rollback instructions

> **Mandatory rule:** the validation gate must exit `0` before Bob will run the
> promotion script. This rule cannot be bypassed in the Fraud ML Ops mode.
