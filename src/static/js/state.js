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
  expandedCenturies: new Set(),
  sectionCache: new Map(),
  sectionOrder: [],
  centuryOrder: [],
  renderedIds: new Set(),
  syncPending: false,
};

export const SESSION_KEY = "ztj_state";

export function saveState() {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({
      expandedNodes: [...state.expandedNodes],
      expandedCenturies: [...state.expandedCenturies],
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
    if (saved.expandedCenturies) state.expandedCenturies = new Set(saved.expandedCenturies);
    if (saved.activeSectionId) state.activeSectionId = saved.activeSectionId;
  } catch (_) {}
}
