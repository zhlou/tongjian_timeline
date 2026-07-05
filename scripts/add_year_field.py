#!/usr/bin/env python3
"""DEPRECATED — kept as a helper library for legacy callers.

Year / ganzhi extraction is now done in ``restructure_json.py`` in the same
pass that builds year-sections. Running this script as a CLI no longer
modifies ``semantic_json/``: it just prints a deprecation notice.

This file still exposes ``CN_DIGITS``, ``parse_cn_num``, ``_RE_PAREN``,
``parse_ganzhi``, and ``parse_western`` so older code that imported them
keeps working.
"""

import json
import re
import sys
from pathlib import Path

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


def _strip_parens(value):
    if not _RE_PAREN.search(value):
        return value
    return _RE_PAREN.sub("", value).strip()


def parse_ganzhi(inner):
    """First short CJK-only token inside the parenthetical, or None."""
    if inner is None:
        return None
    for tok in re.split(r"[，,、]", inner):
        t = tok.strip().rstrip("年").strip()
        if (t and "公元" not in t and "前" not in t
            and len(t) <= 4
            and all('\u4e00' <= ch <= '\u9fff' for ch in t)):
            return t
    return None


def parse_western(inner):
    """'160 BC' / '529 AD' from a '公元前/公元 ...年' token, or None."""
    if inner is None:
        return None
    for tok in re.split(r"[，,、]", inner):
        t = tok.strip().rstrip("年").strip()
        if "前" in t:
            digits = t.replace("公元前", "").replace("前", "")
            return f"{parse_cn_num(digits)} BC"
        if t.startswith("公元"):
            return f"{parse_cn_num(t[2:])} AD"
    return None


def parse_year(era_year):
    """Legacy: return only the Western year string ('403 BC' / '529 AD')."""
    m = _RE_PAREN.search(era_year)
    inner = m.group(1) if m else None
    return parse_western(inner)


def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    for section in data.get("sections", []):
        raw = section.get("era_year", "")
        stripped = _strip_parens(raw) if raw else ""
        if not section.get("era_year") and "era_year" in section:
            section["era_year"] = stripped
        elif raw and "\uff08" in raw:
            section["era_year"] = stripped
        m = _RE_PAREN.search(raw) if raw else None
        inner = m.group(1) if m else None
        if "ganzhi" not in section:
            section["ganzhi"] = parse_ganzhi(inner)
        if "year" not in section:
            section["year"] = parse_western(inner)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    print(
        "ERROR: scripts/add_year_field.py is no longer needed.\n"
        "       `python scripts/restructure_json.py` now writes `year`,\n"
        "       `ganzhi`, and paren-stripped `era_year` in a single pass.\n"
        "Pass --apply to legacy-fill any files missing ganzhi/year.",
        file=sys.stderr,
    )
    if "--apply" not in sys.argv:
        return 1
    sem_dir = Path("semantic_json")
    files = sorted(sem_dir.glob("*.json"))
    success = 0
    for f in files:
        try:
            process_file(str(f))
            success += 1
        except Exception as e:
            print(f"ERROR: {f.name}  {e}", file=sys.stderr)
    print(f"Processed: {success} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())

