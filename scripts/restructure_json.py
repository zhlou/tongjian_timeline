#!/usr/bin/env python3
"""Convert flat name/text JSON into semantic year-section grouped JSON.

Also extracts ganzhi (天干地支) and Western year from the parenthetical in
``era_year`` and strips the parenthetical, plus cleans up volume_name and
volume_time_cycle (strips brackets, fixes encoding corruptions).
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

# Encoding corruptions in volume_time_cycle mapped to correct characters.
TIME_CYCLE_FIXES = {
    "]": "\u9ed3",                # ASCII ]  → 黓  (玄黓, celestial stem for 壬)
    "\u2237": "\u6d92",           # ∷       → 涒  (涒滩, earthly branch for 申)
    "\u3108\u7a1a\u8f8f": "",    # ㄈ稚辏   → (delete, stray corruption in file 152)
    "\u7600\u9022": "\u960f\u9022",   # 瘀逢 (file 016, 061) → 阏逢 (甲 stem)
    "\u6691\u7ef4": "\u5c60\u7ef4",   # 暑维 (file 050) → 屠维 (己 stem)
    "\u5f3a\u56f4": "\u5f3a\u5709",   # 强围 (file 068) → 强圉 (丁 stem)
    "\u5f3a\u56fe": "\u5f3a\u5709",   # 强图 (file 110) → 强圉
    "\u5f3a\u960f": "\u5f3a\u5709",   # 强阏 (files 050, 169) → 强圉
    "\u76ee\u7ae0": "\u4e0a\u7ae0",   # 目章 (file 013) → 上章 (庚 stem)
    "\u65c3\u8499\u5355\u7600": "\u65c3\u8499\u5355\u960f",  # 旃蒙单瘀 (file 290)
    "\u8d64\u5907\u82e5": "\u8d64\u594b\u82e5",  # 赤备若 → 赤奋若 (丑 branch)
    "\u592a\u6e0a\u732e": "\u5927\u6e0a\u732e",  # 太渊献 → 大渊献 (亥 branch)
    "\u8d75\u67d4\u5146": "\u8d77\u67d4\u5146",  # 赵柔兆 → 起柔兆 (file 138)
    "\u8da3\u662d\u9633": "\u8d77\u662d\u9633",  # 趣昭阳 → 起昭阳 (file 201)
}

# Characters unlikely to appear in sane volume_time_cycle; warn on any match.
WARN_CHARS = re.compile(r"[^\u4e00-\u9fff\uff0c\u3001\u3002\uff1a\u300a\u300b"
                        r"\uff08\uff09\u2014\u4e00\u2014\u4e5d\uff0e\u5e74 "
                        r"\u201c\u201d\u00b7\.]")

_RE_BRACKETS = re.compile(r"[\u3010\u3011]")
_RE_DOT_PREFIX = re.compile(r"^\u25ce")  # ◎ prefix on merged vol_name+time_cycle


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


_RULER_KW = {"\u738b", "\u5e1d", "\u7687", "\u540e", "\u5b97", "\u7956"}  # 王帝皇后宗祖
_SENTENCE_PUNCT = {"\u3002", "\uff0c", "\u3001", "\uff1b", "\uff1a", "\uff1f", "\uff01"}  # 。，、；：？！


def _is_ruler_name(text):
    if not (2 <= len(text) <= 8):
        return False
    if not any(kw in text for kw in _RULER_KW):
        return False
    if any(p in text for p in _SENTENCE_PUNCT):
        return False
    return True


def clean_volume_name(raw):
    return _RE_BRACKETS.sub("", raw).strip()


def clean_volume_time_cycle(raw, file_index):
    result = raw
    for bad, good in TIME_CYCLE_FIXES.items():
        result = result.replace(bad, good)

    stray = WARN_CHARS.findall(result)
    if stray:
        print(f"WARNING [{file_index}]: stray chars in volume_time_cycle: {set(stray)}")

    return result


def group_blocks(blocks):
    volume = {}
    sections = []

    state_name = None
    state_year_raw = None
    state_year = None
    state_ganzhi = None
    state_year_str = None
    state_texts = []
    pending_era_name = None

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

    for i, block in enumerate(blocks):
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
                    if pending_era_name:
                        state_name = pending_era_name
                    else:
                        state_name = obj["text"]
                elif obj["name"] == "time_era_year":
                    state_year_raw = obj["text"]
                    state_year, state_ganzhi, state_year_str = extract_era_year_fields(state_year_raw)
        elif "main_text" in names:
            text = block[0]["text"]
            if (len(block) == 1 and _is_ruler_name(text)
                    and i + 1 < len(blocks)
                    and "time_era_name" in {obj["name"] for obj in blocks[i + 1]}):
                flush()
                pending_era_name = text
            else:
                state_texts.append(text)

    flush()
    return {
        "volume_name": volume.get("volume_name", ""),
        "volume_time_cycle": volume.get("volume_time_cycle", ""),
        "sections": sections
    }


def convert_file(filepath, out_dir):
    file_index = os.path.splitext(os.path.basename(filepath))[0]
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    grouped = group_blocks(data)

    grouped["volume_name"] = clean_volume_name(grouped.get("volume_name", ""))

    cycle = grouped.get("volume_time_cycle", "")
    if cycle.startswith("\u25ce"):
        idx = cycle.find("\u8d77")
        if idx > 0:
            grouped["volume_name"] = cycle[1:idx]
            cycle = cycle[idx:]
        else:
            cycle = cycle

    grouped["volume_time_cycle"] = clean_volume_time_cycle(cycle, file_index)

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
