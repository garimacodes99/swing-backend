from pathlib import Path
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

CLOSE_DIR = PROJECT_ROOT / "frontend" / "public" / "close"
INDEX_PATH = CLOSE_DIR / "index.json"


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0


def update_index(run_date: str) -> None:
    CLOSE_DIR.mkdir(parents=True, exist_ok=True)

    if INDEX_PATH.exists():
        try:
            index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index = {"latest": None, "generated_at": None, "dates": []}
    else:
        index = {"latest": None, "generated_at": None, "dates": []}

    file_name = f"swing_close_{run_date}.json"
    file_path = f"/close/{file_name}"
    full_path = CLOSE_DIR / file_name

    rows = count_rows(full_path)

    index["dates"] = [
        entry for entry in index.get("dates", [])
        if entry.get("date") != run_date
    ]

    index["dates"].append(
        {
            "date": run_date,
            "file": file_path,
            "rows": rows,
        }
    )

    index["dates"] = sorted(
        index["dates"],
        key=lambda item: item["date"],
        reverse=True
    )

    index["latest"] = index["dates"][0]["date"] if index["dates"] else None
    index["generated_at"] = datetime.now().isoformat(timespec="seconds")

    INDEX_PATH.write_text(
        json.dumps(index, indent=2),
        encoding="utf-8"
    )

    logger.info("Index updated for %s | rows=%s", run_date, rows)