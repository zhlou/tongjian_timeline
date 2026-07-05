"use strict";

import { el, esc, fetchJSON } from "./utils.js";
import { $searchInput, $searchDropdown, $treeContainer } from "./dom.js";
import { navigateToSection } from "./navigation.js";
import { toggleTreeNode } from "./tree.js";

export function setupSearch() {
  let debounceTimer = null;

  $searchInput.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const q = $searchInput.value.trim();
    if (q.length < 2) {
      $searchDropdown.classList.add("hidden");
      $searchDropdown.innerHTML = "";
      return;
    }
    debounceTimer = setTimeout(() => doSearch(q), 300);
  });

  document.addEventListener("click", (ev) => {
    if (!$searchInput.contains(ev.target) && !$searchDropdown.contains(ev.target)) {
      $searchDropdown.classList.add("hidden");
    }
  });

  $searchInput.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") {
      $searchDropdown.classList.add("hidden");
      $searchInput.blur();
    }
  });
}

async function doSearch(q) {
  try {
    const results = await fetchJSON("/api/search?q=" + encodeURIComponent(q));
    $searchDropdown.innerHTML = "";

    if (results.length === 0) {
      $searchDropdown.innerHTML = `<div class="search-result" style="color:#999">No results for "${esc(q)}"</div>`;
    } else {
      for (const r of results) {
        const div = el("div", "search-result");
        const badge = `<span class="search-result-badge badge-${r.type}">${r.type}</span>`;
        div.innerHTML = badge + `<span class="search-result-label">${esc(r.label)}</span>`;
        div.addEventListener("click", () => {
          handleSearchResult(r);
          $searchDropdown.classList.add("hidden");
          $searchInput.blur();
        });
        $searchDropdown.appendChild(div);
      }
    }
    $searchDropdown.classList.remove("hidden");
  } catch (_) {}
}

function handleSearchResult(r) {
  if (r.type === "era_year" || r.type === "year") {
    navigateToSection(r.section_id);
  } else if (r.type === "dynasty") {
    const name = r.id.slice("dynasty:".length);
    const node = $treeContainer.querySelector(`.tree-node[data-type="dynasty"][data-key="${CSS.escape(name)}"]`);
    if (node) {
      const childUl = node.parentElement.querySelector(":scope > ul");
      if (childUl && childUl.style.display === "none") {
        toggleTreeNode(node);
      }
      node.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  } else if (r.type === "volume") {
    const name = r.id.slice("volume:".length);
    const node = $treeContainer.querySelector(`.tree-node[data-type="volume"][data-key="${CSS.escape(name)}"]`);
    if (node) {
      const childUl = node.parentElement.querySelector(":scope > ul");
      if (childUl && childUl.style.display === "none") {
        toggleTreeNode(node);
      }
      node.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  } else if (r.type === "era") {
    const name = r.id.slice("era:".length);
    const node = $treeContainer.querySelector(`.tree-node[data-type="era"][data-key="${CSS.escape(name)}"]`);
    if (node) {
      const childUl = node.parentElement.querySelector(":scope > ul");
      if (childUl && childUl.style.display === "none") {
        toggleTreeNode(node);
      }
      node.scrollIntoView({ block: "nearest", behavior: "smooth" });
      if (r.section_ids && r.section_ids.length > 0) {
        navigateToSection(r.section_ids[0]);
      }
    }
  }
}
