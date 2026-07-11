#!/usr/bin/env python3
"""
Extract and convert zizhitongjian.epub xhtml to plain text files.

Usage:
    python scripts/unpack_epub.py

Output:
    epub_text/001.txt ... epub_text/294.txt  (one plain-text file per volume)
"""

import json
import os
import re
import sys
import zipfile

from html import unescape

EPUB_PATH = "zizhitongjian.epub"
OUTPUT_DIR = "epub_text"

# Regex matching juan volumes inside the epub
_RE_JUAN = re.compile(r"OPS/c(\d+)_zi_zhi_tong_jian_juan(\d+)\.xhtml")


def _schema_org_about_link(attrs):
    """Return True if this element is a schema.org AboutPage link (navigational)."""
    for k, v in attrs:
        if k == "typeof" and "AboutPage" in v:
            return True
    return False


def _is_license_section(attrs):
    """Return True if this element is a license section to be skipped."""
    for k, v in attrs:
        if k == "class" and "licenseContainer" in v:
            return True
        if k == "about" and "License" in v:
            return True
    return False


def extract_volume(zf, num):
    """Extract plain text for one volume from the epub.

    Returns (volume_number, text, warnings).
    """

    # Find the xhtml file for this volume: c{N}_zi_zhi_tong_jian_juan{N}.xhtml
    # c numbers match juan numbers (c1 → juan1), but there's also
    # zero-padded variant juan001 vs juan1 depending on the actual epub structure.
    candidates = []
    for name in zf.namelist():
        m = _RE_JUAN.match(name)
        if m:
            cnum, jnum = int(m.group(1)), int(m.group(2))
            if jnum == num:
                candidates.append(name)

    if not candidates:
        # Try zero-padded juan number
        for name in zf.namelist():
            m = re.search(r"OPS/c(\d+)_zi_zhi_tong_jian_juan(\d+)\.xhtml", name)
            if m and int(m.group(2)) == num:
                candidates.append(name)

    if not candidates:
        return "", f"Volume {num:03d}: not found in epub", []

    raw = zf.read(candidates[0]).decode("utf-8")

    # Remove CDATA CSS blocks (can be huge)
    raw = re.sub(r"<style[^>]*>.*?</style>", "", raw, flags=re.DOTALL)

    # Extract body
    m = re.search(r"<body[^>]*>(.*?)</body>", raw, re.DOTALL)
    if not m:
        return "", f"Volume {num:03d}: no <body> found", []

    body = m.group(1)

    # Remove sections we don't want
    # - schema.org AboutPage links (prev/next navigation)
    # - license sections at the bottom
    body = re.sub(
        r'<[^>]+typeof="[^"]*AboutPage[^"]*"[^>]*>.*?</\w+>',
        "", body, flags=re.DOTALL,
    )
    body = re.sub(
        r'<div[^>]*class="[^"]*licenseContainer[^"]*"[^>]*>.*?</div>',
        "", body, flags=re.DOTALL,
    )
    body = re.sub(
        r'<section[^>]*about="[^"]*License[^"]*"[^>]*>.*?</section>',
        "", body, flags=re.DOTALL,
    )

    # Strip all remaining tags
    text = re.sub(r"<[^>]+>", "", body)
    text = unescape(text)

    # Normalize whitespace
    text = re.sub(r"[ \t\f\r]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    # Remove wikisource boilerplate lines
    lines = text.split("\n")
    clean = []
    skip_patterns = [
        r"^目錄",
        r"^姊妹计划",
        r"^資治通鑑.*卷",
        r"^本.*作品在全世界都属于公有领域",
        r"^Public domain",
        r"^这部作品在",
        r"^►",
        r"^◄",
        r"^\s*$",
    ]
    skip_re = re.compile("|".join(skip_patterns))

    for line in lines:
        if skip_re.match(line.strip()):
            continue
        clean.append(line.strip())

    text = "\n".join(clean).strip()
    return text, "", []


def main():
    if not os.path.exists(EPUB_PATH):
        print(f"ERROR: {EPUB_PATH} not found")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    zf = zipfile.ZipFile(EPUB_PATH)

    for num in range(1, 295):
        text, err, _ = extract_volume(zf, num)
        if err:
            print(err)
            continue

        out_path = os.path.join(OUTPUT_DIR, f"{num:03d}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text + "\n")

    zf.close()
    count = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".txt")])
    print(f"Done. {count} volumes written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
