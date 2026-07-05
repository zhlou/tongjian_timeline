"use strict";

import { state, saveState, mobileScroll, scrollEl } from "./state.js";
import { $contentScroll, $progressBar } from "./dom.js";
import { pulseElement } from "./utils.js";
import { syncTreeToSection } from "./tree.js";
import { renderBlockRange, prependBlockRange, getRenderedRange } from "./content.js";

export function findTopSectionId() {
  const blocks = $contentScroll.querySelectorAll(".section-block");
  if (blocks.length === 0) return null;
  const rootTop = mobileScroll() ? 0 : $contentScroll.getBoundingClientRect().top;
  let best = null;
  for (const b of blocks) {
    const top = b.getBoundingClientRect().top;
    if (top <= rootTop + 5) {
      if (!best || top > best.top) {
        best = { sid: b.dataset.sectionId, top };
      }
    }
  }
  return best ? best.sid : null;
}

export function checkActiveOnScroll() {
  if (state.syncPending) return;
  const sid = findTopSectionId();
  if (sid && sid !== state.activeSectionId) {
    setActiveSection(sid);
  }
}

export function setupObserver() {
  let scrollCheckTimer = null;
  scrollEl().addEventListener("scroll", () => {
    if (scrollCheckTimer) return;
    scrollCheckTimer = requestAnimationFrame(() => {
      scrollCheckTimer = null;
      checkActiveOnScroll();
    });
  }, { passive: true });
}

export function setActiveSection(sid) {
  if (sid === state.activeSectionId) return;
  state.activeSectionId = sid;
  syncTreeToSection(sid);
  history.replaceState(null, "", "#section=" + sid);
  updateActiveBlockClass();
  updateProgressBar(sid);
  saveState();
}

export function updateProgressBar(sid) {
  const idx = state.sectionOrder.indexOf(sid);
  if (idx >= 0) {
    $progressBar.textContent = `Section ${idx + 1} / ${state.sectionOrder.length}`;
  }
}

export function updateActiveBlockClass() {
  const prev = $contentScroll.querySelector(".section-block.active-section");
  if (prev) prev.classList.remove("active-section");
  const next = $contentScroll.querySelector(`.section-block[data-section-id="${state.activeSectionId}"]`);
  if (next) next.classList.add("active-section");
}

function _onNavScroll() {
  clearTimeout(state._navTimeout);
  state._navTimeout = setTimeout(() => {
    state.syncPending = false;
    scrollEl().removeEventListener("scroll", _onNavScroll);
  }, 200);
}

export async function navigateToSection(sid, _smooth) {
  const idx = state.sectionOrder.indexOf(sid);
  if (idx < 0) return;

  state.syncPending = true;
  clearTimeout(state._navTimeout);
  scrollEl().removeEventListener("scroll", _onNavScroll);

  const start = Math.max(0, idx - 10);
  const end = Math.min(state.sectionOrder.length - 1, idx + 10);

  const existing = $contentScroll.querySelector(`.section-block[data-section-id="${sid}"]`);
  const rebuilt = !existing;
  if (rebuilt) {
    $contentScroll.innerHTML = "";
    state.renderedIds.clear();
    await renderBlockRange(start, end, { fadeIn: true });
  }

  setActiveSection(sid);

  const block = $contentScroll.querySelector(`.section-block[data-section-id="${sid}"]`);
  if (block) {
    if (mobileScroll()) {
      const searchH = document.getElementById("search-bar").getBoundingClientRect().height;
      const y = block.getBoundingClientRect().top + window.scrollY - searchH;
      window.scrollTo({ top: y, behavior: "instant" });
    } else {
      block.scrollIntoView({ block: "start", behavior: "instant" });
    }
    pulseElement(block);
    const header = block.querySelector(".section-header");
    if (header) pulseElement(header);
    const banner = block.querySelector(".volume-banner");
    if (banner) pulseElement(banner);
  }

  scrollEl().addEventListener("scroll", _onNavScroll, { passive: true });
  _onNavScroll();

  saveState();
}

export function setupScrollPrefetch() {
  let prefetchTimer = null;
  scrollEl().addEventListener("scroll", () => {
    if (prefetchTimer) return;
    prefetchTimer = setTimeout(() => {
      prefetchTimer = null;

      const range = getRenderedRange();
      if (range.start < 0) return;

      const target = mobileScroll() ? document.documentElement : $contentScroll;
      const scrollTop = target.scrollTop;
      const scrollBottom = scrollTop + target.clientHeight;
      const contentHeight = target.scrollHeight;

      if (scrollBottom > contentHeight - 2000 && range.end < state.sectionOrder.length - 1) {
        const nextEnd = Math.min(state.sectionOrder.length - 1, range.end + 10);
        renderBlockRange(range.end + 1, nextEnd).catch(() => {});
      }

      if (scrollTop < 2000 && range.start > 0) {
        const prevStart = Math.max(0, range.start - 10);
        prependBlockRange(prevStart, 10).catch(() => {});
      }
    }, 200);
  });
}
