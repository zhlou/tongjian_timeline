#!/usr/bin/env python3
"""Build indices.json from semantic_json/*.json for the web app.

Produces a single JSON file containing:
  - dynasties:  dynasty_name -> [section_ids]
  - dynasty_order: preserved insertion order
  - dynasty_meta: dynasty_name -> {year_min, year_max, year_range}
  - volumes:    volume_name -> [section_ids]
  - volume_order: preserved insertion order
  - volume_meta: volume_name -> {time_cycle, file_index, dynasty, raw_volume_name, year_min, year_max, year_range}
  - eras:       era_name -> [section_ids]
  - era_meta:   era_name -> {year_min, year_max, year_range}
  - era_years:  "{era_name}|{era_year}" -> section_id
  - western_years: "403 BC" -> section_id
  - ganzhi_index: ganzhi -> [section_ids] (chronological)
  - sections:   section_id -> {volume_name, dynasty, era_name, era_year, year, ganzhi, texts, volume_time_cycle}
  - section_order: [section_id, ...]
"""

import json
import re
from pathlib import Path

SEM_DIR = "semantic_json"
OUTPUT_FILE = "indices.json"


def extract_dynasty(volume_name):
    m = re.match(r"^(.+?)纪", volume_name)
    return m.group(1) if m else ""


def format_year(n):
    return f"{abs(n)} BC" if n < 0 else f"{n} AD"


def parse_year_num(year_str):
    m = re.match(r"(\d+)\s+(BC|AD)", year_str or "")
    if m:
        n = int(m.group(1))
        return -n if m.group(2) == "BC" else n
    return 0


def year_int(year_str):
    return parse_year_num(year_str) if year_str else 0


def range_for(sids, sections):
    ints = []
    for sid in sids:
        y = year_int(sections[sid].get("year", ""))
        if y != 0:
            ints.append(y)
    if not ints:
        return None, None, ""
    lo, hi = min(ints), max(ints)
    return lo, hi, f"{format_year(lo)} \u2013 {format_year(hi)}"


def build_indices():
    sem_dir = Path(SEM_DIR)
    files = sorted(sem_dir.glob("*.json"))

    dynasties = {}
    dynasty_order = []
    volumes = {}
    volume_order = []
    eras = {}
    era_years = {}
    western_years = {}
    ganzhi_index = {}
    sections = {}
    leaf_meta = {}
    volume_meta = {}
    dynasty_meta = {}
    era_meta = {}
    section_order = []
    section_labels = {}

    for f in files:
        file_index = f.stem
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        volume_name = data.get("volume_name", "")
        volume_time_cycle = data.get("volume_time_cycle", "")
        dynasty = extract_dynasty(volume_name)

        if volume_name not in volumes:
            volumes[volume_name] = []
            volume_order.append(volume_name)
        if dynasty not in dynasties:
            dynasties[dynasty] = []
            dynasty_order.append(dynasty)

        if volume_name not in volume_meta:
            volume_meta[volume_name] = {
                "time_cycle": volume_time_cycle,
                "file_index": file_index,
                "dynasty": dynasty,
            }

        for si, section in enumerate(data.get("sections", [])):
            section_id = f"{file_index}-{si}"
            section_order.append(section_id)

            era_name = section.get("era_name", "")
            era_year = section.get("era_year", "")
            ganzhi = section.get("ganzhi") or ""
            year = section.get("year", "") or ""
            texts = section.get("texts", [])

            dynasties[dynasty].append(section_id)
            volumes[volume_name].append(section_id)
            eras.setdefault(era_name, []).append(section_id)

            if era_name and era_year:
                key = f"{era_name}|{era_year}"
                era_years[key] = section_id

            if year:
                western_years[year] = section_id

            if ganzhi:
                ganzhi_index.setdefault(ganzhi, []).append(section_id)

            sections[section_id] = {
                "volume_name": volume_name,
                "dynasty": dynasty,
                "era_name": era_name,
                "era_year": era_year,
                "ganzhi": ganzhi,
                "year": year,
                "texts": texts,
                "volume_time_cycle": volume_time_cycle,
                "is_volume_start": si == 0,
            }

            leaf_meta[section_id] = {
                "volume_name": volume_name,
                "dynasty": dynasty,
                "era_name": era_name,
                "era_year": era_year,
                "ganzhi": ganzhi,
                "year": year,
            }

            label_parts = []
            if era_name:
                label_parts.append(era_name)
            if era_year:
                label_parts.append(era_year)
            section_labels[section_id] = " ".join(label_parts) if label_parts else section_id

    for vol_name, sids in volumes.items():
        lo, hi, rng = range_for(sids, sections)
        volume_meta[vol_name]["year_min"] = lo
        volume_meta[vol_name]["year_max"] = hi
        volume_meta[vol_name]["year_range"] = rng

    for dy_name, sids in dynasties.items():
        lo, hi, rng = range_for(sids, sections)
        dynasty_meta[dy_name] = {
            "year_min": lo,
            "year_max": hi,
            "year_range": rng,
        }

    for era_name, sids in eras.items():
        lo, hi, rng = range_for(sids, sections)
        era_meta[era_name] = {
            "year_min": lo,
            "year_max": hi,
            "year_range": rng,
        }

    indices = {
        "dynasties": dynasties,
        "dynasty_order": dynasty_order,
        "dynasty_meta": dynasty_meta,
        "volumes": volumes,
        "volume_order": volume_order,
        "volume_meta": volume_meta,
        "eras": eras,
        "era_meta": era_meta,
        "era_years": era_years,
        "western_years": western_years,
        "ganzhi_index": ganzhi_index,
            "sections": sections,
            "leaf_meta": leaf_meta,
            "section_labels": section_labels,
        "section_order": section_order,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(indices, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Files processed:  {len(files)}")
    print(f"Sections:        {len(section_order)}")
    print(f"Dynasties:       {len(dynasties)} ({', '.join(dynasty_order)})")
    print(f"Volumes:         {len(volumes)}")
    print(f"Eras:            {len(eras)}")
    print(f"Era+Year keys:   {len(era_years)}")
    print(f"Western years:   {len(western_years)}")
    print(f"Ganzhi tokens:   {len(ganzhi_index)}")
    print(f"Output written to {OUTPUT_FILE}")


def main():
    build_indices()


if __name__ == "__main__":
    main()
