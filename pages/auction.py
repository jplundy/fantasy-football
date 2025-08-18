import dash
from layout import create_layout
from models.auction import all_players_sorted, NUM_TEAMS


dash.register_page(__name__, path='/auction')

layout = create_layout(
    all_players_sorted['Name'].tolist(),
    NUM_TEAMS,
    all_players_sorted.to_dict('records'),
)
