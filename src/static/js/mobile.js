"use strict";

import { $mobileToggle, $treeBackdrop } from "./dom.js";

export function showTreeOverlay() {
  document.getElementById("sidebar-tree").classList.add("visible");
  $treeBackdrop.classList.add("visible");
}

export function hideTreeOverlay() {
  document.getElementById("sidebar-tree").classList.remove("visible");
  $treeBackdrop.classList.remove("visible");
}

export function setupMobileToggle() {
  $mobileToggle.addEventListener("click", () => {
    const tree = document.getElementById("sidebar-tree");
    if (tree.classList.contains("visible")) {
      hideTreeOverlay();
    } else {
      showTreeOverlay();
    }
  });

  $treeBackdrop.addEventListener("click", () => {
    hideTreeOverlay();
  });

  document.addEventListener("click", (ev) => {
    const tree = document.getElementById("sidebar-tree");
    if (tree.classList.contains("visible") &&
        !tree.contains(ev.target) &&
        ev.target !== $mobileToggle &&
        !$mobileToggle.contains(ev.target)) {
      hideTreeOverlay();
    }
  });
}
