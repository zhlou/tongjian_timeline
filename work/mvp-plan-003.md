# MVP Plan: Stage 3 — Frontend (HTML + CSS + JS)

## Goal
Single-page app with dual-panel sidebar (tree + western year timeline), quick search, and continuous-scroll content. Tree and timeline stay synced to content scroll position via IntersectionObserver.

## Files
- `src/templates/index.html` — HTML structure
- `src/static/style.css` — All styles
- `src/static/app.js` — All JavaScript logic

## Dependencies
None. No frameworks, no build tools.

## Tasks

### 3.1 HTML Structure (`index.html`)

```html
<div id="app">
  <aside id="sidebar-tree">
    <div class="panel-header">纪传</div>
    <div id="tree-container"></div>
  </aside>
  <aside id="sidebar-timeline">
    <div class="panel-header">公元</div>
    <div id="century-jump">
      <button id="century-prev">◀</button>
      <span id="century-label">4th C. BC</span>
      <button id="century-next">▶</button>
    </div>
    <div id="timeline-container"></div>
  </aside>
  <main id="content">
    <div id="search-bar">
      <input type="text" id="search-input" placeholder="搜索 dynasty/era/year...">
      <div id="search-dropdown" class="hidden"></div>
    </div>
    <div id="content-scroll">
      <!-- <section data-section-id="001-0">...</section> rendered dynamically -->
    </div>
  </main>
</div>
```

- No content-header, no prev/next buttons. Content is one continuous scroll.
- `#content-scroll` is the scrollable container holding `<section>` elements.

### 3.2 CSS (`style.css`)

#### Layout
- Full viewport (`100vh`), CSS Grid: `grid-template-columns: 260px 180px 1fr`
- `#sidebar-tree`: leftmost, width 260px, border-right, `display: flex; flex-direction: column`
- `#sidebar-timeline`: middle, width 180px, border-right, `display: flex; flex-direction: column`
- `#content`: right column, `display: flex; flex-direction: column`

#### Panel Headers
- `.panel-header`: sticky top, background, bold, padding 8px 12px, border-bottom, z-index above scroll

#### Sidebar Tree
- `#tree-container`: `overflow-y: auto; flex: 1`
- Nested `<ul>`/`<li>` with indentation via `padding-left`
- Collapsible: `▶`/`▼` indicators via `::before` pseudo-element
- Active item highlighted
- Level 1 (dynasty): bold, font-size 15px, pl 8px
- Level 2 (volume): normal, font-size 14px, pl 24px
- Level 3 (era): normal, font-size 13px, pl 40px
- Level 4 (year): smaller, muted color, font-size 12px, pl 56px, cursor pointer

#### Western Year Timeline
- `#century-jump`: sticky, display flex, justify-content space-between, padding 6px 8px, bg #e8e8e8, border-bottom
  - Century label centered, prev/next buttons
- `#timeline-container`: `overflow-y: auto; flex: 1`
- Century groups: collapsible `<details>` elements
  - Century header: bold
- Year entries: small font, `pl 16px`, highlight active
- Clicking a year scrolls content to that section

#### Search Bar
- `#search-bar`: sticky top, padding 8px 16px, background white, border-bottom, z-index
- Input: full width, rounded
- Dropdown: absolute below input, white bg, border, shadow, max-height 400px overflow-y auto

#### Content Panel (Continuous Scroll)
- `#content-scroll`: `flex: 1; overflow-y: auto; padding: 0`
- Section headers: `position: sticky; top: 0` (the era/year label sticks as you scroll through a section), padding 12px 24px, background #fafafa with bottom border
  - Actually better: section headers are inline but visually distinct. Let's keep them inline (not sticky) since each section is a natural reading unit. When a section is "active" (crosses 50% viewport), its header could have a subtle left-border accent.
  - Simpler approach: section headers are just styled `<div>` with larger font, bold, padding, and a subtle top border to separate sections visually.
- Paragraphs: `line-height: 1.9`, `margin: 0.8em 0`, `font-size: 16px`, `padding: 0 32px`
- Section header: `padding: 24px 32px 12px`, `font-size: 18px`, `font-weight: bold`, `border-top: 1px solid #e0e0e0`
  - Shows: `[volume_name]` · `era_name` `era_year` (`year`)
- Active section: subtle left-border accent via a class `.section-active` (applied by JS)

#### Colors
- Background: `#fafafa`
- Sidebar bg: `#f2f2f2`
- Text: `#333`
- Active item (tree/timeline): `#d4e6f1` with left border accent
- Active section (content): no background change, just a thin `2px solid #5b9bd5` left border on the header
- Hover: `#e0e0e0`
- Panel header bg: `#e8e8e8`

#### Responsive
- Below 900px: collapse timeline, 2-column (tree + content)
- Below 600px: collapse tree, 1-column (content only) with hamburger toggle

### 3.3 JavaScript (`app.js`)

#### State
```js
const state = {
  activeSectionId: null,          // set by IntersectionObserver
  expandedNodes: new Set(),       // tree nodes by path "dynasty|volume|era"
  expandedCenturies: new Set(),   // century group names
  sectionCache: new Map(),        // section_id → section_data (max ~200 entries)
  sectionOrder: [],               // flat ordered list of all section IDs
  indices: null,                  // raw indices data from /api/indices
  renderedRange: { start: 0, end: 0 },  // indices into sectionOrder
  observer: null,                 // IntersectionObserver instance
};
```

#### 3.3.1 Initialization
- On DOMContentLoaded:
  1. Fetch `GET /api/indices`
  2. Store in state, build tree and timeline DOM
  3. Restore `expandedNodes` and `expandedCenturies` from `sessionStorage`
  4. Determine starting section:
     - If URL hash `#section=001-0`: start at that section
     - Else: start at first section (001-0)
  5. Render initial batch of sections around the starting section (~20 sections)
  6. Set up `IntersectionObserver` on `#content-scroll` to watch `<section>` elements
  7. Scroll to the starting section's element

#### 3.3.2 Tree Building
- For each dynasty (sorted alphabetically):
  - `<li class="tree-node" data-type="dynasty" data-key="周">`
  - Contains toggle arrow + dynasty name
- For each volume under dynasty (sorted by file_index):
  - `<li class="tree-node" data-type="volume" data-key="周纪一">`
- For each era under volume (sorted by first occurrence):
  - `<li class="tree-node" data-type="era" data-key="威烈王">`
- For each year-section under era (sorted by section_order):
  - `<li class="tree-node tree-leaf" data-type="year" data-section-id="001-0">`
  - Text: `"{era_year} ({year})"` e.g. "二十三年 (403 BC)"
  - On click: `navigateToSection(data-section-id)`

#### 3.3.3 Timeline Building
- Iterate `western_timeline` from indices
- For each century group:
  - `<details>` element with `<summary>` as century header
  - Inside: list of year entries, each `<li>` with `data-year="403 BC"` and `data-section-id="001-0"`
  - On click: `navigateToSection(data-section-id)`

#### 3.3.4 Century Jump
- Ordered list of century labels from `western_timeline`
- Prev/Next buttons: move to previous/next century, scroll timeline to it, expand it
- Update `#century-label` text
- Disable at boundaries

#### 3.3.5 Section Rendering (lazy, continuous)
- Function `renderSections(startIdx, endIdx)`:
  - For each section_id in `sectionOrder[startIdx:endIdx]`:
    - If already in DOM, skip
    - Fetch data (from cache or `/api/section/{id}`)
    - Create `<section data-section-id="...">` element:
      ```html
      <section data-section-id="001-0">
        <div class="section-header">
          <span class="section-volume">周纪一</span>
          <span class="section-era">威烈王 二十三年</span>
          <span class="section-year">(403 BC)</span>
        </div>
        <div class="section-texts">
          <p>paragraph...</p>
          <p>paragraph...</p>
        </div>
      </section>
      ```
    - Append to `#content-scroll` (or insert before/after existing)

- **Initial render**: render 10 sections before and 10 after the starting section.
- **Scroll-triggered preloading**: listen to `scroll` event on `#content-scroll`.
  - If scrolled within 2000px of the top → fetch and render previous batch (insertBefore)
  - If scrolled within 2000px of bottom → fetch and render next batch (appendChild)

- **DOM recycling**: keep at most ~80 sections in DOM.
  - If total rendered > 80, remove sections farthest from viewport (above or below).
  - Before removing, ensure they are re-observable if re-rendered later.

#### 3.3.6 IntersectionObserver (sync engine)
- Create observer on `#content-scroll`:
  ```js
  const observer = new IntersectionObserver((entries) => {
    // Find entry with highest intersectionRatio > 0.5
    // That entry's section becomes the active section
    const active = entries
      .filter(e => e.isIntersecting && e.intersectionRatio >= 0.5)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (active) {
      const sectionId = active.target.dataset.sectionId;
      setActiveSection(sectionId);
    }
  }, { root: document.getElementById('content-scroll'), threshold: [0.5] });
  ```
- When a new section becomes active (`setActiveSection`):
  1. `state.activeSectionId = sectionId`
  2. **Sync tree**: expand ancestors, add `.active` class to the matching year `<li>`, scroll it into view
  3. **Sync timeline**: add `.active` class to matching year `<li>`, expand century group, scroll into view
  4. **Update URL**: `history.replaceState(null, '', '#section=' + sectionId)`

- **Debounce**: use a trailing debounce of 100ms to avoid flickering when scrolling fast.

#### 3.3.7 Navigation from Side Panels (`navigateToSection(sectionId)`)
1. Ensure section is rendered in DOM (if not, render around it first)
2. Find `<section data-section-id="...">` element
3. `sectionEl.scrollIntoView({ behavior: 'smooth', block: 'start' })`
4. The IntersectionObserver will then fire and complete the sync cycle
5. For immediacy, also call `setActiveSection(sectionId)` right away (before the scroll animation completes)

#### 3.3.8 Search
- Debounced 300ms, min 2 chars
- Query `/api/search?q={query}`
- Render dropdown:
  - Group by type with badges (dynasty/volume/era/year)
  - dynasty result → `navigateToSection(first section_id in that dynasty)`
  - volume result → `navigateToSection(first section_id in that volume)`
  - era result → `navigateToSection(first section_id in that era)`
  - era_year / year result → `navigateToSection(section_id)`
- Close on Escape, click outside, or after selection

#### 3.3.9 Keyboard Shortcuts
- ArrowUp: scroll to previous section (`scrollIntoView` the section above current active)
- ArrowDown: scroll to next section
- `/`: focus search input
- Escape: close search dropdown

#### 3.3.10 Session Persistence
- `expandedNodes` → `sessionStorage`
- `expandedCenturies` → `sessionStorage`
- On page load: restore tree/timeline expand state, then navigate to URL hash section

## Verification
- Open `http://localhost:5000/`
- Content shows continuous scroll with multiple sections
- Scroll down → tree and timeline highlight changes as sections cross 50% viewport
- Scroll down → new sections lazy-load and append
- Click year in tree → content scrolls to that section, both panels sync
- Click year in timeline → same
- Century jump buttons work
- Search "汉" → navigates to first Han dynasty section
- URL hash updates as you scroll
- ArrowUp/ArrowDown scroll by section
- Page refresh with `#section=042-3` → loads at correct position

## Time Estimate
~4 hours
