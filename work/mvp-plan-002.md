# MVP Plan: Stage 2 — Flask Backend API

## Goal
Flask app under `src/` that loads `indices.json` and serves the API + static files.

## Files
- `src/app.py` — Flask backend

## Dependencies
- Python 3.8+
- Flask — installed via `uv`:
  ```bash
  uv venv && source .venv/bin/activate && uv pip install -r requirements.txt
  ```
- `uv` located at `~/.local/bin/uv`

## Tasks

### 2.1 App skeleton
- Single file `src/app.py`
- Load `indices.json` from repo root at startup:
  ```python
  import json, os
  BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  INDEX_PATH = os.path.join(BASE_DIR, "indices.json")
  with open(INDEX_PATH, "r", encoding="utf-8") as f:
      indices = json.load(f)
  ```
- Handle missing `indices.json` with clear error message and exit
- Static file serving from `src/static/` via Flask's `send_from_directory`
- Template folder: `src/templates/`

### 2.2 GET `/` — Serve HTML
- Render `index.html`

### 2.3 GET `/api/indices` — Return index metadata
- Return `dynasties`, `volumes`, `eras`, `era_years`, `western_years`, `western_timeline`, `volume_meta`, `section_order`
- No `sections` (text data excluded, loaded on demand)

### 2.4 GET `/api/section/<section_id>` — Return full section
- Return section from `indices["sections"][section_id]`
- Include `texts` array
- 404 if not found

### 2.5 GET `/api/sections/batch?ids=001-0,001-5,...` — Batch load
- Accept comma-separated section IDs
- Return dict: `{section_id: section_data, ...}`
- Skip invalid IDs silently

### 2.6 GET `/api/search?q=<query>` — Search across indices
- Search across: dynasty names, volume names, era names, era_years, western years
- Case-insensitive substring match
- Return list of result objects with `type`, `id`/`section_id`, `label`
- Limit to top 20 results
- Prioritize exact matches over substring matches
- For `era` type results, include `section_ids` so frontend can expand tree

### 2.7 Error handling
- 404 for unknown sections
- 400 for missing query params (empty `q` in search)
- Generic 500 handler

### 2.8 Run configuration
```python
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
```

## Verification
- Activate venv: `source .venv/bin/activate`
- `python src/app.py` starts without error
- Curl:
  - `curl http://localhost:5000/api/indices` → returns metadata
  - `curl http://localhost:5000/api/section/001-0` → returns texts
  - `curl http://localhost:5000/api/search?q=403` → returns search results
  - `curl http://localhost:5000/` → returns HTML (may be empty initially)

## Time Estimate
~1 hour
