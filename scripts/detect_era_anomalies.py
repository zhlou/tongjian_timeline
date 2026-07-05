#!/usr/bin/env python3
"""Detect sections where era_year decreases (or resets to 元年) while era_name
stays the same — a signal that the era boundary was missed in the raw data."""

import json
import sys
from pathlib import Path

CN_DIGITS = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "百": 100, "千": 1000, "万": 10000,
}

SEMANTIC_DIR = "semantic_json"


def parse_cn_year(cn_str):
    if not cn_str:
        return None
    stripped = cn_str.rstrip("年")
    if not stripped:
        return None
    if stripped == "元":
        return 1
    result = 0
    section_val = 0
    for ch in stripped:
        if ch in CN_DIGITS and CN_DIGITS[ch] >= 10:
            if section_val == 0:
                section_val = 1
            section_val *= CN_DIGITS[ch]
            result += section_val
            section_val = 0
        elif ch in CN_DIGITS:
            section_val = CN_DIGITS[ch]
        else:
            return None
    result += section_val
    return result if result else None


def detect_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    issues = []
    sections = data.get("sections", [])
    current_era = None
    prev_year_str = None
    prev_year_num = None

    for i, sec in enumerate(sections):
        era_name = sec.get("era_name", "")
        era_year = sec.get("era_year", "")
        year_num = parse_cn_year(era_year)

        if era_name == current_era and prev_year_num is not None and year_num is not None:
            if year_num < prev_year_num:
                issues.append({
                    "section_index": i,
                    "era_name": era_name,
                    "prev_era_year": prev_year_str,
                    "curr_era_year": era_year,
                    "ganzhi": sec.get("ganzhi"),
                    "year": sec.get("year"),
                    "volume_name": data.get("volume_name", ""),
                })

        if era_name != current_era:
            current_era = era_name
        prev_year_num = year_num
        prev_year_str = era_year

    return issues


def main():
    base = Path(SEMANTIC_DIR)
    files = sorted(base.glob("*.json"))
    total_issues = 0

    for fp in files:
        issues = detect_file(str(fp))
        for issue in issues:
            total_issues += 1
            print(
                f"{fp.name} section[{issue['section_index']}] "
                f"│ {issue['volume_name']} │ "
                f"era={issue['era_name']!r}  "
                f"{issue['prev_era_year']!r} → {issue['curr_era_year']!r}  "
                f"({issue['ganzhi']} / {issue['year']})"
            )

    print(f"\nTotal: {total_issues} issue(s) across {len(files)} files")
    return 1 if total_issues else 0


if __name__ == "__main__":
    sys.exit(main())
