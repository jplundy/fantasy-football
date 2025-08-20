import sys
import pathlib
from copy import deepcopy

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from utility.scoring import save_config, load_config, SCORING_CONFIG_DEFAULT
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
