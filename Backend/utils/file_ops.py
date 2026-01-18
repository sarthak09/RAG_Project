import json
from pathlib import Path

DB_DIR = Path("data")
DB_PATH = DB_DIR / "users.json"

def init_storage():
    """Ensure data folder and JSON exist."""
    DB_DIR.mkdir(exist_ok=True)
    if not DB_PATH.exists():
        with open(DB_PATH, "w") as f:
            json.dump({"users": []}, f, indent=4)

def load_users():
    init_storage()
    try:
        with open(DB_PATH, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Corrupted users.json – recreating file.")
        save_users({"users": []})
        return {"users": []}

def save_users(data):
    init_storage()
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=4)
