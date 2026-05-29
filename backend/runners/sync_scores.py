import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

CSV_FILE = BASE_DIR / "universe" / "final_score list.csv"
TAGS_FILE = BASE_DIR / "universe" / "tags.csv"
UNIVERSE_FILE = BASE_DIR / "universe" / "stock_universe.csv"
OUTPUT_JSON = PROJECT_ROOT / "frontend" / "public" / "data" / "scores.json"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    df = df.loc[:, ~df.columns.str.startswith("unnamed")]
    return df


def get_first_existing_column(df: pd.DataFrame, candidates: list[str], label: str) -> str:
    for column in candidates:
        if column in df.columns:
            return column
    raise KeyError(f"Missing required {label} column. Found: {df.columns.tolist()}")


def get_original_ticker_column(df: pd.DataFrame) -> str:
    candidates = ["tickers", "ticker", "symbol"]
    normalized_cols = [str(col).strip().lower() for col in df.columns]
    for col, norm_col in zip(df.columns, normalized_cols):
        if norm_col in candidates:
            return col
    raise KeyError(f"Missing required ticker column. Found: {df.columns.tolist()}")


def clean_csv_by_tickers(file_path: Path, valid_tickers: set, name: str) -> None:
    if not file_path.exists():
        print(f"Skipping {name} clean up - file not found: {file_path}")
        return
        
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    initial_len = len(df)
    
    try:
        ticker_col = get_original_ticker_column(df)
    except KeyError:
        print(f"Skipping {name} clean up - no ticker column found.")
        return
        
    is_valid = df[ticker_col].astype(str).str.strip().str.upper().isin(valid_tickers)
    df_filtered = df[is_valid]
    
    removed_count = initial_len - len(df_filtered)
    
    df_filtered.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"Cleaned {name}:\tRemoved {removed_count} rows \t Kept {len(df_filtered)} rows.")


def sync_csv_to_json() -> None:
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"CSV file not found: {CSV_FILE}")

    scores_df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    
    try:
        score_ticker_col_orig = get_original_ticker_column(scores_df)
        valid_tickers = set(
            scores_df[score_ticker_col_orig].astype(str).str.strip().str.upper()
        )
        print(f"Loaded {len(valid_tickers)} valid tickers from final_score list.csv")
    except KeyError:
        valid_tickers = set()
        print("Warning: Could not find ticker column in final_score list.csv")

    clean_csv_by_tickers(UNIVERSE_FILE, valid_tickers, "stock_universe.csv")
    
    if TAGS_FILE.exists():
        clean_csv_by_tickers(TAGS_FILE, valid_tickers, "tags.csv")
    else:
        raise FileNotFoundError(f"Tags file not found: {TAGS_FILE}")

    tags_df = pd.read_csv(TAGS_FILE, encoding="utf-8-sig")

    scores_df = normalize_columns(scores_df)
    tags_df = normalize_columns(tags_df)

    score_ticker_col = get_first_existing_column(
        scores_df,
        ["tickers", "ticker", "symbol"],
        "ticker"
    )
    tag_ticker_col = get_first_existing_column(
        tags_df,
        ["tickers", "ticker", "symbol"],
        "ticker"
    )
    tag_value_col = get_first_existing_column(
        tags_df,
        ["tag", "tags"],
        "tag"
    )

    scores_df[score_ticker_col] = (
        scores_df[score_ticker_col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    tags_df[tag_ticker_col] = (
        tags_df[tag_ticker_col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    scores_df = scores_df.rename(columns={score_ticker_col: "ticker"})
    tags_df = tags_df.rename(
        columns={
            tag_ticker_col: "ticker",
            tag_value_col: "tags",
        }
    )

    final_df = scores_df.merge(
        tags_df[["ticker", "tags"]],
        on="ticker",
        how="left"
    )

    final_df["tags"] = final_df["tags"].fillna("")

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    final_df.to_json(
        OUTPUT_JSON,
        orient="records",
        indent=4,
        force_ascii=False
    )

    print(f"Sync completed successfully. Output rows: {len(final_df)}")
    print(f"Output: {OUTPUT_JSON}")


if __name__ == "__main__":
    sync_csv_to_json()