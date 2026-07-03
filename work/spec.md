# Spec: Zizhi Tongjian Multi-Index Web App (MVP)

## Overview
An interactive single-page web app for browsing Zizhi Tongjian (资治通鉴) via multiple navigational indices. Backend: Python/Flask with pre-built in-memory indices. Frontend: vanilla HTML/CSS/JS.

## Data Source
`semantic_json/*.json` — 294 files, 1405 year-sections.

### Structure per file
```json
{
  "volume_name": "【周纪一】",
  "volume_time_cycle": "起著雍摄提格...",
  "sections": [
    {
      "era_name": "威烈王",
      "era_year": "二十三年（戊寅，公元前四零三年）",
      "year": "403 BC",
      "texts": ["paragraph1", "paragraph2", ...]
    }
  ]
}
```

### Edge cases (verified 2025-07-02)
- All 294 files have valid `volume_name`, all 1405 sections have valid `era_name` and `era_year`, all have valid `year`.
- No empty fields. Edge case handling is still implemented defensively.

## ETL (Index Building)

### Input
294 `semantic_json/*.json` files.

### Processing
1. Read all JSON files sequentially (sorted by filename).
2. Assign each section a unique ID: `{file_index}-{section_index}` (file index = 001-294, section index = 0-based within file).
3. Extract dynasty name from `volume_name`:
   - Strip `【` and `】`, strip trailing whitespace, then take characters before `纪`
   - e.g. `【周纪一】 ` → `周`, `【汉纪四十二】 ` → `汉`
4. Build the following index structures:
   - **Dynasty index**: `{dynasty_name: [section_ids]}` (sorted by section order)
   - **Volume index**: `{volume_name: [section_ids]}` (preserving file order)
   - **Era index**: `{era_name: [section_ids]}`
   - **Era+Year index**: `{"{era_name}|{era_year}": section_id}` (one-to-one)
   - **Western year index**: `{"403 BC": section_id, "529 AD": section_id}` (one-to-one)
   - **Western year timeline**: ordered list of all unique western years for the timeline panel
5. Build section data store: `{section_id: {volume_name, era_name, era_year, year, texts, volume_time_cycle}}`
6. Build volume metadata: `{volume_name: {time_cycle, file_index, dynasty}}`

### Output
Single file: `indices.json` in repo root, containing:
```json
{
  "dynasties": { "周": ["001-0", "001-1", ...], "汉": [...], ... },
  "volumes": { "周纪一": ["001-0", ...], ... },
  "eras": { "威烈王": ["001-0", ...], ... },
  "era_years": { "威烈王|二十三年（戊寅，公元前四零三年）": "001-0", ... },
  "western_years": { "403 BC": "001-0", "402 BC": "001-1", ... },
  "western_timeline": [
    {"century": "5th Century BC", "years": ["403 BC", "402 BC", ...]},
    {"century": "4th Century BC", "years": [...]},
    ...
    {"century": "10th Century AD", "years": [...]}
  ],
  "sections": {
    "001-0": {
      "volume_name": "【周纪一】",
      "dynasty": "周",
      "era_name": "威烈王",
      "era_year": "二十三年（戊寅，公元前四零三年）",
      "year": "403 BC",
      "texts": ["paragraph...", ...],
      "volume_time_cycle": "起著雍摄提格..."
    },
    ...
  },
  "volume_meta": {
    "【周纪一】": { "time_cycle": "...", "file_index": "001", "dynasty": "周" },
    ...
  },
  "section_order": ["001-0", "001-1", ...]
}
```

### ETL Script
`scripts/build_indices.py` — reads `semantic_json/`, writes `indices.json`.

## Flask Backend

### Location
`src/app.py`

### Startup
- Load `indices.json` from repo root (one `json.load()` call).
- Serve on `0.0.0.0:5000` (configurable via env `PORT`).

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Serve main HTML page |
| GET | `/api/indices` | Return all index metadata (no text data) |
| GET | `/api/section/<section_id>` | Return full section data including `texts` |
| GET | `/api/sections/batch?ids=001-0,001-5,...` | Return multiple sections at once |
| GET | `/api/search?q=威烈王` | Search across all indices |
| GET | `/static/<path>` | Serve static files (CSS, JS) |

### Search Response
```json
[
  {"type": "dynasty", "id": "dynasty:周", "label": "Dynasty: 周"},
  {"type": "volume", "id": "volume:周纪一", "label": "Volume: 周纪一", "dynasty": "周"},
  {"type": "era", "id": "era:威烈王", "label": "Era: 威烈王", "section_ids": [...]},
  {"type": "era_year", "section_id": "001-0", "label": "威烈王 二十三年 (403 BC)"},
  {"type": "year", "section_id": "001-0", "label": "403 BC - 威烈王 二十三年"}
]
```

## Frontend

### Locations
- `src/templates/index.html`
- `src/static/style.css`
- `src/static/app.js`

### Layout (3-column)
```
+------------+------------+------------------------------------------+
|            |            |  Quick Search Bar                         |
|   Tree     |  Western   |------------------------------------------|
| Navigator  |  Year      |                                           |
|            |  Timeline  |           Content Panel                   |
| Dynasty    |            |  (continuous scroll, no page breaks)      |
|  ▶ 周      | ◼ 4th C. BC|                                           |
|   ▶周纪一  |   403 BC ──│── sync via IntersectionObserver ───│  |
|    ▶威烈王 |   402 BC   | ┌─ section 001-0 ────────────────────┐   |
|   * 23年   |   401 BC   | │ 威烈王 二十三年 (403 BC)           │   |
|      24年   |   400 BC   | │ paragraph text...                   │   |
|   ▶周纪二  | ◼ 5th C. BC| │ paragraph text...                   │   |
|  ▶ 汉      | ◼ 3rd C. BC| └────────────────────────────────────┘   |
|            |            | ┌─ section 001-1 ────────────────────┐   |
|            |            | │ 威烈王 二十四年 (402 BC)           │   |
|            |            | │ paragraph text...                   │   |
|            |            | └────────────────────────────────────┘   |
|            |            | ┌─ section 001-2 ────────────────────┐   |
|            |            | │ 元年 (401 BC)                      │   |
|            |            | │ ...                                 │   |
+------------+------------+------------------------------------------+
```

### Sidebar 1: Tree Navigator (leftmost column)
- Width: ~260px. Internally scrollable (`overflow-y: auto`).
- **Level 1**: Dynasty (e.g. 周, 汉, 唐...)
- **Level 2**: Volume (e.g. 周纪一, 周纪二...)
- **Level 3**: Era name (e.g. 威烈王)
- **Level 4**: Year entry — era_year + western year, e.g. "二十三年 (403 BC)"
- Clicking a level-4 entry loads that section in the content panel and **syncs** the western year timeline.
- Tree state (expanded nodes) persists in `sessionStorage`.

### Sidebar 2: Western Year Timeline (middle column)
- Width: ~180px. Internally scrollable.
- Organized by **century** groups — collapsible sections:
  - "5th Century BC", "4th Century BC", ..., "1st Century BC", "1st Century AD", ..., "10th Century AD"
- Each century section lists its years (e.g. "403 BC", "402 BC", ...).
- **Century jump controls**: At the top, an input or dropdown to jump directly to a century (e.g. type "4th Century BC" or use arrow steppers).
- Clicking a year in the timeline loads that section and **syncs** the tree navigator.
- Active year is highlighted. When tree navigates, the timeline auto-scrolls to the matching year.

### Sync Behavior (3-way lock-step)
The three panels are always consistent via bidirectional sync:

**Tree/Timeline → Content (explicit navigation)**
- Clicking a year in tree or timeline: content scrolls to that `<section>` via `scrollIntoView`.

**Content → Tree/Timeline (scroll-driven)**
- `IntersectionObserver` fires as the user scrolls. When a section passes 50% viewport:
  1. Tree auto-expands ancestors, highlights the matching year, scrolls it into view.
  2. Timeline highlights the matching western year, scrolls it into view.
  3. URL hash updated to `#section=001-0`.

This ensures whichever way the user navigates — tree click, timeline click, search result, or scrolling — all three panels stay in lock-step.

### Quick Search Bar
- Positioned at top of content panel.
- Debounced 300ms, queries `/api/search?q=...`.
- Dropdown with results categorized by type. Click navigates to section.
- Keyboard: `/` to focus, `Escape` to close.

### Content Panel — Continuous Scroll
All section texts are rendered as one continuous scrollable document. As the user scrolls, sections flow seamlessly one after another.

#### Section rendering
- Each section rendered as `<section data-section-id="001-0">` with:
  - A section header containing `volume_name`, `era_name`, `era_year` + `year` (sticky or inline)
  - All `texts` paragraphs below
- Section headers are visually distinct (e.g. slightly larger, background tint) but inline in the scroll flow.

#### Sync via IntersectionObserver
- An `IntersectionObserver` watches all rendered `<section>` elements at `threshold: 0.5`.
- When a section crosses 50% viewport visibility (either direction):
  1. That section becomes the "active" section.
  2. **Tree panel**: auto-expands ancestors, highlights the matching year node, scrolls it into view.
  3. **Timeline panel**: highlights the matching western year, scrolls it into view.
  4. **URL hash**: updated to `#section=001-0` via `history.replaceState`.
- The active section is the one with the largest intersecting ratio when multiple sections are partially visible.

#### Navigation from side panels
- Clicking a year in either the tree or timeline scrolls the content to that `<section>` using `element.scrollIntoView({ behavior: "smooth", block: "start" })`.
- The IntersectionObserver will then fire and complete the sync cycle.

#### Lazy loading
- Only the initial window (~20 sections around starting position) is rendered on load.
- As the user scrolls near the visible boundary (within ~2000px), the next/previous batch of sections is fetched via `/api/sections/batch` and appended/prepended to the DOM.
- A max of ~100 rendered sections is kept in DOM at any time; sections far outside the viewport are removed (DOM recycling) to maintain performance.

#### Keyboard shortcuts
- ArrowUp / ArrowDown: scroll content by one section (scroll the next `<section>` into view).
- `/`: focus search input.
- Escape: close search dropdown.

### Technologies
- Vanilla HTML5, CSS3, JavaScript (ES6+). No frameworks. No build step.
- CSS Grid for 3-column layout.
- `fetch()` for API calls.
- `IntersectionObserver` for scroll-sync.

### Scrolling & Long Lists
- Content panel: `overflow-y: auto`, all section texts flow continuously.
- Tree and timeline panels: independently scrollable (`overflow-y: auto`), auto-sync to content scroll position.
- Century jump controls in timeline for quick century-level navigation.

## Project File Structure
```
scripts/build_indices.py       # ETL: semantic_json → indices.json
src/app.py                     # Flask backend
src/templates/index.html       # Main HTML page
src/static/style.css           # Styles
src/static/app.js              # Frontend logic
indices.json                   # Pre-built index data (generated, git-ignored)
```

## Constraints
- Python 3.8+
- No frontend frameworks
- No additional Python packages beyond Flask
- Run from repo root: `python src/app.py`
- Build indices: `python scripts/build_indices.py`
