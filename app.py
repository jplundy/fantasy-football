import dash
from dash import dcc, html, Output, Input, State
from plotly import express as px
import dash_bootstrap_components as dbc
import pandas as pd
from utility import helpers, scoring
import plotly.graph_objs as go
from layout import create_layout
import warnings
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)

def load_position_data(pos: str) -> pd.DataFrame:
    data = helpers.get_position_data(pos)
    data = helpers.clean_offense_data(data, pos=pos)
    scoring_map = {
        'QB': scoring.calculate_qb_points,
        'RB': scoring.calculate_rb_wr_points,
        'WR': scoring.calculate_rb_wr_points,
        'TE': scoring.calculate_te_points,
    }
    score_func = scoring_map.get(pos)
    if score_func:
        data['ModelPoints'] = data.apply(score_func, axis=1)
    else:
        data['ModelPoints'] = 0.0
    return data


positions = ['QB', 'RB', 'WR', 'TE']
position_data = {pos: load_position_data(pos) for pos in positions}

merge_all = pd.concat(position_data.values(), ignore_index=True)
merge_all.to_csv('data/all_data.csv', index=False)
grouped_data = merge_all.groupby('Name').agg({'ModelPoints': ['sum', 'count']})
grouped_data.to_csv('data/grouped_data.csv', index=True)

def calculate_vorp_and_rank(group):
    position = group['Position'].iloc[0]
    if position == 'QB':
        baseline = group['ModelPoints'].nlargest(14).iloc[-1]
    elif position in ['RB', 'WR']:
        baseline = group['ModelPoints'].nlargest(48).iloc[-1]
    elif position == 'TE':
        baseline = group['ModelPoints'].nlargest(14).iloc[-1]
    else:
        baseline = 0  # For any other positions
    
    group['VORP'] = group['ModelPoints'] - baseline
    
    # Add ranking
    group['Rank'] = group['ModelPoints'].rank(method='min', ascending=False)
    
    return group

# Apply the function to each group
grouped_vorp_and_rank_data = merge_all.groupby(['Week', 'Position']).apply(calculate_vorp_and_rank).reset_index(drop=True)

grouped_vorp_and_rank_data = grouped_vorp_and_rank_data.sort_values(['Week', 'Position', 'Rank'])

### At this point we have correctly built data
# using "df" from now on:

df = grouped_vorp_and_rank_data.copy(deep=True)

# Step 1: Aggregate weekly data into season totals
season_totals = df.groupby(['Name', 'Position', 'Team']).agg({
    'PassYds': 'sum',
    'PassTD': 'sum',
    'Int': 'sum',
    'RushYds': 'sum',
    'RushTD': 'sum',
    'Rec': 'sum',
    'RecYds': 'sum',
    'RecTD': 'sum',
    'Fum': 'sum',
    'ModelPoints': 'sum',
}).reset_index()

# Step 2: Split the dataframe by position
positions = ['QB', 'RB', 'WR', 'TE']
base_data = {pos: helpers.clean_offense_data(helpers.get_position_data(pos), pos=pos) for pos in positions}

NUM_TEAMS = 12
INITIAL_BUDGET = 200
TOTAL_BUDGET = NUM_TEAMS * INITIAL_BUDGET
MIN_SPEND = NUM_TEAMS * 17
AUCTION_BUDGET = TOTAL_BUDGET - MIN_SPEND

def compute_values(config):
    qb = base_data['QB'].copy()
    qb['ModelPoints'] = qb.apply(lambda r: scoring.calculate_qb_points(r, config['QB']), axis=1)
    rb = base_data['RB'].copy()
    rb['ModelPoints'] = rb.apply(lambda r: scoring.calculate_rb_wr_points(r, config['RB_WR']), axis=1)
    wr = base_data['WR'].copy()
    wr['ModelPoints'] = wr.apply(lambda r: scoring.calculate_rb_wr_points(r, config['RB_WR']), axis=1)
    te = base_data['TE'].copy()
    te['ModelPoints'] = te.apply(lambda r: scoring.calculate_te_points(r, config['TE']), axis=1)

    merge_all = pd.concat([qb, rb, wr, te], ignore_index=True)
    season_totals = merge_all.groupby(['Name', 'Position', 'Team']).agg({
        'PassYds': 'sum',
        'PassTD': 'sum',
        'Int': 'sum',
        'RushYds': 'sum',
        'RushTD': 'sum',
        'Rec': 'sum',
        'RecYds': 'sum',
        'RecTD': 'sum',
        'Fum': 'sum',
        'ModelPoints': 'sum',
    }).reset_index()

    position_dfs = {pos: season_totals[season_totals['Position'] == pos].sort_values('ModelPoints', ascending=False) for pos in positions}
    baselines = {'QB': 14, 'RB': 48, 'WR': 48, 'TE': 14}
    for pos in positions:
        df_pos = position_dfs[pos]
        if len(df_pos) >= baselines[pos]:
            baseline_value = df_pos.iloc[baselines[pos]-1]['ModelPoints']
        else:
            baseline_value = df_pos['ModelPoints'].min()
        df_pos['VORP'] = df_pos['ModelPoints'] - baseline_value
        position_dfs[pos] = df_pos

    total_vorp = sum(df['VORP'].clip(lower=0).sum() for df in position_dfs.values())
    price_per_point = AUCTION_BUDGET / total_vorp if total_vorp else 0

    for pos in positions:
        position_dfs[pos]['AuctionValue'] = (position_dfs[pos]['VORP'].clip(lower=0) * price_per_point).round(2)

    all_players = pd.concat(position_dfs.values())
    all_players_sorted = all_players.sort_values('AuctionValue', ascending=False)
    return all_players_sorted

DEFAULT_CONFIG = {
    'QB': scoring.QB_SCORING_DEFAULT,
    'RB_WR': scoring.RB_WR_SCORING_DEFAULT,
    'TE': scoring.TE_SCORING_DEFAULT,
}

all_players_sorted = compute_values(DEFAULT_CONFIG)
all_players_sorted['Drafted'] = False
all_players_sorted['DraftedBy'] = ''
all_players_sorted['PricePaid'] = 0

draft_history = []

app = dash.Dash(__name__, use_pages=True, title='FF', update_title='****', suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = create_layout(
    all_players_sorted['Name'].tolist(),
    NUM_TEAMS,
    all_players_sorted.to_dict('records'),
)


@app.callback(
    Output('player-data', 'data'),
    [
        Input('pass-yds-pt', 'value'),
        Input('pass-td-pts', 'value'),
        Input('int-pen', 'value'),
        Input('rush-yds-pt', 'value'),
        Input('rush-td-pts', 'value'),
        Input('fum-pen', 'value'),
        Input('rec-yds-pt', 'value'),
        Input('rec-per', 'value'),
        Input('rec-td-pts', 'value'),
    ],
    State('player-data', 'data'),
)
def update_player_data(pass_yds_pt, pass_td_pts, int_pen, rush_yds_pt, rush_td_pts,
                       fum_pen, rec_yds_pt, rec_per, rec_td_pts, current_data):
    config = {
        'QB': {
            'PassYds': {'points_per': pass_yds_pt, 'bonuses': scoring.QB_SCORING_DEFAULT['PassYds']['bonuses']},
            'PassTD': {'points': pass_td_pts},
            'Int': {'points': int_pen},
            'RushYds': {'points_per': rush_yds_pt, 'bonuses': scoring.QB_SCORING_DEFAULT['RushYds']['bonuses']},
            'RushTD': {'points': rush_td_pts},
            'Fum': {'points': fum_pen},
        },
        'RB_WR': {
            'RushYds': {'points_per': rush_yds_pt, 'bonuses': scoring.RB_WR_SCORING_DEFAULT['RushYds']['bonuses']},
            'RushTD': {'points': rush_td_pts},
            'Fum': {'points': fum_pen},
            'RecYds': {'points_per': rec_yds_pt, 'bonuses': scoring.RB_WR_SCORING_DEFAULT['RecYds']['bonuses']},
            'Rec': {'points_per': rec_per, 'bonuses': scoring.RB_WR_SCORING_DEFAULT['Rec']['bonuses']},
            'RecTD': {'points': rec_td_pts},
            'BigRushTD': scoring.RB_WR_SCORING_DEFAULT['BigRushTD'],
            'BigRec': scoring.RB_WR_SCORING_DEFAULT['BigRec'],
            'BigRecTD': scoring.RB_WR_SCORING_DEFAULT['BigRecTD'],
        },
        'TE': {
            'RecYds': {'points_per': rec_yds_pt, 'bonuses': scoring.TE_SCORING_DEFAULT['RecYds']['bonuses']},
            'Rec': {'points_per': rec_per, 'bonuses': scoring.TE_SCORING_DEFAULT['Rec']['bonuses']},
            'RecTD': {'points': rec_td_pts},
            'Fum': {'points': fum_pen},
        },
    }
    new_players = compute_values(config)
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
    Output('player-data', 'data'),
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
    [Output('value-distribution-graph', 'figure'),
     Output('top-players-graph', 'figure'),
     Output('draft-summary', 'children')] +
    [Output(f'team-{i}-summary', 'children') for i in range(1, NUM_TEAMS + 1)] +
    [Output(f'team-{i}-remaining-budget', 'children') for i in range(1, NUM_TEAMS + 1)] +
    [Output(f'team-{i}-composition-chart', 'figure') for i in range(1, NUM_TEAMS + 1)],
    Input('player-data', 'data'),
)
def update_summaries(data):
    df = pd.DataFrame(data or [])
    value_dist = px.box(df, x='Position', y='AuctionValue', title='Auction Value Distribution by Position')
    top_players = px.bar(df.head(20), x='Name', y='AuctionValue', color='Position', title='Top 20 Players by Auction Value')
    top_players.update_layout(xaxis={'categoryorder': 'total descending'})
    drafted_players = df[df['Drafted']]
    summary = [
        html.P(f"Total Players Drafted: {len(drafted_players)}"),
        html.P(f"Total Spend: ${drafted_players['PricePaid'].sum():.2f}"),
        html.P("Top Drafted Players:"),
        html.Ul([html.Li(f"{row['Name']} - {row['DraftedBy']} - ${row['PricePaid']}") for _, row in drafted_players.sort_values('PricePaid', ascending=False).head(5).iterrows()]),
    ]
    team_summaries = []
    team_budgets = []
    team_charts = []
    for i in range(1, NUM_TEAMS + 1):
        team_name = f'Team {i}'
        team_players = drafted_players[drafted_players['DraftedBy'] == team_name]
        team_spend = team_players['PricePaid'].sum()
        remaining_budget = INITIAL_BUDGET - team_spend
        team_summary = [
            html.P(f"Players Drafted: {len(team_players)}"),
            html.P(f"Total Spend: ${team_spend:.2f}"),
            html.P("Drafted Players:"),
            html.Ul([html.Li(f"{row['Name']} ({row['Position']}) - ${row['PricePaid']}") for _, row in team_players.iterrows()]),
        ]
        team_summaries.append(team_summary)
        team_budgets.append(f"Remaining Budget: ${remaining_budget:.2f}")
        position_counts = team_players['Position'].value_counts()
        team_chart = go.Figure(data=[go.Pie(labels=position_counts.index, values=position_counts.values)])
        team_chart.update_layout(title=f"{team_name} Composition", height=300)
        team_charts.append(team_chart)
    return value_dist, top_players, summary, *team_summaries, *team_budgets, *team_charts


@app.callback(Output('player-table', 'dashGridOptions'), Input('search-input', 'value'))
def update_quick_filter(text):
    return {'pagination': True, 'paginationAutoPageSize': True, 'quickFilterText': text or ''}


if __name__ == '__main__':
    app.run_server(debug=True)
