import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
from espn_api.football import League
import re

def normalize_name(name):
    if pd.isna(name):
        return ""
    name = str(name).lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", name)      # remove suffixes
    name = re.sub(r"[^a-z\s]", "", name)                   # remove punctuation
    name = re.sub(r"\s+", " ", name).strip()               # collapse spaces
    return name

def add_rostered_percentage(proj_df, league_id,year,espn_s2,swid):
    league = League(league_id = league_id, year = year, espn_s2 = espn_s2, swid = swid)

    rostered_map = {}

    # Free agents
    for player in league.free_agents(size=200):
        pct = getattr(player, "percent_owned", 0)
        rostered_map[normalize_name(player.name)] = pct

    # Include rostered players on teams
    for team in league.teams:
        for player in team.roster:
            pct = getattr(player, "percent_owned", 0)
            rostered_map[normalize_name(player.name)] = pct

    proj_df["normalized_name"] = proj_df["player_display_name"].apply(normalize_name)
    proj_df["rostered_pct"] = proj_df["normalized_name"].map(rostered_map).fillna(0)
    return proj_df

def export_recommendations(csv_path,sheet_id,league_id,year,espn_s2,swid):
    proj_df = pd.read_csv(csv_path)

    proj_df = add_rostered_percentage(proj_df,league_id,year,espn_s2,swid)
    proj_df["diff"] = proj_df["projected_points"] - proj_df["baseline"]

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json",scopes = scopes)
    client = gspread.authorize(creds)

    positions = ["QB","RB","WR","TE"]

    for pos in positions:
        pos_df = proj_df[
            (proj_df["position"] == pos) & (proj_df["rostered_pct"]<35) & (proj_df["rostered_pct"] > 0)
        ].copy()

        pos_df = pos_df.sort_values("projected_points",ascending = False).drop_duplicates("normalized_name").head(3)
        

        if pos_df.empty:
            continue
        try:
            worksheet = client.open_by_key(sheet_id).worksheet(f"{pos} Waiver Recs")
            worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            worksheet = client.open_by_key(sheet_id).add_worksheet(
                title = f"{pos} Waiver Recs", rows = "20", cols = "10"
            )
        display_cols = [
            "player_display_name",
            "team",
            "position",
            "opponent",
            "week",
            "baseline",
            "projected_points",
            "diff",
            "rostered_pct"
        ]

        set_with_dataframe(worksheet,pos_df[display_cols])

if __name__ == "__main__":
    export_recommendations(
        csv_path = "weekly_projections.csv",
        sheet_id= "1jzYYVtDsVKi5BZg9MZ8g8BXMHBLVPf_suqMcyORjdGM",
        league_id = 340761201,
        year = 2025,
        espn_s2 = "AEA0BqbFiXqaG4xdI0XWmfxOfOk9iXwD7j%2FLpPSHYu4lhYoYaBgfFnnijEC9HUmc6IebipoHmjjx7YzcwibZ7b5awausjGYvb0aEpBRM18lNWrzlCSGwCjyItiQmHS5i7cChB0AuRYHnPUPO8l8mZOQ5GhcASjAljs6hCNPgqTLwqJwAaBmCtEb6R9YM4N0mMtUBl%2BjSYyp3pV%2Fs0sGYEroCp3eU8EyObqeRToIUWu4x71GPbUv%2Fm3I0i1XrobCA6MeaS%2BPzXVgcU%2BXhGBTahebRtKTgH3PL%2BMtRGV4X8eP3DA%3D%3D",
        swid = "{629A0EE0-7DBF-428C-A92E-BEF70E289499}"
    )


