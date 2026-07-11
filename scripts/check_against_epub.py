#!/usr/bin/env python3
"""
Use the Wikisource epub as a reference to find remaining text corruptions
in raw_json_converted/.

Mirrors correct_text.py but uses the epub (after extracting via unpack_epub.py)
instead of the Kanripo reference.  Reports both auto-fixable corruptions
(ASCII chars, hex fragments replacing CJK) and CJK-variant mismatches
for review.

Usage:
    python scripts/check_against_epub.py [--volume N] [--dry-run] [--review]

Requires: opencc (pip install opencc)
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

# ── character classification ──────────────────────────────────────────────

_CJK_PUNCT = set(
    "\uff0c\u3002\u3001\uff1b\uff1a\uff01\uff1f\u201c\u201d\u2018\u2019"
    "\u300a\u300b\u3008\u3009\u300c\u300d\u300e\u300f"
    "\u3010\u3011\uff08\uff09\u2014\u2026\uff5e\u00b7"
    "\u3000"
)
_ASCII_WS = set(" \n\r\t")


def _is_suspect(ch):
    cp = ord(ch)
    if 0x21 <= cp <= 0x7E:
        return ch not in "0123456789{}[]"
    if 0xFF10 <= cp <= 0xFF19:
        return True
    if 0xFF21 <= cp <= 0xFF3A:
        return True
    if 0xFF41 <= cp <= 0xFF5A:
        return True
    return False


def _is_cjk(ch):
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF)


def _is_cjk_compat(ch):
    return 0xF900 <= ord(ch) <= 0xFAFF


# ── known variant pairs ────────────────────────────────────────────────────

_VARIANTS = {
    "\u4d0d": "\u8654", "\u885e": "\u536b", "\u5f4a": "\u5f3a", "\u830d": "\u82b4",
    "\u7d9c": "\u7ef5", "\u5be6": "\u5b81", "\u5fb5": "\u5fb7", "\u6b74": "\u5386",
    "\u6b77": "\u5386", "\u903a": "\u8fdc", "\u59e7": "\u5978", "\u9b2d": "\u6597",
    "\u704b": "\u6cd5", "\u8c2a": "\u6eaa", "\u9684": "\u5824", "\u8b5b": "\u8c2e",
    "\u5900": "\u5bff", "\u5e81": "\u5eb6", "\u6238": "\u6237", "\u81ef": "\u768b",
    "\u9f43": "\u86d9", "\u9555": "\u7194", "\u938c": "\u7194", "\u888c": "\u79d8",
    "\u79d8": "\u888c", "\u9452": "\u9274", "\u4d58": "\u4e27", "\u7590": "\u758f",
    "\u4f59": "\u9980", "\u70cf": "\u4e4c", "\u7567": "\u7565", "\u95d8": "\u6597",
    "\u5147": "\u51f6", "\u7fa3": "\u7fa4", "\u5cf0": "\u5cf0", "\u7acf": "\u5947",
    "\u5ed0": "\u53a9", "\u8b1a": "\u8c25", "\u71fe": "\u70d8", "\u91bb": "\u9164",
    "\u5fa7": "\u904d", "\u751e": "\u5c1d", "\u8b4e": "\u4ec7", "\u52d1": "\u6555",
    "\u6b75": "\u6b3e", "\u6060": "\u602a", "\u6c37": "\u51b0", "\u6c5a": "\u6c61",
    "\u6d40": "\u51c0", "\u6ff6": "\u9614", "\u7151": "\u716e", "\u7240": "\u5e8a",
    "\u7328": "\u733f", "\u73ce": "\u73cd", "\u770e": "\u89c6", "\u77e6": "\u4faf",
    "\u7ada": "\u4f2b", "\u7b75": "\u8303", "\u7cc9": "\u7cbd", "\u7d35": "\u7ebb",
    "\u7f37": "\u5378", "\u7f78": "\u7f5a", "\u80f7": "\u80f8", "\u8229": "\u8239",
    "\u8276": "\u8273", "\u83d3": "\u679c", "\u8555": "\u8482", "\u8613": "\u82cf",
    "\u874f": "\u87f9", "\u88b4": "\u88e4", "\u8988": "\u6838", "\u898a": "\u7f81",
    "\u8a41": "\u8bc2", "\u8ad5": "\u5413", "\u8b20": "\u55a7", "\u8b41": "\u54d7",
    "\u8b4c": "\u8bb9", "\u8b9a": "\u8d5e", "\u8c53": "\u8273", "\u8cc3": "\u8d5e",
    "\u8ead": "\u803d", "\u8ea6": "\u4f53", "\u8f46": "\u4f53", "\u8f2d": "\u8f6f",
    "\u903a": "\u4e43", "\u9008": "\u8fe5", "\u904b": "\u6e38", "\u9089": "\u8fb9",
    "\u920e": "\u94a9", "\u9262": "\u94b5", "\u92f3": "\u94f8", "\u93bb": "\u9501",
    "\u9421": "\u94c1", "\u9599": "\u95f9", "\u965e": "\u5347", "\u9682": "\u9634",
    "\u98dc": "\u7ffb", "\u9a10": "\u9a8c", "\u9ae3": "\u4eff", "\u9ea5": "\u7c97",
    "\u9ef4": "\u9709", "\u87ed": "\u8702", "\u75ec": "\u70ae", "\u757e": "\u75f1",
    "\u8b41": "\u8c2a", "\u6286": "\u63be",
}
for _k, _v in list(_VARIANTS.items()):
    if _v and _v not in _VARIANTS:
        _VARIANTS[_v] = _k


def _is_variant_pair(a, b):
    return a == b or _VARIANTS.get(a) == b or _VARIANTS.get(b) == a


# ── helpers ────────────────────────────────────────────────────────────────

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


def _add_fix(corrections, norm_pos, n2o, o_ch, k_ch):
    if norm_pos < len(n2o):
        pi, ci = n2o[norm_pos]
        corrections.append({
            "para_idx": pi, "char_idx": ci,
            "old": o_ch, "new": k_ch,
        })


def find_corrections_from_epub(volume_num, cc):
    """Return (auto_fix list, review list) using epub as reference."""
    epub_text = _load_epub_text(volume_num)
    if epub_text is None:
        return [], []

    our_paras = _load_our_paragraphs(volume_num)
    if not our_paras:
        return [], []

    epub_simp = cc.convert(epub_text)
    e_norm = _normalize(epub_simp)

    o_norm, n2o = _build_para_index(our_paras)
    if not o_norm:
        return [], []

    matcher = difflib.SequenceMatcher(None, e_norm, o_norm, autojunk=False)
    blocks = matcher.get_matching_blocks()

    corrections = []
    reviews = []

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

        # Only flag suspect chars in our text
        o_suspect = [i for i, ch in enumerate(o_seg) if _is_suspect(ch)]

        if o_suspect:
            if len(o_seg) == 1 and len(e_seg) > 1 and all(
                    _is_cjk(c) or _is_cjk_compat(c) for c in e_seg):
                _add_fix(corrections, os_, n2o, o_seg[0], e_seg)
                continue

            if len(e_seg) == 1 and len(o_seg) > 1 and all(_is_suspect(c) for c in o_seg):
                if _is_cjk(e_seg[0]) or _is_cjk_compat(e_seg[0]):
                    _add_fix(corrections, os_, n2o, o_seg, e_seg[0])
                continue

            if len(o_seg) == 1:
                e_ch = e_seg[0] if e_seg else ""
                if e_ch and (_is_cjk(e_ch) or _is_cjk_compat(e_ch)):
                    _add_fix(corrections, os_, n2o, o_seg[0], e_ch)
                continue

            subm = difflib.SequenceMatcher(None, e_seg, o_seg, autojunk=False)
            sblocks = subm.get_matching_blocks()
            for sbi in range(len(sblocks) - 1):
                sb1, sb2 = sblocks[sbi], sblocks[sbi + 1]
                ies, iee = sb1.a + sb1.size, sb2.a
                ios, ioe = sb1.b + sb1.size, sb2.b
                if ies >= iee and ios >= ioe:
                    continue
                ie = e_seg[ies:iee]
                io = o_seg[ios:ioe]
                for idx in range(min(len(ie), len(io))):
                    if _is_suspect(io[idx]) and (_is_cjk(ie[idx]) or _is_cjk_compat(ie[idx])):
                        _add_fix(corrections, os_ + ios + idx, n2o,
                                 io[idx], ie[idx])
            continue

        # CJK-CJK mismatch → review
        if e_seg and o_seg and e_seg != o_seg:
            if len(e_seg) == len(o_seg):
                for idx in range(len(o_seg)):
                    o_ch, e_ch = o_seg[idx], e_seg[idx]
                    if o_ch != e_ch and not _is_variant_pair(o_ch, e_ch):
                        if (_is_cjk(o_ch) or _is_cjk_compat(o_ch)) and \
                           (_is_cjk(e_ch) or _is_cjk_compat(e_ch)):
                            mapped = n2o[os_ + idx] if os_ + idx < len(n2o) else None
                            if mapped:
                                pi, ci = mapped
                                reviews.append({
                                    "para_idx": pi, "char_idx": ci,
                                    "old": o_ch, "new": e_ch,
                                })

    return corrections, reviews


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
        gi, oi, obj = text_refs[para_idx]
        text = obj["text"]
        for c in sorted(corrs, key=lambda x: x["char_idx"], reverse=True):
            ci = c["char_idx"]
            old, new = c["old"], c["new"]
            end = ci + len(old)
            if ci < len(text) and text[ci:end] == old:
                text = text[:ci] + new + text[end:]
                changes += 1
            elif ci < len(text):
                window = text[max(0, ci - 5):ci + len(old) + 5]
                if old in window:
                    adj_ci = window.index(old) + max(0, ci - 5)
                    text = text[:adj_ci] + new + text[adj_ci + len(old):]
                    changes += 1
        obj["text"] = text

    if not dry_run and changes > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return changes


def main():
    parser = argparse.ArgumentParser(
        description="Find remaining corruptions using Wikisource epub as reference"
    )
    parser.add_argument("--volume", "-v", type=int,
                        help="Check a single volume number")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Report corrections without modifying files")
    parser.add_argument("--review", "-r", action="store_true",
                        help="Show both auto-fix and review items")
    args = parser.parse_args()

    if not os.path.isdir(EPUB_DIR):
        print(f"ERROR: {EPUB_DIR}/ not found. Run unpack_epub.py first.")
        sys.exit(1)

    cc = OpenCC("t2s")
    volumes = [args.volume] if args.volume else list(range(1, 295))

    total_auto = 0
    total_changes = 0
    total_review = 0
    unfixable_volumes = []

    for vn in volumes:
        corrections, reviews = find_corrections_from_epub(vn, cc)

        if args.review:
            if corrections or reviews:
                print(f"\n=== Volume {vn:03d} ===")
                if corrections:
                    print(f"  AUTO-FIX ({len(corrections)}):")
                    bp = defaultdict(list)
                    for c in corrections:
                        bp[c["para_idx"]].append(c)
                    for pi, crs in sorted(bp.items()):
                        for c in crs:
                            print(f"    p={pi:3d} pos={c['char_idx']:4d}  "
                                  f"'{c['old']}' -> '{c['new']}'")
                if reviews:
                    print(f"  REVIEW ({len(reviews)} — CJK mismatches):")
                    bp = defaultdict(list)
                    for c in reviews:
                        bp[c["para_idx"]].append(c)
                    for pi, crs in sorted(bp.items()):
                        for c in crs:
                            print(f"    p={pi:3d} pos={c['char_idx']:4d}  "
                                  f"'{c['old']}' -> '{c['new']}'")
                total_review += len(reviews)
            continue

        total_auto += len(corrections)
        if corrections:
            our_path = os.path.join(SOURCE_DIR, f"{vn:03d}.json")
            changes = apply_corrections(our_path, corrections, dry_run=args.dry_run)
            total_changes += changes
            if changes > 0:
                tag = "(dry-run)" if args.dry_run else ""
                print(f"Volume {vn:03d}: {changes} chars fixed {tag}")
            else:
                unfixable_volumes.append(vn)

    if args.review:
        print(f"\nSUMMARY: {total_auto} auto-fix + {total_review} review items")
    elif args.dry_run:
        print(f"\nDRY-RUN: {total_auto} potential corrections found")
        print("Run without --dry-run to apply.")
    else:
        print(f"\nDONE: {total_changes} characters fixed across volumes")
    if unfixable_volumes:
        print(f"Note: {len(unfixable_volumes)} volumes had corrections that "
              f"could not be applied (text mismatch)")


if __name__ == "__main__":
    main()
