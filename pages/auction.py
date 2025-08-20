import dash
from pathlib import Path
from layout import create_layout
from models.auction import all_players_sorted
from utility.scoring import load_config


dash.register_page(__name__, path='/auction')

settings = load_config(Path("assets/settings.json"))
team_names = settings.get('league', {}).get(
    'team_names',
    [
        f'Team {i}'
        for i in range(1, settings.get('league', {}).get('num_teams', 12) + 1)
    ],
)

layout = create_layout(
    all_players_sorted['Name'].tolist(),
    team_names,
    all_players_sorted.to_dict('records'),
)
