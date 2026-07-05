"use strict";

import { el } from "./utils.js";
import { $treeContainer } from "./dom.js";
import { state, saveState } from "./state.js";
import { navigateToSection } from "./navigation.js";
import { hideTreeOverlay } from "./mobile.js";

export function buildTree() {
  const { dynasties, volumes, eras, volume_meta, dynasty_order, volume_order } = state.indices;

  const dynastyVols = {};
  for (const [vol, ids] of Object.entries(volumes)) {
    const d = (volume_meta[vol] && volume_meta[vol].dynasty) || "";
    if (!dynastyVols[d]) dynastyVols[d] = [];
    dynastyVols[d].push({ name: vol, ids });
  }

  const eraMap = {};
  for (const [era, ids] of Object.entries(eras)) {
    for (const sid of ids) {
      if (!eraMap[sid]) eraMap[sid] = era;
    }
  }

  const dynastyList = dynasty_order || Object.keys(dynasties);

  const rootUl = el("ul", "tree-list");

  for (const d of dynastyList) {
    const volsForDynasty = dynastyVols[d] || [];

    const volOrderMap = {};
    if (volume_order) {
      volume_order.forEach((v, i) => { volOrderMap[v] = i; });
    }
    volsForDynasty.sort((a, b) => {
      const oa = volOrderMap[a.name] ?? 9999;
      const ob = volOrderMap[b.name] ?? 9999;
      return oa - ob;
    });

    const dLi = el("li");
    const dNode = el("div", "tree-node");
    dNode.dataset.type = "dynasty";
    dNode.dataset.key = d;
    dNode.innerHTML = `<span class="tree-toggle">▶</span><span class="tree-label">${d}</span>`;
    dNode.addEventListener("click", () => toggleTreeNode(dNode));
    dLi.appendChild(dNode);

    const dUl = el("ul", "tree-list");

    for (const vol of volsForDynasty) {
      const vLi = el("li");
      const vNode = el("div", "tree-node");
      vNode.dataset.type = "volume";
      vNode.dataset.key = vol.name;
      vNode.innerHTML = `<span class="tree-toggle">▶</span><span class="tree-label">${vol.name}</span>`;
      vNode.addEventListener("click", () => toggleTreeNode(vNode));
      vLi.appendChild(vNode);

      const eraUl = el("ul", "tree-list");
      let lastEra = null;

      for (const sid of vol.ids) {
        const era = eraMap[sid];
        if (era !== lastEra) {
          lastEra = era;
          const eLi = el("li");
          const eNode = el("div", "tree-node");
          eNode.dataset.type = "era";
          eNode.dataset.key = era;
          eNode.innerHTML = `<span class="tree-toggle">▶</span><span class="tree-label">${era}</span>`;
          eNode.addEventListener("click", () => toggleTreeNode(eNode));
          eLi.appendChild(eNode);

          const yUl = el("ul", "tree-list");
          eNode._childUl = yUl;
          eLi.appendChild(yUl);
          eraUl.appendChild(eLi);
        }

        const yLi = el("li");
        const yNode = el("div", "tree-node tree-leaf");
        yNode.dataset.type = "year";
        yNode.dataset.sectionId = sid;
        yNode.dataset.year = state.indices.western_years[sid] || "";
        const label = state.indices.section_labels[sid] || sid;
        yNode.innerHTML = `<span class="tree-label">${label}</span>`;
        yNode.addEventListener("click", (ev) => {
          ev.stopPropagation();
          if (document.getElementById("sidebar-tree").classList.contains("visible")) {
            hideTreeOverlay();
          }
          navigateToSection(sid);
        });

        const lastEraNode = eraUl.lastChild?.firstChild;
        if (lastEraNode && lastEraNode._childUl) {
          yLi.appendChild(yNode);
          lastEraNode._childUl.appendChild(yLi);
        }
      }

      vLi.appendChild(eraUl);
      dUl.appendChild(vLi);
    }

    dLi.appendChild(dUl);
    rootUl.appendChild(dLi);
  }

  $treeContainer.appendChild(rootUl);

  const allChildUls = $treeContainer.querySelectorAll("li > ul");
  for (const ul of allChildUls) {
    ul.style.display = "none";
    const node = ul.parentElement.querySelector(".tree-node");
    if (node) {
      const toggle = node.querySelector(".tree-toggle");
      if (toggle) toggle.textContent = "▶";
    }
  }

  if (state.expandedNodes.size > 0) {
    restoreTreeExpansion();
  }
}

export function toggleTreeNode(node) {
  const ul = node.parentElement.querySelector(":scope > ul");
  if (!ul) return;
  const key = node.dataset.key;
  const isOpen = ul.style.display !== "none";

  if (isOpen) {
    ul.style.display = "none";
    node.querySelector(".tree-toggle").textContent = "▶";
    state.expandedNodes.delete(key);
  } else {
    ul.style.display = "";
    node.querySelector(".tree-toggle").textContent = "▼";
    state.expandedNodes.add(key);
  }
  saveState();
}

export function expandTreeToNode(path) {
  for (const key of path) {
    const node = $treeContainer.querySelector(`.tree-node[data-key="${CSS.escape(key)}"]`);
    if (!node) continue;
    const ul = node.parentElement.querySelector(":scope > ul");
    if (ul && ul.style.display === "none") {
      ul.style.display = "";
      node.querySelector(".tree-toggle").textContent = "▼";
      state.expandedNodes.add(key);
    }
  }
}

export function restoreTreeExpansion() {
  for (const key of state.expandedNodes) {
    const node = $treeContainer.querySelector(`.tree-node[data-key="${CSS.escape(key)}"]`);
    if (!node) continue;
    const ul = node.parentElement.querySelector(":scope > ul");
    if (ul) {
      ul.style.display = "";
      node.querySelector(".tree-toggle").textContent = "▼";
    }
  }
}

export function collapseAllTreeNodes() {
  state.expandedNodes.clear();
  const allChildUls = $treeContainer.querySelectorAll("li > ul");
  for (const ul of allChildUls) {
    ul.style.display = "none";
    const node = ul.parentElement.querySelector(".tree-node");
    if (node) {
      const toggle = node.querySelector(".tree-toggle");
      if (toggle) toggle.textContent = "▶";
    }
  }
}

export function syncTreeToSection(sid) {
  collapseAllTreeNodes();

  $treeContainer.querySelectorAll(".tree-node.active").forEach(n => n.classList.remove("active"));

  const leaf = $treeContainer.querySelector(`.tree-leaf[data-section-id="${sid}"]`);
  if (!leaf) return;

  leaf.classList.add("active");

  const path = [];
  let parent = leaf.closest("ul")?.closest("li");
  while (parent) {
    const node = parent.querySelector(":scope > .tree-node");
    if (node && node.dataset.key) path.unshift(node.dataset.key);
    parent = parent.parentElement?.closest("li");
  }
  expandTreeToNode(path);

  leaf.scrollIntoView({ block: "nearest", behavior: "smooth" });
}
