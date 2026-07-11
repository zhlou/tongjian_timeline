# 资治通鉴 (Zizhi Tongjian) Data Pipeline &amp; Web App

Data-processing pipeline and interactive web browser for the Zizhi Tongjian historical text corpus.

## Quick Start

### Docker (recommended)

```bash
git clone <repo>
cd tongjian_timeline
docker build -t tongjian-timeline .
docker run -p 5000:5000 tongjian-timeline
```

Open **http://localhost:5000** in your browser.

### Local dev

```bash
git clone <repo>
cd tongjian_timeline

uv venv && source .venv/bin/activate && uv pip install -r requirements.txt

python scripts/build_indices.py   # generates indices.json (required)
python src/app.py                 # start at http://localhost:5000
```

## Directory Layout

| Dir | Purpose |
|---|---|
| `raw_json/` | Original JSON — Chinese text as `\uXXXX` escapes (294 files) |
| `raw_json_converted/` | **Source of truth** — Unicode-decoded, with corrections baked in |
| `semantic_json/` | Restructured: grouped by year-section with `era_year`, `ganzhi`, and `year` (1405 sections) |
| `scripts/` | Processing and ETL scripts |
| `src/` | Web app (Flask backend + templates + static) |
| `work/` | Spec and implementation plan |
| `Dockerfile` | Container build for deployment |
| `.dockerignore` | Build-context exclusions |
| `.venv/` | Python virtual environment (git-ignored) |

## Data Format

Each `semantic_json/*.json`:
```json
{
  "volume_name": "周纪一",
  "volume_time_cycle": "起著雍摄提格...",
  "sections": [
    {
      "era_name": "威烈王",
      "era_year": "二十三年",
      "ganzhi": "戊寅",
      "year": "403 BC",
      "texts": ["初命晋大夫魏斯...", "..."]
    }
  ]
}
```

294 files · 1405 year-sections · 16 dynasties · 403 BC to 959 AD

## Scripts

Run all from repo root with Python 3.8+:

```bash
python scripts/convert_unicode.py      # raw_json → raw_json_converted
python scripts/fix_raw_converted.py     # bake vol_name/time_cycle corrections in-place
python scripts/correct_text.py          # fix ASCII/moji-bake via Kanripo reference
python scripts/restructure_json.py      # raw_json_converted → semantic_json
python scripts/verify_counts.py         # validate no texts were lost (expects 41 files × 1-2 stripped ruler-name texts)
python scripts/build_indices.py         # semantic_json → indices.json (web app)
```

## Web App API

The Flask backend serves a single-page app with multi-index browsing.

| Endpoint | Description |
|---|---|
| `GET /` | Main HTML page |
| `GET /api/indices` | All index metadata (dynasties, volumes, eras, ganzhi_index, year ranges) |
| `GET /api/section/<id>` | Full section data including text paragraphs |
| `GET /api/sections/batch?ids=...` | Batch load multiple sections |
| `GET /api/search?q=...` | Search across all indices |

## Navigation Indices

The web app supports browsing by:

- **Dynasty** (朝代): 周, 秦, 汉, 魏, 晋, 宋, 齐, 梁, 陈, 隋, 唐, 后梁, 后唐, 后晋, 后汉, 后周
- **Volume** (卷): e.g. 周纪一, 汉纪四十二
- **Era name** (年号): e.g. 威烈王, 显王
- **Era + year** (年号+年): e.g. 威烈王二十三年
- **Western year** (公元): e.g. 403 BC, 529 AD
- **Ganzhi** (天干地支): e.g. 戊寅, 甲子 — each match lists every section sharing that stem-branch cycle, ordered chronologically

Tree leaves display `era_year`, `ganzhi`, and Western year inline; dynasty / volume / era nodes show their `year_range` (e.g. `403 BC – 369 BC`). The standalone timeline panel was removed in favour of this inline metadata.

### Navigation

Section jumps are instant — clicking a tree leaf or pressing `j/k/↑/↓` snaps directly to the target and pulses a brief yellow highlight (~800ms) on the active content block and tree leaf. Far jumps that need to re-render blocks fade in the new content (~250ms) to mask the loading state.

## Tech Stack

- **Backend**: Python 3.12+ / Flask / gunicorn (production WSGI)
- **Frontend**: Vanilla HTML, CSS, JavaScript (ES modules, no build step, no frameworks)
- **Data**: Pre-built JSON index (ETL from semantic JSON files)
- **Package manager**: uv
