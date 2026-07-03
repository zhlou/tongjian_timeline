(function () {
  "use strict";

  /* ---- CSS.escape polyfill ---- */
  if (!CSS.escape) {
    CSS.escape = function (v) {
      return String(v).replace(/[^\w-]/g, function (c) {
        return "\\" + c.charCodeAt(0).toString(16).padStart(6, "0") + " ";
      });
    };
  }

  /* ==================== DOM refs ==================== */
  const $treeContainer = document.getElementById("tree-container");
  const $timelineContainer = document.getElementById("timeline-container");
  const $centuryLabel = document.getElementById("century-label");
  const $centuryPrev = document.getElementById("century-prev");
  const $centuryNext = document.getElementById("century-next");
  const $contentScroll = document.getElementById("content-scroll");
  const $searchInput = document.getElementById("search-input");
  const $searchDropdown = document.getElementById("search-dropdown");
  const $progressBar = document.getElementById("progress-bar");
  const $mobileToggle = document.getElementById("mobile-tree-toggle");

  /* ==================== State ==================== */
  const state = {
    indices: null,
    activeSectionId: null,
    expandedNodes: new Set(),
    expandedCenturies: new Set(),
    sectionCache: new Map(),
    sectionOrder: [],
    centuryOrder: [],
    renderedIds: new Set(),
    observer: null,
    syncPending: false,
  };

  /* ==================== Utils ==================== */
  const SESSION_KEY = "ztj_state";

  function saveState() {
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify({
        expandedNodes: [...state.expandedNodes],
        expandedCenturies: [...state.expandedCenturies],
        activeSectionId: state.activeSectionId,
      }));
    } catch (_) {}
  }

  function restoreState() {
    try {
      const raw = sessionStorage.getItem(SESSION_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (saved.expandedNodes) state.expandedNodes = new Set(saved.expandedNodes);
      if (saved.expandedCenturies) state.expandedCenturies = new Set(saved.expandedCenturies);
      if (saved.activeSectionId) state.activeSectionId = saved.activeSectionId;
    } catch (_) {}
  }

  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  /* ==================== API ==================== */
  async function fetchJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  }

  /* ==================== Init ==================== */
  async function init() {
    restoreState();
    state.indices = await fetchJSON("/api/indices");
    state.sectionOrder = state.indices.section_order;
    state.centuryOrder = state.indices.western_timeline.map(c => c.century);

    buildTree();
    buildTimeline();

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

  /* ==================== Tree ==================== */
  function buildTree() {
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

  function toggleTreeNode(node) {
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

  function expandTreeToNode(path) {
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

  function restoreTreeExpansion() {
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

  /* ==================== Timeline ==================== */
  function buildTimeline() {
    const { western_timeline, western_years, volume_meta } = state.indices;

    for (const [ci, century] of western_timeline.entries()) {
      const cDiv = el("div", "timeline-century");
      cDiv.dataset.centuryIdx = ci;

      const header = el("div", "timeline-century-header");
      const open = state.expandedCenturies.has(century.century);
      header.innerHTML = `<span class="arrow">${open ? "▼" : "▶"}</span>${century.century}`;
      header.addEventListener("click", () => toggleCentury(century.century, cDiv, header));

      const yList = el("ul", "timeline-year-list");
      if (!open) yList.style.display = "none";

      for (const yr of century.years) {
        const sid = western_years[yr];
        const li = el("li", "timeline-year");
        li.dataset.year = yr;
        li.dataset.sectionId = sid || "";
        li.textContent = yr;
        li.addEventListener("click", () => {
          if (sid) navigateToSection(sid);
        });
        yList.appendChild(li);
      }

      cDiv.appendChild(header);
      cDiv.appendChild(yList);
      $timelineContainer.appendChild(cDiv);
    }

    updateCenturyJump(0);
  }

  function toggleCentury(centuryName, cDiv, header) {
    const yList = cDiv.querySelector(".timeline-year-list");
    const isOpen = yList.style.display !== "none";
    if (isOpen) {
      yList.style.display = "none";
      header.querySelector(".arrow").textContent = "▶";
      state.expandedCenturies.delete(centuryName);
    } else {
      yList.style.display = "";
      header.querySelector(".arrow").textContent = "▼";
      state.expandedCenturies.add(centuryName);
    }
    saveState();
  }

  function scrollToCentury(ci) {
    const century = $timelineContainer.querySelector(`.timeline-century[data-century-idx="${ci}"]`);
    if (!century) return;
    const header = century.querySelector(".timeline-century-header");
    const yList = century.querySelector(".timeline-year-list");
    const cName = state.centuryOrder[ci];

    if (yList && yList.style.display === "none") {
      yList.style.display = "";
      header.querySelector(".arrow").textContent = "▼";
      state.expandedCenturies.add(cName);
    }
    century.scrollIntoView({ block: "start", behavior: "smooth" });
    updateCenturyJump(ci);
    saveState();
  }

  function updateCenturyJump(ci) {
    $centuryLabel.textContent = state.centuryOrder[ci] || "";
    $centuryPrev.disabled = ci <= 0;
    $centuryNext.disabled = ci >= state.centuryOrder.length - 1;
  }

  $centuryPrev.addEventListener("click", () => {
    const ci = state.centuryOrder.indexOf($centuryLabel.textContent);
    if (ci > 0) scrollToCentury(ci - 1);
  });

  $centuryNext.addEventListener("click", () => {
    const ci = state.centuryOrder.indexOf($centuryLabel.textContent);
    if (ci < state.centuryOrder.length - 1) scrollToCentury(ci + 1);
  });

  /* ==================== Content rendering ==================== */
  function renderSectionBlock(sid) {
    const sec = state.sectionCache.get(sid);
    if (!sec) return null;

    const block = el("div", "section-block");
    block.dataset.sectionId = sid;

    const header = el("div", "section-header");
    header.innerHTML = `<span class="vol">${esc(sec.volume_name)}</span>  ·  <span class="era">${esc(sec.era_name)} ${esc(sec.era_year)}</span>  <span class="wyr">(${esc(sec.year)})</span>`;
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

  function esc(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  let _loadingCount = 0;
  function showLoading() {
    _loadingCount++;
    if (_loadingCount === 1) {
      const el = document.getElementById("loading-indicator");
      if (el) el.style.display = "flex";
    }
  }
  function hideLoading() {
    _loadingCount = Math.max(0, _loadingCount - 1);
    if (_loadingCount === 0) {
      const el = document.getElementById("loading-indicator");
      if (el) el.style.display = "none";
    }
  }

  async function loadSections(ids) {
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

  function getRenderedRange() {
    const blocks = $contentScroll.querySelectorAll(".section-block");
    if (blocks.length === 0) return { start: -1, end: -1 };
    const firstId = blocks[0].dataset.sectionId;
    const lastId = blocks[blocks.length - 1].dataset.sectionId;
    return {
      start: state.sectionOrder.indexOf(firstId),
      end: state.sectionOrder.indexOf(lastId),
    };
  }

  async function renderBlockRange(startIdx, endIdx) {
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
      const block = renderSectionBlock(id);
      if (!block) continue;
      state.renderedIds.add(id);
      $contentScroll.appendChild(block);
      if (state.observer) state.observer.observe(block);
    }
    recycleDOM();
  }

  async function prependBlockRange(startIdx, count) {
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
      if (state.observer) state.observer.observe(block);
    }
    recycleDOM();
  }

  function recycleDOM() {
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
      if (state.observer) state.observer.unobserve(b);
      b.remove();
      state.renderedIds.delete(b.dataset.sectionId);
      range.start++;
      removed++;
    }

    while (range.end - activeIdx > 25 && blocks.length > 40) {
      const b = $contentScroll.querySelector(".section-block:last-child");
      if (!b || b.dataset.sectionId === state.activeSectionId) break;
      if (state.observer) state.observer.unobserve(b);
      b.remove();
      state.renderedIds.delete(b.dataset.sectionId);
      range.end--;
      removed++;
    }
  }

  /* ==================== IntersectionObserver ==================== */
  function setupObserver() {
    state.observer = new IntersectionObserver((entries) => {
      if (state.syncPending) return;
      const visible = entries.filter(e => e.isIntersecting && e.intersectionRatio >= 0.4);
      if (visible.length === 0) return;

      visible.sort((a, b) => b.intersectionRatio - a.intersectionRatio);
      const top = visible[0];
      const sid = top.target.dataset.sectionId;
      if (sid && sid !== state.activeSectionId) {
        setActiveSection(sid);
      }
    }, { root: $contentScroll, threshold: [0.4] });

    const blocks = $contentScroll.querySelectorAll(".section-block");
    for (const b of blocks) state.observer.observe(b);
  }

  function setActiveSection(sid) {
    if (sid === state.activeSectionId) return;
    state.activeSectionId = sid;
    syncTreeToSection(sid);
    syncTimelineToSection(sid);
    history.replaceState(null, "", "#section=" + sid);
    updateActiveBlockClass();
    updateProgressBar(sid);
    saveState();
  }

  function updateProgressBar(sid) {
    const idx = state.sectionOrder.indexOf(sid);
    if (idx >= 0) {
      $progressBar.textContent = `Section ${idx + 1} / ${state.sectionOrder.length}`;
    }
  }

  function updateActiveBlockClass() {
    const prev = $contentScroll.querySelector(".section-block.active-section");
    if (prev) prev.classList.remove("active-section");
    const next = $contentScroll.querySelector(`.section-block[data-section-id="${state.activeSectionId}"]`);
    if (next) next.classList.add("active-section");
  }

  function collapseAllTreeNodes() {
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

  function syncTreeToSection(sid) {
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

  async function syncTimelineToSection(sid) {
    let sec = state.sectionCache.get(sid);
    if (!sec || !sec.year) {
      try {
        sec = await fetchJSON("/api/section/" + sid);
        state.sectionCache.set(sid, sec);
      } catch (_) { return; }
    }
    if (!sec || !sec.year) return;

    $timelineContainer.querySelectorAll(".timeline-year.active").forEach(y => y.classList.remove("active"));
    const yrEl = $timelineContainer.querySelector(`.timeline-year[data-year="${CSS.escape(sec.year)}"]`);
    if (yrEl) {
      yrEl.classList.add("active");
      const centuryDiv = yrEl.closest(".timeline-century");
      if (centuryDiv) {
        const yList = centuryDiv.querySelector(".timeline-year-list");
        const header = centuryDiv.querySelector(".timeline-century-header");
        if (yList && yList.style.display === "none") {
          yList.style.display = "";
          header.querySelector(".arrow").textContent = "▼";
          const cName = state.centuryOrder[parseInt(centuryDiv.dataset.centuryIdx, 10)];
          state.expandedCenturies.add(cName);
        }
        const ci = parseInt(centuryDiv.dataset.centuryIdx, 10);
        updateCenturyJump(ci);
        yrEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    }
  }

  /* ==================== Navigation ==================== */
  async function navigateToSection(sid, smooth) {
    if (smooth === undefined) smooth = true;

    const idx = state.sectionOrder.indexOf(sid);
    if (idx < 0) return;

    state.syncPending = true;
    clearTimeout(state._navTimeout);

    const start = Math.max(0, idx - 10);
    const end = Math.min(state.sectionOrder.length - 1, idx + 10);

    const existing = $contentScroll.querySelector(`.section-block[data-section-id="${sid}"]`);
    if (!existing) {
      $contentScroll.innerHTML = "";
      state.renderedIds.clear();
      await renderBlockRange(start, end);
    }

    setActiveSection(sid);

    const block = $contentScroll.querySelector(`.section-block[data-section-id="${sid}"]`);
    if (block) {
      block.scrollIntoView({ block: "start", behavior: smooth ? "smooth" : "instant" });
    }

    state._navTimeout = setTimeout(() => {
      state.syncPending = false;
    }, smooth ? 1200 : 100);

    saveState();
  }

  function setupScrollPrefetch() {
    let prefetchTimer = null;
    $contentScroll.addEventListener("scroll", () => {
      if (prefetchTimer) return;
      prefetchTimer = setTimeout(() => {
        prefetchTimer = null;

        const range = getRenderedRange();
        if (range.start < 0) return;

        const scrollTop = $contentScroll.scrollTop;
        const scrollBottom = scrollTop + $contentScroll.clientHeight;
        const contentHeight = $contentScroll.scrollHeight;

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

  /* ==================== Search ==================== */
  function setupSearch() {
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

  /* ==================== Keyboard ==================== */
  function setupKeyboard() {
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

  /* ==================== Mobile toggle ==================== */
  $mobileToggle.addEventListener("click", () => {
    const tree = document.getElementById("sidebar-tree");
    tree.classList.toggle("visible");
  });

  document.addEventListener("click", (ev) => {
    const tree = document.getElementById("sidebar-tree");
    if (tree.classList.contains("visible") &&
        !tree.contains(ev.target) &&
        ev.target !== $mobileToggle &&
        !$mobileToggle.contains(ev.target)) {
      tree.classList.remove("visible");
    }
  });

  /* ==================== Start ==================== */
  document.addEventListener("DOMContentLoaded", init);

})();
