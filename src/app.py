#!/usr/bin/env python3
"""Flask backend for Zizhi Tongjian multi-index web app."""

import json
import os

from flask import Flask, jsonify, render_template, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE_DIR, "indices.json")

_app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
)


def _load_indices():
    if not os.path.exists(INDEX_PATH):
        _app.logger.error("indices.json not found. Run: python scripts/build_indices.py")
        return None
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_indices = _load_indices()
_sections = _indices.get("sections", {}) if _indices else {}
_dynasties = _indices.get("dynasties", {}) if _indices else {}
_volumes = _indices.get("volumes", {}) if _indices else {}
_eras = _indices.get("eras", {}) if _indices else {}
_era_years = _indices.get("era_years", {}) if _indices else {}
_western_years = _indices.get("western_years", {}) if _indices else {}
_ganzhi_index = _indices.get("ganzhi_index", {}) if _indices else {}


def _homepage_stats():
    if _indices is None:
        return None
    sections = _indices.get("section_order", [])
    first_year = _sections.get(sections[0], {}).get("year", "?") if sections else "?"
    last_year = _sections.get(sections[-1], {}).get("year", "?") if sections else "?"
    return {
        "num_dynasties": len(_indices.get("dynasty_order", [])),
        "num_volumes": len(_indices.get("volume_order", [])),
        "num_sections": len(sections),
        "first_year": first_year,
        "last_year": last_year,
    }


@_app.route("/")
def index():
    return render_template("home.html", stats=_homepage_stats())


@_app.route("/read")
def reader():
    return render_template("index.html")


@_app.route("/api/indices")
def api_indices():
    if _indices is None:
        return jsonify({"error": "indices.json not found"}), 500
    return jsonify({
        "dynasties": {k: list(v) for k, v in _dynasties.items()},
        "dynasty_order": _indices.get("dynasty_order", []),
        "dynasty_meta": _indices.get("dynasty_meta", {}),
        "volumes": {k: list(v) for k, v in _volumes.items()},
        "volume_order": _indices.get("volume_order", []),
        "volume_meta": _indices.get("volume_meta", {}),
        "eras": {k: list(v) for k, v in _eras.items()},
        "era_meta": _indices.get("era_meta", {}),
        "era_years": _era_years,
        "western_years": _western_years,
        "ganzhi_index": {k: list(v) for k, v in _ganzhi_index.items()},
        "section_order": _indices.get("section_order", []),
        "section_labels": _indices.get("section_labels", {}),
        "leaf_meta": _indices.get("leaf_meta", {}),
    })


@_app.route("/api/section/<section_id>")
def api_section(section_id):
    section = _sections.get(section_id)
    if section is None:
        return jsonify({"error": "section not found"}), 404
    return jsonify(section)


@_app.route("/api/sections/batch")
def api_sections_batch():
    ids_param = request.args.get("ids", "")
    ids = [i.strip() for i in ids_param.split(",") if i.strip()]
    result = {}
    for sid in ids:
        if sid in _sections:
            result[sid] = _sections[sid]
    return jsonify(result)


@_app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    results = []

    for name, ids in _dynasties.items():
        if q.lower() in name.lower():
            results.append({
                "type": "dynasty",
                "id": f"dynasty:{name}",
                "label": f"Dynasty: {name}",
                "sort": 0 if name == q else 1,
            })

    for name, ids in _volumes.items():
        if q.lower() in name.lower():
            results.append({
                "type": "volume",
                "id": f"volume:{name}",
                "label": f"Volume: {name}",
                "dynasty": _indices.get("volume_meta", {}).get(name, {}).get("dynasty", ""),
                "sort": 0 if name == q else 1,
            })

    for name, ids in _eras.items():
        if q.lower() in name.lower():
            results.append({
                "type": "era",
                "id": f"era:{name}",
                "label": f"Era: {name}",
                "section_ids": ids[:3],
                "sort": 0 if name == q else 1,
            })

    for key, section_id in _era_years.items():
        if q.lower() in key.lower():
            era_name, era_year = key.split("|", 1)
            section = _sections.get(section_id, {})
            results.append({
                "type": "era_year",
                "section_id": section_id,
                "label": f"{era_name} {era_year} ({section.get('year', '')})",
                "sort": 0 if q in key else 1,
            })

    for year_str, section_id in _western_years.items():
        if q.lower() in year_str.lower():
            section = _sections.get(section_id, {})
            results.append({
                "type": "year",
                "section_id": section_id,
                "label": f"{year_str} — {section.get('era_name', '')} {section.get('era_year', '')}",
                "sort": 0 if year_str == q else 1,
            })

    for ganzhi, sids in _ganzhi_index.items():
        if q in ganzhi:
            for sid in sids:
                section = _sections.get(sid, {})
                results.append({
                    "type": "ganzhi",
                    "section_id": sid,
                    "ganzhi": ganzhi,
                    "label": f"{ganzhi} · {section.get('era_name','')} {section.get('era_year','')} ({section.get('year','')})",
                    "sort": 0 if ganzhi == q else 1,
                })

    results.sort(key=lambda r: (r["sort"], r["label"]))
    return jsonify(results[:20])


@_app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(_app.static_folder, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    _app.run(host="0.0.0.0", port=port, debug=debug)
