#!/usr/bin/env python3
"""
Bake corrections into raw_json_converted/ in-place.

Applies the fixes that restructure_json.py has been doing on-the-fly:
  - Strips 【】 brackets from vol_name
  - Fixes encoding corruptions in volume_time_cycle
  - Splits merged ◎vol_name+time_cycle in files 111 and 140

Usage:
    python scripts/fix_raw_converted.py [--dry-run]
"""

import json
import os
import re
import sys
import argparse

SOURCE_DIR = "raw_json_converted"

TIME_CYCLE_FIXES = {
    "]": "\u9ed3",
    "\u2237": "\u6d92",
    "\u3108\u7a1a\u8f8f": "",
    "\u7600\u9022": "\u960f\u9022",
    "\u6691\u7ef4": "\u5c60\u7ef4",
    "\u5f3a\u56f4": "\u5f3a\u5709",
    "\u5f3a\u56fe": "\u5f3a\u5709",
    "\u5f3a\u960f": "\u5f3a\u5709",
    "\u76ee\u7ae0": "\u4e0a\u7ae0",
    "\u65c3\u8499\u5355\u7600": "\u65c3\u8499\u5355\u960f",
    "\u8d64\u5907\u82e5": "\u8d64\u594b\u82e5",
    "\u592a\u6e0a\u732e": "\u5927\u6e0a\u732e",
    "\u8d75\u67d4\u5146": "\u8d77\u67d4\u5146",
    "\u8da3\u662d\u9633": "\u8d77\u662d\u9633",
}

_RE_BRACKETS = re.compile(r"[\u3010\u3011]")


def fix_volume_name(text):
    return _RE_BRACKETS.sub("", text).strip()


def fix_volume_time_cycle(text):
    result = text
    for bad, good in TIME_CYCLE_FIXES.items():
        result = result.replace(bad, good)
    return result


def fix_file(path, dry_run=False):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    changes = []
    name = os.path.basename(path)

    for group in data:
        for obj in group:
            if obj["name"] == "vol_name":
                old = obj["text"]
                new = fix_volume_name(old)
                if old != new:
                    obj["text"] = new
                    changes.append(f"vol_name: [{old.strip()[:40]}] -> [{new[:40]}]")

            elif obj["name"] == "vol_time_cycle":
                old = obj["text"]
                # Handle ◎-merged case (files 111 and 140)
                if old.startswith("\u25ce"):
                    idx = old.find("\u8d77")  # 起
                    if idx > 0:
                        # Split: ◎vol_name 起... → vol_name = part after ◎, cycle = 起...
                        merged_name = old[1:idx]
                        merged_cycle = old[idx:]
                        changes.append(f"split ◎-merge: vol_name={merged_name[:20]}, cycle={merged_cycle[:30]}")

                        # Update vol_name and vol_time_cycle
                        found_vol_name = False
                        for g in data:
                            for o in g:
                                if o["name"] == "vol_name":
                                    o["text"] = fix_volume_name(merged_name)
                                    found_vol_name = True
                                    break
                            if found_vol_name:
                                break
                        obj["text"] = fix_volume_time_cycle(merged_cycle)
                    else:
                        new = fix_volume_time_cycle(old)
                        if old != new:
                            obj["text"] = new
                            changes.append(f"time_cycle fixed: [{old[:40]}]")
                else:
                    new = fix_volume_time_cycle(old)
                    if old != new:
                        obj["text"] = new
                        changes.append(f"time_cycle: [{old[:40]}] -> [{new[:40]}]")

    if not changes:
        return False

    if dry_run:
        for c in changes:
            print(f"  {name}: {c}")
        return True

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    for c in changes:
        print(f"  {name}: {c}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Bake restructure_json corrections into raw_json_converted/"
    )
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Show changes without modifying files")
    args = parser.parse_args()

    total = 0
    for num in range(1, 295):
        path = os.path.join(SOURCE_DIR, f"{num:03d}.json")
        if fix_file(path, dry_run=args.dry_run):
            total += 1

    if args.dry_run:
        print(f"\nDRY-RUN: {total} files would be modified")
    else:
        print(f"\nDONE: {total} files updated")


if __name__ == "__main__":
    main()
