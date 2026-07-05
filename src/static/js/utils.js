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
