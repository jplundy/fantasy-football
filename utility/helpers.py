import pandas as pd
import sqlite3
from datetime import datetime
from pathlib import Path
from utility import scoring

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = str(BASE_DIR / 'data' / 'draft_history.db')
CURRENT_SEASON = datetime.now().year


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS draft_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            season INTEGER NOT NULL,
            player TEXT,
            position TEXT,
            team TEXT,
            owner TEXT,
            price REAL
        )
        """
    )
    conn.commit()
    conn.close()

def get_schedule():
    file_path = '/Users/justin/Desktop/chest/fantasy_football/2025/assets/schedule_2025.csv'
    try:
        df = pd.read_csv(file_path)
    except:
        print("schedule not found")
    return df

def clean_schedule(df: pd.DataFrame):
    # Melt the DataFrame to long format
    df_long = pd.melt(df, id_vars=['TEAM'], var_name='Week', value_name='Opponent')

    # Fix non-integer weeks
    df_long['Week'] = df_long['Week'].apply(lambda x: int(x) if x else x)

    # Extract the location (home/away) and opponent team
    df_long['Location'] = df_long['Opponent'].apply(lambda x: 'Away' if '@' in x else 'Home')
    df_long['Opponent'] = df_long['Opponent'].str.replace('@', '').str.strip()

    # Handle BYE weeks
    df_long['Game_Type'] = df_long['Opponent'].apply(lambda x: 'BYE' if x == 'BYE' else 'Game')
    df_long['Opponent'] = df_long['Opponent'].replace('BYE', 'None')

    # Sort by team and week
    df_long = df_long.sort_values(by=['TEAM', 'Week'])

    return df_long

def get_offense_data():
    file_path = '/Users/justin/Desktop/chest/fantasy_football/2025/data/2025_weekly_proj/off.csv'
    try:
        df = pd.read_csv(file_path, index_col=0, header=0)
    except :
        print("no data")
        df = pd.DataFrame()
    return df

def clean_offense_data(df: pd.DataFrame, pos: str = None):
    '''
    Player,Opp,PassYds,PassTD,Int,RushYds,RushTD,Rec,RecYds,RecTD,RetTD,FumTD,TwoPt,Lost,Points,Week,Name,_position,_team
    '''
    main_cols = ['Name', 'Position', 'Team', 'Opp', 'Week']
    # Rename columns for clarity
    rename_map = {
        '_position': 'Position', 
        '_team': 'Team', 
        #'Yds':'PassYds',
        #'TD':'PassTD',
        #'Yds.1':'RushYds',
        #'TD.1':'RushTD',
        #'Yds.2':'RecYds',
        #'TD.2':'RecTD',
        'Lost':'Fum'
    }
    df.rename(columns=rename_map, inplace=True)

    df.drop(columns=['FumTD', 'TwoPt'], inplace=True)

    ordered_cols = main_cols + [col for col in df.columns if col not in main_cols+['Player']]

    df = df[ordered_cols]

    str_cols = ['Name', 'Position', 'Team', 'Opp']
    for c in df.columns:
        #print(str(c))
        if c not in str_cols:
            df[c].fillna(float(0))
            df[c] = df[c].astype(float)
        else:
            df[c].fillna('')
            df[c] = df[c].astype(str)
            df[c] = df[c].apply(lambda x: x.strip() if x is str else x)


    if pos:
        pos = pos.upper()
        if pos == 'QB': cols = main_cols + ['PassYds', 'PassTD', 'Int', 'RushYds', 'RushTD', 'Fum']
        elif pos == 'RB' or 'WR': cols = main_cols + ['RushYds', 'RushTD', 'Rec', 'RecYds', 'RecTD', 'Fum']
        elif pos == 'TE': cols = main_cols + ['Rec', 'RecYds', 'RecTD', 'Fum']
        else: cols = df.columns
        df = df[cols]

    return df

def get_board():
    file_path = '/Users/justin/Desktop/chest/fantasy_football/2025/data/board.csv'
    try:
        board_df = pd.read_csv(file_path)
    except :
        print("no board")
        off_data = get_offense_data()
        off_data = clean_offense_data(off_data)
        board_df = pd.DataFrame()
        board_df = off_data.loc[:, ['Name', 'Position', 'Team']].copy(deep=True)
        board_df['Owner'] = pd.NA
        board_df['Price'] = pd.NA
    return board_df

def clean_board(df: pd.DataFrame):
    if df.empty:
        return None
    df['Owner'] = df['Owner'].fillna('').astype(str)
    df['Price'] = df['Price'].fillna(0).astype(float)

    return df

def save_board(df):
    file_path = '/Users/justin/Desktop/chest/fantasy_football/2025/data/board.csv'
    if df is pd.DataFrame:
        try:
            df.to_csv(file_path, index=False)
            return True
        except:
            return False
    return False

def get_position_data(pos: str):
    pos = pos.upper()
    if pos not in ['QB', 'RB', 'WR', 'TE', 'K']: return pd.DataFrame()
    file_path = f'/Users/justin/Desktop/chest/fantasy_football/2025/data/2025_weekly_proj/{pos}.csv'
    try:
        df = pd.read_csv(file_path, header=0)
    except :
        print("no data")
        df = pd.DataFrame()
    return df


def log_draft_picks(df: pd.DataFrame, season: int = CURRENT_SEASON):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    for _, row in df.iterrows():
        owner = str(row.get('Owner', '')).strip()
        if owner:
            cur.execute(
                'SELECT 1 FROM draft_picks WHERE season=? AND player=?',
                (season, row['Name'])
            )
            if not cur.fetchone():
                cur.execute(
                    'INSERT INTO draft_picks(timestamp, season, player, position, team, owner, price) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (
                        datetime.utcnow().isoformat(),
                        season,
                        row['Name'],
                        row.get('Position'),
                        row.get('Team'),
                        owner,
                        float(row.get('Price', 0))
                    )
                )
    conn.commit()
    conn.close()


def get_draft_history(season: int = None):
    conn = sqlite3.connect(DB_FILE)
    query = 'SELECT * FROM draft_picks'
    params = ()
    if season is not None:
        query += ' WHERE season=?'
        params = (season,)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


init_db()
