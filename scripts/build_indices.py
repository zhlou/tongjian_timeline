#!/usr/bin/env python3
"""Build indices.json from semantic_json/*.json for the web app.

Produces a single JSON file containing:
  - dynasties:  dynasty_name -> [section_ids]
  - volumes:    volume_name -> [section_ids]
  - eras:       era_name -> [section_ids]
  - era_years:  "{era_name}|{era_year}" -> section_id
  - western_years: "403 BC" -> section_id
  - western_timeline: [{"century": "...", "years": [...]}]
  - sections:   section_id -> {volume_name, dynasty, era_name, era_year, year, texts, volume_time_cycle}
  - volume_meta: volume_name -> {time_cycle, file_index, dynasty, raw_volume_name}
  - section_order: [section_id, ...]
"""

import json
import re
from pathlib import Path

SEM_DIR = "semantic_json"
OUTPUT_FILE = "indices.json"


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def extract_dynasty(volume_name):
    name = volume_name.replace("\u3010", "").replace("\u3011", "").strip()
    m = re.match(r"^(.+?)纪", name)
    return m.group(1) if m else ""


KNOWN_EMPTY_VOLUMES = {
    "111": "【晋纪三十三】 ",
    "140": "【齐纪六】 ",
}


def fix_volume_name(file_index, raw_name):
    if file_index in KNOWN_EMPTY_VOLUMES and (not raw_name or raw_name.replace("\u3010", "").replace("\u3011", "").strip() == ""):
        return KNOWN_EMPTY_VOLUMES[file_index]
    return raw_name


def parse_year_num(year_str):
    m = re.match(r"(\d+)\s+(BC|AD)", year_str)
    if m:
        n = int(m.group(1))
        return -n if m.group(2) == "BC" else n
    return 0


def century_label(year_str):
    m = re.match(r"(\d+)\s+(BC|AD)", year_str)
    if not m:
        return None
    n = int(m.group(1))
    era = m.group(2)
    c = (n - 1) // 100 + 1
    return f"{ordinal(c)} Century {era}"


def build_indices():
    sem_dir = Path(SEM_DIR)
    files = sorted(sem_dir.glob("*.json"))

    dynasties = {}
    volumes = {}
    eras = {}
    era_years = {}
    western_years = {}
    sections = {}
    volume_meta = {}
    section_order = []
    section_labels = {}
    year_set = set()

    for f in files:
        file_index = f.stem
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        raw_volume_name = fix_volume_name(file_index, data.get("volume_name", ""))
        volume_time_cycle = data.get("volume_time_cycle", "")
        dynasty = extract_dynasty(raw_volume_name)
        cleaned_name = raw_volume_name.replace("\u3010", "").replace("\u3011", "").strip()

        volumes.setdefault(cleaned_name, [])
        dynasties.setdefault(dynasty, [])

        volume_meta[cleaned_name] = {
            "time_cycle": volume_time_cycle,
            "file_index": file_index,
            "dynasty": dynasty,
            "raw_volume_name": raw_volume_name,
        }

        for si, section in enumerate(data.get("sections", [])):
            section_id = f"{file_index}-{si}"
            section_order.append(section_id)

            era_name = section.get("era_name", "")
            era_year = section.get("era_year", "")
            year = section.get("year", "")
            texts = section.get("texts", [])

            dynasties[dynasty].append(section_id)
            volumes[cleaned_name].append(section_id)
            eras.setdefault(era_name, []).append(section_id)

            if era_name and era_year:
                key = f"{era_name}|{era_year}"
                era_years[key] = section_id

            if year:
                western_years[year] = section_id
                year_set.add(year)

            sections[section_id] = {
                "volume_name": cleaned_name,
                "dynasty": dynasty,
                "era_name": era_name,
                "era_year": era_year,
                "year": year,
                "texts": texts,
                "volume_time_cycle": volume_time_cycle,
            }

            label_parts = []
            if era_name:
                label_parts.append(era_name)
            if era_year:
                label_parts.append(era_year)
            if year:
                label_parts.append(f"({year})")
            section_labels[section_id] = " ".join(label_parts) if label_parts else section_id

    sorted_years = sorted(year_set, key=parse_year_num)

    western_timeline = []
    current_century = None
    century_years = []

    for y in sorted_years:
        cl = century_label(y)
        if cl != current_century:
            if current_century is not None:
                western_timeline.append({"century": current_century, "years": century_years})
            current_century = cl
            century_years = []
        century_years.append(y)

    if current_century is not None:
        western_timeline.append({"century": current_century, "years": century_years})

    indices = {
        "dynasties": dynasties,
        "volumes": volumes,
        "eras": eras,
        "era_years": era_years,
        "western_years": western_years,
        "western_timeline": western_timeline,
        "sections": sections,
        "section_labels": section_labels,
        "volume_meta": volume_meta,
        "section_order": section_order,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(indices, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Files processed:  {len(files)}")
    print(f"Sections:        {len(section_order)}")
    print(f"Dynasties:       {len(dynasties)} ({', '.join(sorted(dynasties))})")
    print(f"Volumes:         {len(volumes)}")
    print(f"Eras:            {len(eras)}")
    print(f"Era+Year keys:   {len(era_years)}")
    print(f"Western years:   {len(sorted_years)} ({sorted_years[0]} to {sorted_years[-1]})")
    print(f"Centuries:       {len(western_timeline)} ({western_timeline[0]['century']} to {western_timeline[-1]['century']})")
    print(f"Output written to {OUTPUT_FILE}")


def main():
    build_indices()


if __name__ == "__main__":
    main()
