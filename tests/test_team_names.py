import sys
import pathlib
from copy import deepcopy
import importlib

import pandas as pd
from dash_ag_grid import AgGrid

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from utility.scoring import save_config, load_config, SCORING_CONFIG_DEFAULT
import utility.scoring as scoring
from utility import helpers
import app


def test_team_names_persist(tmp_path):
    cfg = deepcopy(SCORING_CONFIG_DEFAULT)
    cfg['league']['team_names'] = ['Alpha', 'Beta']
    path = tmp_path / 'settings.json'
    save_config(path, cfg)
    loaded = load_config(path)
    assert loaded['league']['team_names'] == ['Alpha', 'Beta']


def test_team_names_in_summary(monkeypatch):
    monkeypatch.setattr(app, 'TEAM_NAMES', ['Alpha', 'Beta'])
    monkeypatch.setattr(app, 'NUM_TEAMS', 2)
    monkeypatch.setattr(app, 'INITIAL_BUDGET', 200)

    data = [
        {
            'Name': 'Player1',
            'Position': 'QB',
            'AuctionValue': 10,
            'Drafted': True,
            'DraftedBy': 'Alpha',
            'PricePaid': 50,
        }
    ]

    outputs = app.update_summaries(data)
    chart_start = 3 + 2 * len(app.TEAM_NAMES)
    team_chart = outputs[chart_start]
    assert team_chart.layout.title.text == 'Alpha Composition'


def test_draftboard_owner_dropdown_uses_config_names(monkeypatch):
    mock_settings = {'league': {'team_names': ['Alpha', 'Beta']}}
    monkeypatch.setattr(scoring, 'load_config', lambda path: mock_settings)

    board = pd.DataFrame({
        'Name': ['Player1'],
        'Position': ['QB'],
        'Team': ['NE'],
        'Owner': [''],
        'Price': [0],
    })

    monkeypatch.setattr(helpers, 'get_board', lambda: board)
    monkeypatch.setattr(helpers, 'clean_board', lambda df: df)

    draftboard = importlib.reload(importlib.import_module('pages.draftboard'))
    component = draftboard.layout()
    grid = next(child for child in component.children if isinstance(child, AgGrid))
    owner_column = next(col for col in grid.columnDefs if col.get('field') == 'Owner')
    assert owner_column['cellEditorParams']['values'] == ['Alpha', 'Beta']


def test_saved_board_maps_players_to_correct_teams(tmp_path, monkeypatch):
    fake_module_path = tmp_path / 'utility' / 'helpers.py'
    fake_module_path.parent.mkdir(parents=True)
    fake_module_path.write_text('')
    monkeypatch.setattr(helpers, '__file__', str(fake_module_path))
    (tmp_path / 'data').mkdir()

    df = pd.DataFrame({
        'Name': ['Player1'],
        'Position': ['QB'],
        'Team': ['NE'],
        'Owner': ['Alpha'],
        'Price': [10],
    })

    df.to_csv(tmp_path / 'data' / 'board.csv', index=False)
    loaded = helpers.get_board()
    cleaned = helpers.clean_board(loaded)
    assert cleaned.loc[0, 'Owner'] == 'Alpha'
