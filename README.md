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
| `raw_json_converted/` | Same data with escapes decoded to Unicode, pretty-printed |
| `semantic_json/` | Restructured: grouped by year-section with `year` field (1405 sections) |
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
      "era_year": "二十三年（戊寅，公元前四零三年）",
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
python scripts/convert_unicode.py     # raw_json → raw_json_converted
python scripts/restructure_json.py    # raw_json_converted → semantic_json
python scripts/verify_counts.py       # validate no texts were lost
python scripts/build_indices.py      # semantic_json → indices.json (web app)
```

## Web App API

The Flask backend serves a single-page app with multi-index browsing.

| Endpoint | Description |
|---|---|
| `GET /` | Main HTML page |
| `GET /api/indices` | All index metadata (dynasties, volumes, eras, timeline) |
| `GET /api/section/<id>` | Full section data including text paragraphs |
| `GET /api/sections/batch?ids=...` | Batch load multiple sections |
| `GET /api/search?q=...` | Search across all indices |

## Navigation Indices

The web app supports browsing by:

- **Dynasty** (朝代): 周, 汉, 唐, 宋, 晋, 梁, 齐, 魏, 秦, 陈, 隋
- **Later Dynasties** (后代): 后周, 后唐, 后晋, 后梁, 后汉
- **Volume** (卷): e.g. 周纪一, 汉纪四十二
- **Era name** (年号): e.g. 威烈王, 显王
- **Era + year** (年号+年): e.g. 威烈王二十三年
- **Western year** (公元): e.g. 403 BC, 529 AD

## Tech Stack

- **Backend**: Python 3.12+ / Flask / gunicorn (production WSGI)
- **Frontend**: Vanilla HTML, CSS, JavaScript (ES modules, no build step, no frameworks)
- **Data**: Pre-built JSON index (ETL from semantic JSON files)
- **Package manager**: uv
