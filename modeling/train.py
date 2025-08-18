import os
import json
from typing import List
import numpy as np
import pandas as pd
from features import load_player_stats, build_features


def train_position_model(position: str, data_dir: str = "data", models_dir: str = "models") -> str:
    """Train and persist a model for a single position.

    Parameters
    ----------
    position : str
        Position code such as ``QB`` or ``WR``.
    data_dir : str, optional
        Directory containing historical CSV files.
    models_dir : str, optional
        Directory to store the trained model.
    """
    df = load_player_stats(data_dir, position)
    if df.empty:
        raise ValueError(f"No data found for position {position}")
    df = build_features(df)
    if "Points" not in df.columns:
        raise ValueError("Required target column 'Points' not present")
    y = df["Points"].values
    X = df.select_dtypes(include=[float, int]).drop(columns=["Points"], errors="ignore")
    # Add intercept term
    X_mat = np.hstack([np.ones((X.shape[0], 1)), X.values])
    coef, *_ = np.linalg.lstsq(X_mat, y, rcond=None)
    model_data = {"coef": coef.tolist(), "columns": X.columns.tolist()}
    os.makedirs(models_dir, exist_ok=True)
    path = os.path.join(models_dir, f"{position.lower()}.json")
    with open(path, "w") as fh:
        json.dump(model_data, fh)
    return path


def train_all_positions(positions: List[str] = None, data_dir: str = "data", models_dir: str = "models"):
    """Train models for a list of positions."""
    positions = positions or ["QB", "RB", "WR", "TE"]
    paths = {}
    for pos in positions:
        try:
            paths[pos] = train_position_model(pos, data_dir, models_dir)
        except Exception as exc:
            print(f"Could not train {pos}: {exc}")
    return paths


if __name__ == "__main__":
    train_all_positions()
