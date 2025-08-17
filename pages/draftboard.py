import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from utility import helpers
from datetime import datetime
import time


dash.register_page(__name__, path='/draftboard')

board_df = helpers.get_board()
board_df = helpers.clean_board(board_df)


# Layout for the draft board page
def layout():
    component = html.Div([
        html.H1("Draft Board"),

        dcc.Store(id='draftboard-saved', data=board_df.to_dict('records')),
        dcc.Store(id='last-save-timestamp', data=0),

        dash_table.DataTable(
            id='draftboard-table',
            columns=[
                {'name': col, 'id': col, 'editable': True, 'presentation': 'dropdown'} if col == 'Owner'
                else {'name': col, 'id': col, 'editable': True} if col == 'Price'
                else {'name': col, 'id': col}
                for col in board_df.columns
            ],
            data=board_df.to_dict('records'),
            style_data_conditional=[
                {
                    'if': {
                        'filter_query': '{Owner} != "" && {Owner} != "nan" && {Owner} != "None"',
                    },
                    'backgroundColor': 'lightgrey',
                    'color': 'grey'
                }
            ],
            editable=True,
            row_deletable=False,
            dropdown={
                'Owner': {
                    'options': [
                        {'label': 'Bob', 'value': 'Bob'},
                        {'label': 'Josh', 'value': 'Josh'},
                        {'label': 'Joe', 'value': 'Joe'}
                    ]
                }
            }
        ),
        html.Button("Save", id='save-draftboard', n_clicks=0, disabled=True),
        html.Div(id='draftboard-status', style={'margin-top': '20px'})
    ])
    return component


# Enable the save button only when changes are made
@callback(
    Output('save-draftboard', 'disabled'),
    Input('draftboard-table', 'data_timestamp'),
    State('draftboard-table', 'data'),
    State('draftboard-saved', 'data'),
    prevent_initial_call=True
)
def toggle_save_button(timestamp, current_rows, saved_rows):
    if timestamp is None:
        return True
    changed = not pd.DataFrame(current_rows).equals(pd.DataFrame(saved_rows))
    return not changed


# Callback for saving the draft board when the save button is clicked
@callback(
    Output('draftboard-status', 'children'),
    Output('draftboard-saved', 'data'),
    Output('save-draftboard', 'disabled'),
    Output('last-save-timestamp', 'data'),
    Input('save-draftboard', 'n_clicks'),
    State('draftboard-table', 'data'),
    State('draftboard-saved', 'data'),
    State('last-save-timestamp', 'data'),
    prevent_initial_call=True
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

