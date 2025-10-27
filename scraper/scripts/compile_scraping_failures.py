import json
import glob
import os

config_dir = "config"
output_file = "unscraped_list.json"

unscraped = []

for path in glob.glob(os.path.join(config_dir, "scraper_*.json")):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both single object or list of objects
    if isinstance(data, dict):
        data = [data]

    for obj in data:
        if not obj.get("scraped", True):
            unscraped.append({
                "name": obj.get("name"),
                "url": obj.get("url")
            })

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(unscraped, f, indent=2, ensure_ascii=False)

print(f"Found {len(unscraped)} unscraped entries. Saved to {output_file}.")
