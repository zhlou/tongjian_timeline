# AGENTS.md

## Repo overview

Data-processing pipeline for 资治通鉴 (Zizhi Tongjian) historical text corpus.

## Directory layout

| Dir | Purpose |
|---|---|
| `raw_json/` | Original JSON — Chinese text as `\uXXXX` escapes (294 files, one per page) |
| `raw_json_converted/` | Same data with `\uXXXX` decoded to real Unicode, pretty-printed |
| `semantic_json/` | Restructured: flat name/text pairs → grouped by year-section |
| `scripts/` | Processing scripts |

## Data structure quirk

Each `raw_json_converted/*.json` is a flat array of `[{name, text}]` blocks. The flow is:

```
[vol_name, vol_time_cycle]        → volume header (once per file)
[time_era_name, time_era_year]    → year marker
[main_text]                       → paragraph (1–50+ per year)
[main_text]                       → …
[time_era_name, time_era_year]    → next year
…
```

`semantic_json/*.json` groups these into `{volume_name, volume_time_cycle, sections: [{era_name, era_year, texts[]}]}`.

## Scripts

Run all from repo root (`/home/zhlou/Work/tongjian-timeline`):

```bash
python scripts/convert_unicode.py    # raw_json → raw_json_converted
python scripts/restructure_json.py   # raw_json_converted → semantic_json
python scripts/verify_counts.py      # validate no texts were lost
```

**Always verify** after restructuring:
```bash
python scripts/verify_counts.py
```
Should report `OK: all 294 files match` with identical totals.

## Edge case

Some files (e.g. 153) have `main_text` entries without a preceding `time_era_name`/`time_era_year` block. The restructure script handles this by creating a section with empty `era_name`/`era_year`.
