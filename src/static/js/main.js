"use strict";

import { fetchJSON } from "./utils.js";
import { state, restoreState } from "./state.js";
import { buildTree } from "./tree.js";
import { navigateToSection, setupObserver, setupScrollPrefetch } from "./navigation.js";
import { setupSearch } from "./search.js";
import { setupKeyboard } from "./keyboard.js";
import { setupMobileToggle } from "./mobile.js";

async function init() {
  restoreState();
  state.indices = await fetchJSON("/api/indices");
  state.sectionOrder = state.indices.section_order;

  buildTree();
  setupMobileToggle();

  let startId = state.activeSectionId;

  if (!startId) {
    const hash = window.location.hash;
    if (hash.startsWith("#section=")) {
      startId = hash.slice("#section=".length);
    }
  }

  if (!startId) startId = state.sectionOrder[0];

  await navigateToSection(startId, false);
  setupObserver();
  setupSearch();
  setupKeyboard();
  setupScrollPrefetch();
}

document.addEventListener("DOMContentLoaded", init);
