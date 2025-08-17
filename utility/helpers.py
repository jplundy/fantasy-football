import pandas as pd
from utility import scoring

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



    if pos:
        pos = pos.upper()
        if pos == 'QB': 
            df['ModelPoints'] = df.apply(scoring.calculate_qb_points, axis=1)
        elif pos == 'RB' or 'WR': 
            df['ModelPoints'] = df.apply(scoring.calculate_rb_wr_points, axis=1)
        elif pos == 'TE':
            df['ModelPoints'] = df.apply(scoring.calculate_te_points, axis=1)
        else:
            df['ModelPoints'] = 0.0

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
