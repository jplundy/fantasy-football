import json
from copy import deepcopy
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
    bonus points. Probabilities are scaled by a player's breakaway rate
    calculated from ``Att/Br`` when available.
    """

    # Determine how often a player breaks a long run.
    br_rate = rb_player_stats.get('breakaway_rate')
    if br_rate is None:
        att_per_br = rb_player_stats.get('Att/Br')
        br_rate = 1 / att_per_br if att_per_br and att_per_br > 0 else 0

    # Scale distance-based probabilities by the breakaway rate.
    adj = 1 + br_rate
    p40 = rb_player_stats['p() 40yd rus'] * adj
    p60 = rb_player_stats['p() 60yd rus'] * adj
    p80 = rb_player_stats['p() 80yd rus'] * adj

    bonus_80 = rush_td * p80 * 3
    bonus_60 = rush_td * (p60 - p80) * 2
    bonus_40 = rush_td * (p40 - p60 - p80)

    return bonus_80 + bonus_60 + bonus_40


def receiving_bonus(rec, rec_td, wr_player_stats):
    """Bonus points for long receptions and receiving touchdowns.

    Probabilities for each distance bucket are estimated from average depth of
    target and yards after the catch. Probabilities are scaled by a player's
    breakaway rate calculated from ``Rec/Br`` when available.
    """

    br_rate = wr_player_stats.get('breakaway_rate')
    if br_rate is None:
        rec_per_br = wr_player_stats.get('Rec/Br')
        br_rate = 1 / rec_per_br if rec_per_br and rec_per_br > 0 else 0

    adj = 1 + br_rate
    p20 = wr_player_stats['p() 20yd rec'] * adj
    p40 = wr_player_stats['p() 40yd rec'] * adj
    p60 = wr_player_stats['p() 60yd rec'] * adj
    p80 = wr_player_stats['p() 80yd rec'] * adj

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

    # Look up the player's advanced rushing metrics.  If the player isn't
    # found, assume no bonus points.  The CSVs loaded at module import contain
    # a ``Player`` column, while ``row`` may use ``Name`` or ``Player`` – handle
    # both for robustness.
    player_name = row.get('Name') or row.get('Player')

    rb_player_stats = rb_adv_stats.loc[rb_adv_stats['Player'] == player_name]
    if rb_player_stats.empty:
        rush_td_bonus = 0
    else:
        rb_player_stats = rb_player_stats.iloc[0].copy()
        att_per_br = rb_player_stats.get('Att/Br')
        rb_player_stats['breakaway_rate'] = (
            1 / att_per_br if att_per_br and att_per_br > 0 else 0
        )
        if 'p() 40yd rus' not in rb_player_stats:
            p20 = (rb_player_stats.get('YBC/Att', 0) + rb_player_stats.get('YAC/Att', 0)) / 20
            rb_player_stats['p() 40yd rus'] = p20 / 2
            rb_player_stats['p() 60yd rus'] = p20 / 3
            rb_player_stats['p() 80yd rus'] = p20 / 4
        rush_td_bonus = rushing_bonus(row['RushTD'], rb_player_stats)

    wr_player_stats = wr_adv_stats.loc[wr_adv_stats['Player'] == player_name]
    if wr_player_stats.empty:
        receiving_td_bonus = 0
    else:
        wr_player_stats = wr_player_stats.iloc[0].copy()
        rec_per_br = wr_player_stats.get('Rec/Br')
        wr_player_stats['breakaway_rate'] = (
            1 / rec_per_br if rec_per_br and rec_per_br > 0 else 0
        )
        if 'p() 20yd rec' not in wr_player_stats:
            p20 = (wr_player_stats.get('ADOT', 0) + wr_player_stats.get('YAC/R', 0)) / 20
            wr_player_stats['p() 20yd rec'] = p20
            wr_player_stats['p() 40yd rec'] = p20 / 2
            wr_player_stats['p() 60yd rec'] = p20 / 3
            wr_player_stats['p() 80yd rec'] = p20 / 4
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


SCORING_CONFIG_DEFAULT = {
    'QB': QB_SCORING_DEFAULT,
    'RB': RB_WR_SCORING_DEFAULT,
    'WR': RB_WR_SCORING_DEFAULT,
    'TE': TE_SCORING_DEFAULT,
}


def save_config(path: str | Path, config: dict) -> None:
    """Serialize a scoring configuration to JSON.

    Parameters
    ----------
    path:
        Destination file path.
    config:
        Scoring configuration mapping to persist.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


def load_config(path: str | Path) -> dict:
    """Load a scoring configuration from JSON.

    If the file does not exist or cannot be parsed, a deep copy of
    :data:`SCORING_CONFIG_DEFAULT` is returned.
    """

    path = Path(path)
    if not path.exists():
        return deepcopy(SCORING_CONFIG_DEFAULT)
    try:
        with path.open(encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return deepcopy(SCORING_CONFIG_DEFAULT)


def calculate_prop_points(df: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
    """Calculate fantasy points for each player based on position.

    Parameters
    ----------
    df:
        DataFrame containing at least ``Pos`` and the statistical columns used
        by the scoring functions.
    config:
        Optional mapping of position to scoring configuration.  If omitted,
        :data:`SCORING_CONFIG_DEFAULT` is used.
    """

    if df is None or df.empty:
        return df

    config = config or SCORING_CONFIG_DEFAULT
    df = df.copy()
    df['Pos'] = df['Pos'].str.upper()

    qb_mask = df['Pos'] == 'QB'
    if qb_mask.any():
        qb_cfg = config.get('QB', QB_SCORING_DEFAULT)
        df.loc[qb_mask, 'ModelPoints'] = df.loc[qb_mask].apply(
            lambda row: calculate_qb_points(row, qb_cfg), axis=1
        )

    rb_wr_mask = df['Pos'].isin(['RB', 'WR'])
    if rb_wr_mask.any():
        df.loc[rb_wr_mask, 'ModelPoints'] = df.loc[rb_wr_mask].apply(
            calculate_rb_wr_points, axis=1
        )

    te_mask = df['Pos'] == 'TE'
    if te_mask.any():
        te_cfg = config.get('TE', TE_SCORING_DEFAULT)
        df.loc[te_mask, 'ModelPoints'] = df.loc[te_mask].apply(
            lambda row: calculate_te_points(row, te_cfg), axis=1
        )

    df['ModelPoints'] = pd.to_numeric(df['ModelPoints'], errors='coerce').fillna(0)
    return df
