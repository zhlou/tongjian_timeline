#!/usr/bin/env python3
r"""Convert \uXXXX escape sequences in JSON files to proper Unicode Chinese characters."""

import json
import os
from pathlib import Path

SOURCE_DIR = "raw_json"
OUTPUT_DIR = "raw_json_converted"

def convert_file(filepath, out_dir):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    out_path = os.path.join(out_dir, os.path.basename(filepath))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Converted: {filepath} -> {out_path}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    source_dir = Path(SOURCE_DIR)
    for f in sorted(source_dir.glob("*.json")):
        convert_file(str(f), OUTPUT_DIR)
    print(f"Done. {len(list(source_dir.glob('*.json')))} files converted to '{OUTPUT_DIR}/'")

if __name__ == "__main__":
    main()
