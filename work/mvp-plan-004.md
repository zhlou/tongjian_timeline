# MVP Plan: Stage 4 — Polish & Verification

## Goal
Polish the UI, handle edge cases, and verify end-to-end.

## Tasks

### 4.1 Western year timeline polish
- Correct ordinal suffixes: "1st", "2nd", "3rd" (not "1th" etc.) — verify ETL produces correct century labels
- Timeline scrolls smoothly to active year on navigation
- Century jump buttons disabled at min/max boundaries
- Active year has a visual indicator (left border accent or dot)

### 4.2 Tree polish
- Smooth scroll when auto-scrolling to active node
- Ensure deeply nested nodes (under expanded branches) remain visible
- Loading indicator when section fetch is in-flight
- "No results" empty state for search

### 4.3 Content polish
- Smooth scroll-to-top of content panel on section load
- Year label in header links to western year in timeline (optional click-to-sync)
- Responsive breakpoints actually work
- Section progress indicator shows "Section 42 / 1405"

### 4.4 Keyboard shortcuts
- ArrowUp/ArrowDown: scroll to prev/next section
- `/`: focus search input
- Escape: close search dropdown

### 4.5 Backend robustness
- Handle missing `indices.json` gracefully (clear error + exit with message)
- Handle malformed section IDs (404)
- Handle empty search query (400)

### 4.6 .gitignore additions
```
indices.json
__pycache__/
*.pyc
```

### 4.7 Update AGENTS.md
- Add `python scripts/build_indices.py` — build indices for web app
- Add `python src/app.py` — run web app
- Note: `indices.json` must be built before running app

### 4.8 End-to-end test checklist
- [ ] `python scripts/build_indices.py` succeeds (294 files, 1405 sections, 1344 years, 16 centuries)
- [ ] `python src/app.py` starts without errors
- [ ] `curl localhost:5000/api/indices` returns valid JSON
- [ ] `curl localhost:5000/api/section/001-0` returns first section texts
- [ ] Browser: tree loads all 16 dynasties
- [ ] Browser: timeline shows all 16 century groups
- [ ] Click dynasty → expands to volumes → era → year → content loads
- [ ] Click year in timeline → content scrolls to section, tree syncs
- [ ] Scroll content → tree and timeline auto-sync via IntersectionObserver
- [ ] Century jump prev/next works
- [ ] Search "汉" → navigates to first Han section
- [ ] Search "403 BC" → direct section navigation
- [ ] URL hash `#section=042-3` → scrolls to correct position on load
- [ ] ArrowUp/ArrowDown scroll by section
- [ ] Sections flow continuously, lazy-load on scroll
- [ ] Refresh restores tree/timeline state
- [ ] Timeline scrollable for long centuries
- [ ] Responsive: narrow window collapses appropriately

## Time Estimate
~2 hours
