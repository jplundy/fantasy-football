import os
import json
import numpy as np
import pandas as pd
from features import build_features


def load_model(position: str, models_dir: str = "models"):
    """Load a serialized model for ``position``."""
    path = os.path.join(models_dir, f"{position.lower()}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model for position {position} not found at {path}")
    with open(path, "r") as fh:
        return json.load(fh)


def predict_position(df: pd.DataFrame, position: str, models_dir: str = "models") -> pd.Series:
    """Generate fantasy point projections for ``df`` using a trained model."""
    model_data = load_model(position, models_dir)
    columns = model_data["columns"]
    feats = build_features(df)
    X = feats.select_dtypes(include=[float, int])
    X = X.reindex(columns=columns, fill_value=0)
    X_mat = np.hstack([np.ones((X.shape[0], 1)), X.values])
    coef = np.array(model_data["coef"])
    predictions = X_mat.dot(coef)
    return pd.Series(predictions, index=df.index)
