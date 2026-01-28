"""
INDEX BUILDER (CLOSE ONLY)
-------------------------
Single source of truth for CLOSE snapshots.
"""

from pathlib import Path
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

INDEX_PATH = Path("frontend/public/data/index.json")
CLOSE_DIR = Path("frontend/public/data/close")

def count_rows(path: Path) -> int:
    try:
        with open(path, "r") as f:
            return len(json.load(f))
    except Exception:
        return 0

def update_index(run_date: str):

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    if INDEX_PATH.exists():
        index = json.loads(INDEX_PATH.read_text())
    else:
        index = {
            "latest": None,
            "generated_at": None,
            "dates": []
        }

    file_name = f"swing_close_{run_date}.json"
    file_path = f"data/close/{file_name}"
    full_path = CLOSE_DIR / file_name

    rows = count_rows(full_path)

    index["dates"] = [
        d for d in index["dates"] if d["date"] != run_date
    ]

    index["dates"].append({
        "date": run_date,
        "file": file_path,
        "rows": rows
    })

    index["dates"] = sorted(
        index["dates"], key=lambda x: x["date"], reverse=True
    )

    index["latest"] = index["dates"][0]["date"]
    index["generated_at"] = datetime.now().isoformat(timespec="seconds")

    INDEX_PATH.write_text(json.dumps(index, indent=2))
    log.info(f"[INDEX] Updated | {run_date} | Rows={rows}")
