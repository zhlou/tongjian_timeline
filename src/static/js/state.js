"use strict";

import { $contentScroll } from "./dom.js";

export function mobileScroll() {
  return window.innerWidth <= 600;
}

export function scrollEl() {
  return mobileScroll() ? document : $contentScroll;
}

export const state = {
  indices: null,
  activeSectionId: null,
  expandedNodes: new Set(),
  sectionCache: new Map(),
  sectionOrder: [],
  renderedIds: new Set(),
  syncPending: false,
};

export const SESSION_KEY = "ztj_state_v2";

export function saveState() {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({
      expandedNodes: [...state.expandedNodes],
      activeSectionId: state.activeSectionId,
    }));
  } catch (_) {}
}

export function restoreState() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (saved.expandedNodes) state.expandedNodes = new Set(saved.expandedNodes);
    if (saved.activeSectionId) state.activeSectionId = saved.activeSectionId;
  } catch (_) {}
}
