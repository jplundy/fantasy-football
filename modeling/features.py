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
