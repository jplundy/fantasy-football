import pytest
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from models.auction import compute_values
from utility import scoring


def _base_config(num_teams=12, budget=200):
    return {
        'league': {'num_teams': num_teams, 'initial_budget': budget},
        'QB': scoring.QB_SCORING_DEFAULT,
        'RB': scoring.RB_WR_SCORING_DEFAULT,
        'WR': scoring.RB_WR_SCORING_DEFAULT,
        'TE': scoring.TE_SCORING_DEFAULT,
    }


def test_values_scale_with_num_teams():
    cfg_default = _base_config(num_teams=12, budget=200)
    cfg_half = _base_config(num_teams=6, budget=200)

    df_default = compute_values(cfg_default)
    df_half = compute_values(cfg_half)

    player = df_default.iloc[0]['Name']
    val_default = df_default[df_default['Name'] == player]['AuctionValue'].iloc[0]
    val_half = df_half[df_half['Name'] == player]['AuctionValue'].iloc[0]

    assert val_half == pytest.approx(val_default * 0.5, rel=1e-6)


def test_values_scale_with_budget():
    cfg_default = _base_config(num_teams=12, budget=200)
    cfg_low_budget = _base_config(num_teams=12, budget=100)

    df_default = compute_values(cfg_default)
    df_low = compute_values(cfg_low_budget)

    player = df_default.iloc[0]['Name']
    val_default = df_default[df_default['Name'] == player]['AuctionValue'].iloc[0]
    val_low = df_low[df_low['Name'] == player]['AuctionValue'].iloc[0]

    expected_ratio = (12 * 100 - 12 * 17) / (12 * 200 - 12 * 17)
    assert val_low == pytest.approx(val_default * expected_ratio, rel=1e-6)
