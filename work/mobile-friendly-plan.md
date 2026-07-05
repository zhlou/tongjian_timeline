# Mobile-Friendly Web App — Implementation Plan

## Phase 1: Content Readability (≤600px)

### 1.1 Reduce horizontal padding for reading area
- **Files**: `src/static/style.css`
- **What**: `.section-header` padding `20px 32px 10px` → `16px 12px 8px` on mobile
- **What**: `.section-texts` padding `4px 32px 20px` → `4px 12px 16px` on mobile
- **What**: Adjust `.section-texts` font-size from `16px` → `15px` on mobile
- **Rationale**: 32px side padding wastes space on narrow screens. Chinese text at 15px is still very readable.

### 1.2 Adjust text-indent for narrow widths
- **Files**: `src/static/style.css`
- **What**: `.section-texts` `text-indent: 2em` stays, but ensure no overflow with `word-break: break-all` or `overflow-wrap: break-word`
- **Rationale**: Long classical Chinese sentences may overflow on narrow screens.

## Phase 2: Touch-Friendly Interactive Elements

### 2.1 Enlarge tree sidebar node touch targets
- **Files**: `src/static/style.css`
- **What**: `.tree-node`, `.tree-toggle`, `.tree-parent` padding from `3px 8px` → `8px 10px` on screens ≤900px
- **What**: `.timeline-year` padding from `2px 8px 2px 20px` → `8px 8px 8px 20px` on tablets (the timeline sidebar is hidden at ≤900px, so this only applies when visible)
- **Rationale**: Minimum recommended touch target is 44px height. Current nodes are ~22px, too small for fingers.

### 2.2 Enlarge search bar
- **Files**: `src/static/style.css`, possibly `src/static/app.js`
- **What**: `#search-input` height and padding increased to ~44px touch target on mobile
- **What**: Search dropdown items get larger padding for easier tapping

## Phase 3: Off-Canvas Tree Sidebar Improvements (≤600px)

### 3.1 Add overlay backdrop/scrim
- **Files**: `src/static/style.css`, `src/static/app.js`, `src/templates/index.html` (possibly)
- **What**: Create a backdrop `<div>` that appears behind the off-canvas tree overlay
- **What**: Clicking the backdrop closes the tree sidebar
- **What**: Semi-transparent dark background (`rgba(0,0,0,0.3)`) that covers the content area
- **Rationale**: Provides clear visual feedback that the sidebar is an overlay and gives users a natural way to dismiss it.

### 3.2 Close tree on tree-node selection (mobile only)
- **Files**: `src/static/app.js`
- **What**: When a tree node is clicked and the viewport is ≤600px, auto-close the sidebar
- **Rationale**: On mobile, after navigating to a section, the user wants to see the content. Keeping the overlay open is an extra tap.

### 3.3 Prevent body scroll when overlay is open
- **Files**: `src/static/app.js`
- **What**: Toggle `overflow: hidden` on `<body>` when tree overlay is visible
- **Rationale**: Prevents the page background from scrolling behind the open overlay.

## Phase 4: Search Bar Mobile Optimization (≤600px)

### 4.1 Full-width search dropdown on mobile
- **Files**: `src/static/style.css`
- **What**: `#search-results` takes full viewport width and height-constrained
- **What**: Ensure search result items are large enough to tap (min 44px height)

### 4.2 Dismiss search dropdown with overlay click
- **Files**: `src/static/app.js` (may already exist, verify)
- **What**: Clicking outside the search results dismisses them on mobile

## Phase 5: Progress Bar Mobile Fix

### 5.1 Reposition progress bar
- **Files**: `src/static/style.css`
- **What**: On mobile, move progress bar from `float: right` to a more reliable layout (e.g., flexbox row at top of content)
- **What**: Reduce font size and padding to avoid overlap with section headers

## Phase 6: Tablet Refinements (601px–900px)

### 6.1 Content padding adjustment
- **Files**: `src/static/style.css`
- **What**: `.section-header` padding → `20px 20px 10px` (from 32px)
- **What**: `.section-texts` padding → `4px 20px 20px` (from 32px)
- **What**: `.section-texts` font-size → `16px` (keep unchanged)

### 6.2 Tree sidebar width
- **Files**: `src/static/style.css`
- **What**: Keep current 220px (already set), review if 240px is better for touch

## Phase 7: Add Orientation-Based Overrides

### 7.1 Portrait-specific adjustments
- **Files**: `src/static/style.css`
- **What**: On landscape tablets (768px–1024px in landscape), restore the timeline sidebar since there's enough horizontal room
- **What**: Check `orientation: landscape` and `min-width: 768px` combination

## Phase 8: Verification

### 8.1 Manual testing checklist
- [ ] iPhone SE (375px wide): Tree overlay works, content readable, search usable
- [ ] iPhone 14 Pro (390px wide): Same checks
- [ ] iPad portrait (768px): Timeline hidden, tree narrower, content good
- [ ] iPad landscape (1024px): Three-column layout works
- [ ] Touch targets all tappable (no mis-taps)
- [ ] No horizontal scrollbar on any viewport
- [ ] Scroll performance smooth on mobile devices

### 8.2 Dev tools testing
- Use Chrome DevTools device mode to test all common viewports
- Test with touch simulation enabled

---

## File Change Summary

| File | Changes |
|---|---|
| `src/static/style.css` | Add/modify media queries for Phases 1-7 |
| `src/static/app.js` | Phase 3: backdrop logic, auto-close on select, body scroll lock |
| `src/templates/index.html` | Possibly add backdrop element for Phase 3.1 |

## Order of Implementation

1. **Phase 3** first (backdrop + body scroll lock + auto-close) — JavaScript changes with DOM impact
2. **Phase 1 + 5 + 6** — CSS-only content readability changes (can batch together)
3. **Phase 2** — Touch target enlargements (CSS-only)
4. **Phase 4** — Search bar (CSS + possibly JS)
5. **Phase 7** — Orientation polish (CSS-only, lowest priority)
