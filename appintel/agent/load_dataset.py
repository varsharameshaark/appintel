import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "apps.json"

def load_apps():
    with DATA_PATH.open("r", encoding="utf-8") as file:
        apps = json.load(file)
    if len(apps) != 100:
        raise ValueError(f"Expected 100 apps, found {len(apps)}")
    ids = [app["id"] for app in apps]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate application IDs found")
    return apps

if __name__ == "__main__":
    apps = load_apps()
    print(f"Loaded {len(apps)} applications.")
    for app in apps[:5]:
        print(f'{app["id"]:>3}. {app["name"]} — {app["category"]}')
