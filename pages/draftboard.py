import dash
from dash import dcc, html, Input, Output, State, callback
from dash_ag_grid import AgGrid
import pandas as pd
from utility import helpers
from utility.scoring import load_config
from pathlib import Path
from datetime import datetime
import time


dash.register_page(__name__, path='/draftboard')

settings = load_config(Path("assets/settings.json"))
TEAM_NAMES = settings.get('league', {}).get('team_names', [])

board_df = helpers.get_board()
board_df = helpers.clean_board(board_df)


# Layout for the draft board page
def layout():
    component = html.Div([
        html.H1("Draft Board"),

        dcc.Store(id='draftboard-saved', data=board_df.to_dict('records')),
        dcc.Store(id='last-save-timestamp', data=0),

        dcc.Input(id='draftboard-search', type='text', placeholder='Search...'),
        dcc.Dropdown(
            id='draftboard-name-dropdown',
            options=[{'label': name, 'value': name} for name in board_df['Name'].unique()],
            multi=True,
            placeholder="Select Name",
        ),
        dcc.Dropdown(
            id='draftboard-pos-dropdown',
            options=[{'label': pos, 'value': pos} for pos in board_df['Position'].unique()],
            multi=True,
            placeholder="Select Position",
        ),
        dcc.Dropdown(
            id='draftboard-team-dropdown',
            options=[{'label': team, 'value': team} for team in board_df['Team'].unique()],
            multi=True,
            placeholder="Select Team",
        ),

        AgGrid(
            id='draftboard-grid',
            columnDefs=[
                {'field': 'Name', 'filter': True, 'sortable': True},
                {'field': 'Position', 'filter': True, 'sortable': True},
                {'field': 'Team', 'filter': True, 'sortable': True},
                {
                    'field': 'Owner',
                    'editable': True,
                    'cellEditor': 'agSelectCellEditor',
                    'cellEditorParams': {'values': TEAM_NAMES},
                    'filter': True,
                    'sortable': True,
                },
                {
                    'field': 'Price',
                    'editable': True,
                    'filter': True,
                    'sortable': True,
                    'valueParser': 'Number(value)',
                    'valueFormatter': {'function': 'Number(params.value).toFixed(2)'},
                },
            ],
            rowData=board_df.to_dict('records'),
            dashGridOptions={
                'rowClassRules': {
                    'drafted': "data.Owner && data.Owner !== '' && data.Owner !== 'nan' && data.Owner !== 'None'",
                },
            },
            columnSize="autoSize",
        ),
        html.Button("Save", id='save-draftboard', n_clicks=0, disabled=True),
        html.Div(id='draftboard-status', style={'margin-top': '20px'}),
    ])
    return component


# Update quick filter and column filters
@callback(
    Output('draftboard-grid', 'dashGridOptions'),
    Input('draftboard-search', 'value'),
    State('draftboard-grid', 'dashGridOptions'),
    prevent_initial_call=True,
)
def update_quick_filter(search_text, grid_options):
    options = grid_options or {}
    options['quickFilterText'] = search_text or ''
    return options


@callback(
    Output('draftboard-grid', 'filterModel'),
    Input('draftboard-name-dropdown', 'value'),
    Input('draftboard-pos-dropdown', 'value'),
    Input('draftboard-team-dropdown', 'value'),
)
def update_column_filters(names, positions, teams):
    model = {}
    if names:
        model['Name'] = {'filterType': 'set', 'values': names}
    if positions:
        model['Position'] = {'filterType': 'set', 'values': positions}
    if teams:
        model['Team'] = {'filterType': 'set', 'values': teams}
    return model


# Enable the save button only when changes are made
@callback(
    Output('save-draftboard', 'disabled', allow_duplicate=True),
    Input('draftboard-grid', 'rowData'),
    State('draftboard-saved', 'data'),
    prevent_initial_call=True,
)
def toggle_save_button(current_rows, saved_rows):
    if current_rows is None:
        return True
    changed = not pd.DataFrame(current_rows).equals(pd.DataFrame(saved_rows))
    return not changed


# Callback for saving the draft board when the save button is clicked
@callback(
    Output('draftboard-status', 'children'),
    Output('draftboard-saved', 'data'),
    Output('save-draftboard', 'disabled', allow_duplicate=True),
    Output('last-save-timestamp', 'data'),
    Input('save-draftboard', 'n_clicks'),
    State('draftboard-grid', 'rowData'),
    State('draftboard-saved', 'data'),
    State('last-save-timestamp', 'data'),
    prevent_initial_call=True,
)
def save_draft_board(n_clicks, rows, saved_rows, last_save):
    if n_clicks is None:
        return dash.no_update, dash.no_update, dash.no_update, last_save
    if pd.DataFrame(rows).equals(pd.DataFrame(saved_rows)):
        return "No changes to save", saved_rows, True, last_save
    now = time.time()
    if now - last_save < 1:  # Debounce rapid successive saves
        return dash.no_update, saved_rows, False, last_save
    updated_board = pd.DataFrame(rows)
    helpers.save_board(updated_board)
    helpers.log_draft_picks(updated_board)
    timestamp = datetime.now().strftime('%H:%M:%S')
    return f"Draft board saved at {timestamp}", rows, True, now

