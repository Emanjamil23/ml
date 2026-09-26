from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import joblib
from pathlib import Path

from shared.features import engineer_features

app = FastAPI(title="Fraud Detection API")

# Enable CORS so web frontends can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve path to model directory (backend/model/)
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "model"

# Load trained model artifacts directly from backend/model/
model = joblib.load(MODEL_DIR / "model.pkl")
scaler = joblib.load(MODEL_DIR / "scaler.pkl")
features = joblib.load(MODEL_DIR / "features.pkl")
threshold = joblib.load(MODEL_DIR / "threshold.pkl")


class Transaction(BaseModel):
    step: int
    type: str
    amount: float
    oldbalanceOrg: float
    newbalanceOrig: float
    oldbalanceDest: float
    newbalanceDest: float


@app.get("/")
def home():
    return {
        "message": "Fraud Detection API is running!",
        "status": "success"
    }


@app.post("/predict")
def predict(transaction: Transaction):

    data = pd.DataFrame([{
        "step": transaction.step,
        "type": transaction.type,
        "amount": transaction.amount,
        "oldbalanceOrg": transaction.oldbalanceOrg,
        "newbalanceOrig": transaction.newbalanceOrig,
        "oldbalanceDest": transaction.oldbalanceDest,
        "newbalanceDest": transaction.newbalanceDest
    }])

    # Apply shared feature engineering (is_training=False: injects isFlaggedFraud=0)
    data = engineer_features(data, threshold, is_training=False)

    # Safety net: align column order with trained features.pkl
    data = data.reindex(columns=features, fill_value=0)

    # Scale
    data_scaled = scaler.transform(data)

    # Prediction
    prediction = model.predict(data_scaled)[0]

    if prediction == 1:
        result = "Fraudulent Transaction"
    else:
        result = "Legitimate Transaction"

    return {
        "prediction": int(prediction),
        "result": result
    }
