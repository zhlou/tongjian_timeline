#!/usr/bin/env python3
"""Parse era_year into a human-readable year string and add as "year" field.

e.g. "二十三年（戊寅，公元前四零三年）" -> "403 BC"
     "中大通元年（己酉，公元五二九年）"   -> "529 AD"
"""

import json
import re
from pathlib import Path

SEM_DIR = "semantic_json"

CN_DIGITS = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}

_RE_PAREN = re.compile(r"[\uff08(](.+)[\uff09)]年?$")


def parse_cn_num(cn_str):
    """Convert a Chinese digit string like '四零三' to integer 403."""
    result = 0
    for ch in cn_str:
        if ch in CN_DIGITS:
            result = result * 10 + CN_DIGITS[ch]
    return result


def parse_year(era_year):
    """Extract e.g. '403 BC' or '529 AD' from an era_year string."""
    m = _RE_PAREN.search(era_year)
    if not m:
        return None
    inner = m.group(1)

    # split on comma or ideographic comma
    parts = re.split(r"[，,、]", inner)
    if len(parts) < 2:
        return None
    year_part = parts[1].strip()

    if "前" in year_part:
        year_part = year_part.replace("公元前", "").replace("前", "")
        if year_part.endswith("年"):
            year_part = year_part[:-1]
        n = parse_cn_num(year_part)
        return f"{n} BC"
    elif year_part.startswith("公元"):
        digits = year_part[2:-1] if year_part.endswith("年") else year_part[2:]
        n = parse_cn_num(digits)
        return f"{n} AD"
    return None


def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    for section in data.get("sections", []):
        era = section.get("era_year", "")
        year = parse_year(era) if era else None
        section["year"] = year

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    sem_dir = Path(SEM_DIR)
    files = sorted(sem_dir.glob("*.json"))
    success = 0
    fail = 0

    for f in files:
        try:
            process_file(str(f))
            success += 1
        except Exception as e:
            print(f"ERROR: {f.name}  {e}")
            fail += 1

    print(f"Processed: {success} files")
    if fail:
        print(f"Errors: {fail} files")


if __name__ == "__main__":
    main()
