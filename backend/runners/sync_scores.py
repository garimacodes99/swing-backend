import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

EXCEL_FILE = BASE_DIR / "universe" / "final_score list.xlsx"
TAGS_FILE = BASE_DIR / "universe" / "tags.csv"
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


def sync_excel_to_json() -> None:
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(f"Excel file not found: {EXCEL_FILE}")

    if not TAGS_FILE.exists():
        raise FileNotFoundError(f"Tags file not found: {TAGS_FILE}")

    scores_df = pd.read_excel(EXCEL_FILE)
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

    print(f"Sync completed successfully. Rows written: {len(final_df)}")
    print(f"Output: {OUTPUT_JSON}")


if __name__ == "__main__":
    sync_excel_to_json()