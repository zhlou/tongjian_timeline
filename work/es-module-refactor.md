# Refactor `src/static/app.js` → ES Modules

## Goal

Break the single 898-line IIFE file into **10 ES modules** under `src/static/js/`, preserving all functionality with zero behavior changes.

## Target structure

```
src/static/
  js/
    dom.js           (25 lines)   — all document.getElementById() refs
    state.js         (45 lines)   — global state, save/restore, mobileScroll/scrollEl
    utils.js         (40 lines)   — el(), esc(), fetchJSON(), showLoading/hideLoading, CSS.escape polyfill
    tree.js          (145 lines)  — buildTree, toggleTreeNode, expandTreeToNode, collapseAllTreeNodes, syncTreeToSection
    timeline.js      (115 lines)  — buildTimeline, toggleCentury, scrollToCentury, syncTimelineToSection, setupCenturyJump
    content.js       (130 lines)  — renderSectionBlock, loadSections, renderBlockRange, prependBlockRange, recycleDOM
    navigation.js    (185 lines)  — navigateToSection, setActiveSection, setupObserver, setupScrollPrefetch
    search.js        (100 lines)  — setupSearch, doSearch, handleSearchResult
    keyboard.js      (45 lines)   — setupKeyboard
    mobile.js        (35 lines)   — showTreeOverlay, hideTreeOverlay, setupMobileToggle
    main.js          (60 lines)   — init(), entry point
  style.css          (unchanged)
```

HTML change: replace the single `<script>` tag with `<script type="module" src="/static/js/main.js">`.

Total ~925 lines (slight increase from import/export boilerplate, offset by removed IIFE wrapper).

## Module-by-module breakdown

### `dom.js`
**Exports**: `$treeContainer`, `$timelineContainer`, `$centuryLabel`, `$centuryPrev`, `$centuryNext`, `$contentScroll`, `$searchInput`, `$searchDropdown`, `$progressBar`, `$mobileToggle`, `$treeBackdrop`

No imports. Plain `const` exports of `document.getElementById(...)`.

### `state.js`
**Exports**: `state`, `SESSION_KEY`, `saveState()`, `restoreState()`, `mobileScroll()`, `scrollEl()`

No imports. The `state` object is a `const` that other modules mutate via its properties.

### `utils.js`
**Exports**: `el()`, `esc()`, `fetchJSON()`, `showLoading()`, `hideLoading()`

Also runs the `CSS.escape` polyfill as a module-side effect (no export needed — patches the global).

No imports.

### `tree.js`
**Exports**: `buildTree()`, `toggleTreeNode()`, `expandTreeToNode()`, `collapseAllTreeNodes()`, `syncTreeToSection()`, `restoreTreeExpansion()`

**Imports**:
- `el` from `utils.js`
- `$treeContainer` from `dom.js`
- `state`, `saveState` from `state.js`
- `navigateToSection` from `navigation.js`
- `hideTreeOverlay` from `mobile.js`

**Circular import note**: `tree.js` → `navigation.js` in the year-leaf click handler (runtime only, inside event listener). `navigation.js` → `tree.js` for `syncTreeToSection()`. ES modules resolve live bindings at call time, so this is safe.

### `timeline.js`
**Exports**: `buildTimeline()`, `toggleCentury()`, `scrollToCentury()`, `syncTimelineToSection()`, `setupCenturyJump()`

**Imports**:
- `el`, `fetchJSON` from `utils.js`
- `$timelineContainer`, `$centuryLabel`, `$centuryPrev`, `$centuryNext` from `dom.js`
- `state`, `saveState`, `scrollEl` from `state.js`
- `navigateToSection` from `navigation.js`

**Note**: The century-next/prev button listeners (currently module-scope lines 352–360) move into `setupCenturyJump()`, called once during `init()`.

### `content.js`
**Exports**: `renderSectionBlock()`, `loadSections()`, `getRenderedRange()`, `renderBlockRange()`, `prependBlockRange()`, `recycleDOM()`

**Imports**:
- `el`, `esc`, `fetchJSON`, `showLoading`, `hideLoading` from `utils.js`
- `$contentScroll` from `dom.js`
- `state` from `state.js`

Straightforward — no circular deps.

### `navigation.js`
**Exports**: `navigateToSection()`, `setActiveSection()`, `setupObserver()`, `setupScrollPrefetch()`, `findTopSectionId()`, `updateProgressBar()`, `updateActiveBlockClass()`

**Imports**:
- `state`, `saveState`, `mobileScroll`, `scrollEl` from `state.js`
- `$contentScroll`, `$progressBar` from `dom.js`
- `syncTreeToSection`, `collapseAllTreeNodes` from `tree.js`
- `syncTimelineToSection` from `timeline.js`
- `renderBlockRange`, `prependBlockRange`, `getRenderedRange` from `content.js`

**Module-private**: `_onNavScroll()`, `checkActiveOnScroll()` (not exported).

**Note**: The `_onNavScroll` function moves to module-private scope (not on `state`). The `state._navTimeout` property remains on the shared state object (could be module-private but kept for simplicity).

### `search.js`
**Exports**: `setupSearch()`

**Imports**:
- `el`, `esc`, `fetchJSON` from `utils.js`
- `$searchInput`, `$searchDropdown` from `dom.js`
- `navigateToSection` from `navigation.js`

**Module-private**: `doSearch()`, `handleSearchResult()` (not exported).

### `keyboard.js`
**Exports**: `setupKeyboard()`

**Imports**:
- `$searchInput`, `$searchDropdown` from `dom.js`
- `state` from `state.js`
- `navigateToSection` from `navigation.js`

Straightforward — no circular deps.

### `mobile.js`
**Exports**: `showTreeOverlay()`, `hideTreeOverlay()`, `setupMobileToggle()`

**Imports**:
- `$mobileToggle`, `$treeBackdrop` from `dom.js`

**Note**: The `document` click listener (line 885) and the toggle/backdrop click listeners move into `setupMobileToggle()`, called once during `init()`.

### `main.js`
**Exports**: none (entry point).

**Imports**:
- `state`, `restoreState` from `state.js`
- `init` function orchestrates everything:
  1. `restoreState()`
  2. `fetchJSON("/api/indices")` → sets `state.indices`, `state.sectionOrder`, `state.centuryOrder`
  3. `buildTree()`
  4. `buildTimeline()`
  5. Resolve `startId` from restored state / hash / first section
  6. `navigateToSection(startId, false)`
  7. `setupObserver()`, `setupSearch()`, `setupKeyboard()`, `setupScrollPrefetch()`, `setupMobileToggle()`, `setupCenturyJump()`

Wraps in `document.addEventListener("DOMContentLoaded", init)`.

## Dependency graph

```
                     ┌─────────┐
                     │ dom.js  │  (no deps)
                     └────┬────┘
        ┌─────────────────┼──────────────────┐
   ┌────┴────┐      ┌────┴────┐        ┌────┴─────┐
   │utils.js │      │state.js │        │mobile.js │
   └────┬────┘      └────┬────┘        └────┬─────┘
        │                │                  │
   ┌────┴────┐      ┌────┴────┐             │
   │content.js│     │tree.js ◄├─────────────┘
   └────┬────┘     └───┬──┬──┘
        │              │  │
   ┌────┴────┐    ┌────┴──┴───┐
   │timeline.js   │navigation.js│
   └────────┘    └──┬──┬──┬───┘
                    │  │  │
             ┌──────┘  │  └──────┐
        ┌────┴───┐ ┌───┴────┐ ┌──┴───────┐
        │search.js│ │keyboard.js │ main.js  │
        └─────────┘ └─────────┘ └──────────┘
```

## Migration steps

### Step 1: Create `src/static/js/` directory
```bash
mkdir -p src/static/js
```

### Step 2: Create modules in dependency order

Files with no internal deps first:
1. `dom.js`
2. `state.js`
3. `utils.js`
4. `mobile.js`

Then:
5. `content.js`
6. `tree.js`
7. `timeline.js`
8. `navigation.js`
9. `search.js`
10. `keyboard.js`
11. `main.js`

### Step 3: Update HTML

In `src/templates/index.html`, replace:
```html
<script src="/static/app.js"></script>
```
with:
```html
<script type="module" src="/static/js/main.js"></script>
```

### Step 4: Verify

1. Start Flask: `python src/app.py`
2. Test desktop layout: expand/collapse tree, timeline nav, search, keyboard shortcuts, scroll sync
3. Test mobile (≤600px): hamburger toggle, off-canvas tree, backdrop dismiss, sticky search
4. Run existing test suite if any

### Step 5: Remove old file

```bash
rm src/static/app.js
```

## Risk assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Circular import dead zone | Low | All cross-references are in callbacks/event handlers, evaluated at runtime, not module-eval time |
| `CSS.escape` polyfill timing | Low | Lives in `utils.js` which is imported before any user of `CSS.escape` (tree, search, timeline) |
| `DOMContentLoaded` timing | Low | `<script type="module">` is deferred by default, but we still wrap `init()` in DOMContentLoaded for safety |
| Session state format change | None | `saveState()`/`restoreState()` use the same `SESSION_KEY` and format |
| API calls unchanged | None | `fetchJSON()` signature identical |
| 2× line-count increase | Low | ~25 lines of import/export boilerplate, offset by removing IIFE wrapper. Net ~30 lines. |
| `_navTimeout` on `state` object | Low | Keep it there — only `navigation.js` reads/writes it. Could move to module scope but `setTimeout`/`clearTimeout` calls make it awkward |

## Non-goals (out of scope for this refactor)

- Adding a build step (bundler, transpiler)
- Changing any runtime behavior
- Adding TypeScript
- Restructuring `state` into immutable patterns
- Adding error boundaries or new error handling
- Adding ARIA attributes
- Performance optimizations beyond what exists
