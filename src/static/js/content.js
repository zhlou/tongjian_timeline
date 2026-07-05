"use strict";

import { el, esc, fetchJSON, showLoading, hideLoading } from "./utils.js";
import { $contentScroll } from "./dom.js";
import { state } from "./state.js";

export function renderSectionBlock(sid, opts) {
  const sec = state.sectionCache.get(sid);
  if (!sec) return null;

  const block = el("div", "section-block");
  block.dataset.sectionId = sid;
  if (opts && opts.fadeIn) block.classList.add("faded-in");

  if (sec.is_volume_start) {
    const banner = el("div", "volume-banner");
    banner.innerHTML =
      `<span class="vol-name">${esc(sec.volume_name)}</span>` +
      (sec.volume_time_cycle
        ? `<span class="vol-cycle">${esc(sec.volume_time_cycle)}</span>`
        : "");
    block.appendChild(banner);
  }

  const header = el("div", "section-header");
  header.innerHTML =
    `<span class="vol">${esc(sec.volume_name)}</span>` +
    `<span class="era">${esc(sec.era_name)} ${esc(sec.era_year)}</span>` +
    (sec.ganzhi ? `<span class="gz">${esc(sec.ganzhi)}</span>` : "") +
    (sec.year   ? `<span class="yr">(${esc(sec.year)})</span>`   : "");
  block.appendChild(header);

  const textsDiv = el("div", "section-texts");
  for (const t of sec.texts) {
    const p = el("p");
    p.textContent = t;
    textsDiv.appendChild(p);
  }
  block.appendChild(textsDiv);

  return block;
}

export async function loadSections(ids) {
  const missing = ids.filter(id => !state.sectionCache.has(id));
  if (missing.length === 0) return;
  showLoading();
  try {
    const batch = await fetchJSON("/api/sections/batch?ids=" + missing.join(","));
    for (const [sid, data] of Object.entries(batch)) {
      state.sectionCache.set(sid, data);
    }
  } finally {
    hideLoading();
  }
}

export function getRenderedRange() {
  const blocks = $contentScroll.querySelectorAll(".section-block");
  if (blocks.length === 0) return { start: -1, end: -1 };
  const firstId = blocks[0].dataset.sectionId;
  const lastId = blocks[blocks.length - 1].dataset.sectionId;
  return {
    start: state.sectionOrder.indexOf(firstId),
    end: state.sectionOrder.indexOf(lastId),
  };
}

export async function renderBlockRange(startIdx, endIdx, opts) {
  const ids = [];
  for (let i = startIdx; i <= endIdx; i++) {
    const id = state.sectionOrder[i];
    if (!state.renderedIds.has(id)) ids.push(id);
  }
  if (ids.length === 0) return;

  await loadSections(ids);

  for (let i = startIdx; i <= endIdx; i++) {
    const id = state.sectionOrder[i];
    if (state.renderedIds.has(id)) continue;
    const block = renderSectionBlock(id, opts);
    if (!block) continue;
    state.renderedIds.add(id);
    $contentScroll.appendChild(block);
  }
  recycleDOM();
}

export async function prependBlockRange(startIdx, count) {
  const endIdx = getRenderedRange().start;
  const realStart = Math.max(0, startIdx);
  const realEnd = Math.max(0, endIdx - 1);
  if (realStart > realEnd) return;

  const ids = [];
  for (let i = realStart; i <= realEnd; i++) {
    const id = state.sectionOrder[i];
    if (!state.renderedIds.has(id)) ids.push(id);
  }
  if (ids.length === 0) return;

  await loadSections(ids);

  const anchor = $contentScroll.querySelector(".section-block:first-child");
  for (let i = realEnd; i >= realStart; i--) {
    const id = state.sectionOrder[i];
    if (state.renderedIds.has(id)) continue;
    const block = renderSectionBlock(id);
    if (!block) continue;
    state.renderedIds.add(id);
    if (anchor) {
      $contentScroll.insertBefore(block, anchor);
    } else {
      $contentScroll.appendChild(block);
    }
  }
  recycleDOM();
}

export function recycleDOM() {
  const blocks = $contentScroll.querySelectorAll(".section-block");
  if (blocks.length <= 60) return;

  const range = getRenderedRange();
  if (range.start < 0) return;
  const activeIdx = state.sectionOrder.indexOf(state.activeSectionId);
  if (activeIdx < 0) return;

  let removed = 0;
  while (activeIdx - range.start > 25 && blocks.length > 40) {
    const b = $contentScroll.querySelector(".section-block:first-child");
    if (!b || b.dataset.sectionId === state.activeSectionId) break;
    b.remove();
    state.renderedIds.delete(b.dataset.sectionId);
    range.start++;
    removed++;
  }

  while (range.end - activeIdx > 25 && blocks.length > 40) {
    const b = $contentScroll.querySelector(".section-block:last-child");
    if (!b || b.dataset.sectionId === state.activeSectionId) break;
    b.remove();
    state.renderedIds.delete(b.dataset.sectionId);
    range.end--;
    removed++;
  }
}
