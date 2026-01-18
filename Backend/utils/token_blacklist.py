import json
from pathlib import Path

BLACKLIST_PATH = Path("data/blacklist.json")

def _load_blacklist():
    if BLACKLIST_PATH.exists():
        try:
            with open(BLACKLIST_PATH, "r") as f:
                data = json.load(f)
                return set(data.get("tokens", []))
        except:
            return set()
    return set()

def _save_blacklist(tokens):
    BLACKLIST_PATH.parent.mkdir(exist_ok=True)
    with open(BLACKLIST_PATH, "w") as f:
        json.dump({"tokens": list(tokens)}, f, indent=4)

blacklisted_tokens = _load_blacklist()

def blacklist_token(token: str):
    blacklisted_tokens.add(token)
    _save_blacklist(blacklisted_tokens)

def is_token_blacklisted(token: str) -> bool:
    return token in blacklisted_tokens
