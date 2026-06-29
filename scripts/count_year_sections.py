#!/usr/bin/env python3
"""Count year sections in each semantic_json file."""

import json
from pathlib import Path

SEM_DIR = "semantic_json"


def count_sections(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return len(data.get("sections", []))


def main():
    sem_dir = Path(SEM_DIR)
    files = sorted(sem_dir.glob("*.json"))
    total = 0

    for f in files:
        n = count_sections(str(f))
        total += n
        print(f"{f.name}  {n}")

    print(f"\nTotal files: {len(files)}")
    print(f"Total year sections: {total}")


if __name__ == "__main__":
    main()
