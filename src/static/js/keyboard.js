"use strict";

import { $searchInput, $searchDropdown } from "./dom.js";
import { state } from "./state.js";
import { navigateToSection } from "./navigation.js";

export function setupKeyboard() {
  document.addEventListener("keydown", (ev) => {
    if (ev.target.tagName === "INPUT") {
      if (ev.key === "Escape") {
        $searchDropdown.classList.add("hidden");
        $searchInput.value = "";
        $searchInput.blur();
      }
      return;
    }

    if (ev.key === "/") {
      ev.preventDefault();
      $searchInput.focus();
      return;
    }

    if (ev.key === "Escape") {
      $searchDropdown.classList.add("hidden");
      return;
    }

    if (ev.key === "ArrowDown" || ev.key === "j") {
      ev.preventDefault();
      const idx = state.sectionOrder.indexOf(state.activeSectionId);
      if (idx >= 0 && idx < state.sectionOrder.length - 1) {
        navigateToSection(state.sectionOrder[idx + 1]);
      }
      return;
    }

    if (ev.key === "ArrowUp" || ev.key === "k") {
      ev.preventDefault();
      const idx = state.sectionOrder.indexOf(state.activeSectionId);
      if (idx > 0) {
        navigateToSection(state.sectionOrder[idx - 1]);
      }
      return;
    }
  });
}
