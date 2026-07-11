#!/usr/bin/env python3
"""
Fix multi-character moji-bake patterns in raw_json_converted/.

Detects cases where a CJK radical + phonetic component got split into two
characters (e.g. "纟林" → "綝", "钅句" → "钩").  Uses the epub as a
reference to confirm the correct single-character form.

Only fixes patterns where the first character is a CJK radical — these are
virtually never legitimate in running classical Chinese text.

Usage:
    python scripts/fix_multi_char_mojibake.py [--dry-run]
    python scripts/fix_multi_char_mojibake.py --review  # show all proposed fixes
"""

import json
import os
import re
import sys
import argparse
import difflib
from collections import defaultdict

from opencc import OpenCC

EPUB_DIR = "epub_text"
SOURCE_DIR = "raw_json_converted"

# ── CJK radicals that should NOT appear standalone in running text ──────────

_RADICAL_SET = set(
    "\u7e9f\u9963\u9485\u8ba0\u5fc4\u624c\u793b\u4ebb\u5f73"
    "\u961d\u6c75\u706c\u8279\u51ab\u8fb6\u5ef4\u5369\u5202"
)

# ── helpers ────────────────────────────────────────────────────────────────

_CJK_PUNCT = set(
    "\uff0c\u3002\u3001\uff1b\uff1a\uff01\uff1f\u201c\u201d\u2018\u2019"
    "\u300a\u300b\u3008\u3009\u300c\u300d\u300e\u300f"
    "\u3010\u3011\uff08\uff09\u2014\u2026\uff5e\u00b7"
    "\u3000"
)
_ASCII_WS = set(" \n\r\t")


def _normalize(text):
    result = []
    for ch in text:
        if ch in _CJK_PUNCT or ch in _ASCII_WS:
            continue
        result.append(ch)
    return "".join(result)


def _build_para_index(paragraphs):
    norm, mapping = [], []
    for pi, para in enumerate(paragraphs):
        for ci, ch in enumerate(para):
            if ch not in _CJK_PUNCT and ch not in _ASCII_WS:
                norm.append(ch)
                mapping.append((pi, ci))
    return "".join(norm), mapping


def _load_epub_text(num):
    path = os.path.join(EPUB_DIR, f"{num:03d}.txt")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def _load_our_paragraphs(num):
    path = os.path.join(SOURCE_DIR, f"{num:03d}.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    paragraphs = []
    for group in data:
        for obj in group:
            if obj["name"] == "main_text":
                paragraphs.append(obj["text"])
    return paragraphs


def _add_multi_fix(corrections, norm_start, n2o, old_text, new_text):
    if norm_start < len(n2o):
        pi, ci = n2o[norm_start]
        corrections.append({
            "para_idx": pi, "char_idx": ci,
            "old": old_text, "new": new_text,
        })


def find_multi_char_fixes(volume_num, cc):
    epub_text = _load_epub_text(volume_num)
    if epub_text is None:
        return []

    our_paras = _load_our_paragraphs(volume_num)
    if not our_paras:
        return []

    epub_simp = cc.convert(epub_text)
    e_norm = _normalize(epub_simp)
    o_norm, n2o = _build_para_index(our_paras)
    if not o_norm:
        return []

    matcher = difflib.SequenceMatcher(None, e_norm, o_norm, autojunk=False)
    blocks = matcher.get_matching_blocks()

    corrections = []

    for bi in range(len(blocks) - 1):
        b1, b2 = blocks[bi], blocks[bi + 1]
        es, ee = b1.a + b1.size, b2.a
        os_, oe_ = b1.b + b1.size, b2.b
        if es >= ee and os_ >= oe_:
            continue
        e_seg = e_norm[es:ee]
        o_seg = o_norm[os_:oe_]
        if not e_seg and not o_seg:
            continue

        # Only fix: our side has N (2-3) chars, epub side has 1 char
        # AND the first char of our segment is a CJK radical
        if len(o_seg) in (2, 3) and len(e_seg) == 1:
            if o_seg[0] in _RADICAL_SET:
                # Relaxed context check: at least 2 chars of context match on each side
                ctx_before_e = e_norm[max(0, es - 3):es]
                ctx_after_e = e_norm[ee:ee + 3]
                ctx_before_o = o_norm[max(0, os_ - 3):os_]
                ctx_after_o = o_norm[oe_:oe_ + 3]
                if (ctx_before_e == ctx_before_o and ctx_after_e == ctx_after_o) or \
                   (len(ctx_before_e) >= 2 and ctx_before_e == ctx_before_o):
                    _add_multi_fix(corrections, os_, n2o, o_seg, e_seg)

    return corrections


def apply_corrections(filepath, corrections, dry_run=False):
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    text_refs = []
    for gi, group in enumerate(data):
        for oi, obj in enumerate(group):
            if obj["name"] == "main_text":
                text_refs.append((gi, oi, obj))

    by_para = defaultdict(list)
    for c in corrections:
        by_para[c["para_idx"]].append(c)

    changes = 0
    for para_idx, corrs in sorted(by_para.items()):
        if para_idx >= len(text_refs):
            continue
        _, _, obj = text_refs[para_idx]
        text = obj["text"]
        for c in sorted(corrs, key=lambda x: x["char_idx"], reverse=True):
            ci = c["char_idx"]
            old, new = c["old"], c["new"]
            end = ci + len(old)
            if ci < len(text) and text[ci:end] == old:
                text = text[:ci] + new + text[end:]
                changes += 1
        obj["text"] = text

    if not dry_run and changes > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return changes


def main():
    parser = argparse.ArgumentParser(
        description="Fix multi-character moji-bake using epub reference"
    )
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Show corrections without modifying files")
    parser.add_argument("--review", "-r", action="store_true",
                        help="Show all proposed fixes with context")
    args = parser.parse_args()

    if not os.path.isdir(EPUB_DIR):
        print(f"ERROR: {EPUB_DIR}/ not found. Run unpack_epub.py first.")
        sys.exit(1)

    cc = OpenCC("t2s")

    total_fixes = 0
    total_applied = 0

    for vn in range(1, 295):
        fixes = find_multi_char_fixes(vn, cc)
        if not fixes:
            continue
        total_fixes += len(fixes)

        if args.review:
            print(f"\n=== Volume {vn:03d} ===")
            grouped = defaultdict(list)
            for f in fixes:
                key = f"'{f['old']}' → '{f['new']}'"
                grouped[key].append(f)
            for key, items in sorted(grouped.items()):
                print(f"  {key} ({len(items)}×)")
                for f in items[:3]:
                    para = _load_our_paragraphs(vn)[f["para_idx"]]
                    ci = f["char_idx"]
                    ctx = para[max(0, ci - 8):ci + len(f["old"]) + 8]
                    print(f"    p={f['para_idx']:3d} pos={f['char_idx']:4d}  ...{ctx}...")
            continue

        our_path = os.path.join(SOURCE_DIR, f"{vn:03d}.json")
        changes = apply_corrections(our_path, fixes, dry_run=args.dry_run)
        if changes > 0:
            total_applied += changes
            tag = "(dry-run)" if args.dry_run else ""
            print(f"Volume {vn:03d}: {changes} multi-char fixes {tag}")

    if args.review:
        print(f"\nSUMMARY: {total_fixes} multi-char fixes found")
    elif args.dry_run:
        print(f"\nDRY-RUN: {total_fixes} multi-char corrections found")
    else:
        print(f"\nDONE: {total_applied} multi-char fixes applied")


if __name__ == "__main__":
    main()
