#!/usr/bin/env python3
"""
Reference-based text correction for the Zizhi Tongjian corpus.

Aligns raw_json_converted main_text against the Kanripo KR2b0007 reference
(Siku Quanshu edition) to detect and auto-fix character-level corruptions.

Usage:
    python scripts/correct_text.py [--volume N] [--dry-run] [--review]

Strategy:
    - Auto-fix: ASCII chars / fullwidth digits / brackets / hex fragments
      that provably replace CJK characters, using the Kanripo reference.
    - Review:   CJK-CJK mismatches that may be moji-bake, edition variants,
      or bracket-placeholder notation ({艹}).

Reference: https://github.com/kanripo/KR2b0007 (CC BY-SA 4.0)
"""

import json, os, re, sys, argparse, difflib
from pathlib import Path
from collections import defaultdict

from opencc import OpenCC

REF_DIR = os.environ.get("REF_DIR", "/tmp/reference_kanripo")
SOURCE_DIR = "raw_json_converted"

# ── character classification ──────────────────────────────────────────────

# CJK punctuation – stripped during normalisation
_CJK_PUNCT = set(
    "，。、；：？！""''（）【】…—～・·　"
    "\u3000\u3001\u3002\uff0c\uff0e\uff1a\uff1b\uff01\uff1f"
    "\u2018\u2019\u201c\u201d\u300a\u300b\u3008\u3009"
    "\u3010\u3011\uff08\uff09\u2014\u2026\uff5e\u00b7"
    "\u2500\u2501"
)
_ASCII_WS = set(" \n\r\t")

# Hex-fragment pattern: e.g. A170, C090, B111
_RE_HEX_FRAGMENT = re.compile(r"[A-Fa-f][0-9A-Fa-f]{2,3}")

# Bracket-placeholder: {艹}, {土}, {敝衣}
_RE_BRACKET_PLACEHOLDER = re.compile(r"\{[^}]+\}")

# Characters that are PROBABLY wrong when appearing in classical Chinese
def _is_suspect(ch):
    cp = ord(ch)
    # ASCII printable, excluding digits (year-names) and braces (notation)
    if 0x21 <= cp <= 0x7E:
        return ch not in "0123456789{}[]"
    # Fullwidth digits / letters (０-９, Ａ-Ｚ, ａ-ｚ)
    if 0xFF10 <= cp <= 0xFF19:  return True
    if 0xFF21 <= cp <= 0xFF3A:  return True
    if 0xFF41 <= cp <= 0xFF5A:  return True
    # Enclosed CJK / alphanumerics  ㈠㈡ …
    if 0x3200 <= cp <= 0x32FF:   return True
    # Corner brackets that replace CJK chars
    if 0x300C <= cp <= 0x300F:   return True
    return False


def _is_cjk(ch):
    """CJK Unified Ideograph (BMP + Extension A)."""
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF)


def _is_cjk_compat(ch):
    """CJK Compatibility Ideograph."""
    return 0xF900 <= ord(ch) <= 0xFAFF


# ── known trad / simp variant pairs (not corruption) ──────────────────────

_VARIANTS = {
    "䖍":"虔","衞":"卫","彊":"强","茍":"苟","緜":"绵","寜":"宁",
    "徳":"德","歴":"历","歷":"历","逺":"远","姧":"奸","鬭":"斗",
    "灋":"法","谿":"溪","隄":"堤","譛":"谮","夀":"寿","庻":"庶",
    "戸":"户","臯":"皋","鼃":"蛙","镕":"熔","鎔":"熔","袐":"秘",
    "秘":"祕","鑑":"鉴","䘮":"丧","疎":"疏","余":"馀","烏":"乌",
    "畧":"略","闘":"斗","兇":"凶","羣":"群","峯":"峰","竒":"奇",
    "廐":"厩","謚":"谥","燾":"焘","醻":"酬","徧":"遍","甞":"尝",
    "讎":"仇","勑":"敕","欵":"款","恠":"怪","氷":"冰","汚":"污",
    "浄":"净","濶":"阔","煑":"煮","牀":"床","猨":"猿","珎":"珍",
    "眎":"视","矦":"侯","竚":"伫","笵":"范","糉":"粽","紵":"纻",
    "缷":"卸","罸":"罚","胷":"胸","舩":"船","艶":"艳","菓":"果",
    "蔕":"蒂","蘓":"苏","蠏":"蟹","袴":"裤","覈":"核","覊":"羁",
    "詁":"诂","諕":"吓","諠":"喧","譁":"哗","譌":"讹","讚":"赞",
    "豓":"艳","賛":"赞","躭":"耽","躰":"体","軆":"体","輭":"软",
    "迺":"乃","逈":"迥","遊":"游","邉":"边","鈎":"钩","鉢":"钵",
    "鋳":"铸","鎻":"锁","鐡":"铁","閙":"闹","陞":"升","隂":"阴",
    "飜":"翻","騐":"验","髣":"仿","麁":"粗","黴":"霉","蠭":"蜂",
    "痬":"疡","疿":"痱","讁":"谪","抆":"揾",
}
for _k, _v in list(_VARIANTS.items()):
    if _v and _v not in _VARIANTS:
        _VARIANTS[_v] = _k


def _is_variant_pair(a, b):
    return a == b or _VARIANTS.get(a) == b or _VARIANTS.get(b) == a


# ── helpers ────────────────────────────────────────────────────────────────

def _clean_kanripo(filepath):
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()
    parts = []
    for line in lines:
        if line.startswith("#") or line.startswith("<pb:"):
            continue
        line = line.rstrip("¶\n")
        line = re.sub(r"\([^)]*\)", "", line)
        line = line.strip()
        if line:
            parts.append(line)
    text = "".join(parts)
    # Trim to first dynasty-era heading
    m = re.search(
        r"[\u5468\u79e6\u6f22\u9b4f\u6649\u5b8b\u9f4a\u6881"
        r"\u9673\u968b\u5510\u5f8c\u6881\u5f8c\u5510\u5f8c\u6649"
        r"\u5f8c\u6f22\u5f8c\u5468]\u7d00", text)
    if m:
        text = text[m.start():]
    return text


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


# ── core alignment & correction detection ──────────────────────────────────

def find_corrections(volume_num, cc):
    """Return (auto_fix list, review list) for a single volume."""
    ref_path = os.path.join(REF_DIR, f"KR2b0007_{volume_num:03d}.txt")
    our_path = os.path.join(SOURCE_DIR, f"{volume_num:03d}.json")
    if not os.path.exists(ref_path) or not os.path.exists(our_path):
        return [], []

    kanripo_simp = cc.convert(_clean_kanripo(ref_path))
    k_norm = _normalize(kanripo_simp)

    with open(our_path, encoding="utf-8") as f:
        data = json.load(f)

    paragraphs = []
    for group in data:
        for obj in group:
            if obj["name"] == "main_text":
                paragraphs.append(obj["text"])

    if not paragraphs:
        return [], []

    o_norm, n2o = _build_para_index(paragraphs)

    matcher = difflib.SequenceMatcher(None, k_norm, o_norm, autojunk=False)
    blocks = matcher.get_matching_blocks()

    corrections = []   # auto-fix
    reviews = []       # manual review

    for bi in range(len(blocks) - 1):
        b1, b2 = blocks[bi], blocks[bi + 1]
        ks, ke = b1.a + b1.size, b2.a
        os_, oe_ = b1.b + b1.size, b2.b
        if ks >= ke and os_ >= oe_:
            continue
        k_seg = k_norm[ks:ke]
        o_seg = o_norm[os_:oe_]
        if not k_seg and not o_seg:
            continue

        # ── Moji-bake chain detection ──────────────────────────────
        if (_is_mojibake_chain(k_seg, o_seg)):
            for idx in range(len(o_seg)):
                if o_seg[idx] != k_seg[idx]:
                    _add_fix(corrections, os_ + idx, n2o,
                             o_seg[idx], k_seg[idx])
            continue

        # ── Scan for suspect chars ─────────────────────────────────
        o_suspect = [i for i, ch in enumerate(o_seg) if _is_suspect(ch)]

        if o_suspect:
            # 1→N: single suspect char, N correct CJK chars
            if len(o_seg) == 1 and len(k_seg) > 1 and all(
                    _is_cjk(c) or _is_cjk_compat(c) for c in k_seg):
                _add_multi_fix(corrections, os_, n2o, o_seg[0], k_seg)
                continue

            # N→1: multiple suspect chars, single correct CJK
            if len(k_seg) == 1 and len(o_seg) > 1 and all(_is_suspect(c) for c in o_seg):
                if _is_cjk(k_seg[0]) or _is_cjk_compat(k_seg[0]):
                    _add_multi_fix(corrections, os_, n2o, o_seg, k_seg[0])
                continue

            # Single suspect inside single-char segment → direct 1:1
            if len(o_seg) == 1:
                k_ch = k_seg[0] if k_seg else ""
                if k_ch and (_is_cjk(k_ch) or _is_cjk_compat(k_ch)):
                    _add_fix(corrections, os_, n2o, o_seg[0], k_ch)
                continue

            # Use sub-alignment to find counterpart
            subm = difflib.SequenceMatcher(None, k_seg, o_seg, autojunk=False)
            sblocks = subm.get_matching_blocks()
            for sbi in range(len(sblocks) - 1):
                sb1, sb2 = sblocks[sbi], sblocks[sbi + 1]
                iks, ike = sb1.a + sb1.size, sb2.a
                ios, ioe = sb1.b + sb1.size, sb2.b
                if iks >= ike and ios >= ioe:
                    continue
                ik = k_seg[iks:ike]
                io = o_seg[ios:ioe]
                for idx in range(min(len(ik), len(io))):
                    if _is_suspect(io[idx]) and (_is_cjk(ik[idx]) or _is_cjk_compat(ik[idx])):
                        _add_fix(corrections, os_ + ios + idx, n2o,
                                 io[idx], ik[idx])
            continue

        # ── CJK mismatch → review ──────────────────────────────────
        if k_seg and o_seg and k_seg != o_seg:
            if len(k_seg) == len(o_seg):
                for idx in range(len(o_seg)):
                    o_ch, k_ch = o_seg[idx], k_seg[idx]
                    if o_ch != k_ch and not _is_variant_pair(o_ch, k_ch):
                        if (_is_cjk(o_ch) or _is_cjk_compat(o_ch)) and \
                           (_is_cjk(k_ch) or _is_cjk_compat(k_ch)):
                            mapped = n2o[os_ + idx] if os_ + idx < len(n2o) else None
                            if mapped:
                                pi, ci = mapped
                                reviews.append({
                                    "para_idx": pi, "char_idx": ci,
                                    "old": o_ch, "new": k_ch,
                                    "old_cp": f"U+{ord(o_ch):04X}",
                                    "new_cp": f"U+{ord(k_ch):04X}",
                                })

    return corrections, reviews


def _is_mojibake_chain(k_seg, o_seg):
    if len(k_seg) != len(o_seg) or len(k_seg) < 2:
        return False
    if not any(_is_suspect(ch) for ch in o_seg):
        return False
    subm = difflib.SequenceMatcher(None, k_seg, o_seg, autojunk=False)
    matched = sum(b.size for b in subm.get_matching_blocks())
    return (matched / len(k_seg)) < 0.3


def _add_fix(corrections, norm_pos, n2o, o_ch, k_ch):
    if norm_pos < len(n2o):
        pi, ci = n2o[norm_pos]
        corrections.append({
            "para_idx": pi, "char_idx": ci,
            "old": o_ch, "new": k_ch,
        })


def _add_multi_fix(corrections, norm_start, n2o, old_text, new_text):
    """Handle N↔M replacements (e.g. '」' → '湣公' or 'QKDP' → '詧')."""
    if norm_start < len(n2o):
        pi, ci = n2o[norm_start]
        corrections.append({
            "para_idx": pi, "char_idx": ci,
            "old": old_text, "new": new_text,
        })


# ── hex-fragment detection (scans paragraph text directly) ─────────────────

def _find_hex_fragments(paragraphs, cc, volume_num):
    """Detect hex fragments like A170 in paragraph text.
    Returns corrections for N-chars → 1 CJK char replacements.
    """
    corrections = []
    ref_path = os.path.join(REF_DIR, f"KR2b0007_{volume_num:03d}.txt")

    for pi, para in enumerate(paragraphs):
        for m in _RE_HEX_FRAGMENT.finditer(para):
            fragment = m.group()
            start = m.start()
            end = m.end()
            ctx_start = max(0, start - 6)
            ctx_end = min(len(para), end + 6)
            ctx = para[ctx_start:ctx_end]

            # Try to find the hex value in Kanripo context
            # A170 = 0xA170 = potential GBK/Unicode code point
            try:
                hex_val = int(fragment, 16)
            except ValueError:
                continue

            # Try as GBK bytes
            hi, lo = (hex_val >> 8) & 0xFF, hex_val & 0xFF
            if 0x81 <= hi <= 0xFE:
                for enc in ['gbk', 'gb18030']:
                    try:
                        decoded = bytes([hi, lo]).decode(enc)
                        if decoded and _is_cjk(decoded):
                            corrections.append({
                                "para_idx": pi, "char_idx": start,
                                "old": fragment, "new": decoded,
                            })
                            break
                    except Exception:
                        continue

    return corrections


# ── apply ──────────────────────────────────────────────────────────────────

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
                # old text may have been shifted by prior edits; try nearby
                window = text[max(0, ci-5):ci+len(old)+5]
                if old in window:
                    adj_ci = window.index(old) + max(0, ci-5)
                    text = text[:adj_ci] + new + text[adj_ci + len(old):]
                    changes += 1
        obj["text"] = text

    if not dry_run and changes > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return changes


# ── main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Correct corrupted characters using Kanripo reference"
    )
    parser.add_argument("--volume", "-v", type=int,
                        help="Process only a single volume number")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Report corrections without modifying files")
    parser.add_argument("--review", "-r", action="store_true",
                        help="Output review format with CJK mismatches")
    args = parser.parse_args()

    if not os.path.isdir(REF_DIR):
        print(f"ERROR: Reference directory not found: {REF_DIR}")
        print(f"Clone: git clone https://github.com/kanripo/KR2b0007.git {REF_DIR}")
        sys.exit(1)

    cc = OpenCC("t2s")
    volumes = [args.volume] if args.volume else list(range(1, 295))

    total_auto = 0
    total_changes = 0
    total_review = 0

    for vn in volumes:
        corrections, reviews = find_corrections(vn, cc)

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
                                  f"'{c['old']}' → '{c['new']}'")
                if reviews:
                    print(f"  REVIEW ({len(reviews)} — CJK mismatches):")
                    bp = defaultdict(list)
                    for c in reviews:
                        bp[c["para_idx"]].append(c)
                    for pi, crs in sorted(bp.items()):
                        for c in crs:
                            print(f"    p={pi:3d} pos={c['char_idx']:4d}  "
                                  f"'{c['old']}'({c['old_cp']}) → "
                                  f"'{c['new']}'({c['new_cp']})")
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

    if args.review:
        print(f"\nSUMMARY: {total_auto} auto-fix + {total_review} review items")
    elif args.dry_run:
        print(f"\nDRY-RUN: {total_auto} corrections found")
        print("Run without --dry-run to apply.")
    else:
        print(f"\nDONE: {total_changes} characters fixed across "
              f"{sum(1 for v in volumes if find_corrections(v, cc)[0])} volumes")


if __name__ == "__main__":
    main()
