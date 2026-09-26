"""
shared/features.py
------------------
Single source of truth for feature engineering used by both:
  - training/Fraud_detection.ipynb  (is_training=True)
  - backend/api/index.py            (is_training=False)

Function
--------
engineer_features(df, threshold, is_training=False) -> pd.DataFrame

Parameters
----------
df : pd.DataFrame
    Raw transaction data.  Must contain the columns used as inputs
    (see REQUIRED_COLS below).  In training mode the DataFrame already
    contains isFlaggedFraud; in serving mode it is not present in the
    API request and is injected as 0.

threshold : float
    The training-time median of the ``amount`` column, loaded from
    ``backend/model/threshold.pkl``.  Used to compute large_transaction
    consistently between training and serving.

is_training : bool, default False
    True  -> called from the training notebook; isFlaggedFraud is
             already present in df and must not be overwritten.
    False -> called from the API; isFlaggedFraud is absent from the
             request payload and is added as 0 before encoding.

Returns
-------
pd.DataFrame
    Engineered feature DataFrame ready for StandardScaler and model
    inference.  Column order matches features.pkl exactly:

    ['step', 'amount', 'oldbalanceOrg', 'newbalanceOrig',
     'oldbalanceDest', 'newbalanceDest', 'isFlaggedFraud',
     'origin_balance_change', 'destination_balance_change',
     'large_transaction', 'origin_balance_empty',
     'destination_balance_empty',
     'type_CASH_OUT', 'type_DEBIT', 'type_PAYMENT', 'type_TRANSFER']
"""

import pandas as pd

# All five known transaction types in the dataset.
# CASH_IN is the dropped baseline (drop_first=True on alphabetical order).
# The remaining four become explicit one-hot columns.
_ALL_TYPES = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]
_TYPE_DUMMIES = ["type_CASH_OUT", "type_DEBIT", "type_PAYMENT", "type_TRANSFER"]


def engineer_features(df: pd.DataFrame, threshold: float, is_training: bool = False) -> pd.DataFrame:
    """
    Apply all feature transformations used by the Fraud Detection model.

    Preserves existing columns already in df; adds engineered ones in-place
    on a copy so the caller's DataFrame is never mutated.
    """
    df = df.copy()

    # ------------------------------------------------------------------
    # 1. Balance change features
    # ------------------------------------------------------------------
    df["origin_balance_change"] = (
        df["oldbalanceOrg"] - df["newbalanceOrig"]
    )

    df["destination_balance_change"] = (
        df["newbalanceDest"] - df["oldbalanceDest"]
    )

    # ------------------------------------------------------------------
    # 2. Transaction flag features
    # ------------------------------------------------------------------
    # large_transaction: above the training-time median amount threshold.
    # threshold is loaded from backend/model/threshold.pkl (= 20756.62).
    df["large_transaction"] = (
        df["amount"] > threshold
    ).astype(int)

    df["origin_balance_empty"] = (
        df["newbalanceOrig"] == 0
    ).astype(int)

    df["destination_balance_empty"] = (
        df["newbalanceDest"] == 0
    ).astype(int)

    # ------------------------------------------------------------------
    # 3. isFlaggedFraud — training vs serving handling
    # ------------------------------------------------------------------
    # In training mode the column already exists in the DataFrame
    # (it is part of the raw CSV and was not dropped before this call).
    # In serving mode the API request schema does not include it, so we
    # inject it as 0 to preserve the exact 16-column feature set the
    # model was trained on.
    if not is_training:
        df["isFlaggedFraud"] = 0

    # ------------------------------------------------------------------
    # 4. One-hot encode transaction type
    # ------------------------------------------------------------------
    # pd.get_dummies with drop_first=True only drops the first category
    # it *sees* in the data — on a single-row serving request that may
    # not be CASH_IN, corrupting the encoding.  Instead we build the
    # four dummy columns explicitly so CASH_IN is always the baseline
    # regardless of what value is present in the row.
    type_col = df["type"]
    for dummy in _TYPE_DUMMIES:
        category = dummy[len("type_"):]          # e.g. "type_CASH_OUT" -> "CASH_OUT"
        df[dummy] = (type_col == category).astype(int)
    df = df.drop(columns=["type"])

    # ------------------------------------------------------------------
    # 5. Return columns in the canonical training order so that the
    #    result is consistent with features.pkl regardless of how
    #    pandas orders new columns internally.
    # ------------------------------------------------------------------
    canonical_order = [
        "step",
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "isFlaggedFraud",
        "origin_balance_change",
        "destination_balance_change",
        "large_transaction",
        "origin_balance_empty",
        "destination_balance_empty",
        "type_CASH_OUT",
        "type_DEBIT",
        "type_PAYMENT",
        "type_TRANSFER",
    ]

    return df[canonical_order]
