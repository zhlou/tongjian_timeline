# AGENTS.md

> When making changes to the project, always update both `AGENTS.md` and `README.md`
> to reflect the current state.

## Repo overview

Data-processing pipeline for 资治通鉴 (Zizhi Tongjian) historical text corpus.

## Directory layout

| Dir | Purpose |
|---|---|
| `raw_json/` | Original JSON — Chinese text as `\uXXXX` escapes (294 files, one per page) |
| `raw_json_converted/` | **Source of truth** — Unicode-decoded, bracket-stripped, encoding-corrected, with moji-bake fixes baked in. `raw_json/` is kept as provenance archive only. |
| `semantic_json/` | Restructured: flat name/text pairs → grouped by year-section, with `era_name`, `era_year` (paren-stripped), `ganzhi`, `year`, `texts`. `volume_name` is bracket-stripped; `volume_time_cycle` has encoding corruptions fixed (`]` → `黓`, etc.). |
| `scripts/` | Processing scripts |
| `src/` | Web app (Flask backend + frontend) |
| `src/static/js/` | Frontend ES modules (10 files, no build step) |
| `Dockerfile` | Container build for deployment |
| `.dockerignore` | Build-context exclusions |

## Frontend modules

`src/static/js/` — vanilla ES modules, no build step. Entry: `main.js`.

| Module | Purpose |
|---|---|
| `dom.js` | `document.getElementById()` refs for all `$`-prefixed elements |
| `state.js` | Global mutable `state` object, session persistence, viewport helpers |
| `utils.js` | `el()`, `esc()`, `fetchJSON()`, loading indicator, CSS.escape polyfill, pulseElement |
| `tree.js` | Dynasty/volume/era/year tree: build with inline ganzhi + Western year on each leaf, year-range badges on higher-level nodes, toggle, expand/collapse, sync-to-section |
| `content.js` | Section blocks: batch load, DOM render, virtual-scroll prepend/append, recycling; volume banner (name + time_cycle) on `is_volume_start` sections; section header is `era · ganzhi · (year)` |
| `navigation.js` | Nav, scroll-observer, active-section detection, prefetch, progress bar, instant-jump + WAAPI pulse |
| `search.js` | Debounced typeahead search with dropdown (dynasty/volume/era/era_year/year/ganzhi types) |
| `keyboard.js` | `/`, Escape, j/k, ArrowUp/Down shortcuts |
| `mobile.js` | Off-canvas tree overlay, backdrop, outside-click dismiss |
| `main.js` | `init()` orchestrator, `DOMContentLoaded` entry point |

One intentional circular import: `tree.js` ↔ `navigation.js` (navigate-to-section in tree leaf click handler vs sync-tree-to-section in active-section detection). ES module live bindings resolve this at call time.

### Navigation feedback

Section jumps use **instant** scroll (no auto-scroll). The newly-active block is highlighted with an 800ms yellow-flash + orange inset border-ring via `pulseElement()` (`utils.js`) — Web Animations API, cancels any in-flight animation on the same element and starts a fresh one, so the flash fires reliably on every jump (close, far, initial load, rapid `j`/`k` repeats). The active tree leaf is marked with the same `.active` class (left blue border) and pulsed in step.

Replacing the previous smooth-scroll was needed because the browser's default smooth animation could overrun 5s for large jumps inside the virtualized container; that was the source of the mid-scroll `state.syncPending` watchdog timeout.

When `navigateToSection` triggers a full re-render (target outside the ±10 rendered window), newly built blocks additionally get the `.faded-in` class for a brief 250ms opacity fade-in, covering the blank-flash during the `/api/sections/batch` fetch.

Smooth scroll is still used for the sidepanel auto-alignment (tree leaf, search dropdown rows) where the user is visually tracking a small element.

### Tree labels

Each node carries four pieces separated into spans for clean alignment:

- `.tree-label` — flex-grow 1, ellipsises on narrow screens (volume name, era name, era_year for leaves)
- `.tree-gz` — ganzhi cycle (e.g. `戊寅`), small muted, fixed min-width
- `.tree-yr` — Western year range (`403 BC – 369 BC`) on higher-level nodes; single year (`403 BC`) on leaves; tabular numerals, fixed min-width

`sessionStorage` key bumped to `ztj_state_v2` when the temporal-state (`expandedCenturies`) field was dropped alongside the timeline panel.

## Web app

### Local dev

Requires Python venv with Flask:
```bash
uv venv && source .venv/bin/activate && uv pip install -r requirements.txt
```

```bash
python scripts/restructure_json.py   # raw_json_converted → semantic_json (one pass — populates year + ganzhi)
python scripts/build_indices.py     # semantic_json → indices.json (must run second)
python src/app.py                   # start web server at http://localhost:5000
```

### Docker

```bash
docker build -t tongjian-timeline .
docker run -p 5000:5000 tongjian-timeline
```

Base: `python:3.12-slim` with gunicorn (4 workers) as the production WSGI server.
Debug mode controlled via `FLASK_DEBUG` env var (default off).

Responsive breakpoints in `src/static/style.css`:
- ≤900px: tree gets extra touch padding, section padding halved
- ≤600px: single-column, slimmer padding (12px), tree off-canvas overlay
- ≥768px landscape: previously restored timeline column; no longer relevant after Phase 4

## Data structure quirk

Each `raw_json_converted/*.json` is a flat array of `[{name, text}]` blocks. The flow is:

```
[vol_name, vol_time_cycle]        → volume header (once per file)
[time_era_name, time_era_year]    → year marker (raw: "二十三年（戊寅，公元前四零三年）")
[main_text]                       → paragraph (1–50+ per year)
…
```

`scripts/restructure_json.py` groups these into:
```json
{
  "volume_name": "周纪一",
  "volume_time_cycle": "起著雍摄提格，尽玄黓困敦，凡三十五年。",
  "sections": [
    {
      "era_name": "威烈王",
      "era_year": "二十三年",
      "ganzhi": "戊寅",
      "year": "403 BC",
      "texts": ["…", "…"]
    }
  ]
}
```

`restructure_json.py` also extracts ganzhi and Western year from `era_year` (paren-stripped). `volume_name` and `volume_time_cycle` corrections (brackets, encoding fixes, `◎`-merge splits) are now baked into `raw_json_converted/` via `fix_raw_converted.py`.

`scripts/build_indices.py` adds `is_volume_start: true` to the first section of each volume. The first section of each volume renders a volume banner (name + time_cycle) in the frontend.

The parenthetical in `time_era_year` is parsed in the same pass that builds each section; both ganzhi and Western year become top-level fields. The remaining `era_year` value is the cleaned-up text without the parenthetical (e.g. just `"二十三年"`).

## Scripts

Run all from repo root:

```bash
python scripts/convert_unicode.py      # raw_json → raw_json_converted
python scripts/fix_raw_converted.py     # bake vol_name/time_cycle corrections in-place
python scripts/correct_text.py          # fix ~9,800 ASCII/moji-bake via Kanripo reference
python scripts/restructure_json.py      # raw_json_converted → semantic_json
python scripts/verify_counts.py         # validate no texts were lost
python scripts/build_indices.py         # semantic_json → indices.json (for web app)
```

`scripts/add_year_field.py` is **deprecated** — kept as a helper library for legacy callers. Running it standalone prints a deprecation notice and exits unless invoked with `--apply`.

### Text correction

`scripts/correct_text.py` fixes ~9,800 ASCII and moji-bake corruptions in `raw_json_converted/` by aligning against the Kanripo KR2b0007 reference (Siku Quanshu edition). The bulk of the corruption comes from GBK trail bytes in ASCII range (0x40–0x7E) that survived when lead bytes were lost (e.g. `T` → `蜹`, `p` → `朱泚`).

```bash
# Clone reference once:
git clone https://github.com/kanripo/KR2b0007.git /tmp/reference_kanripo

# Correct all 294 volumes:
python scripts/correct_text.py

# After correction, regenerate and re-run pipeline:
python scripts/restructure_json.py
python scripts/build_indices.py
```

Options:
- `--dry-run` / `-n` : report without modifying
- `--review` / `-r` : show auto-fix + CJK mismatch review items
- `--volume N` : single volume only

The reference goes to `/tmp/reference_kanripo` by default; override with env var `REF_DIR`. A backup is created in `raw_json_converted_backup/`.

### Epub-based correction

`zizhitongjian.epub` is a Wikisource-sourced epub that serves as a secondary reference. It is not checked into the repo.

| Script | Purpose |
|---|---|
| `unpack_epub.py` | Extract 294 xhtml files from the epub into `epub_text/` plain text |
| `check_against_epub.py` | Find remaining ASCII→CJK moji-bake (165 fixes beyond Kanripo) |
| `fix_multi_char_mojibake.py` | Fix radical+component splits (纟林→綝, 钅句→钩, etc.; 219 fixes) |

```bash
python scripts/unpack_epub.py           # one-time: extract epub → epub_text/
python scripts/check_against_epub.py    # apply ASCII→CJK fixes
python scripts/fix_multi_char_mojibake.py  # apply radical-split fixes
```

**Validation helpers:**

| Script | Purpose |
|---|---|
| `detect_era_anomalies.py` | Find sections where `era_year` decreases under same `era_name` (should return 0) |
| `find_missing_era.py` | Find sections with empty `era_name` or `era_year` |
| `count_year_sections.py` | Tally year-sections per file |

**Always verify** after restructuring:
```bash
python scripts/verify_counts.py        # expect 41 files with 45 total stripped (ruler names promoted to era_name)
python scripts/detect_era_anomalies.py # expect 0 issues
```
