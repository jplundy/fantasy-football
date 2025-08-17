import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from utility import helpers


dash.register_page(__name__, 
                   path='/draftboard')

board_df = helpers.get_board()
board_df = helpers.clean_board(board_df)



# Layout for the draft board page
def layout():
    component = html.Div([
        html.H1("Draft Board"),
        
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
        dcc.Interval(
            id='draftboard-interval',
            interval=3*1000,  # 3 seconds
            n_intervals=0
        ),

        html.Div(id='draftboard-status', style={'margin-top': '20px'})
    ])
    return component

# Callback for updating the draft board every interval
@callback(
    Output('draftboard-status', 'children'),
    Input('draftboard-interval', 'n_intervals'),
    State('draftboard-table', 'data')
)
def save_draft_board(n, rows):
    if n > 0:  # Avoid saving on the initial load
        updated_board = pd.DataFrame(rows)
        helpers.save_board(updated_board)
        return f"Draft board saved at interval {n}"
    return ""

# Callback for updating the draft board
@callback(
    Output('draftboard-table', 'data'),
    Input('draftboard-table', 'data_timestamp'),
    State('draftboard-table', 'data')
)
def update_draft_board(timestamp, rows):
    if timestamp is not None:
        # Update the board data and save it to CSV
        updated_board = pd.DataFrame(rows)
        helpers.save_board(updated_board)
        return updated_board.to_dict('records')
    return dash.no_update
