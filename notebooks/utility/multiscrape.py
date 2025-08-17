from selenium import webdriver
from selenium.webdriver import Firefox,FirefoxOptions,FirefoxProfile
# from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import regex as re
from concurrent.futures import ThreadPoolExecutor

BASE_URL = 'https://fantasy.nfl.com/research/projections?offset={offset}&position={position}&sort=projectedPts&statCategory=projectedStats&statSeason=2025&statType=weekProjectedStats&statWeek={week}'

POSITIONS = [1,2,3,4,7,8,'O']
positions_map = {
    1:'QB',
    2:'RB',
    3:'WR',
    4:'TE',
    7:'K',
    8:'DEF',
    'O':'Off'
}
position_offsets = {
    1:26, # 1:126, # qb
    2:51, # 2:226, # rb
    3:101, # 3:426, # wr
    4:26, # 4:201, # te
    7:26, # 7:51, # k
    8:26, # dst
    'O':376 # all offense
}

def scrape_position(driver, position):
    all_position_data = []
    max_offset = position_offsets[position]
    offsets = [n for n in range(1, max_offset, 25)]

    for week in range(1, 19):
        if week == 1:
            headers = [header.text for header in table.find('thead').find_all('th')]
            try:
                start_index = headers.index('Player')
            except:
                start_index = headers.index('Team')
            headers = headers[start_index:]

        for o in offsets:
            url = BASE_URL.format(offset=o, position=position, week=week)
            print(f"position: {positions_map[position]} / week: {week} / offset: {o}")
            driver.get(url)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'tableType-player'))
            )

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find('table', {'class': 'tableType-player hasGroups'})

            rows = []
            for row in table.find('tbody').find_all('tr'):
                cells = row.find_all('td')
                rows.append([cell.text.strip() for cell in cells])

            for row in rows:
                row.append(week)
                row.append(positions_map[position])

            all_position_data.extend(rows)

    df_pos = pd.DataFrame(all_position_data, columns=headers + ['Week', 'Position'])
    print(df_pos.head(8))
    clean_df_pos = clean_scrape(df_pos)
    clean_df_pos.to_csv(f'/Users/justin/Desktop/chest/fantasy_football/2025/data/{positions_map[position]}_ms_scraped_data.csv', index=False)
    return clean_df_pos

def scrape(positions=POSITIONS):
    driver = webdriver.Firefox()
    all_data = pd.DataFrame()

    try:
        with ThreadPoolExecutor(max_workers=len(positions)) as executor:
            futures = []
            for position in positions:
                    futures.append(executor.submit(scrape_position, driver, position))

            for future in futures:
                result = future.result()
                try:
                    result_df = pd.DataFrame(result)
                except:
                    result_df = pd.DataFrame()
                    print("a future result failed to convert to df")
                all_data = pd.concat([all_data, result_df], sort=False, ignore_index=True)
    except:
        print("error")

    driver.quit()

    all_data.to_csv('/Users/justin/Desktop/chest/fantasy_football/2025/data/ms_scraped_data.csv', index=False)
    print("all data pushed to CSV")

    return all_data

def clean_scrape(df: pd.DataFrame):
    columns = df.columns.astype(str).to_list()
    for c in columns:
        c = str(c)
        if c == "Player" or c == "Opp" or c == "Team" or c == "Position" or c == "Week":
            continue
        df[c] = df[c].fillna(float(0)).replace("-", float(0))

    def repair_player(x: str):
        x = x.replace("View News", "").strip()
        match = re.match(r"(.+?)\s([A-Z]+)\s-\s([A-Z]+)", x)
        if not match:
            match = re.match(r"(.+?)\s([A-Z]+)(?:,([A-Z]+))?", x)
        
        if match:
            name = match.group(1).strip()
            position = match.group(2).strip()
            team = match.group(3).strip() if match.group(3) else None
        else:
            name = position = team = None
        
        return name, position, team


    try:
        df['Name'], df['_position'], df['_team'] = zip(*df['Player'].apply(lambda x: repair_player(str(x))))
    except:
        try:
            df['Name'], df['_position'], df['_team'] = zip(*df['Team'].apply(lambda x: repair_player(str(x))))
        except:
            df['Name'] = df['_position'] = df['_team'] = pd.NA

    

    return df
