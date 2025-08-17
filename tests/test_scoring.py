import importlib
from unittest.mock import patch

import pandas as pd
import pytest


def _load_scoring():
    qb_df = pd.DataFrame({'Player': []})
    rb_df = pd.DataFrame({'Player': ['Test Player'], 'YBC/Att': [5], 'YAC/Att': [3]})
    wr_df = pd.DataFrame({'Player': ['Test Player'], 'ADOT': [12], 'YAC/R': [6]})

    with patch('pandas.read_csv', side_effect=[qb_df, rb_df, wr_df]):
        scoring = importlib.import_module('utility.scoring')
    return scoring, rb_df, wr_df


def test_calculate_rb_wr_points_sample():
    scoring, rb_df, wr_df = _load_scoring()

    row = pd.Series({
        'Name': 'Test Player',
        'RushYds': 120,
        'RushTD': 1,
        'Fum': 0,
        'RecYds': 110,
        'RecTD': 1,
        'Rec': 8,
    })

    result = scoring.calculate_rb_wr_points(row)

    rb_stats = rb_df.iloc[0]
    rb_stats['p() 20yd rus'] = (rb_stats['YBC/Att'] + rb_stats['YAC/Att']) / 20
    rb_stats['p() 40yd rus'] = rb_stats['p() 20yd rus'] / 2
    rb_stats['p() 60yd rus'] = rb_stats['p() 20yd rus'] / 3
    rb_stats['p() 80yd rus'] = rb_stats['p() 20yd rus'] / 4

    wr_stats = wr_df.iloc[0]
    wr_stats['p() 20yd rec'] = (wr_stats['ADOT'] + wr_stats['YAC/R']) / 20
    wr_stats['p() 40yd rec'] = wr_stats['p() 20yd rec'] / 2
    wr_stats['p() 60yd rec'] = wr_stats['p() 20yd rec'] / 3
    wr_stats['p() 80yd rec'] = wr_stats['p() 20yd rec'] / 4

    expected = (
        row['RushYds'] // 10
        + (3 if row['RushYds'] >= 100 else 0)
        + (3 if row['RushYds'] >= 200 else 0)
        + (3 if row['RushYds'] >= 300 else 0)
        + row['RushTD'] * 6
        + row['Fum'] * -3
        + row['RecYds'] // 10
        + (3 if row['RecYds'] >= 100 else 0)
        + (3 if row['RecYds'] >= 200 else 0)
        + (3 if row['RecYds'] >= 300 else 0)
        + row['Rec'] // 5
        + (1 if row['Rec'] >= 10 else 0)
        + (1 if row['Rec'] >= 15 else 0)
        + row['RecTD'] * 6
        + row['RushTD'] * rb_stats['p() 80yd rus'] * 3
        + row['RushTD'] * (rb_stats['p() 60yd rus'] - rb_stats['p() 80yd rus']) * 2
        + row['RushTD'] * (rb_stats['p() 40yd rus'] - rb_stats['p() 60yd rus'] - rb_stats['p() 80yd rus'])
        + row['Rec'] * wr_stats['p() 20yd rec'] * 1
        + row['Rec'] * wr_stats['p() 40yd rec'] * 2
        + row['RecTD'] * (wr_stats['p() 80yd rec']) * 3
        + row['RecTD'] * (wr_stats['p() 60yd rec'] - wr_stats['p() 80yd rec']) * 2
        + row['RecTD'] * (wr_stats['p() 40yd rec'] - wr_stats['p() 60yd rec'] - wr_stats['p() 80yd rec']) * 1
    )

    assert result == pytest.approx(expected)


def test_calculate_rb_wr_points_zero_line():
    scoring, _, _ = _load_scoring()

    row = pd.Series({
        'Name': 'Test Player',
        'RushYds': 0,
        'RushTD': 0,
        'Fum': 0,
        'RecYds': 0,
        'RecTD': 0,
        'Rec': 0,
    })

    assert scoring.calculate_rb_wr_points(row) == 0
