import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / 'data' / '2024_adv_stats'
qb_adv_stats = pd.read_csv(DATA_DIR / 'AirYards_by_team.csv')
rb_adv_stats = pd.read_csv(DATA_DIR / 'RB_by_player.csv')
wr_adv_stats = pd.read_csv(DATA_DIR / 'WR_by_player.csv')

for df in (qb_adv_stats, rb_adv_stats, wr_adv_stats):
    if 'Player' in df.columns:
        df['Player'] = df['Player'].str.replace(r'[^\w\s]', '', regex=True)

QB_SCORING_DEFAULT = {
    'PassYds': {'points_per': 25, 'bonuses': {250: 3, 350: 3, 450: 3, 550: 3, 650: 3}},
    'PassTD': {'points': 6},
    'Int': {'points': -3},
    'RushYds': {'points_per': 10, 'bonuses': {100: 3, 200: 3, 300: 3}},
    'RushTD': {'points': 6},
    'Fum': {'points': -3},
}

RB_WR_SCORING_DEFAULT = {
    'RushYds': {'points_per': 10, 'bonuses': {100: 3, 200: 3, 300: 3}},
    'RushTD': {'points': 6},
    'Fum': {'points': -3},
    'RecYds': {'points_per': 10, 'bonuses': {100: 3, 200: 3, 300: 3}},
    'Rec': {'points_per': 5, 'bonuses': {10: 1, 15: 1}},
    'RecTD': {'points': 6},
    'BigRushTD': {'80': 3, '60': 2, '40': 1},
    'BigRec': {'20': 1, '40': 2},
    'BigRecTD': {'80': 3, '60': 2, '40': 1},
}

TE_SCORING_DEFAULT = {
    'RecYds': {'points_per': 10, 'bonuses': {100: 3, 200: 3, 300: 3}},
    'Rec': {'points_per': 5, 'bonuses': {10: 1, 15: 1}},
    'RecTD': {'points': 6},
    'Fum': {'points': -3},
}

def _apply_yardage(value, config):
    points = value // config.get('points_per', 1)
    for threshold, bonus in config.get('bonuses', {}).items():
        if value >= threshold:
            points += bonus
    return points

def calculate_qb_points(row, config=QB_SCORING_DEFAULT):
    score = 0
    score += _apply_yardage(row['PassYds'], config['PassYds'])
    score += row['PassTD'] * config['PassTD']['points']
    score += row['Int'] * config['Int']['points']
    score += _apply_yardage(row['RushYds'], config['RushYds'])
    score += row['RushTD'] * config['RushTD']['points']
    score += row['Fum'] * config['Fum']['points']
    return score

def calculate_rb_wr_points(row, config=RB_WR_SCORING_DEFAULT):
    player_name = row['Name']
    rb_player_stats = rb_adv_stats.loc[rb_adv_stats['Player'] == player_name]
    wr_player_stats = wr_adv_stats.loc[wr_adv_stats['Player'] == player_name]

    if rb_player_stats.empty:
        rb_player_stats = pd.Series({'YBC/Att': 0, 'YAC/Att': 0})
    else:
        rb_player_stats = rb_player_stats.iloc[0]

    if wr_player_stats.empty:
        wr_player_stats = pd.Series({'ADOT': 0, 'YAC/R': 0})
    else:
        wr_player_stats = wr_player_stats.iloc[0]

    rb_player_stats['p() 20yd rus'] = (rb_player_stats['YBC/Att'] + rb_player_stats['YAC/Att']) / 20
    rb_player_stats['p() 40yd rus'] = rb_player_stats['p() 20yd rus'] / 2
    rb_player_stats['p() 60yd rus'] = rb_player_stats['p() 20yd rus'] / 3
    rb_player_stats['p() 80yd rus'] = rb_player_stats['p() 20yd rus'] / 4

    wr_player_stats['p() 20yd rec'] = (wr_player_stats['ADOT'] + wr_player_stats['YAC/R']) / 20
    wr_player_stats['p() 40yd rec'] = wr_player_stats['p() 20yd rec'] / 2
    wr_player_stats['p() 60yd rec'] = wr_player_stats['p() 20yd rec'] / 3
    wr_player_stats['p() 80yd rec'] = wr_player_stats['p() 20yd rec'] / 4

    score = 0
    score += _apply_yardage(row['RushYds'], config['RushYds'])
    score += row['RushTD'] * config['RushTD']['points']
    score += row['Fum'] * config['Fum']['points']
    score += _apply_yardage(row['RecYds'], config['RecYds'])
    score += _apply_yardage(row['Rec'], config['Rec'])
    score += row['RecTD'] * config['RecTD']['points']

    score += row['RushTD'] * (rb_player_stats['p() 80yd rus']) * config['BigRushTD']['80']
    score += row['RushTD'] * (rb_player_stats['p() 60yd rus'] - rb_player_stats['p() 80yd rus']) * config['BigRushTD']['60']
    score += row['RushTD'] * (rb_player_stats['p() 40yd rus'] - rb_player_stats['p() 60yd rus'] - rb_player_stats['p() 80yd rus']) * config['BigRushTD']['40']

    score += row['Rec'] * wr_player_stats['p() 20yd rec'] * config['BigRec']['20']
    score += row['Rec'] * wr_player_stats['p() 40yd rec'] * config['BigRec']['40']
    score += row['RecTD'] * (wr_player_stats['p() 80yd rec']) * config['BigRecTD']['80']
    score += row['RecTD'] * (wr_player_stats['p() 60yd rec'] - wr_player_stats['p() 80yd rec']) * config['BigRecTD']['60']
    score += row['RecTD'] * (wr_player_stats['p() 40yd rec'] - wr_player_stats['p() 60yd rec'] - wr_player_stats['p() 80yd rec']) * config['BigRecTD']['40']

    return score

def calculate_te_points(row, config=TE_SCORING_DEFAULT):
    score = 0
    score += _apply_yardage(row['RecYds'], config['RecYds'])
    score += _apply_yardage(row['Rec'], config['Rec'])
    score += row['RecTD'] * config['RecTD']['points']
    score += row['Fum'] * config['Fum']['points']
    return score
