# MVP Plan: Stage 1 — ETL Index Building

## Goal
Build a single `indices.json` from the 294 `semantic_json/*.json` files.

## Script
`scripts/build_indices.py`

## Tasks

### 1.1 Read all semantic JSON files
- Iterate `semantic_json/` sorted by filename.
- Parse each file as JSON.

### 1.2 Assign section IDs
- Format: `{file_number}-{section_index}`
  - `file_number`: 3-digit zero-padded from filename (e.g. `001`)
  - `section_index`: 0-based index within the file's `sections` array
- Example: `"001-0"` is the first section in `001.json`
- Build `section_order`: flat ordered list of all section IDs

### 1.3 Build dynasty index
- For each section, extract dynasty from `volume_name`:
  - Strip `【` and `】`, strip whitespace
  - Take substring before `纪` (e.g. `周纪一` → `周`)
  - If `volume_name` is empty, use `""` as key
- Map: `{dynasty_name: [section_ids]}` (append in file order)

### 1.4 Build volume index
- Map: `{volume_name: [section_ids]}`
- Use the cleaned volume_name (strip brackets and whitespace) as key

### 1.5 Build era index
- Map: `{era_name: [section_ids]}`

### 1.6 Build era+year index (one-to-one)
- Map: `{"{era_name}|{era_year}": section_id}`

### 1.7 Build western year index (one-to-one)
- Map: `{"403 BC": "001-0", "529 AD": "..."}`
- Also track the ordered list of **unique** western years for the timeline

### 1.8 Build western year timeline
- Compute unique western years across all sections
- Sort chronologically: BC years descending (403 BC > 402 BC ... > 1 BC), then AD years ascending (1 AD > 2 AD ...)
- Group into centuries:
  - Century computation: year N BC → `ceil(N/100)`th Century BC (e.g. 403 BC → 5th)
  - Year N AD → `ceil(N/100)`th Century AD (e.g. 529 AD → 6th)
  - Special: 1-99 AD → "1st Century AD"
  - Use ordinal suffixes correctly: "1st", "2nd", "3rd", "4th-10th"
- Output format:
  ```json
  [
    {"century": "5th Century BC", "years": ["403 BC", "402 BC", ...]},
    ...
  ]
  ```

### 1.9 Build sections store
- Map: `{section_id: {volume_name, dynasty, era_name, era_year, year, texts, volume_time_cycle}}`
- Include extracted `dynasty` to avoid client-side re-extraction

### 1.10 Build volume metadata
- Map: `{cleaned_volume_name: {time_cycle, file_index, dynasty, raw_volume_name}}`
- `raw_volume_name` = original value (e.g. `"【周纪一】 "`)

### 1.11 Write output
- Write `indices.json` to repo root with `ensure_ascii=False, indent=2`, trailing newline
- Print summary: total files, total sections, unique dynasties, unique years, centuries covered

## Verification
- Run `python scripts/build_indices.py`
- Verify: 294 files, 1405 sections, 1344 unique western years, 16 centuries (5th BC to 10th AD)
- Spot-check: "403 BC" → section "001-0"
- Spot-check: `western_timeline[0]` has century "5th Century BC" with "403 BC" as first entry

## Time Estimate
~45 min
