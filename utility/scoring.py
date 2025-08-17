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

def calculate_rb_wr_points(row):
    player_name = row['Name']

    rb_player_stats = rb_adv_stats.loc[rb_adv_stats['Player'] == player_name]
    # if len(rb_player_stats) == 0:
    #     rb_player_stats['YBC/Att'] = 0
    #     rb_player_stats['YAC/Att'] = 0

    wr_player_stats = wr_adv_stats.loc[wr_adv_stats['Player'] == player_name]
    # if len(wr_player_stats) == 0:
    #     wr_player_stats['ADOT'] = 0
    #     wr_player_stats['YAC/R'] = 0

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
    
    score = 0

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

    # more conditions for specific bonuses, such as RuTD of 40+ yards, etc.
    score += row['RushTD'] * (rb_player_stats['p() 80yd rus']) * 3
    score += row['RushTD'] * (rb_player_stats['p() 60yd rus'] - rb_player_stats['p() 80yd rus']) * 2
    score += row['RushTD'] * (rb_player_stats['p() 40yd rus'] - rb_player_stats['p() 60yd rus'] - rb_player_stats['p() 80yd rus']) * 1

    score += row['Rec'] * wr_player_stats['p() 20yd rec'] * 1
    score += row['Rec'] * wr_player_stats['p() 40yd rec'] * 2
    score += row['RecTD'] * (wr_player_stats['p() 80yd rec']) * 3
    score += row['RecTD'] * (wr_player_stats['p() 60yd rec'] - wr_player_stats['p() 80yd rec']) * 2
    score += row['RecTD'] * (wr_player_stats['p() 40yd rec'] - wr_player_stats['p() 60yd rec'] - wr_player_stats['p() 80yd rec']) * 1

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

