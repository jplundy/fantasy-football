import pandas as pd
import warnings
from utility import helpers, scoring

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


def calculate_vorp_and_rank(group: pd.DataFrame) -> pd.DataFrame:
    position = group['Position'].iloc[0]
    if position == 'QB':
        baseline = group['ModelPoints'].nlargest(14).iloc[-1]
    elif position in ['RB', 'WR']:
        baseline = group['ModelPoints'].nlargest(48).iloc[-1]
    elif position == 'TE':
        baseline = group['ModelPoints'].nlargest(14).iloc[-1]
    else:
        baseline = 0

    group['VORP'] = group['ModelPoints'] - baseline
    group['Rank'] = group['ModelPoints'].rank(method='min', ascending=False)
    return group


grouped_vorp_and_rank_data = (
    merge_all.groupby(['Week', 'Position'])
    .apply(calculate_vorp_and_rank)
    .reset_index(drop=True)
)

grouped_vorp_and_rank_data = grouped_vorp_and_rank_data.sort_values(
    ['Week', 'Position', 'Rank']
)


df = grouped_vorp_and_rank_data.copy(deep=True)

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

base_data = {
    pos: helpers.clean_offense_data(helpers.get_position_data(pos), pos=pos)
    for pos in positions
}

NUM_TEAMS = 12
INITIAL_BUDGET = 200
TOTAL_BUDGET = NUM_TEAMS * INITIAL_BUDGET
MIN_SPEND = NUM_TEAMS * 17
AUCTION_BUDGET = TOTAL_BUDGET - MIN_SPEND


def compute_values(config):
    qb = base_data['QB'].copy()
    qb['ModelPoints'] = qb.apply(
        lambda r: scoring.calculate_qb_points(r, config['QB']), axis=1
    )
    rb = base_data['RB'].copy()
    rb['ModelPoints'] = rb.apply(scoring.calculate_rb_wr_points, axis=1)
    wr = base_data['WR'].copy()
    wr['ModelPoints'] = wr.apply(scoring.calculate_rb_wr_points, axis=1)
    te = base_data['TE'].copy()
    te['ModelPoints'] = te.apply(
        lambda r: scoring.calculate_te_points(r, config['TE']), axis=1
    )

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

    position_dfs = {
        pos: season_totals[season_totals['Position'] == pos].sort_values(
            'ModelPoints', ascending=False
        )
        for pos in positions
    }
    baselines = {'QB': 14, 'RB': 48, 'WR': 48, 'TE': 14}
    for pos in positions:
        df_pos = position_dfs[pos]
        if len(df_pos) >= baselines[pos]:
            baseline_value = df_pos.iloc[baselines[pos] - 1]['ModelPoints']
        else:
            baseline_value = df_pos['ModelPoints'].min()
        df_pos['VORP'] = df_pos['ModelPoints'] - baseline_value
        position_dfs[pos] = df_pos

    total_vorp = sum(df['VORP'].clip(lower=0).sum() for df in position_dfs.values())
    price_per_point = AUCTION_BUDGET / total_vorp if total_vorp else 0

    for pos in positions:
        position_dfs[pos]['AuctionValue'] = (
            position_dfs[pos]['VORP'].clip(lower=0) * price_per_point
        ).round(2)

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

