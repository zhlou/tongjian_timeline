# AGENTS.md

> When making changes to the project, always update both `AGENTS.md` and `README.md`
> to reflect the current state.

## Repo overview

Data-processing pipeline for 资治通鉴 (Zizhi Tongjian) historical text corpus.

## Directory layout

| Dir | Purpose |
|---|---|
| `raw_json/` | Original JSON — Chinese text as `\uXXXX` escapes (294 files, one per page) |
| `raw_json_converted/` | Same data with `\uXXXX` decoded to real Unicode, pretty-printed |
| `semantic_json/` | Restructured: flat name/text pairs → grouped by year-section |
 | `scripts/` | Processing scripts |
 | `src/` | Web app (Flask backend + frontend) |
| `Dockerfile` | Container build for deployment |
| `.dockerignore` | Build-context exclusions |

 ## Web app

### Local dev

Requires Python venv with Flask:
```bash
uv venv && source .venv/bin/activate && uv pip install -r requirements.txt
```

```bash
python scripts/build_indices.py   # semantic_json → indices.json (must run first)
python src/app.py                 # start web server at http://localhost:5000
```

### Docker

```bash
docker build -t tongjian-timeline .
docker run -p 5000:5000 tongjian-timeline
```

Base: `python:3.12-slim` with gunicorn (4 workers) as the production WSGI server.
Debug mode controlled via `FLASK_DEBUG` env var (default off).

Responsive breakpoints in `src/static/style.css`:
- ≤900px: 2-column (220px tree + content), timeline hidden
- ≤600px: single-column, slimmer padding (12px), tree off-canvas overlay
- ≥768px landscape: 3-column with 140px timeline restored

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

Run all from repo root:

```bash
python scripts/convert_unicode.py    # raw_json → raw_json_converted
python scripts/restructure_json.py   # raw_json_converted → semantic_json
python scripts/verify_counts.py      # validate no texts were lost
python scripts/build_indices.py     # semantic_json → indices.json (for web app)
```

**Always verify** after restructuring:
```bash
python scripts/verify_counts.py
```
Should report `OK: all 294 files match` with identical totals.
