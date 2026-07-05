"use strict";

import { el, fetchJSON } from "./utils.js";
import { $timelineContainer, $centuryLabel, $centuryPrev, $centuryNext } from "./dom.js";
import { state, saveState } from "./state.js";
import { navigateToSection } from "./navigation.js";

export function buildTimeline() {
  const { western_timeline, western_years } = state.indices;

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

export function toggleCentury(centuryName, cDiv, header) {
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

export function scrollToCentury(ci) {
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

export function updateCenturyJump(ci) {
  $centuryLabel.textContent = state.centuryOrder[ci] || "";
  $centuryPrev.disabled = ci <= 0;
  $centuryNext.disabled = ci >= state.centuryOrder.length - 1;
}

export function setupCenturyJump() {
  $centuryPrev.addEventListener("click", () => {
    const ci = state.centuryOrder.indexOf($centuryLabel.textContent);
    if (ci > 0) scrollToCentury(ci - 1);
  });

  $centuryNext.addEventListener("click", () => {
    const ci = state.centuryOrder.indexOf($centuryLabel.textContent);
    if (ci < state.centuryOrder.length - 1) scrollToCentury(ci + 1);
  });
}

export async function syncTimelineToSection(sid) {
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
