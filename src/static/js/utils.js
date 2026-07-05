"use strict";

/* ---- CSS.escape polyfill ---- */
if (!CSS.escape) {
  CSS.escape = function (v) {
    return String(v).replace(/[^\w-]/g, function (c) {
      return "\\" + c.charCodeAt(0).toString(16).padStart(6, "0") + " ";
    });
  };
}

export function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

export function esc(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

let _loadingCount = 0;

export function showLoading() {
  _loadingCount++;
  if (_loadingCount === 1) {
    const el = document.getElementById("loading-indicator");
    if (el) el.style.display = "flex";
  }
}

export function hideLoading() {
  _loadingCount = Math.max(0, _loadingCount - 1);
  if (_loadingCount === 0) {
    const el = document.getElementById("loading-indicator");
    if (el) el.style.display = "none";
  }
}

/* ---- navigation pulse (Web Animations API) ----
 * Cancel any in-flight pulse and start a fresh one. Adding the same CSS
 * animation rule twice in a row is unreliable across browsers; creating a
 * new Animation object each call guarantees the flash runs even on close
 * jumps (block already in DOM) and on rapid re-clicks.
 */
export function pulseElement(el) {
  if (!el || typeof el.animate !== "function") return;
  if (el._pulseAnim) {
    try { el._pulseAnim.cancel(); } catch (_) {}
    el._pulseAnim = null;
  }
  const reduceMotion =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const anim = el.animate(
    reduceMotion
      ? [
          { backgroundColor: "rgba(255, 215, 0, 0.45)", offset: 0 },
          { backgroundColor: "rgba(255, 215, 0, 0.45)", offset: 0.7 },
          { backgroundColor: "transparent", offset: 1 },
        ]
      : [
          { backgroundColor: "transparent",
            boxShadow: "inset 0 0 0 0px rgba(255, 140, 0, 0)", offset: 0 },
          { backgroundColor: "rgba(255, 215, 0, 0.75)",
            boxShadow: "inset 0 0 0 4px rgba(255, 140, 0, 0.95)", offset: 0.12 },
          { backgroundColor: "rgba(255, 215, 0, 0.55)",
            boxShadow: "inset 0 0 0 2px rgba(255, 140, 0, 0.55)", offset: 0.35 },
          { backgroundColor: "transparent",
            boxShadow: "inset 0 0 0 0px rgba(255, 140, 0, 0)", offset: 1 },
        ],
    reduceMotion
      ? { duration: 1000, easing: "ease-out", fill: "none" }
      : { duration: 800, easing: "ease-out", fill: "none" }
  );
  el._pulseAnim = anim;
  anim.onfinish = () => {
    if (el._pulseAnim === anim) el._pulseAnim = null;
  };
}
