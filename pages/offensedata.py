import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import dash_table
import pandas as pd
from utility import helpers

dash.register_page(__name__, 
                   path='/offensedata')

df = helpers.get_offense_data()
df = helpers.clean_offense_data(df)

# Layout
def layout():
    component = dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.H1("Player Statistics"),
                        width=3,
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id='offdata-name-dropdown',
                            options=[{'label': name, 'value': name} for name in df['Name'].unique()],
                            multi=True,
                            placeholder="Select Player",
                        ),
                        width=3
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id='offdata-pos-dropdown',
                            options=[{'label': name, 'value': name} for name in df['Position'].unique()],
                            multi=True,
                            placeholder="Select Position",
                        ),
                        width=3
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id='offdata-team-dropdown',
                            options=[{'label': team, 'value': team} for team in df['Team'].unique()],
                            multi=True,
                            placeholder="Select Team",
                        ),
                        width=3
                    ),
                ],
                style={'width':'100%', 'height':'100%', 'margin':'0px', 'padding':'0px'}
            ),
            dbc.Row(
                dash_table.DataTable(
                    id='offdata-table',
                    columns=[{'name': col, 'id': col} for col in df.columns],
                    data=df.to_dict('records'),
                    sort_action='native',
                    page_size=20
                )
            )
        ],
        fluid=True,
        style={'width':'100%', 'height':'100%', 'margin':'0px', 'padding':'0px'}
    )
    return component

# Callback to update the table based on filters
@callback(
    Output('offdata-table', 'data'),
    [Input('offdata-name-dropdown', 'value'),
     Input('offdata-pos-dropdown', 'value'),
     Input('offdata-team-dropdown', 'value')]
)
def update_table(selected_names, selected_positions, selected_teams):
    filtered_df = df
    
    if selected_names:
        filtered_df = filtered_df[filtered_df['Name'].isin(selected_names)]

    if selected_positions:
        filtered_df = filtered_df[filtered_df['Position'].isin(selected_positions)]    

    if selected_teams:
        filtered_df = filtered_df[filtered_df['Team'].isin(selected_teams)]
    
    return filtered_df.to_dict('records')
