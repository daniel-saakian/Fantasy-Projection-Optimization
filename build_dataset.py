import pandas as pd
import os

def build_dataset(raw_folder = "/Users/danielsaakian/Desktop/raw_data", output_file = "all_years_weekly stats.csv"):
    all_data = []
    for filename in os.listdir(raw_folder):
        if filename.endswith(".csv"):
            filepath = os.path.join(raw_folder,filename)
            print(f"Loading {filepath}...")
            dataframe = pd.read_csv(filepath)

            required_cols = ["season", "week", "player_id", "player_display_name","team", "opponent_team","position"]
            for col in required_cols:
                if col not in dataframe.columns:
                    raise ValueError(f"Missing Column: {col} in {filename}")
            stat_cols = [
                "passing_yards", "passing_tds", "passing_interceptions",
                "rushing_yards", "rushing_tds", "rushing_fumbles",
                "receiving_yards", "receiving_tds", "receptions",
                "receiving_fumbles", "carries", "targets"
            ]
            for col in stat_cols:
                grouped = (
                    dataframe.groupby(
                        ["season","week","player_id","player_display_name","team","opponent_team", "position"],
                        as_index = False
                    )[stat_cols]
                    .sum()
                )
                
                all_data.append(grouped)
    full_data = pd.concat(all_data, ignore_index=True)
    cols = ["player_display_name","player_id","season","week","team", "opponent_team","position"] +stat_cols
    full_data = full_data[cols]

    full_data.to_csv(output_file,index=False)
    print("dataset saved to export file")

if __name__ == "__main__":
    dataset = build_dataset()