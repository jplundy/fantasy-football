import pandas as pd
import numpy as np

qb_adv_stats = pd.read_csv('/Users/justin/Desktop/chest/fantasy_football/2025/data/2024_adv_stats/AirYards_by_team.csv')
rb_adv_stats = pd.read_csv('/Users/justin/Desktop/chest/fantasy_football/2025/data/2024_adv_stats/RB_by_player.csv')
wr_adv_stats = pd.read_csv('/Users/justin/Desktop/chest/fantasy_football/2025/data/2024_adv_stats/WR_by_player.csv')

stats = [qb_adv_stats, rb_adv_stats, wr_adv_stats]
for s in stats:
    if 'Player' in s.columns:
        s['Player'] = s['Player'].str.replace(r'[^\w\s]', '', regex=True)


def calculate_qb_points(row):  
    score = 0

    # Passing Yards: 1 point per 25 PaYds + bonuses
    score += row['PassYds'] // 25
    if row['PassYds'] >= 250:
        score += 3
    if row['PassYds'] >= 350:
        score += 3
    if row['PassYds'] >= 450:
        score += 3
    if row['PassYds'] >= 550:
        score += 3
    if row['PassYds'] >= 650:
        score += 3

    # Passing TDs: 6 points per PaTD
    score += row['PassTD'] * 6

    # Interceptions: -3 points per Int
    score += row['Int'] * -3

    # Rushing Yards: 1 point per 10 RuYds + bonuses
    score += row['RushYds'] // 10
    if row['RushYds'] >= 100:
        score += 3
    if row['RushYds'] >= 200:
        score += 3
    if row['RushYds'] >= 300:
        score += 3

    # Rushing TDs: 6 points per RuTD
    score += row['RushTD'] * 6

    # Fumbles: -3 points per Fum
    score += row['Fum'] * -3

    # more conditions for specific bonuses, such as PaTD of 40+ yards, etc.

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

    player_name = row['Name']

    rb_player_stats = rb_adv_stats.loc[rb_adv_stats['Player'] == player_name]
    wr_player_stats = wr_adv_stats.loc[wr_adv_stats['Player'] == player_name]

    # Handle cases where the player's stats are missing
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

    rushing = rushing_points(row)
    receiving = receiving_points(row)
    fumbles = row['Fum'] * -3

    rush_td_bonus = rushing_bonus(row['RushTD'], rb_player_stats)
    receiving_td_bonus = receiving_bonus(row['Rec'], row['RecTD'], wr_player_stats)

    score = rushing + receiving + fumbles + rush_td_bonus + receiving_td_bonus

    return score

def calculate_te_points(row):
    score = 0

    # Receiving Yards: 1 point per 10 ReYds + bonuses
    score += row['RecYds'] // 10
    if row['RecYds'] >= 100:
        score += 3
    if row['RecYds'] >= 200:
        score += 3
    if row['RecYds'] >= 300:
        score += 3

    # Receptions: 1 point per 5 Recpt + bonuses
    score += row['Rec'] // 5
    if row['Rec'] >= 10:
        score += 1
    if row['Rec'] >= 15:
        score += 1

    # Receiving TDs: 6 points per ReTD
    score += row['RecTD'] * 6

    # Fumbles: -3 points per Fum
    score += row['Fum'] * -3

    # more conditions for specific bonuses, such as RuTD of 40+ yards, etc.

    return score

