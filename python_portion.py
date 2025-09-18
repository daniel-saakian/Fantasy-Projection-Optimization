import os
import pandas as pd
import numpy as np
from espn_api.football import League
import gspread
from gspread_dataframe import set_with_dataframe
from gspread_formatting import *
from google.oauth2.service_account import Credentials
import requests
import re
import time



league_id = 340761201
espn_year = 2025
swid = "{629A0EE0-7DBF-428C-A92E-BEF70E289499}"
espn_s2 = 'AEASLWMQkk8Gs8R5nrE2C6pjJjRAd8giVPB%2BhbmRYatVTf3r%2FDX%2B15Ex8zA8d15dbeJcwcd6gxkAu8kAPcYv2NlxuzoVL2QxaVGX8n8XCP6z3%2FoDK3GxBU%2FQGbLyx476eRnPMt9znEYWgtQEQwqOJvJL3gejRa%2BatDNNQw2ZwXKcnENEg46%2BJbBE9R8j1LSq5zOjAOhQMcEx6e5bJO4Q2kaWVQdKj1db368rIQulb0iW2xI0uUtlrL3sPMopGliO0BmqNenalFf7A%2FFNbdj1R3ZihIvfqk%2Fhh0jok1r5pqY0ew%3D%3D'
min_roster_pct = 35.0
week = 3

# Google Sheets implementation


sheet_id = "1jzYYVtDsVKi5BZg9MZ8g8BXMHBLVPf_suqMcyORjdGM"

def export_to_gsheet(proj_df,sheet_id):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json", scopes = scopes)
    client = gspread.authorize(creds)  

    spreadsheet = client.open_by_key(sheet_id)
    proj_df["diff"] = proj_df["projected_points"] - proj_df["baseline"]

    display_cols = [
        "player_display_name",
        "team",
        "position",
        "opponent",
        "week",
        "baseline",
        "projected_points",
        "diff"
    ]
    positions = proj_df["position"].unique()

    for pos in positions:
        # Filter + sort by diff descending
        pos_df = proj_df[proj_df["position"] == pos].copy()
        pos_df = pos_df.drop_duplicates(
            subset=["player_display_name", "team", "position", "week"]
        )
        pos_df["diff"] = pos_df["projected_points"] - pos_df["baseline"]
        pos_df = pos_df[display_cols].sort_values(by="diff", ascending=False)

        # Check if sheet exists, else create
        try:
            worksheet = spreadsheet.worksheet(pos)
            worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=pos, rows="200", cols="20")

        # Write dataframe to sheet
        set_with_dataframe(worksheet, pos_df, include_index=False)

        num_rows = len(pos_df) + 1  # +1 for header row

        # Header format
        header_format = CellFormat(
            backgroundColor=Color(0.8, 0.8, 0.8),
            textFormat=TextFormat(bold=True, foregroundColor=Color(0, 0, 0))
        )
        format_cell_range(worksheet, "A1:H1", header_format)

        # Bold player names
        name_format = CellFormat(textFormat=TextFormat(bold=True))
        format_cell_range(worksheet, f"A2:A{num_rows}", name_format)

        # Clear old conditional formatting
        rules = get_conditional_format_rules(worksheet)
        rules.clear()

        # Gradient coloring based on diff
        diff_col = "H"
        rule_gradient = ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(f'{diff_col}2:{diff_col}{num_rows}', worksheet)],
            gradientRule=GradientRule(
                minpoint=InterpolationPoint(type='NUMBER', value=str(pos_df["diff"].min()), color=Color(1, 0.8, 0.8)),  # light red
                midpoint=InterpolationPoint(type='NUMBER', value="0", color=Color(1, 1, 1)),  # white at 0
                maxpoint=InterpolationPoint(type='NUMBER', value=str(pos_df["diff"].max()), color=Color(0.8, 1, 0.8))   # light green
            )
        )
        rules.append(rule_gradient)
        rules.save()



#Free Agents
league = League(league_id = league_id, year = espn_year, espn_s2 = espn_s2, swid = swid)

free_agents = league.free_agents(size = 50)
waiver_targets = [p for p in free_agents if p.percent_owned < min_roster_pct]

#Defensive Rankings (Lower means an easier matchup, or most fantasy points allowed to that specific position)

defensive_rankings = {
    "ARI": {"QB": 18, "RB": 20, "WR": 11, "TE": 6},
    "ATL": {"QB": 27, "RB": 27, "WR": 18, "TE": 32},
    "BAL": {"QB": 4, "RB": 7, "WR": 15, "TE": 2},
    "BUF": {"QB": 7, "RB": 19, "WR": 24, "TE": 31},
    "CAR": {"QB": 30, "RB": 15, "WR": 30, "TE": 3},
    "CHI": {"QB": 1,"RB": 2,"WR": 2,"TE": 16},
    "CIN": {"QB": 15, "RB": 3, "WR": 14, "TE": 15},
    "CLE": {"QB": 17, "RB": 30, "WR": 13, "TE": 25},
    "DAL": {"QB": 3, "RB": 14, "WR": 4, "TE": 22},
    "DEN": {"QB": 31, "RB": 18, "WR": 29, "TE": 17},
    "DET": {"QB": 14, "RB": 21, "WR": 7, "TE": 21},
    "GB": {"QB": 23, "RB": 28, "WR": 21, "TE": 5},
    "HOU": {"QB": 19, "RB": 9, "WR": 10, "TE": 30},
    "IND": {"QB": 25, "RB": 17, "WR": 17, "TE": 20},
    "JAX": {"QB": 13, "RB": 25, "WR": 8, "TE": 26},
    "KC": {"QB": 9, "RB": 24, "WR": 9, "TE": 29},
    "LV":{"QB": 16, "RB": 20, "WR": 5, "TE": 28},
    "LAC": {"QB": 20, "RB": 31, "WR": 26, "TE": 10},
    "LA": {"QB": 32, "RB": 32, "WR": 25, "TE": 18},
    "MIA": {"QB": 2, "RB": 5, "WR": 19, "TE": 11},
    "MIN": {"QB": 26, "RB": 13, "WR": 31, "TE": 27},
    "NE": {"QB": 12, "RB": 16, "WR": 3, "TE": 14},
    "NO": {"QB": 8, "RB": 12, "WR": 22, "TE": 7},
    "NYG": {"QB": 6, "RB": 1, "WR": 1, "TE": 9},
    "NYJ": {"QB": 11, "RB": 8, "WR": 16, "TE": 8},
    "PHI": {"QB": 24, "RB": 22, "WR": 23, "TE": 24},
    "PIT": {"QB": 5, "RB": 4, "WR": 12, "TE": 12},
    "SF": {"QB": 28, "RB": 23, "WR": 20,"TE": 19},
    "SEA": {"QB": 22, "RB": 6, "WR": 32, "TE": 1},
    "TB": {"QB": 10, "RB": 11, "WR": 28, "TE": 23},
    "TEN": {"QB": 29, "RB": 10, "WR": 6, "TE": 16},
    "WAS": {"QB": 21, "RB": 26, "WR": 27, "TE": 4}
}


#WINNING ODDS
vegas_odds_per_team = [
    {"week": 3, "home_team": "BUF", "away_team": "MIA", "spread_h": -12.5, "spread_a": 12.5, "total": 49.5},
    {"week": 3, "home_team": "NYJ", "away_team": "TB", "spread_h": 6.5, "spread_a": -6.5,"total": 44.5},
    {"week": 3, "home_team": "IND", "away_team": "TEN", "spread_h": -3.5,"spread_a": 3.5,"total": 43.5},
    {"week": 3, "home_team": "LV", "away_team": "WAS", "spread_h": 3.5, "spread_a": -3.5,"total": 44.5},
    {"week": 3, "home_team": "LA", "away_team": "PHI", "spread_h": 3.5,"spread_a": -3.5,"total": 44.5},
    {"week": 3, "home_team": "ATL", "away_team": "CAR", "spread_h": -5.5,"spread_a": 5.5,"total": 43.5},
    {"week": 3, "home_team": "HOU", "away_team": "JAX", "spread_h": 1.5,"spread_a": -1.5,"total": 44.5},
    {"week": 3, "home_team": "GB", "away_team": "CLE", "spread_h": -7.5,"spread_a": 7.5,"total": 42.5},
    {"week": 3, "home_team": "PIT", "away_team": "NE", "spread_h": -1.5,"spread_a": 1.5,"total": 44.5},
    {"week": 3, "home_team": "CIN", "away_team": "MIN", "spread_h": 3.5,"spread_a": -3.5,"total": 42.5},
    {"week": 3, "home_team": "DEN", "away_team": "LAC", "spread_h": 2.5,"spread_a": -2.5,"total": 45.5},
    {"week": 3, "home_team": "NO", "away_team": "SEA", "spread_h": 7.5,"spread_a": -7.5,"total": 41.5},
    {"week": 3, "home_team": "ARI", "away_team": "SF", "spread_h": 1.5,"spread_a": -1.5,"total": 44.5},
    {"week": 3, "home_team": "DAL", "away_team": "CHI", "spread_h": 1.5,"spread_a": -1.5,"total": 49.5},
    {"week": 3, "home_team": "KC", "away_team": "NYG", "spread_h": -6.5,"spread_a": 6.5,"total": 44.5},
    {"week": 3, "home_team": "DET", "away_team": "BAL", "spread_h": 5.5,"spread_a": -5.5,"total": 51.5}
]
games_df = pd.DataFrame(vegas_odds_per_team)

def implied_team_totals(games_df, spread_is_home_positive = True):
    rows = []
    for r in games_df.itertuples(index=False):
        total = r.total
        spread_h = r.spread_h
        spread_a = r.spread_a

        home_total = (total - spread_h)/2.0
        away_total = total-home_total
        rows.append({
            "week": r.week,
            "team": r.home_team,
            "opponent": r.away_team,
            "is_home": True,
            "implied_team_total": home_total,
            "implied_opponent_total": away_total,
            "spread": r.spread_h,
            "game_total": total
        })
        rows.append({
            "week": r.week,
            "team": r.away_team,
            "opponent": r.home_team,
            "is_home": True,
            "implied_team_total": away_total,
            "implied_opponent_total": home_total,
            "spread": r.spread_a,
            "game_total": total
        })
    return pd.DataFrame(rows)

team_totals_df = implied_team_totals(games_df)

def normalize_name(name):
    name = name.lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", name)
    # remove punctuation
    name = re.sub(r"[^a-z\s]", "", name)
    # normalize spaces
    name = re.sub(r"\s+", " ", name).strip()
    return name

offense_positions = ["QB","RB","WR","TE"]
playerstatsdata = pd.read_csv("all_years_weekly stats.csv")
stats_df = playerstatsdata[playerstatsdata["position"].isin(offense_positions)]

active_players = stats_df[stats_df["season"]==2025]["player_id"].unique()
stats_df = stats_df[stats_df["player_id"].isin(active_players)]
stats_df['name_norm'] = stats_df["player_display_name"].apply(normalize_name)

def calc_fantasy_points(row):
    pts = 0
    pts += row["passing_yards"]/25
    pts += row["passing_tds"] *4
    pts -= row["passing_interceptions"]*2
    pts += row["rushing_yards"] /10
    pts += row["rushing_tds"] *6
    pts += row["receiving_yards"] /10
    pts += row["receiving_tds"] *6
    pts += row["receptions"] * 1
    pts -= row["receiving_fumbles"] *2
    return pts

stats_df["fantasy_pts"] = stats_df.apply(calc_fantasy_points,axis=1)

#Historical data implementation (weighted to where the recent years are taken more into consideration in projection calculation)
def weighted_history(player_id,week,stats_df):
    player_games = stats_df.query("player_id == @player_id and week < @week")

    avg_2025 = player_games.query("season == 2025")["fantasy_pts"].mean()
    avg_2024 = stats_df.query("player_id == @player_id and season == 2024")["fantasy_pts"].mean()
    avg_2023 = stats_df.query("player_id == @player_id and season == 2023")["fantasy_pts"].mean()
    avg_2022 = stats_df.query("player_id == @player_id and season == 2022")["fantasy_pts"].mean()

    if pd.isna(avg_2024) and pd.isna(avg_2023):
        return avg_2025
    
    if not pd.isna(avg_2025) and not pd.isna(avg_2024) and pd.isna(avg_2023) and pd.isna(avg_2022):
        return 0.8 * avg_2025 + 0.2 * avg_2024

    # Case 3: 3rd-year (2025 + 2024 + 2023)
    if not pd.isna(avg_2025) and not pd.isna(avg_2024) and not pd.isna(avg_2023) and pd.isna(avg_2022):
        return 0.7 * avg_2025 + 0.2 * avg_2024 + 0.1 * avg_2023

    # Case 4: 4+ years (2025 + 2024 + 2023 + 2022)
    if not pd.isna(avg_2025) and not pd.isna(avg_2024) and not pd.isna(avg_2023) and not pd.isna(avg_2022):
        return 0.65 * avg_2025 + 0.2 * avg_2024 + 0.1 * avg_2023 + 0.05 * avg_2022


def vegas_adjustment(spread,total,position):
    factor = 1
    if spread <= -7: #meaning a very large favorite, by a touchdown or more
        if position in ["QB","WR","TE"]:
            factor *= 0.85
        elif position == "RB":
            factor *= 1.1
    elif spread >= 7: #Large underdog
        if position in ["WR","TE"]:
            factor *= 1.15
        elif position == "RB":
            factor *= 0.9
        elif position == "QB":
            factor = 1
    else: #Close game (Within one touchdown)
        if position in ["QB","WR","TE"]:
            factor = 1.1
        elif position == "RB":
            factor = 1

    if total >= 47:
        factor *= 1.05
    elif total <= 42:
        factor *= 0.95
    return factor

def defensive_adjustment(team,defensive_rankings,position):
    """
    per position teams are ranked based on how many points they allowed to the opposing teams in positions
    """
    def_rank = defensive_rankings[team][position]
    factor = 1.15-(def_rank - 1 )*(0.30/31) #meaning that when they are playing the worst team *1.15, and best *0.85
    return factor


    


#weekly stats
def project_points(player_id,week, position,spread,total,opp_team,stats_df,defensive_rankings, injury_status):
    baseline = weighted_history(player_id, week, stats_df)
    if pd.isna(baseline):
        return None,None
    vegas_factor = vegas_adjustment(spread,total,position)
    defense_factor = defensive_adjustment(opp_team,defensive_rankings, position)
    if injury_status in ["OUT","INJURY_RESERVE"]:
        proj_points = 0
    else:
        proj_points = baseline * vegas_factor * defense_factor

    return proj_points, baseline

def run_projections(week, stats_df, games_df, defensive_rankings, output_csv = "weekly_projections.csv"):
    results =[]
    implied_df = implied_team_totals(games_df)



    all_players = {}
    for team in league.teams:
        for player in team.roster:
            player.name_norm = normalize_name(player.name)
            all_players[player.name_norm] = player
    for player in league.free_agents(size=200):
        player.name_norm = normalize_name(player.name)
        all_players[player.name_norm] = player



    active_players = stats_df[stats_df["season"] == 2025]["player_id"].unique()
    for _, player_info in stats_df[stats_df["season"]==2025].iterrows():
        team = player_info["team"]
        position = player_info["position"]
        name_norm = player_info["name_norm"]
        name_display = player_info["player_display_name"]

        # Lookup ESPN player for injury
        espn_player = all_players.get(name_norm, None)
        injury_status = espn_player.injuryStatus if espn_player else "ACTIVE"

        # Skip if no matchup info
        game_row = implied_df.query("week == @week and team == @team")
        if game_row.empty:
            continue

        opp_team = game_row.iloc[0]["opponent"]
        spread = game_row.iloc[0]["spread"]
        total = game_row.iloc[0]["game_total"]

        proj_points, baseline = project_points(
            player_id=player_info["player_id"],
            week=week,
            position=position,
            spread=spread,
            total=total,
            opp_team=opp_team,
            stats_df=stats_df,
            defensive_rankings=defensive_rankings,
            injury_status=injury_status
        )
        if proj_points is not None:
            results.append({
                "player_id": player_info["player_id"],
                "player_display_name": name_display,
                "team": team,
                "position": position,
                "opponent": opp_team,
                "week": week,
                "baseline": baseline,
                "projected_points": proj_points,
                "injury_status": injury_status
            })
    proj_df = pd.DataFrame(results)

    for team in proj_df["team"].unique():
        team_players = proj_df[proj_df["team"] == team]
        for position in ["QB","RB","WR","TE"]:
            injured = team_players.query("position == @position and injury_status in ['OUT','INJURY_RESERVE']")
            if not injured.empty:
                injured_pid = injured.iloc[0]["player_id"]
                candidates = stats_df.query("team == @team and position == @position and season == 2025 and player_id != @injured_pid").groupby("player_id")["fantasy_pts"].mean().sort_values(ascending = False)
                if not candidates.empty:
                    backup_id = candidates.index[0]
                    proj_df.loc[proj_df["player_id"] == backup_id,"projected_points"] *= 1.25



    proj_df.to_csv(output_csv, index = False)
    print(f"saved to {output_csv}")
    return proj_df

projections_df = run_projections(
    week = week,
    stats_df = stats_df,
    games_df = games_df,
    defensive_rankings = defensive_rankings,
    output_csv = "weekly_projections.csv"
)

export_to_gsheet(projections_df, sheet_id="1jzYYVtDsVKi5BZg9MZ8g8BXMHBLVPf_suqMcyORjdGM")
print(projections_df.head())



