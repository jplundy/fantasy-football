# scrape_nfl_projections_2025.py

from __future__ import annotations
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup
import pandas as pd
import time
import regex as re
from pathlib import Path
import os
import sys

# -------------------- CONFIG --------------------
BASE_URL = (
    "https://fantasy.nfl.com/research/projections"
    "?offset={offset}&position={position}&sort=projectedPts"
    "&statCategory=projectedStats&statSeason=2025"
    "&statType=weekProjectedStats&statWeek={week}"
)

# NFL site positions
POSITIONS = [1, 2, 3, 4, 7, 8]
positions_map = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 7: "K", 8: "DEF"}

# how deep to page for each position (multiple of 25, include 0)
position_offsets = {
    1: 26,   # QB ~ (0,25)
    2: 51,   # RB
    3: 101,  # WR
    4: 26,   # TE
    7: 26,   # K
    8: 26    # DEF
}

# output dir
OUT_DIR = Path("/Users/justin/Desktop/chest/fantasy_football/2025/data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADLESS = True          # set False to watch the browser
BROWSER  = "firefox"     # "firefox" or "chrome"
TIMEOUT  = 20            # explicit wait timeout
PAUSE    = 0.3           # throttle between page loads
# ------------------------------------------------


def get_driver(browser: str = BROWSER, headless: bool = HEADLESS):
    """Return a Selenium driver with auto-managed browser driver."""
    if browser.lower() == "firefox":
        opts = FirefoxOptions()
        if headless:
            opts.add_argument("--headless")
        # mild UA spoof helps some sites load full markup
        opts.set_preference(
            "general.useragent.override",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        driver = webdriver.Firefox(
            executable_path=GeckoDriverManager().install(),
            options=opts
        )
    else:
        opts = ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=opts)

    driver.set_page_load_timeout(60)
    return driver


def normalize_offense_headers(cols: list[str], pos_code: int) -> list[str]:
    """
    NFL offensive tables flatten to unlabeled columns. Replace with stable, prefixed names.
    For QB/RB/WR/TE pages, expected order is roughly:
      Player, Opp, PassYds, PassTD, Int, RushYds, RushTD, Rec, RecYds, RecTD, RetTD, FumTD, TwoPt, Lost, Points
    K/DEF handled separately/minimally.
    """
    # Kickers: keep minimal standardization
    if pos_code == 7:  # K
        # site varies; we'll standardize typical set and allow extras to pass through
        standard = ["Player", "Opp", "FGM", "FGA", "FG0_19", "FG20_29", "FG30_39", "FG40_49", "FG50", "XPM", "XPA", "Points"]
        keep = [c for c in ["Player", "Opp"] if c in cols]
        rest = [h for h in standard if h not in keep]
        extras = [c for c in cols if c not in keep and c not in standard]
        return keep + rest + extras

    if pos_code == 8:  # DEF/DST: leave as-is (columns vary a lot)
        return cols

    # Offensive positions: align to canonical after Player/Opp
    try:
        start_idx = cols.index("Player")
    except ValueError:
        try:
            start_idx = cols.index("Team")
        except ValueError:
            start_idx = 0

    hdrs = cols[start_idx:]

    canonical = [
        "Player", "Opp",
        "PassYds", "PassTD", "Int",
        "RushYds", "RushTD",
        "Rec", "RecYds", "RecTD",
        "RetTD", "FumTD", "TwoPt", "Lost",
        "Points"
    ]

    if len(hdrs) >= 15:
        out = canonical + hdrs[15:]  # preserve extra trailing columns if present
    else:
        # keep Player/Opp if present, then fill to length using canonical
        keep_leads = []
        if "Player" in hdrs:
            keep_leads.append("Player")
        if "Opp" in hdrs:
            keep_leads.append("Opp")
        needed = max(0, len(hdrs) - len(keep_leads))
        out = keep_leads + canonical[len(keep_leads):len(keep_leads) + needed]

    # ensure uniqueness
    deduped = []
    counts = {}
    for h in out:
        if h in counts:
            counts[h] += 1
            deduped.append(f"{h}_{counts[h]}")
        else:
            counts[h] = 0
            deduped.append(h)
    return deduped


def clean_scrape(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df.columns = [str(c) for c in df.columns]

    # fill numeric-ish columns with 0 (skip text columns)
    skip = {"Player", "Team", "Opp", "Position", "Week", "Name", "_position", "_team"}
    for c in df.columns:
        if c in skip:
            continue
        try:
            ser = pd.to_numeric(df[c].replace("-", "0"), errors="coerce")
            if ser.notna().mean() > 0.5:
                df[c] = ser.fillna(0)
        except Exception:
            pass

    def repair_player(x: str):
        x = str(x).replace("View News", "").strip()
        x = re.sub(r"\s+", " ", x)
        # capture TEAM at end if present
        m_team = re.search(r"(?:\s[-,]?\s)?([A-Z]{2,4})\s*$", x)
        team = m_team.group(1) if m_team else None
        base = x[:m_team.start()].strip() if m_team else x

        # capture POS attached to end (allow no-space)
        m_pos = re.search(r"(QB|RB|WR|TE|K|DEF|DST)\s*$", base)
        if not m_pos:
            m_pos = re.search(r"(QB|RB|WR|TE|K|DEF|DST)$", base)
        position = m_pos.group(1) if m_pos else None
        name = base[:m_pos.start()].strip() if m_pos else base

        name = name.rstrip(" -,")
        if position == "DST":
            position = "DEF"

        # if nothing parsed, return base as name
        return (name or None), position, team

    target_col = "Player" if "Player" in df.columns else ("Team" if "Team" in df.columns else None)
    if target_col:
        try:
            df["Name"], df["_position"], df["_team"] = zip(*df[target_col].map(lambda x: repair_player(str(x))))
        except Exception:
            df["Name"] = df.get("Name", pd.Series([pd.NA] * len(df)))
            df["_position"] = df.get("_position", pd.Series([pd.NA] * len(df)))
            df["_team"] = df.get("_team", pd.Series([pd.NA] * len(df)))
    else:
        df["Name"] = pd.NA
        df["_position"] = pd.NA
        df["_team"] = pd.NA

    return df


def scrape(positions=POSITIONS) -> pd.DataFrame:
    driver = get_driver()
    all_frames: list[pd.DataFrame] = []
    ps = 0

    try:
        for p in positions:
            pos_name = positions_map[p]
            all_position_rows = []
            max_offset = position_offsets[p]
            offsets = list(range(0, max_offset, 25))
            headers = None

            for w in range(1, 19):  # weeks 1..18
                for o in offsets:
                    print(f"position: {pos_name} / week: {w} / offset: {o} / pages scraped: {ps}")
                    url = BASE_URL.format(offset=o, position=p, week=w)
                    driver.get(url)

                    # wait best-effort for table
                    try:
                        WebDriverWait(driver, TIMEOUT).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table.tableType-player.hasGroups"))
                        )
                    except Exception:
                        time.sleep(1.5)

                    ps += 1
                    time.sleep(PAUSE)

                    soup = BeautifulSoup(driver.page_source, "lxml")
                    table = soup.select_one("table.tableType-player.hasGroups")
                    if table is None:
                        continue

                    thead = table.find("thead")
                    if headers is None and thead:
                        headers_raw = [th.get_text(strip=True) for th in thead.find_all("th")]
                        # align to Player/Team
                        start_index = None
                        for key in ("Player", "Team"):
                            if key in headers_raw:
                                start_index = headers_raw.index(key)
                                break
                        headers = headers_raw[start_index:] if start_index is not None else headers_raw
                        # normalize based on position
                        headers = normalize_offense_headers(headers, pos_code=p)

                    tbody = table.find("tbody")
                    if not tbody:
                        continue

                    for tr in tbody.find_all("tr"):
                        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                        if not tds:
                            continue
                        # pad if shorter than headers
                        if headers and len(tds) < len(headers):
                            tds += [""] * (len(headers) - len(tds))
                        # append week
                        tds.append(w)
                        all_position_rows.append(tds)

            if not all_position_rows:
                print(f"no rows found for position {pos_name}. skipping write.")
                continue

            # ensure Week header
            if headers is None:
                # fallback for truly weird cases
                headers = ["Player", "Opp",
                           "PassYds", "PassTD", "Int",
                           "RushYds", "RushTD",
                           "Rec", "RecYds", "RecTD",
                           "RetTD", "FumTD", "TwoPt", "Lost",
                           "Points"]
            if headers[-1] != "Week":
                headers = headers + ["Week"]

            df_pos = pd.DataFrame(all_position_rows, columns=headers)

            # final column de-dup
            seen = {}
            new_cols = []
            for c in df_pos.columns:
                if c in seen:
                    seen[c] += 1
                    new_cols.append(f"{c}_{seen[c]}")
                else:
                    seen[c] = 0
                    new_cols.append(c)
            df_pos.columns = new_cols

            df_pos = clean_scrape(df_pos)

            out_pos = OUT_DIR / f"{pos_name}.csv"
            df_pos.to_csv(out_pos, index=False)
            print(f"position {pos_name} pushed to csv -> {out_pos}")

            all_frames.append(df_pos)

        if all_frames:
            # union schema to avoid concat alignment issues
            all_cols = set()
            for df in all_frames:
                all_cols.update(df.columns.tolist())
            all_cols = list(all_cols)

            aligned = [df.reindex(columns=all_cols) for df in all_frames]
            all_df = pd.concat(aligned, ignore_index=True, sort=False)

            all_out = OUT_DIR / "scraped_data.csv"
            all_df.to_csv(all_out, index=False)
            print(f"all data pushed to csv -> {all_out}")
            return all_df
        else:
            print("no data scraped.")
            return pd.DataFrame()

    finally:
        try:
            driver.quit()
        except Exception:
            pass


# if __name__ == "__main__":
#     # optional: allow overriding browser/headless via env vars
#     b = os.environ.get("NFL_BROWSER")
#     if b:
#         global BROWSER
#         BROWSER = b
#     h = os.environ.get("NFL_HEADLESS")
#     if h is not None:
#         global HEADLESS
#         HEADLESS = h.lower() in ("1", "true", "yes")
#     scrape()
