# Auto-Scroll Removal & Highlight-Pulse Replacement — Implementation Plan

## Goal

Remove the browser-default smooth auto-scroll on section jumps (when `navigateToSection` fires) and replace it with an instant jump + a brief CSS highlight pulse on the newly-active block. The pulse draws the eye to where the user now is, restoring the visual feedback the slow scroll was trying to provide — without the slow animation and the 5s watchdog timeout.

Keep smooth scroll for sidebar / dropdown nav (tree leaf, timeline year, search dropdown rows) since those containers are small and the user is visually tracking a specific item.

---

## Background

### Current behaviour (`src/static/js/navigation.js:77-126`)

```js
const useSmoothScroll = smooth && Math.abs(targetFi - currentFi) <= 1;
// ...
block.scrollIntoView({ block: "start", behavior: useSmoothScroll ? "smooth" : "instant" });
// ...
if (useSmoothScroll) {
  scrollEl().addEventListener("scroll", _onNavScroll, { passive: true });
  state._navTimeout = setTimeout(() => {
    state.syncPending = false;
    scrollEl().removeEventListener("scroll", _onNavScroll);
  }, 5000);                          // <-- the "timeout" the user noticed
}
```

The 5000ms watchdog (`_navTimeout`) is the "time out midway" — it forcibly clears `syncPending` if the browser's smooth animation runs longer than 5s, which can happen on tall virtualized containers.

### Why the jump feels slow

1. **Browser-default smooth-scroll duration** is non-tunable from JS — only via your own rAF animation. For a large delta inside `.content-scroll` it can run several seconds.
2. **DOM mutation before scroll**: when the target section isn't already rendered, `navigateToSection` does `$contentScroll.innerHTML = ""` then `await renderBlockRange(...)` *before* starting the scroll (navigation.js:95-99). User sees blank → spinner → content restored at old scroll position → then smooth-scroll begins.
3. **Mid-flight DOM shifts**: `prependBlockRange` may insert blocks above the target during the animation, fighting the smooth-scroll curve.

---

## Phase 1: Always Instantly Jump in `navigation.js`

### 1.1 Drop the `useSmoothScroll` branch
- **File**: `src/static/js/navigation.js`
- **What**: Keep the function signature (`navigateToSection(sid, smooth)`) so other callers don't break, but ignore the `smooth` argument for the content scroll. Always pass `behavior: "instant"` (or omit `behavior`) to `scrollIntoView` and `window.scrollTo`.
- **What**: Drop `state._navTimeout` setTimeout entirely once smooth is gone — `syncPending` only needs the existing 200ms debounce via `_onNavScroll` (the inner timeout on lines 69-75). The outer 5000ms watchdog becomes dead code.
- **Why**: Removes the long browser smooth-scroll latency and the timeout failure mode in one change. Instant jump + `setActiveSection(sid)` (already called at navigation.js:101) means the active-section state is in sync before the next paint.

### 1.2 Simplify the post-scroll `syncPending` reset
- **File**: `src/static/js/navigation.js`
- **What**: Replace the `if (useSmoothScroll) { ... } else { ... }` block at lines 114-123 with a single short debounce (e.g. `setTimeout(() => { state.syncPending = false; }, 200)`). Keep the `_onNavScroll` listener attached just long enough to flush pending scroll events from the instant jump.

---

## Phase 2: Add Highlight Pulse on Active Block

### 2.1 New CSS keyframe + class
- **File**: `src/static/style.css`
- **What**: Add a `@keyframes just-navigated-pulse` that briefly outlines + background-shifts the block:
  - `0%`: no decoration
  - `15%`: `background-color` or `border` flash in the active-section accent colour (something like `var(--accent)` or `#f7e8b3`, 600ms)
  - `100%`: back to normal
- **What**: Add `.section-block.just-navigated { animation: just-navigated-pulse 700ms ease-out; }`.
- **What**: Ensure the animation respects `prefers-reduced-motion: reduce` — under that media query, replace animation with a static 1s outline that just fades.
- **Why**: Replaces what smooth scroll was visually signalling ("here's where you are now") with a clearly-visible flash. Cheap (transform / opacity / colour only), animatable on the compositor thread.

### 2.2 Tag the target block on jump
- **File**: `src/static/js/navigation.js`
- **What**: In `navigateToSection`, after `setActiveSection(sid)` resolves (the `block` reference is already obtained at line 103), remove any prior `.just-navigated` from `.section-block` siblings, then add it to the target. Force a reflow (`block.offsetWidth`) so the animation re-triggers on repeat jumps to the same section.
- **What**: Also handle the case where the target was just rendered — `$contentScroll.innerHTML = ""` + re-render path in lines 95-99. The animation will run on the freshly-appended block (compositor, not blocked by layout).
- **Why**: Gives every navigation call a consistent, immediate visual response — replacing the slow scroll's main purpose.

### 2.3 Optional: fade-in on rebuilt blocks (covers the blank-flash)
- **File**: `src/static/js/content.js`, `src/static/style.css`
- **What**: When `renderBlockRange` is invoked after a `$contentScroll.innerHTML = ""` rebuild (i.e. when `existing` was null in navigation.js:94-99), add a `.section-block.faded-in` class to each new block that runs `opacity 0 → 1` over ~150ms.
- **Why**: Removes the jarring "viewport blanks for 100–500ms while `/api/sections/batch` resolves" UX between click and the pulse appearing. This is a related-but-separate win.

---

## Phase 3: Same Pulse on Sidebar Syncs (Optional, Recommended)

The active-section sync already marks `.active` on tree leaves (`tree.js:186-205`) and timeline years (`timeline.js:93-121`). Those code paths can adopt the same highlight-pulse for consistency.

### 3.1 Pulse tree leaf
- **File**: `src/static/js/tree.js`
- **What**: At `syncTreeToSection` (line 186), after adding `.active` to the leaf, also add `.just-navigated` (same CSS keyframe). Force reflow to restart on rapid jumps.
- **Why**: Visual consistency — the relevant tree node flashes the same way the content block flashes.

### 3.2 Pulse timeline year
- **File**: `src/static/js/timeline.js`
- **What**: At `syncTimelineToSection` (line 93), same treatment for the matched `.timeline-year` element.

---

## Phase 3 (note — keep these smooth, do NOT pulse)

These are the side-panel auto-scrolls that *should* stay smooth because the user is visually tracking a specific small element. Do NOT add the pulse to these:

- `tree.js:205` — `leaf.scrollIntoView({block: "nearest", behavior: "smooth"})` — keep
- `timeline.js:70,119` — `century.scrollIntoView` / `yrEl.scrollIntoView({block: "nearest", behavior: "smooth"})` — keep
- `search.js:71,81,91` — dropdown row scrollIntoView smooth — keep

(If desired later, tune these via custom rAF, but they're not the bottleneck.)

---

## Phase 4: Verification

### 4.1 Manual smoke
- [ ] Click any tree leaf → content jumps immediately, target block pulses ~700ms, tree leaf also pulses, timeline year pulses
- [ ] Press `j`/`k` or `↓`/`↑` repeatedly — every jump is instant, pulse re-triggers each time
- [ ] Trigger a far jump that causes `$contentScroll.innerHTML = ""` re-render — no visible blank (fade-in covers it), pulse appears on arrival
- [ ] Toggle `prefers-reduced-motion: reduce` in DevTools — pulse becomes a static outline fade, scroll still instant
- [ ] Watch `state.syncPending` — no 5000ms watchdog timer should fire; the 200ms inner debounce should suffice

### 4.2 Performance check
- [ ] Open DevTools Performance panel; record a tree-leaf click. Verify no main-thread block > 50ms during the jump.
- [ ] Confirm no `setTimeout(..., 5000)` is set after the change (check via debugger or code grep).

---

## File Change Summary

| File | Changes |
|---|---|
| `src/static/js/navigation.js` | Phases 1.1 + 1.2: drop smooth branch, drop 5000ms watchdog, always instantly scroll; add `.just-navigated` tagging at line ~104 |
| `src/static/style.css` | Phase 2.1: `@keyframes just-navigated-pulse`, `.section-block.just-navigated`; Phase 2.3: `.section-block.faded-in` opacity 0→1; add `prefers-reduced-motion` overrides |
| `src/static/js/content.js` | Phase 2.3: tag faded-in class when re-rendered after `innerHTML = ""` |
| `src/static/js/tree.js` | Phase 3.1: tag `.just-navigated` on the active leaf in `syncTreeToSection` |
| `src/static/js/timeline.js` | Phase 3.2: tag `.just-navigated` on the active year in `syncTimelineToSection` |

## Order of Implementation

1. **Phase 1** (navigation.js) — single biggest win; removes the slow scroll and the failing watchdog
2. **Phase 2.1 + 2.2** (CSS keyframe + tagging) — restores the visual feedback that smooth scroll was providing
3. **Phase 2.3** (fade-in on rebuild) — covers the blank-flash on far jumps
4. **Phase 3** (sidebar pulse) — cosmetic consistency
5. **Phase 4** — verify everything
6. Update `AGENTS.md` and `README.md` to reflect new behaviour
