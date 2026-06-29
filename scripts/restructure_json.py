#!/usr/bin/env python3
"""Convert flat name/text JSON into semantic year-section grouped JSON."""

import json
import os
from pathlib import Path

SOURCE_DIR = "raw_json_converted"
OUTPUT_DIR = "semantic_json"


def group_blocks(blocks):
    volume = {}
    sections = []

    state_name = None
    state_year = None
    state_texts = []

    def flush():
        nonlocal state_name, state_year, state_texts
        if state_texts:
            sections.append({
                "era_name": state_name or "",
                "era_year": state_year or "",
                "texts": state_texts
            })
        state_name = None
        state_year = None
        state_texts = []

    for block in blocks:
        names = {obj["name"] for obj in block}
        if "vol_name" in names:
            for obj in block:
                if obj["name"] == "vol_name":
                    volume["volume_name"] = obj["text"]
                elif obj["name"] == "vol_time_cycle":
                    volume["volume_time_cycle"] = obj["text"]
        elif "time_era_name" in names:
            flush()
            for obj in block:
                if obj["name"] == "time_era_name":
                    state_name = obj["text"]
                elif obj["name"] == "time_era_year":
                    state_year = obj["text"]
        elif "main_text" in names:
            state_texts.append(block[0]["text"])

    flush()
    return {
        "volume_name": volume.get("volume_name", ""),
        "volume_time_cycle": volume.get("volume_time_cycle", ""),
        "sections": sections
    }


def convert_file(filepath, out_dir):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    grouped = group_blocks(data)
    out_path = os.path.join(out_dir, os.path.basename(filepath))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)
    count = len(grouped["sections"])
    print(f"Converted: {filepath} -> {out_path} ({count} year-sections)")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    source_dir = Path(SOURCE_DIR)
    files = sorted(source_dir.glob("*.json"))
    for f in files:
        convert_file(str(f), OUTPUT_DIR)
    print(f"\nDone. {len(files)} files converted to '{OUTPUT_DIR}/'")


if __name__ == "__main__":
    main()
