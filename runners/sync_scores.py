import pandas as pd
from pathlib import Path
import os

def sync_excel_to_json():

    # Gets the root directory (swing_trading_engine)
    base_path = Path(__file__).parent.parent

    # Main scores excel
    excel_path = base_path / 'frontend' / 'public' / 'data' / 'final_score list.xlsx'

    # Tags CSV
    tags_path = base_path / 'universe' / 'tags.csv'

    # Final JSON output
    json_path = base_path / 'frontend' / 'public' / 'data' / 'scores.json'

    print(f"🔍 Searching for Excel at: {excel_path}")

    if excel_path.exists():

        # Read score excel
        scores_df = pd.read_excel(excel_path)
        print(scores_df.columns)

        # Read tags csv
        tags_df = pd.read_csv(tags_path)

        # Clean ticker format
        scores_df["Tickers"] = scores_df["Tickers"].str.strip().str.upper()
 
        tags_df["Tickers"] = tags_df["Tickers"].str.strip().str.upper()

        # Rename columns
        scores_df = scores_df.rename(columns={
            "Tickers": "ticker"
        })

        tags_df = tags_df.rename(columns={
            "Tickers": "ticker",
            "TAG": "tags"
        })

        # Merge
        scores_df = scores_df.merge(
            tags_df[["ticker", "tags"]],
            on="ticker",
            how="left"
        )
        
        scores_df["tags"] = scores_df["tags"].fillna("")

        # Convert to JSON
        scores_df.to_json(json_path, orient='records', indent=4)

        print(f"✅ SUCCESS: {len(scores_df)} stocks synced with tags!")

    else:
        print(f"❌ ERROR: 'final_score list.xlsx' is not in the data folder!")

        # Debugging folder contents
        data_dir = base_path / 'frontend' / 'public' / 'data'

        if data_dir.exists():
            print(f"📂 Folder contents of {data_dir}:")
            print(os.listdir(data_dir))

if __name__ == "__main__":
    sync_excel_to_json()