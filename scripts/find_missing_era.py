#!/usr/bin/env python3
"""Find all year-sections with missing era_name or era_year."""

import json
from pathlib import Path

SEM_DIR = "semantic_json"


def main():
    sem_dir = Path(SEM_DIR)
    files = sorted(sem_dir.glob("*.json"))
    found = 0

    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for i, section in enumerate(data.get("sections", [])):
            if not section.get("era_name") or not section.get("era_year"):
                found += 1
                name = data.get("volume_name", "").strip()
                print(f"{f.name}  section[{i}]: era_name='{section.get('era_name', '')}'  era_year='{section.get('era_year', '')}'  texts={len(section.get('texts', []))}  volume={name}")

    print(f"\n{found} section(s) with missing era_name or era_year across {len(files)} files.")


if __name__ == "__main__":
    main()
