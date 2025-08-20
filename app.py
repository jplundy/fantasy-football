import dash
from dash import dcc, html, Output, Input, State
from pathlib import Path
from plotly import express as px
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
from utility import scoring
from utility.scoring import load_config
from models.auction import (
    all_players_sorted,
    compute_values,
)

settings_path = Path("assets/settings.json")
initial_settings = load_config(settings_path)
TEAM_NAMES = initial_settings.get('league', {}).get(
    'team_names',
    [
        f'Team {i}'
        for i in range(1, initial_settings.get('league', {}).get('num_teams', 12) + 1)
    ],
)
NUM_TEAMS = len(TEAM_NAMES)
INITIAL_BUDGET = initial_settings.get('league', {}).get('initial_budget', 200)

draft_history = []

app = dash.Dash(
    __name__,
    use_pages=True,
    title='FF',
    update_title='****',
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
server = app.server

app.layout = dbc.Container(
    [
        dcc.Store(id="scoring-config", data=initial_settings),
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Home", href="/")),
                dbc.NavItem(dbc.NavLink("Auction", href="/auction")),
                dbc.NavItem(dbc.NavLink("Draft Board", href="/draftboard")),
                dbc.NavItem(dbc.NavLink("Offense Data", href="/offensedata")),
                dbc.NavItem(dbc.NavLink("Projections", href="/projections")),
                dbc.NavItem(dbc.NavLink("Modeling", href="/modeling")),
                dbc.NavItem(dbc.NavLink("History", href="/history")),
                dbc.NavItem(dbc.NavLink("Playground", href="/playground")),
                dbc.NavItem(dbc.NavLink("League Settings", href="/settings")),
            ],
            brand="sigFantasy",
            brand_href="/",
            color="grey",
            fluid=True,
        ),
        dash.page_container,
    ],
    fluid=True,
)

@app.callback(
    Output('player-data', 'data', allow_duplicate=True),
    Input('scoring-config', 'data'),
    State('player-data', 'data'),
    prevent_initial_call=True,
)
def update_player_data(config, current_data):
    cfg = config or scoring.SCORING_CONFIG_DEFAULT
    new_players = compute_values(cfg)
    if current_data:
        drafted_cols = pd.DataFrame(current_data)[['Name', 'Drafted', 'DraftedBy', 'PricePaid']]
        new_players = new_players.merge(drafted_cols, on='Name', how='left')
        new_players['Drafted'] = new_players['Drafted'].fillna(False)
        new_players['DraftedBy'] = new_players['DraftedBy'].fillna('')
        new_players['PricePaid'] = new_players['PricePaid'].fillna(0)
    else:
        new_players['Drafted'] = False
        new_players['DraftedBy'] = ''
        new_players['PricePaid'] = 0
    return new_players.to_dict('records')


@app.callback(
    Output('player-data', 'data', allow_duplicate=True),
    [Input('draft-button', 'n_clicks'),
     Input('undo-button', 'n_clicks')],
    [State('draft-name', 'value'),
     State('draft-team', 'value'),
     State('draft-price', 'value'),
     State('player-data', 'data')],
    prevent_initial_call=True,
)
def update_draft(draft_clicks, undo_clicks, draft_name, draft_team, draft_price, data):
    ctx = dash.callback_context
    if data is None:
        raise dash.exceptions.PreventUpdate
    df = pd.DataFrame(data)
    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'draft-button.n_clicks':
        if draft_name and draft_team and draft_price is not None:
            player = df[df['Name'] == draft_name]
            if not player.empty and not player.iloc[0]['Drafted']:
                draft_history.append((draft_name, draft_team, draft_price))
                df.loc[df['Name'] == draft_name, ['Drafted', 'DraftedBy', 'PricePaid']] = [True, draft_team, draft_price]
    elif ctx.triggered and ctx.triggered[0]['prop_id'] == 'undo-button.n_clicks' and draft_history:
        last_draft = draft_history.pop()
        df.loc[df['Name'] == last_draft[0], ['Drafted', 'DraftedBy', 'PricePaid']] = [False, '', 0]
    return df.to_dict('records')


@app.callback(Output('player-table', 'rowData'), Input('player-data', 'data'))
def update_table(data):
    return data or []


@app.callback(
    [
        Output('value-distribution-graph', 'figure'),
        Output('top-players-graph', 'figure'),
        Output('draft-summary', 'children'),
        Output('team-summary-display', 'children'),
    ],
    [Input('player-data', 'data'), Input('team-selector', 'value')],
)
def update_summaries(data, selected_team):
    df = pd.DataFrame(data or [])
    value_dist = px.box(df, x='Position', y='AuctionValue', title='Auction Value Distribution by Position')
    top_players = px.bar(df.head(20), x='Name', y='AuctionValue', color='Position', title='Top 20 Players by Auction Value')
    top_players.update_layout(xaxis={'categoryorder': 'total descending'})

    drafted_players = df[df['Drafted']]
    summary = [
        html.P(f"Total Players Drafted: {len(drafted_players)}"),
        html.P(f"Total Spend: ${drafted_players['PricePaid'].sum():.2f}"),
        html.P("Top Drafted Players:"),
        html.Ul([
            html.Li(f"{row['Name']} - {row['DraftedBy']} - ${row['PricePaid']}")
            for _, row in drafted_players.sort_values('PricePaid', ascending=False).head(5).iterrows()
        ]),
    ]

    team_summary_df = (
        drafted_players.groupby('DraftedBy')
        .agg(Players=('Name', 'count'), Spend=('PricePaid', 'sum'))
        .reindex(TEAM_NAMES, fill_value=0)
    )
    team_summary_df['Remaining'] = INITIAL_BUDGET - team_summary_df['Spend']

    if selected_team in team_summary_df.index:
        team_row = team_summary_df.loc[selected_team]
    else:
        team_row = pd.Series({'Players': 0, 'Spend': 0.0, 'Remaining': INITIAL_BUDGET})

    position_counts = (
        drafted_players[drafted_players['DraftedBy'] == selected_team]['Position']
        .value_counts()
        .to_dict()
    )

    table_rows = [
        html.Tr([html.Th('Players Drafted'), html.Td(int(team_row['Players']))]),
        html.Tr([html.Th('Total Spend'), html.Td(f"${team_row['Spend']:.2f}")]),
        html.Tr([html.Th('Remaining Budget'), html.Td(f"${team_row['Remaining']:.2f}")]),
    ]
    for pos, count in position_counts.items():
        table_rows.append(html.Tr([html.Th(pos), html.Td(count)]))

    team_table = dbc.Table([html.Tbody(table_rows)], bordered=True, hover=True, size='sm')

    return value_dist, top_players, summary, team_table


@app.callback(Output('player-table', 'dashGridOptions'), Input('search-input', 'value'))
def update_quick_filter(text):
    return {'pagination': True, 'paginationAutoPageSize': True, 'quickFilterText': text or ''}


if __name__ == '__main__':
    app.run(debug=True)
