import dash
from dash import dcc, html, Output, Input, callback, State, dash_table
from plotly import express as px
import dash_bootstrap_components as dbc  # Optional for better styling
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import random
from scipy import stats
from utility import helpers
from utility import scoring
import plotly.graph_objs as go
from layout import create_layout
import warnings
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)

pos = 'QB'
qb_data_w_scoring = helpers.get_position_data(pos)
qb_data_w_scoring = helpers.clean_offense_data(qb_data_w_scoring, pos=pos)

pos = 'RB'
rb_data_w_scoring = helpers.get_position_data(pos)
rb_data_w_scoring = helpers.clean_offense_data(rb_data_w_scoring, pos=pos)

pos = 'WR'
wr_data_w_scoring = helpers.get_position_data(pos)
wr_data_w_scoring = helpers.clean_offense_data(wr_data_w_scoring, pos=pos)

pos = 'TE'
te_data_w_scoring = helpers.get_position_data(pos)
te_data_w_scoring = helpers.clean_offense_data(te_data_w_scoring, pos=pos)

qb_data_w_scoring['ModelPoints'] = qb_data_w_scoring.apply(scoring.calculate_qb_points, axis=1)
rb_data_w_scoring['ModelPoints'] = rb_data_w_scoring.apply(scoring.calculate_rb_wr_points, axis=1)
wr_data_w_scoring['ModelPoints'] = wr_data_w_scoring.apply(scoring.calculate_rb_wr_points, axis=1)
te_data_w_scoring['ModelPoints'] = te_data_w_scoring.apply(scoring.calculate_te_points, axis=1)

merge_all = pd.concat([qb_data_w_scoring, rb_data_w_scoring, wr_data_w_scoring, te_data_w_scoring], ignore_index=True)
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
position_dfs = {pos: season_totals[season_totals['Position'] == pos] for pos in positions}

# Step 3: Define baselines for each position
baselines = {'QB': 14, 'RB': 48, 'WR': 48, 'TE': 14}

# Step 4: Calculate VORP for each position
for pos in positions:
    position_dfs[pos] = position_dfs[pos].sort_values('ModelPoints', ascending=False)
    baseline_value = position_dfs[pos].iloc[baselines[pos] - 1]['ModelPoints']
    position_dfs[pos]['VORP'] = position_dfs[pos]['ModelPoints'] - baseline_value

# Step 5: Calculate total VORP across all positions
total_vorp = sum(position_dfs[pos]['VORP'].clip(lower=0).sum() for pos in positions)

# Step 6: Calculate price per point
total_budget = 12 * 200  # 12 teams, $200 each
min_spend = 12 * 17  # 12 teams, 17 rounds, $1 minimum
auction_budget = total_budget - min_spend
price_per_point = auction_budget / total_vorp

# Step 7: Calculate auction values
for pos in positions:
    position_dfs[pos]['AuctionValue'] = (position_dfs[pos]['VORP'].clip(lower=0) * price_per_point + 0).round(2)


from utility import excel

# Call the function to save the data
excel.save_to_excel(position_dfs)

# Print summary for each position
for pos in positions:
    print(f"\n{pos} Top 10 Auction Values:")
    print(position_dfs[pos][['Name', 'ModelPoints', 'VORP', 'AuctionValue']].head(10))

# Print top 20 players across all positions
all_players = pd.concat(position_dfs.values())
all_players_sorted = all_players.sort_values('AuctionValue', ascending=False)
print("\nTop 20 Players Across All Positions:")
print(all_players_sorted[['Name', 'Position', 'ModelPoints', 'VORP', 'AuctionValue']].head(20))

# Calculate and print total auction values
total_auction_value = all_players['AuctionValue'].sum()
print(f"\nTotal Auction Value: ${total_auction_value:.2f}")
print(f"Expected Total Value: ${total_budget:.2f}")


# Prepare the data
all_players = pd.concat(position_dfs.values())
all_players_sorted = all_players.sort_values('AuctionValue', ascending=False)
all_players_sorted['Drafted'] = False
all_players_sorted['DraftedBy'] = ''
all_players_sorted['PricePaid'] = 0

app = dash.Dash(__name__, 
                use_pages=True,
                title='FF',
                update_title='****',
                suppress_callback_exceptions=True,
                external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server


# # # # # # # # # # #


# Set number of teams and initial budget
NUM_TEAMS = 12
INITIAL_BUDGET = 200

# Create a draft history to enable undo functionality
draft_history = []

# Set the layout
app.layout = create_layout(all_players_sorted['Name'].tolist(), positions, NUM_TEAMS)

# Callback to update player table, graphs, and team summaries
@app.callback(
    [Output('player-table', 'rowData'),
     Output('value-distribution-graph', 'figure'),
     Output('top-players-graph', 'figure'),
     Output('draft-message', 'children'),
     Output('draft-summary', 'children')] +
    [Output(f'team-{i}-summary', 'children') for i in range(1, NUM_TEAMS + 1)] +
    [Output(f'team-{i}-remaining-budget', 'children') for i in range(1, NUM_TEAMS + 1)] +
    [Output(f'team-{i}-composition-chart', 'figure') for i in range(1, NUM_TEAMS + 1)],
    [Input('position-filter', 'value'),
     Input('search-input', 'value'),
     Input('draft-button', 'n_clicks'),
     Input('undo-button', 'n_clicks')],
    [State('draft-name', 'value'),
     State('draft-team', 'value'),
     State('draft-price', 'value')]
)
def update_data(position, search, draft_clicks, undo_clicks, draft_name, draft_team, draft_price):
    ctx = dash.callback_context
    global all_players_sorted, draft_history

    if ctx.triggered[0]['prop_id'] == 'draft-button.n_clicks':
        if draft_name and draft_team and draft_price:
            player = all_players_sorted[all_players_sorted['Name'] == draft_name]
            if not player.empty and not player['Drafted'].iloc[0]:
                draft_history.append((draft_name, draft_team, draft_price))
                all_players_sorted.loc[all_players_sorted['Name'] == draft_name, 'Drafted'] = True
                all_players_sorted.loc[all_players_sorted['Name'] == draft_name, 'DraftedBy'] = draft_team
                all_players_sorted.loc[all_players_sorted['Name'] == draft_name, 'PricePaid'] = draft_price
    
    elif ctx.triggered[0]['prop_id'] == 'undo-button.n_clicks' and draft_history:
        last_draft = draft_history.pop()
        all_players_sorted.loc[all_players_sorted['Name'] == last_draft[0], 'Drafted'] = False
        all_players_sorted.loc[all_players_sorted['Name'] == last_draft[0], 'DraftedBy'] = ''
        all_players_sorted.loc[all_players_sorted['Name'] == last_draft[0], 'PricePaid'] = 0

    filtered_df = all_players_sorted

    if position != 'All':
        filtered_df = filtered_df[filtered_df['Position'] == position]
    
    if search:
        filtered_df = filtered_df[filtered_df['Name'].str.contains(search, case=False)]

    # Create value distribution graph
    value_dist = px.box(filtered_df, x='Position', y='AuctionValue', title='Auction Value Distribution by Position')
    
    # Create top players graph
    top_players = px.bar(filtered_df.head(20), x='Name', y='AuctionValue', color='Position',
                         title='Top 20 Players by Auction Value')
    top_players.update_layout(xaxis={'categoryorder':'total descending'})

    # Create overall draft summary
    drafted_players = all_players_sorted[all_players_sorted['Drafted']]
    summary = [
        html.P(f"Total Players Drafted: {len(drafted_players)}"),
        html.P(f"Total Spend: ${drafted_players['PricePaid'].sum():.2f}"),
        html.P("Top Drafted Players:"),
        html.Ul([html.Li(f"{row['Name']} - {row['DraftedBy']} - ${row['PricePaid']}") 
                 for _, row in drafted_players.sort_values('PricePaid', ascending=False).head(5).iterrows()])
    ]

    # Create team summaries, remaining budgets, and composition charts
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
            html.Ul([html.Li(f"{row['Name']} ({row['Position']}) - ${row['PricePaid']}") 
                     for _, row in team_players.iterrows()])
        ]
        team_summaries.append(team_summary)
        
        team_budgets.append(f"Remaining Budget: ${remaining_budget:.2f}")
        
        position_counts = team_players['Position'].value_counts()
        team_chart = go.Figure(data=[go.Pie(labels=position_counts.index, values=position_counts.values)])
        team_chart.update_layout(title=f"{team_name} Composition", height=300)
        team_charts.append(team_chart)

    return (filtered_df.to_dict('records'), value_dist, top_players, '', summary, 
            *team_summaries, *team_budgets, *team_charts)

if __name__ == '__main__':
    app.run_server(debug=True)