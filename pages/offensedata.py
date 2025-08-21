import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
from dash_ag_grid import AgGrid
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
                dcc.RadioItems(
                    id='offdata-view-mode',
                    options=[
                        {'label': 'Weekly', 'value': 'weekly'},
                        {'label': 'Season', 'value': 'season'}
                    ],
                    value='weekly',
                    inline=True
                ),
                className='my-2'
            ),
            dbc.Row(
                AgGrid(
                    id='offdata-grid',
                    columnDefs=[
                        {
                            "headerName": col,
                            "field": col,
                            **(
                                {"valueFormatter": {"function": "Number(params.value).toFixed(2)"}}
                                if pd.api.types.is_numeric_dtype(df[col])
                                else {}
                            ),
                        }
                        for col in df.columns
                    ],
                    rowData=df.to_dict('records'),
                    dashGridOptions={"defaultColDef": {"sortable": True, "filter": True}},
                    columnSize="autoSize",
                )
            )
        ],
        fluid=True,
        style={'width':'100%', 'height':'100%', 'margin':'0px', 'padding':'0px'}
    )
    return component

# Callback to update the table based on filters
@callback(
    Output('offdata-grid', 'rowData'),
    Output('offdata-grid', 'columnDefs'),
    Input('offdata-name-dropdown', 'value'),
    Input('offdata-pos-dropdown', 'value'),
    Input('offdata-team-dropdown', 'value'),
    Input('offdata-view-mode', 'value'),
)
def update_table(selected_names, selected_positions, selected_teams, view_mode):
    filtered_df = df

    if selected_names:
        filtered_df = filtered_df[filtered_df['Name'].isin(selected_names)]

    if selected_positions:
        filtered_df = filtered_df[filtered_df['Position'].isin(selected_positions)]

    if selected_teams:
        filtered_df = filtered_df[filtered_df['Team'].isin(selected_teams)]

    if view_mode == 'season':
        filtered_df = filtered_df.drop(columns=[c for c in ['Week', 'Opponent'] if c in filtered_df.columns])
        filtered_df = filtered_df.groupby(['Name', 'Position', 'Team'], as_index=False).sum(numeric_only=True)

    column_defs = [
        {
            "headerName": col,
            "field": col,
            **(
                {"valueFormatter": {"function": "Number(params.value).toFixed(2)"}}
                if pd.api.types.is_numeric_dtype(filtered_df[col])
                else {}
            ),
        }
        for col in filtered_df.columns
    ]
    row_data = filtered_df.to_dict('records')
    return row_data, column_defs
