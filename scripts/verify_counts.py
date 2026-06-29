#!/usr/bin/env python3
"""Verify that no main_text entries were lost during restructure."""

import json
from pathlib import Path

RAW_DIR = "raw_json_converted"
SEM_DIR = "semantic_json"


def count_raw(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return sum(1 for block in data if any(obj["name"] == "main_text" for obj in block))


def count_semantic(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return sum(len(s["texts"]) for s in data.get("sections", []))


def main():
    raw_dir = Path(RAW_DIR)
    sem_dir = Path(SEM_DIR)
    files = sorted(raw_dir.glob("*.json"))
    raw_total = 0
    sem_total = 0
    mismatches = 0

    for f in files:
        sem_path = sem_dir / f.name
        if not sem_path.exists():
            print(f"MISSING: {sem_path}")
            continue
        rc = count_raw(str(f))
        sc = count_semantic(str(sem_path))
        raw_total += rc
        sem_total += sc
        if rc != sc:
            mismatches += 1
            print(f"MISMATCH: {f.name}  raw={rc}  sem={sc}")

    print(f"\nGrand total: raw={raw_total}  sem={sem_total}")
    if mismatches:
        print(f"ERROR: {mismatches} file(s) have mismatched counts!")
    else:
        print(f"OK: all {len(files)} files match.")


if __name__ == "__main__":
    main()
