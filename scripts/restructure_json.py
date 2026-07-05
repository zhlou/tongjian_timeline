#!/usr/bin/env python3
"""Convert flat name/text JSON into semantic year-section grouped JSON.

Also extracts ganzhi (天干地支) and Western year from the parenthetical in
``era_year`` and strips the parenthetical. Runs the parse step that the
older ``add_year_field.py`` used to do as a post-pass.
"""

import json
import os
import re
from pathlib import Path

SOURCE_DIR = "raw_json_converted"
OUTPUT_DIR = "semantic_json"

CN_DIGITS = {
    "\u96f6": 0, "\u4e00": 1, "\u4e8c": 2, "\u4e09": 3, "\u56db": 4,
    "\u4e94": 5, "\u516d": 6, "\u4e03": 7, "\u516b": 8, "\u4e5d": 9,
}

_RE_PAREN = re.compile(r"[\uff08(](.+)[\uff09)]\u5e74?$")


def parse_cn_num(cn_str):
    result = 0
    for ch in cn_str:
        if ch in CN_DIGITS:
            result = result * 10 + CN_DIGITS[ch]
    return result


def _strip_parens(value):
    """Remove a trailing parenthetical like '\uff08\u620a\u5bc5\uff09' from value."""
    if not _RE_PAREN.search(value):
        return value
    return _RE_PAREN.sub("", value).strip()


def parse_ganzhi(inner):
    """First short CJK-only token inside the parenthetical, or None."""
    if inner is None:
        return None
    for tok in re.split(r"[\uff0c,\u3001]", inner):
        t = tok.strip().rstrip("\u5e74").strip()
        if (t and "\u516c\u5143" not in t and "\u524d" not in t
            and len(t) <= 4
            and all('\u4e00' <= ch <= '\u9fff' for ch in t)):
            return t
    return None


def parse_western(inner):
    """'160 BC' / '529 AD' from a '公元前/公元 ...年' token, or None."""
    if inner is None:
        return None
    for tok in re.split(r"[\uff0c,\u3001]", inner):
        t = tok.strip().rstrip("\u5e74").strip()
        if "\u524d" in t:
            digits = t.replace("\u516c\u5143\u524d", "").replace("\u524d", "")
            return f"{parse_cn_num(digits)} BC"
        if t.startswith("\u516c\u5143"):
            return f"{parse_cn_num(t[2:])} AD"
    return None


def extract_era_year_fields(raw):
    """Return (stripped_era_year, ganzhi, year_str) from a raw era_year string."""
    stripped = _strip_parens(raw)
    m = _RE_PAREN.search(raw)
    inner = m.group(1) if m else None
    return stripped, parse_ganzhi(inner), parse_western(inner)


def group_blocks(blocks):
    volume = {}
    sections = []

    state_name = None
    state_year_raw = None
    state_year = None
    state_ganzhi = None
    state_year_str = None
    state_texts = []

    def flush():
        nonlocal state_name, state_year_raw, state_year, state_ganzhi
        nonlocal state_year_str, state_texts
        if state_texts:
            sections.append({
                "era_name": state_name or "",
                "era_year": state_year or "",
                "ganzhi": state_ganzhi,
                "year": state_year_str,
                "texts": state_texts,
            })
        state_name = None
        state_year_raw = None
        state_year = None
        state_ganzhi = None
        state_year_str = None
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
                    state_year_raw = obj["text"]
                    state_year, state_ganzhi, state_year_str = extract_era_year_fields(state_year_raw)
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
        f.write("\n")
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
