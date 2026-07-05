# Volume Header Display Plan

Display volume name + time cycle as a banner on the first section of each volume,
after cleaning up stray characters in both fields.

## Phase 1 — Data cleanup in `semantic_json/`

All cleanup happens in `scripts/restructure_json.py` so that `semantic_json/` gets
clean data on the next run.

### 1.1 Strip brackets from `volume_name`

All 294 files follow the pattern `【X纪Y】 ` (CJK fullwidth brackets `【】` + trailing space).
Strip brackets and trim whitespace during `group_blocks()` just before writing.

```python
volume["volume_name"] = obj["text"].replace("【", "").replace("】", "").strip()
```

This removes the need for `build_indices.py` to strip brackets itself at line 101
(that line becomes redundant but harmless).

### 1.2 Fix `]` → `黓` in `volume_time_cycle`

The stray ASCII `]` (U+005D) is an encoding artifact for the rare character
`黓` (U+9ED3, part of the celestial stem `玄黓` for 壬). It appears in 53 files.

Add a substitution map in `restructure_json.py` for `volume_time_cycle`:

```python
TIME_CYCLE_FIXES = {
    "]": "黓",       # 玄]困敦 → 玄黓困敦  (and other combos)
    "∷": "涒",       # ∷滩 → 涒滩
    "ㄈ稚辏": "",     # stray Bopomofo/corruption in file 152
    "瘀逢": "阏逢",   # corruption in files 016, 061
    "暑维": "屠维",   # file 050
    "强围": "强圉",   # file 068
    "强图": "强圉",   # file 110
    "强阏": "强圉",   # files 050, 169
    "目章": "上章",   # file 013
    "旃蒙单瘀": "旃蒙单阏",  # file 290
    "赤备若": "赤奋若",  # file 094
    "太渊献": "大渊献",  # file 254
    "赵柔兆": "起柔兆",  # file 138
    "趣昭阳": "起昭阳",  # file 201
    "玄默": "玄黓",   # legitimate substitution, normalize to 黓 (optional)
}
```

Apply these sequentially to `volume["volume_time_cycle"]` before writing.

**Note:** `馓玻` (used 42 times) is NOT corruption — it's the edition's variant for
`敦牂` (午 branch). Leave it as-is. Same for `淹茂`/`阄茂` (戌 branch variants).

Other corrupted combos like `玄扪嗣` (files 008, 200), `著雍郭` (file 096),
`馓参逶拢`/`馓踩月` etc. (files 108–135) — flag these with a warning but don't
auto-fix since they require human judgment.

### 1.3 Fix `◎KEEP_KNOWN_EMPTY_VOLUMES prefix bug

Files 111 and 140 have empty `volume_name` because `group_blocks()` attaches the
volume name text to `volume_time_cycle` instead, producing `「晋纪三十三起屠维大渊献...」`.

Root cause: the raw JSON for these files has `name` keys that don't match the expected
`vol_name` pattern. The existing `KNOWN_EMPTY_VOLUMES` dict in `build_indices.py`
already provides the correct names. Drop the `KNOWN_EMPTY_VOLUMES` workaround and
instead fix the source in `restructure_json.py` by detecting the `◎` prefix and
splitting on the dynasty name + 纪 pattern.

### 1.4 Verification

After running `restructure_json.py`, verify with:

```bash
python scripts/verify_counts.py
python scripts/detect_era_anomalies.py
```

Also run an anomaly scan on the cleaned `volume_time_cycle` to confirm no stray
ASCII or non-CJK characters remain beyond the known textual variants.

---

## Phase 2 — Add `is_volume_start` flag to indices

In `scripts/build_indices.py`, track which sections are the first in their volume
and add an `is_volume_start: true` field.

In the main loop over files (line 118), keep a flag for the first section of each file:

```python
for si, section in enumerate(data.get("sections", [])):
    section_id = f"{file_index}-{si}"
    # ...
    sections[section_id] = {
        # ... existing fields ...
        "volume_time_cycle": volume_time_cycle,
        "is_volume_start": (si == 0),   # NEW
    }
```

Also set `is_volume_start` in the API response for single sections (it's already
covered since `_sections` is the same dict).

---

## Phase 3 — Render volume header in the first section

### 3.1 Frontend: `content.js`

Modify `renderSectionBlock()` to conditionally render a volume banner when
`sec.is_volume_start` is true:

```javascript
export function renderSectionBlock(sid, opts) {
  const sec = state.sectionCache.get(sid);
  if (!sec) return null;

  const block = el("div", "section-block");
  block.dataset.sectionId = sid;
  if (opts && opts.fadeIn) block.classList.add("faded-in");

  // Volume banner (first section of each volume)
  if (sec.is_volume_start) {
    const banner = el("div", "volume-banner");
    banner.innerHTML =
      `<span class="vol-name">${esc(sec.volume_name)}</span>` +
      (sec.volume_time_cycle
        ? `<span class="vol-cycle">${esc(sec.volume_time_cycle)}</span>`
        : "");
    block.appendChild(banner);
  }

  // Existing section header
  const header = el("div", "section-header");
  header.innerHTML =
    `<span class="era">${esc(sec.era_name)} ${esc(sec.era_year)}</span>` +
    (sec.ganzhi ? `<span class="gz">${esc(sec.ganzhi)}</span>` : "") +
    (sec.year   ? `<span class="yr">(${esc(sec.year)})</span>`   : "");
  block.appendChild(header);

  // Existing section texts
  const textsDiv = el("div", "section-texts");
  for (const t of sec.texts) {
    const p = el("p");
    p.textContent = t;
    textsDiv.appendChild(p);
  }
  block.appendChild(textsDiv);

  return block;
}
```

Note: the `.vol` span is removed from the section header (it was redundant since
every section in the same volume had the same volume name). It's moved into the
banner.

### 3.2 Frontend: `style.css`

Add styles for the volume banner:

```css
.volume-banner {
  padding: 12px 0 8px 0;
  margin-bottom: 12px;
  border-bottom: 2px solid var(--color-accent);
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}

.volume-banner .vol-name {
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--color-text);
}

.volume-banner .vol-cycle {
  font-size: 0.85rem;
  color: var(--color-muted);
  font-style: italic;
}
```

### 3.3 Frontend: `tree.js`

The tree sidebar already shows volume_name at the volume node level — no change
needed unless we want to also show `volume_time_cycle` in the tree (out of scope
for this plan).

---

## Execution order

1. Run `scripts/restructure_json.py` with new cleanup logic → regenerated `semantic_json/`
2. Run verification scripts
3. Run `scripts/build_indices.py` → regenerated `indices.json`
4. Apply frontend changes to `content.js` and `style.css`
5. Start Flask dev server and manually test a few volume boundaries

## Rollback

No database migration — all data is file-based. Restore `semantic_json/` from git
if the cleanup produces unexpected results.

## Out of scope

- Fixing time cycle corruptions that require human judgment (these will be
  logged as warnings)
- Displaying `volume_time_cycle` in the tree sidebar
- Fixing corruptions in the body text (only `volume_name` / `volume_time_cycle`
  are in scope)
