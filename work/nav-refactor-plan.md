# Navigation Refactor — Plan: Drop Timeline Panel, Inline Year on Tree

> Source spec: `work/refactor-navigation.md`

## Goal

Replace the standalone timeline (century / Western-year) panel with year information embedded directly on the tree:

1. **Drop the timeline panel** — `<aside id="sidebar-timeline">`, `timeline.js`, all timeline CSS, `western_timeline` index, etc.
2. **Show the Western year right-aligned on every tree leaf** (e.g. `二十三年 … 403 BC`).
3. **Strip the parenthetical in `era_year`** — `"二十三年（戊寅，公元前四零三年）"` becomes `"二十三年"`.
4. **Show year ranges on higher-level nodes** (era / volume / dynasty) right-aligned, e.g. `周纪 … 403 BC – 369 BC`.
5. Integrate year extraction into the main pipeline — `scripts/add_year_field.py` becomes redundant.

---

## Background

### Current pipeline

```
raw_json  ──convert_unicode──▶  raw_json_converted
            ──restructure────▶  semantic_json  (era_name, era_year, texts only)
            ──add_year_field─▶  semantic_json  (adds "year" field, "403 BC" / "529 AD")
            ──build_indices──▶  indices.json   (used by web app)
```

Year parsing is currently a post-pass in `scripts/add_year_field.py:31-54` (`parse_year()` using regex on the parenthetical). The intent of this refactor is to fold that step into the restructuring pass so the canonical `semantic_json` ships with `year` populated, and so we can rewrite `era_year` to drop the parenthetical in the same pass.

### Current UI behaviour

- **Tree leaf label** (`src/static/js/tree.js:88-89`): single span built from `section_labels[sid]`, which equals `"{era_name} {era_year} ({year})"` after `build_indices.py:140-147`.
- **Content header** (`src/static/js/content.js:16`): same fields are rendered as `era_name  ·  era_year (year)`.
- **Timeline sidebar** (`#sidebar-timeline`): the third grid column listing centuries and individual Western years, with `◀ ▶` century-jump.

### Cross-references to timeline data

`grep western_year\|era_year\|western_timeline src/` shows:

| Location | Field used | After refactor |
|---|---|---|
| `app.py:32-53, 116-133` | `_era_years`, `_western_years` (search dropdown) | **Keep** — search needs both keys |
| `app.py:53` | `western_timeline` index → exposed via `/api/indices` | **Drop** |
| `tree.js:87` | `state.indices.western_years[sid]` → `data-year` (only consumed by `timeline.js`) | **Drop** |
| `timeline.js` (whole file) | `western_timeline`, `western_years` | **Drop module** |
| `main.js:16` | `state.centuryOrder = state.indices.western_timeline.map(...)` | **Drop** |
| `state.js:17, 31, 43` | `state.expandedCenturies` (persisted in session) | **Drop** |
| `dom.js:2-5` | `$timelineContainer`, `$centuryLabel`, `$centuryPrev`, `$centuryNext` | **Drop** |
| `style.css:31-37, 119-197, 382-393, 477-480` | timeline styles + responsive rules | **Drop** |
| `index.html:16-24` | `<aside id="sidebar-timeline">` markup | **Drop** |

Decisions on year-keyed indices:
- `era_years`: keep (search uses it; also matches the user's intent of "era + year" navigation).
- `western_years`: keep (search uses it, key is `year_str → sid`). Tree builds its own per-section `year` from `section_labels` / precomputed `sections[sid].year`.
- `western_timeline`: drop (no remaining consumer; century-jump UI is gone).

---

## Phase 1 — Pipeline: Roll year extraction into restructuring

### 1.1 Move `parse_year()` and `_RE_PAREN` into `restructure_json.py`, and split out `ganzhi`

- **File**: `scripts/restructure_json.py`
- Move the Chinese-digit parser, the paren-detection regex, and the parse helpers from `add_year_field.py:14-54` (`CN_DIGITS`, `parse_cn_num`, `_RE_PAREN`).
- Replace the existing single-output `parse_year()` with two helpers — one returns the ganzhi, another returns the Western year:

  ```python
  def parse_paren_tokens(era_year):
      """Return (raw_inner_str_or_None). Captures everything between parens."""
      m = _RE_PAREN.search(era_year)
      return m.group(1) if m else None

  def parse_ganzhi(inner):
      """'戊寅，公元前三三八年' -> '戊寅'. Returns None if no ganzhi in the parens."""
      if inner is None:
          return None
      for token in re.split(r"[，,、]", inner):
          tok = token.strip().rstrip("年").strip()
          # ganzhi = two CJK chars (one stem + one branch) with no '公元'/'前'
          if (tok and "公元" not in tok and "前" not in tok
              and len(tok) <= 4
              and all('\u4e00' <= ch <= '\u9fff' for ch in tok)):
              return tok
      return None

  def parse_western(inner):
      """'戊寅，公元前四零三年' -> '403 BC'. Returns None when no western year."""
      if inner is None:
          return None
      for token in re.split(r"[，,、]", inner):
          tok = token.strip().rstrip("年").strip()
          if "前" in tok:
              digits = tok.replace("公元前", "").replace("前", "")
              return f"{parse_cn_num(digits)} BC"
          if tok.startswith("公元"):
              return f"{parse_cn_num(tok[2:])} AD"
      return None
  ```

- In the same pass that builds each section from the flat blocks (`restructure_json.py:47-49`), for each `time_era_name + time_era_year` pair:
  1. Strip the parenthetical from `state_year` once, store the stripped value as `era_year`. Use `_RE_PAREN` to detect the shape; if matched, replace with empty string via `re.sub(r"\s*[\uff08(][^\uff09)]*[\uff09)]\s*", "", state_year).strip()`. If unmatched, leave `state_year` alone.
  2. Run `parse_paren_tokens(state_year)` on the *original* paren-bearing string to get `inner`.
  3. `ganzhi = parse_ganzhi(inner)`, `year = parse_western(inner)`.

- **Output shape per section** (`scripts/restructure_json.py:22-27`):
  ```python
  sections.append({
      "era_name": state_name or "",
      "era_year": stripped_era_year,    # e.g. "二十三年" — parens removed
      "ganzhi": ganzhi,                  # e.g. "戊寅"  (NEW: separate field)
      "year": parsed_year,               # e.g. "403 BC" or None
      "texts": state_texts,
  })
  ```

- **Edge cases worth testing**:
  - `元年（戊辰）` → `ganzhi="戊辰"`, `year=None`
  - `三年（辛巳，公元前一零零年）` → already covered above
  - Half-width parens (rare): regex matches both `（...）` and `(...)` via `\uff08`/`\uff09`. Confirm on a sample file.
  - `era_year` with no parens at all: `ganzhi=None`, `year=None`, `era_year` unchanged.

### 1.2 Deprecate `scripts/add_year_field.py`

- Replace the script body with a deprecation warning printed on import / execution:
  ```
  ERROR: scripts/add_year_field.py is no longer needed.
         `python scripts/restructure_json.py` now writes "year" + stripped "era_year" in one pass.
  ```
- Leave the helpers (`parse_year`, `parse_cn_num`, `CN_DIGITS`, `_RE_PAREN`) in place — they are now imported by `build_indices.py` too in Phase 2 for year-range aggregation; this avoids duplicating the regex twice.

### 1.3 Verify

- Run on a single file: `python scripts/restructure_json.py` overwrites `semantic_json/` in place — make sure all 294 files round-trip.
- `python scripts/verify_counts.py` should still report `OK: all 294 files match`.
- Spot-check a known era: `威烈王 二十三年（戊寅，公元前四零三年）` → `{era_year: "二十三年", year: "403 BC"}`.

---

## Phase 2 — Indices: year ranges, drop timeline

### 2.1 Reuse Chinese-year helpers from `add_year_field.py`

- **File**: `scripts/build_indices.py`
- Import `CN_DIGITS`, `parse_cn_num`, `parse_year` from `add_year_field` (or extract into a shared module — preference is to keep them in `add_year_field.py` for now with a deprecation header so we don't proliferate files; once the field no longer needs a post-pass we can rename / move them).
- `parse_year_num(year_str)` already exists at `build_indices.py:50-55` and is what we'll reuse.

### 2.2 Drop `western_timeline`

- **File**: `scripts/build_indices.py:151-180`
- Remove the `western_timeline` aggregation loop entirely. Don't emit the key in `indices`. (Keep it as an empty dict for one cycle if it helps the in-flight deployment; then remove in a follow-up — but flat removal is fine since we control all consumers.)

### 2.3 Build `_range` metadata per dynasty / volume / era

- **File**: `scripts/build_indices.py`, after the per-section loop (around `build_indices.py:130`)
- For each `dynasty`, `volume_name`, `era_name`, compute `(year_min, year_max)` over the section ids in that bucket by:
  1. `int_year = parse_year_num(sections[sid]["year"])`  → `0` when missing.
  2. min is the most-negative int (earliest BC); max is the largest positive int (latest AD).
  3. Format as `"{min_str} – {max_str}"` using a helper:

  ```python
  def format_year(n):
      return f"{abs(n)} BC" if n < 0 else f"{n} AD"
  ```

- Add to existing meta dicts:
  - `volume_meta[cleaned_name]` gains `year_min`, `year_max`, `year_range` (`build_indices.py:102-107`).
  - `dynasty_meta[dynasty]` (new key alongside existing `dynasties` map) gains the same three.
  - `era_meta[era_name]` (new key) gains the same three. (We already have `eras: era → [sid]`; `era_meta` runs parallel to `volume_meta`.)

### 2.4 Tidy `section_labels`

- **File**: `scripts/build_indices.py:140-147`
- With era_year stripped in Phase 1.1, the label no longer needs the `({year})` parenthetical — drop it. Tree leaves only consume the plain `era_year`. Leave the format string as just `f"{era_name} {era_year}"`. The `era_name` repetition is harmless because the era parent still shows above; alternatively, since the era parent already says the era_name, label can be just `era_year`. (See Phase 3.1 below — decide: full or trimmed.)

### 2.5 Build a ganzhi → sections index

- **File**: `scripts/build_indices.py`, in the per-section loop (~line 130) and the final `indices = {...}` block (~line 167).
- While iterating each section, if `section["ganzhi"]` is truthy, push `sid` into a running `ganzhi_index[section["ganzhi"]]` list. Insert the field into the final `indices` dict as:
  ```python
  "ganzhi_index": ganzhi_index,   # {"戊寅": ["001-0", "001-7", ...], ...}
  ```
- Each list should be in `section_order` (i.e. chronological) order — Python dicts preserve insertion order, and since `build_indices.py` already iterates files in order, push-only appends preserve chronological order naturally. Optionally sort by `parse_year_num(section["year"])` for safety (most will already be in order).
- Sanity: a 1405-section corpus spanning 1362 years (403 BC → 959 AD) gives 60 ganzhi tokens, so each list has ~22 entries on average; largest is at most ~27.

### 2.6 Verify indices

- `python scripts/build_indices.py` should still print `Sections: 1405` (unchanged).
- Spot-check `year_range` on `周纪一`: `403 BC – 369 BC`. On `周纪二`: expect `368 BC – 321 BC` (verifies the BC numbering boundary). On the final Song dynasty: `960 AD – 959 AD` for the closing volumes (confirm with the corpus).
- Spot-check `ganzhi_index["戊寅"]`: should be a non-empty list of sids each tagged with the era-year that starts with `戊寅` (this very first ganzhi appears at `001-0` = `威烈王二十三年`).

---

## Phase 3 — Tree: right-aligned year on every node

### 3.1 Build tree leaves with label + ganzhi + year

- **File**: `src/static/js/tree.js`, replace lines `tree.js:84-89`:
  ```js
  // before:
  const yNode = el("div", "tree-node tree-leaf");
  yNode.dataset.type = "year";
  yNode.dataset.sectionId = sid;
  yNode.dataset.year = state.indices.western_years[sid] || "";
  const label = state.indices.section_labels[sid] || sid;
  yNode.innerHTML = `<span class="tree-label">${label}</span>`;

  // after:
  const sec = state.indices.sections[sid] || {};
  const yNode = el("div", "tree-node tree-leaf");
  yNode.dataset.type = "year";
  yNode.dataset.sectionId = sid;
  yNode.innerHTML = `
    <span class="tree-toggle"></span>
    <span class="tree-label">${esc(sec.era_year || sid)}</span>
    <span class="tree-gz">${esc(sec.ganzhi || "")}</span>
    <span class="tree-yr">${esc(sec.year || "")}</span>`;
  ```
- Drop `data-year` (no longer wired to anything).
- Notes:
  - We now read `sec.ganzhi` and `sec.year` from `state.indices.sections[sid]` (always populated by Phase 1.1+2.x).
  - Empty `<span class="tree-toggle">` keeps the indent consistent with parent nodes even when no toggle is needed — alternatively hide via `visibility: hidden` if the visual baseline shifts.
  - Order rationale: ganzhi sits closer to the era year (it cycles with the reign mark), Western year sits at the right edge as a numeric anchor. This mirrors the order in the canonical Chinese historical date `（年号）...年（干支），公元...年`.
  - When `ganzhi` is empty (rare era_year without a ganzhi tag), the span renders empty — the gap before `.tree-yr` is preserved by CSS `gap` so the layout doesn't shift visually.

### 3.2 Render year ranges on higher-level nodes

- **File**: `src/static/js/tree.js`, in each of the dynasty / volume / era node builders (`tree.js:43-48`, `tree.js:53-60`, `tree.js:69-75`):
  - Look up `dynasty_meta[d].year_range`, `volume_meta[vol.name].year_range`, `era_meta[era].year_range` (read from `state.indices`).
  - Append a `<span class="tree-year">${range}</span>` to the existing label HTML.

- Era is the most visually busy — it carries many sibling sections, so the range is informative ("I cover years 30 – 1 of this reign").

### 3.3 CSS: flex layout for tree nodes

- **File**: `src/static/style.css`, update `#app` grid (Phase 4.1 will reduce columns) and the existing tree rules:
  - Change `.tree-node` to `display: flex; align-items: center; gap: 4px;` (already implicit via flex components; tighten the rule).
  - `.tree-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }` — label takes all remaining space and ellipsises when narrow.
  - `.tree-gz { color: #777; font-size: 11px; white-space: nowrap; min-width: 2.4em; text-align: right; font-family: "Noto Sans SC", sans-serif; }` — CJK chars, slightly muted, fixed-ish width so columns align.
  - `.tree-yr { color: #888; font-size: 11px; font-variant-numeric: tabular-nums; white-space: nowrap; min-width: 4.5em; text-align: right; }` — Latin numerals, even more muted, mono-width so columns align.

- Optional: differentiate by depth:
  - `.tree-node[data-type="dynasty"] .tree-gz,
     .tree-node[data-type="dynasty"] .tree-yr { font-size: 12px; opacity: 0.85; }`
  - `.tree-node[data-type="year"] .tree-gz,
     .tree-node[data-type="year"] .tree-yr { font-size: 11px; color: #999; }`

- **Narrow column safety**: `min-width` on `.tree-yr` / `.tree-gz` prevents collapse; on the ≤600px mobile sidebar (which is 280px wide), there is enough room. If overflow becomes a problem, drop `min-width` and rely on `nowrap` + tree-label ellipsis. Don't shrink below ~10px — Chinese ganzhi glyphs become illegible.

### 3.4 Content header: volume · era · ganzhi · year

- **File**: `src/static/js/content.js:16`
- The header now shows four pieces: volume name, era (name + era_year), ganzhi, and Western year. Built conditionally so missing fields don't leave blank slots:
  ```js
  header.innerHTML = `
    <span class="vol">${esc(sec.volume_name)}</span>
    <span class="era">${esc(sec.era_name)} ${esc(sec.era_year)}</span>
    ${sec.ganzhi ? `<span class="gz">${esc(sec.ganzhi)}</span>` : ""}
    ${sec.year   ? `<span class="yr">(${esc(sec.year)})</span>`   : ""}
  `;
  ```
- **File**: `src/static/style.css`, update `.section-header` rules (lines 283-294):
  - Keep `.section-header` itself.
  - `.section-header .vol { color: #555; }` (unchanged).
  - `.section-header .era { color: #333; font-weight: 600; margin-left: 8px; }`.
  - **Add** `.section-header .gz  { color: #888; margin-left: 10px; font-size: 13px; }` — CJK chars, slightly muted, sits between era_year and the western year.
  - **Retain** `.section-header .yr  { color: #aaa; margin-left: 8px;  font-size: 13px; }` — replaces old `.wyr` rule.
  - Use `·` (Chinese interpunct) inserted via inline markup (e.g. via CSS `::before` with content: `"  ·  "`) if a dot separator is desired between spans; or rely on `margin-left` only. Pick one — consistency with Phase 3.3 tree styling matters, but we deliberately keep the header looser (no flex) so adding/removing ganzhi doesn't reflow the line.
  - Strip old `.section-header .wyr` selector (line 294).

  Final sample render: `【周纪一】· 威烈王 二十三年 · 戊寅 (403 BC)` (interpreted loosely).

### 3.5 Search drops ganzhi into the dropdown

- **File**: `src/app.py`, extend `_load_indices()` and `/api/search`.
- After loading the existing maps, also load:
  ```python
  _ganzhi_index = _indices.get("ganzhi_index", {}) if _indices else {}
  ```
- Expose it in `/api/indices` payload (`app.py:51-57`) for completeness:
  ```python
  "ganzhi_index": {k: list(v) for k, v in _ganzhi_index.items()},
  ```
- In `/api/search` (`app.py:127-135`), add a ganzhi loop *before* the `results.sort(...)` line. Emit one row per `(ganzhi, sid)` so the user can pick the specific year they meant:
  ```python
  for ganzhi, sids in _ganzhi_index.items():
      if q in ganzhi:                       # exact CJK match (no lowercasing needed)
          for sid in sids:
              section = _sections.get(sid, {})
              results.append({
                  "type": "ganzhi",
                  "section_id": sid,
                  "label": f"{ganzhi} · {section.get('era_name','')} {section.get('era_year','')} ({section.get('year','')})",
                  "sort": 0 if ganzhi == q else 1,
              })
  ```
- Note `q in ganzhi` (no `.lower()`) — ganzhi glyphs are CJK and case-folding is meaningless; lowercased searches from English/Latin queries won't accidentally hit. Good.

### 3.6 Search result handler for `ganzhi`

- **File**: `src/static/js/search.js`, `handleSearchResult` (line 60). Append a case:
  ```js
  } else if (r.type === "ganzhi") {
      navigateToSection(r.section_id);
  }
  ```
- No tree expansion needed — `ganzhi` lands directly on a leaf, no node-toggle behaviour.

### 3.7 Search dropdown badge for `ganzhi`

- **File**: `src/static/style.css`, add `.badge-ganzhi` next to the existing badge colours (lines 259-263). Pick a hue distinct from the existing palette — propose a muted red/burgundy that reads as "stem-branch cycle":
  ```css
  .badge-ganzhi  { background: #c0392b; }
  ```
- The badge text is rendered by `app.py:46` as `${r.type}` ("ganzhi" — six ASCII chars, fits the badge width).

### 3.8 Search dropdown labels (optional trim)

- **File**: `src/app.py:121-135`
- The existing `era_year` and `year` rows already read correctly after Phase 1 (paren-stripped `era_year` + `year` parenthesised). Consider trimming the `era_year` row label to drop the redundant era_name (the tree parent already names the era):
  ```python
  "label": f"{era_year} ({year})",
  ```
  That's a small QoL wins; not required for the refactor. Decide based on taste.

### 3.9 Optional: cap dropdown rows for ganzhi

- A 60-token cycle × ~22 sections-per-token = ~1320 candidate rows for one query. The existing `[:20]` cap at `app.py:138` already protects the dropdown; it's enough. Order in `sort`: exact ganzhi match first, then sort ascending by `parse_year_num(section["year"])` so the dropdown shows the earliest match first.

  In code, the easiest way is to push rows with sortable `sort` keys then rank — currently `sort` is `0`/`1`; extend to a tuple `(int(q == gz), year_int, label)`. Python sorts tuples lexicographically.

---

## Phase 4 — Timeline removal

### 4.1 HTML: drop the timeline aside

- **File**: `src/templates/index.html:16-24`
- Delete the entire `<aside id="sidebar-timeline">…</aside>` block. Layout will reflow in CSS (Phase 4.2).

### 4.2 CSS: two-column layout

- **File**: `src/static/style.css`
- Change the grid for `#app` (`style.css:19`):
  ```css
  grid-template-columns: 260px 1fr;
  ```
- Drop `#sidebar-timeline` (`style.css:31-37`), `#century-jump` (`style.css:120-143`), `#timeline-container` (`style.css:145-149`), and all `.timeline-*` rules (`style.css:151-197`).
- Drop the timeline-side media-query:
  - `@media (max-width: 900px)` (`style.css:382`) — keep the rules for `#century-jump button` only inside the mobile overrides if still needed; otherwise drop the entire 900px breakpoint and let `≤600px` handle the layout.
  - `@media (min-width: 768px) and (orientation: landscape)` (`style.css:477`) — drop entirely (its only purpose was to restore the timeline column).
- The `<=600px` rules continue to handle tree-as-overlay (with timeline gone, the right column is now content-only).

### 4.3 JS: drop the module and its wiring

- **File**: `src/static/js/timeline.js` — delete (or convert to a one-line stub that throws). Just remove the file.
- **File**: `src/static/js/main.js:6, 16, 19-20`:
  - Drop `import { buildTimeline, setupCenturyJump } from "./timeline.js";`
  - Drop `state.centuryOrder = state.indices.western_timeline.map(...);`
  - Drop the `buildTimeline()` and `setupCenturyJump()` calls.
- **File**: `src/static/js/navigation.js:7, 49`:
  - Drop `import { syncTimelineToSection } from "./timeline.js";`
  - Drop the `syncTimelineToSection(sid);` call in `setActiveSection`.

### 4.4 DOM refs

- **File**: `src/static/js/dom.js:2-5`
- Remove `$timelineContainer`, `$centuryLabel`, `$centuryPrev`, `$centuryNext`. (Other modules — `timeline.js`, `main.js`, `navigation.js` — no longer reference them.)

### 4.5 State and persistence

- **File**: `src/static/js/state.js`
- Remove `expandedCenturies: new Set()` (`state.js:17`) and `centuryOrder: []` (`state.js:20`).
- In `saveState` (`state.js:27-35`): drop the `expandedCenturies` field. Bump the `SESSION_KEY` value (e.g. `"ztj_state_v2"`) so existing users with the old `expandedCenturies` data don't crash on load.
- In `restoreState` (`state.js:37-46`): drop the `expandedCenturies` branch and add a guard — if the loaded object has unknown fields, ignore them (already implicit via the per-key `if` checks).

### 4.6 Indices exposed by `/api/indices`

- **File**: `src/app.py:51-57`
- Drop `western_timeline` from the API payload. Keep `western_years` and `era_years` (search), and add `ganzhi_index` (Phase 3.5 already added loading code; this phase keeps the wiring consistent).

---

## Phase 5 — Docs follow-up (per AGENTS.md policy)

`AGENTS.md` and `README.md` must be updated to reflect the new state once the implementation lands. Plan these edits:

- **AGENTS.md**:
  - Remove the timeline module row from the **Frontend modules** table.
  - Remove the century/era jump description from `## Navigation feedback`.
  - Update the **Web app** section (currently mentions `tree.js` ↔ `navigation.js` circular import — keep, the import graph still has the same cycle via `tree.js` ↔ `navigation.js` if any sync path remains; if not, simplify).
  - Update the **Scripts** table to remove `convert_unicode.py`-less calls if redundant; explicitly note `add_year_field.py` is now a no-op / vestigial.
  - Update the **Data structure quirk** to reflect that `semantic_json` now keeps `year`, `ganzhi`, and stripped `era_year` natively.
- **README.md**:
  - Drop "Timeline" from the navigation index list (the **Navigation Indices** section currently lists "Western year (公元)"; replace with note that year and ganzhi are shown inline on tree leaves, and headlined at the top of every section).
  - Update the **Scripts** section: remove `python scripts/add_year_field.py` references.
  - Update the **Data Format** JSON example to show `"era_year": "二十三年"`, `"ganzhi": "戊寅"`, `"year": "403 BC"`.
  - Update the **Navigation** paragraph to describe the inline-year UX (drops the "timeline year" pulse).
  - In the **Navigation Indices** section, add a row for `ganzhi` (天干地支) explaining the dropdown rows now show `戊寅 · 威烈王 二十三年 (403 BC)` with a distinguishable badge.

---

## Phase 6 — Verification

### 6.1 Data integrity

- `python scripts/verify_counts.py` → `OK: all 294 files match.` (text count unchanged)
- `python scripts/find_missing_era.py` → `0 section(s)…` (existing checker still applies now that `era_name`/`era_year` remains set)
- Spot-check 5 files: `semantic_json/001.json`, `semantic_json/050.json`, `semantic_json/150.json`, `semantic_json/250.json`, `semantic_json/294.json` — verify `era_year` is now paren-free, `ganzhi` is set for most sections, and `year` is set.
- Add a one-off diagnostic (temporary script) that iterates all `semantic_json/*.json` and reports:
  - Count where `ganzhi` is empty but `year` is set (suspicious — usually both should be present).
  - Count where `ganzhi` is set but `year` is None (legitimate, e.g. special entries).
  - Count where `era_year` still contains `（` or `(` (should be 0).

### 6.2 UI smoke

- [ ] Load the page: tree expands; every leaf shows `era_year` left, then `ganzhi`, then `year` at the right; tree doesn't get a horizontal scrollbar (year fits in 260px column).
- [ ] Dynasty / volume / era nodes show e.g. `403 BC – 959 AD` muted to the right (ganzhi is leaf-only).
- [ ] Spot-check a known year (e.g. first leaf): reads as `二十三年    戊寅    403 BC`.
- [ ] Click a leaf → instant jump + 800ms yellow pulse on the content block **and** the leaf.
- [ ] Press `j` / `k` repeatedly → every step fires a new pulse (Web Animations cancels prior, restarts).
- [ ] Content header reads `【周纪一】· 威烈王 二十三年 · 戊寅 (403 BC)` for the typical case; sections with no ganzhi still render cleanly (no empty gap).
- [ ] `/` search returns:
  - dynasties/volumes/eras/year/era_year as before
  - `ganzhi` rows show up when query like `戊寅` is typed — each row carries a red badge, label like `戊寅 · 威烈王 二十三年 (403 BC)`, click navigates correctly. Multiple matches capped to top 20.
- [ ] On narrow viewport (≤900px) the layout is now `260px tree + 1fr content` (no orphan third column).
- [ ] On mobile (≤600px) the off-canvas tree still toggles via ☰; the timeline column is gone; ganzhi+year are still visible on leaves inside the 280px overlay.
- [ ] Reduce-motion preference: pulse replaced with static fade; scroll still instant.
- [ ] Refresh mid-session: `expandedCenturies` from old session is ignored (no console errors); the tree expansion choices persist via `expandedNodes`.
- [ ] DevTools Network: `/api/indices` payload has no `western_timeline` key and now has `ganzhi_index`; each `sections[sid]` object has both `ganzhi` and `year` keys.
- [ ] DevTools Sources: no module `timeline.js` loaded (check with `Ctrl+P` → "timeline" → should be empty).

### 6.3 Performance

- [ ] `indices.json` size shrinks overall (no `western_timeline` aggregate); net adds ~1 KB for `ganzhi_index` (≈60 keys × short sids).
- [ ] Tree initial paint: similar to before — year-on-leaf shouldn't add a measurable cost (extra `<span>` per node, no change to layout behaviour).
- [ ] Search latency for `戊寅`-shaped queries is still under 100 ms (the longest list ~22 entries; iteration + JSON serialisation < 5 ms).
---

## File Change Summary

| File | Changes |
|---|---|
| `scripts/restructure_json.py` | Phase 1.1: import `parse_*`/`parse_cn_num`/`_RE_PAREN` from `add_year_field.py`; strip parenthetical from `era_year`; populate `ganzhi` and `year` per section |
| `scripts/add_year_field.py` | Phase 1.2: deprecation header; still provides helpers for `restructure_json.py` and `build_indices.py` |
| `scripts/build_indices.py` | Phases 2.1–2.6: drop `western_timeline`; add `year_min`/`year_max`/`year_range` to `volume_meta`, new `dynasty_meta`, new `era_meta`; simplify `section_labels`; add `ganzhi_index` aggregating `ganzhi → [sid]` |
| `scripts/find_missing_era.py` | Verify (no edit expected) |
| `scripts/verify_counts.py` | Verify (no edit expected) |
| `src/templates/index.html` | Phase 4.1: remove `<aside id="sidebar-timeline">` |
| `src/static/style.css` | Phases 3.3 + 4.2: flex tree layout with `.tree-gz` and right-aligned `.tree-yr`; drop `#sidebar-timeline`, `.timeline-*`, `#century-jump`; simplify grid to 2 columns; prune obsolete media queries |
| `src/static/js/timeline.js` | Phase 4.3: delete file |
| `src/static/js/main.js` | Phase 4.3: drop imports + calls |
| `src/static/js/navigation.js` | Phase 4.3: drop `syncTimelineToSection` import + call |
| `src/static/js/tree.js` | Phases 3.1 + 3.2: leaves built as `label · ganzhi · year`; dynasty/volume/era nodes gain right-aligned year range |
| `src/static/js/content.js` | Phase 3.4: header shows `volume · era · ganzhi · (year)` (re-add year, add ganzhi) |
| `src/static/js/search.js` | Phase 3.6: handle `ganzhi` search result type |
| `src/static/js/dom.js` | Phase 4.4: drop `$timelineContainer`, `$centuryLabel`, `$centuryPrev`, `$centuryNext` |
| `src/static/js/state.js` | Phase 4.5: drop `expandedCenturies`, `centuryOrder`; bump session key |
| `src/app.py` | Phase 3.5 + 4.6: extend `/api/search` to a ganzhi loop, expose `ganzhi_index`, drop `western_timeline` from payload |
| `AGENTS.md` | Phase 5 |
| `README.md` | Phase 5 |

## Order of Implementation

1. **Phase 1** — single-pass pipeline (`restructure_json.py` does everything; `add_year_field.py` becomes deprecation header).
2. **Phase 2** — restructure indices; this is the data contract the frontend will consume.
3. **Phase 3** — frontend tree rework; can ship in isolation behind a feature flag if you want a safety check, but the indices are the source of truth.
4. **Phase 4** — physically remove the timeline panel, file, refs, state; safe once tree is verified.
5. **Phase 5** — doc alignment.
6. **Phase 6** — verification gate.

The phases are sequenced so that any subset of 1–3 is independently shippable; Phase 4 is a strict cleanup that follows once the new UX is signed off.
