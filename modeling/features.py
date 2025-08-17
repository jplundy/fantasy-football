import os
import glob
import numpy as np
import pandas as pd


def load_player_stats(data_dir: str, position: str) -> pd.DataFrame:
    """Load historical stats for a position from CSV files.

    Searches ``data_dir`` recursively for files matching ``{position}.csv`` and
    concatenates them into a single ``DataFrame``. Non-numeric columns are left
    untouched while others are coerced to numeric types.
    """
    pattern = os.path.join(data_dir, "**", f"{position.upper()}.csv")
    files = glob.glob(pattern, recursive=True)
    data_frames = []
    for file in files:
        try:
            df = pd.read_csv(file)
            data_frames.append(df)
        except Exception:
            # Ignore files that fail to parse
            continue
    if not data_frames:
        return pd.DataFrame()
    df = pd.concat(data_frames, ignore_index=True)
    return _coerce_numeric(df)


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Convert all non-key columns to numeric when possible."""
    df = df.copy()
    for col in df.columns:
        if col in {"Name", "Player", "Team", "Opp", "_position", "_team"}:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _rolling_features(group: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = group.select_dtypes(include=[np.number]).columns.tolist()
    for col in ["Week", "Points"]:
        if col in numeric_cols:
            numeric_cols.remove(col)
    group = group.sort_values("Week")
    rolling = group[numeric_cols].rolling(window=3, min_periods=1).mean()
    rolling.columns = [f"{c}_roll3" for c in rolling.columns]
    return pd.concat([group, rolling], axis=1)


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add target share, air yards efficiency and rolling averages."""
    df = df.copy()
    if "Team" in df.columns and "Targets" in df.columns:
        team_targets = df.groupby(["Team", "Week"]) ["Targets"].transform("sum")
        df["TargetShare"] = df["Targets"] / team_targets
    if "AirYds" in df.columns and "Targets" in df.columns:
        df["AirYdsPerTarget"] = df["AirYds"] / df["Targets"].replace({0: np.nan})
        df["AirYdsPerTarget"].fillna(0, inplace=True)
    df = df.groupby("Name", group_keys=False).apply(_rolling_features)
    df.fillna(0, inplace=True)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Public API: ensure numeric types and derived features."""
    if df.empty:
        return df
    df = _coerce_numeric(df)
    df = add_derived_features(df)
    return df
=======
import pandas as pd
from typing import Optional

from utility import helpers


def build_player_features(pos: Optional[str] = None) -> pd.DataFrame:
    """Return player level features with schedule adjusted metrics.

    Parameters
    ----------
    pos: str | None
        Optional position filter (e.g. ``'QB'``).
    """

    # Load and clean offensive projections
    off_df = helpers.get_offense_data()
    off_df = helpers.clean_offense_data(off_df, pos=pos)

    # Load schedule and defensive metrics
    sched_df = helpers.get_schedule()
    def_df = helpers.get_defense_metrics()
    sched_df = helpers.clean_schedule(sched_df, def_df)

    # Merge player data with schedule metrics
    features = off_df.merge(
        sched_df[['TEAM', 'Week', 'Opp_DVOA', 'Opp_FantasyPointsAllowed']],
        left_on=['Team', 'Week'],
        right_on=['TEAM', 'Week'],
        how='left',
    )
    features.drop(columns=['TEAM'], inplace=True)

    # Replace missing metrics with neutral values
    for col in ['Opp_DVOA', 'Opp_FantasyPointsAllowed']:
        features[col] = features[col].fillna(0)

    # Compute adjusted fantasy points using opponent strength
    def _adjust(row: pd.Series) -> float:
        multiplier = 1 - row.get('Opp_DVOA', 0) / 100
        multiplier += row.get('Opp_FantasyPointsAllowed', 0) / 1000
        return row['ModelPoints'] * multiplier

    features['AdjustedPoints'] = features.apply(_adjust, axis=1)
    return features