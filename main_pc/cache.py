import json
from pathlib import Path

CACHE_FILE = Path(__file__).parent / "cache.json"
CYCLE_HISTORY_FILE = Path(__file__).parent / "cycle_history.json"

def load_resources():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_resources(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def load_cycle_history():
    if CYCLE_HISTORY_FILE.exists():
        with open(CYCLE_HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def get_recent_cycle_history(limit=3):
    history = load_cycle_history()
    return history[-limit:]

def save_cycle_history(data):
    with open(CYCLE_HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

# history has max of 10 entries(for now...)
def add_cycle_report(cycle_report):
    history = load_cycle_history()
    history.append(cycle_report)
    if len(history) > 10:
        history.pop(0)
    save_cycle_history(history)
