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

def rushing_points(row):
    """Calculate fantasy points from rushing production.

    Points are awarded for yardage milestones and touchdowns. Yardage is
    measured in 10 yard increments with additional bonuses at 100, 200 and
    300 yards. Touchdowns are worth six points each.
    """

    rushing_yards = row['RushYds']
    rushing_tds = row['RushTD']

    yard_points = rushing_yards // 10
    hundred_bonus = 3 if rushing_yards >= 100 else 0
    two_hundred_bonus = 3 if rushing_yards >= 200 else 0
    three_hundred_bonus = 3 if rushing_yards >= 300 else 0
    td_points = rushing_tds * 6

    return yard_points + hundred_bonus + two_hundred_bonus + three_hundred_bonus + td_points


def receiving_points(row):
    """Calculate fantasy points from receiving production.

    Yardage and receptions are rewarded with incremental bonuses while each
    receiving touchdown is worth six points.
    """

    receiving_yards = row['RecYds']
    receptions = row['Rec']
    receiving_tds = row['RecTD']

    yard_points = receiving_yards // 10
    hundred_bonus = 3 if receiving_yards >= 100 else 0
    two_hundred_bonus = 3 if receiving_yards >= 200 else 0
    three_hundred_bonus = 3 if receiving_yards >= 300 else 0

    reception_points = receptions // 5
    ten_reception_bonus = 1 if receptions >= 10 else 0
    fifteen_reception_bonus = 1 if receptions >= 15 else 0

    td_points = receiving_tds * 6

    return (
        yard_points
        + hundred_bonus
        + two_hundred_bonus
        + three_hundred_bonus
        + reception_points
        + ten_reception_bonus
        + fifteen_reception_bonus
        + td_points
    )


def rushing_bonus(rush_td, rb_player_stats):
    """Bonus points for long rushing touchdowns.

    Probabilities of touchdowns of 40+ yards are derived from yards-before
    contact and yards-after contact metrics. Each threshold awards additional
    bonus points.
    """

    p40 = rb_player_stats['p() 40yd rus']
    p60 = rb_player_stats['p() 60yd rus']
    p80 = rb_player_stats['p() 80yd rus']

    bonus_80 = rush_td * p80 * 3
    bonus_60 = rush_td * (p60 - p80) * 2
    bonus_40 = rush_td * (p40 - p60 - p80)

    return bonus_80 + bonus_60 + bonus_40


def receiving_bonus(rec, rec_td, wr_player_stats):
    """Bonus points for long receptions and receiving touchdowns.

    Probabilities for each distance bucket are estimated from average depth of
    target and yards after the catch.
    """

    p20 = wr_player_stats['p() 20yd rec']
    p40 = wr_player_stats['p() 40yd rec']
    p60 = wr_player_stats['p() 60yd rec']
    p80 = wr_player_stats['p() 80yd rec']

    rec_bonus = rec * p20 + rec * p40 * 2

    td_bonus_80 = rec_td * p80 * 3
    td_bonus_60 = rec_td * (p60 - p80) * 2
    td_bonus_40 = rec_td * (p40 - p60 - p80)

    return rec_bonus + td_bonus_80 + td_bonus_60 + td_bonus_40


def calculate_rb_wr_points(row):
    """Calculate fantasy points for running backs and wide receivers."""
		
    rushing = rushing_points(row)
    receiving = receiving_points(row)
    fumbles = row['Fum'] * -3

    rush_td_bonus = rushing_bonus(row['RushTD'], rb_player_stats)
    receiving_td_bonus = receiving_bonus(row['Rec'], row['RecTD'], wr_player_stats)

    score = rushing + receiving + fumbles + rush_td_bonus + receiving_td_bonus
		
    return score

def calculate_te_points(row, config=TE_SCORING_DEFAULT):
    score = 0
    score += _apply_yardage(row['RecYds'], config['RecYds'])
    score += _apply_yardage(row['Rec'], config['Rec'])
    score += row['RecTD'] * config['RecTD']['points']
    score += row['Fum'] * config['Fum']['points']
    return score
