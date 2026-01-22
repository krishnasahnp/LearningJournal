from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import List, Dict, Any

from flask import Flask, jsonify, render_template, request, abort

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "backend" / "reflections.json"
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
    static_url_path="",  # serve static assets from the root for PWA compatibility
)
file_lock = Lock()


def _ensure_data_file() -> None:
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def _load_reflections() -> List[Dict[str, Any]]:
    _ensure_data_file()
    try:
        with DATA_FILE.open("r", encoding="utf-8") as source:
            return json.load(source)
    except json.JSONDecodeError:
        return []


def _persist_reflections(entries: List[Dict[str, Any]]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as target:
        json.dump(entries, target, indent=4)


def _normalize_entry(payload: Dict[str, Any]) -> Dict[str, Any]:
    location = payload.get("location") or {}
    normalized = {
        "week": str(payload.get("week", "")).strip(),
        "title": (payload.get("title") or payload.get("journalName") or "").strip(),
        "date": (payload.get("date") or "").strip(),
        "taskName": (payload.get("taskName") or "").strip(),
        "reflection": (payload.get("reflection") or payload.get("taskDescription") or "").strip(),
        "location": {
            "lat": (location.get("lat") or "").strip(),
            "lon": (location.get("lon") or "").strip(),
            "address": (location.get("address") or "").strip(),
        },
        "tech": payload.get("tech") or [],
        "timestamp": payload.get("timestamp") or datetime.utcnow().isoformat(),
    }
    return normalized


def _validate_entry(entry: Dict[str, Any]) -> List[str]:
    required_fields = ["week", "title", "date", "taskName", "reflection"]
    missing = [field for field in required_fields if not entry.get(field)]
    if not isinstance(entry.get("tech"), list):
        missing.append("tech (must be a list)")
    return missing


@app.route("/")
@app.route("/index")
@app.route("/index.html")
def home():
    return render_template("index.html")


@app.route("/journal")
@app.route("/journal.html")
def journal_page():
    return render_template("journal.html")


@app.route("/about")
@app.route("/about.html")
def about_page():
    return render_template("about.html")


@app.route("/projects")
@app.route("/projects.html")
def projects_page():
    return render_template("projects.html")


@app.route("/reflections", methods=["GET"])
def get_reflections():
    entries = sorted(
        _load_reflections(),
        key=lambda entry: entry.get("date") or entry.get("timestamp"),
        reverse=True,
    )
    return jsonify(entries)


@app.route("/add_reflection", methods=["POST"])
def add_reflection():
    payload = request.get_json(silent=True) or {}
    normalized = _normalize_entry(payload)
    errors = _validate_entry(normalized)

    if errors:
        return jsonify({"status": "error", "message": "Invalid data", "errors": errors}), 400

    with file_lock:
        entries = _load_reflections()
        entries.append(normalized)
        _persist_reflections(entries)

    return jsonify({"status": "success", "entry": normalized}), 201


@app.route("/reflections/<entry_id>", methods=["DELETE"])
def delete_reflection(entry_id: str):
    if not entry_id:
        abort(400, description="Missing entry identifier")

    with file_lock:
        entries = _load_reflections()
        updated = [entry for entry in entries if str(entry.get("timestamp")) != entry_id]

        if len(entries) == len(updated):
            abort(404, description="Reflection not found")

        _persist_reflections(updated)

    return "", 204


@app.route("/reflections/<entry_id>", methods=["PUT"])
def update_reflection(entry_id: str):
    if not entry_id:
        abort(400, description="Missing entry identifier")

    payload = request.get_json(silent=True) or {}
    if not payload:
        abort(400, description="No update payload provided")

    allowed_fields = {"week", "title", "date", "taskName", "reflection", "tech", "location"}

    updates: Dict[str, Any] = {}
    for field in allowed_fields:
        if field not in payload:
            continue
        value = payload[field]

        if field == "location":
            loc = value if isinstance(value, dict) else {}
            updates["location"] = {
                "lat": str(loc.get("lat") or "").strip(),
                "lon": str(loc.get("lon") or "").strip(),
                "address": str(loc.get("address") or "").strip(),
            }
        elif field == "tech":
            if not isinstance(value, list):
                abort(400, description="tech must be an array")
            updates["tech"] = value
        else:
            updates[field] = str(value or "").strip()

    if not updates:
        abort(400, description="No valid fields provided for update")

    with file_lock:
        entries = _load_reflections()
        for index, entry in enumerate(entries):
            if str(entry.get("timestamp")) == entry_id:
                entry.update(updates)
                missing = _validate_entry(entry)
                if missing:
                    abort(400, description=f"Invalid entry after update: {missing}")

                entries[index] = entry
                _persist_reflections(entries)
                return jsonify(entry)

    abort(404, description="Reflection not found")


@app.route("/reflections/search", methods=["GET"])
def search_reflections():
    query = (request.args.get("q") or "").strip().lower()
    week = (request.args.get("week") or "").strip()
    tech = (request.args.get("tech") or "").strip()

    entries = _load_reflections()

    def matches(entry: Dict[str, Any]) -> bool:
        if query:
            haystack = " ".join(
                str(entry.get(field, "")) for field in ("title", "taskName", "reflection")
            ).lower()
            if query not in haystack:
                return False
        if week and str(entry.get("week")) != week:
            return False
        if tech:
            if tech not in entry.get("tech", []):
                return False
        return True

    filtered = sorted(
        (entry for entry in entries if matches(entry)),
        key=lambda entry: entry.get("date") or entry.get("timestamp"),
        reverse=True,
    )

    return jsonify(filtered)


@app.route("/healthz", methods=["GET"])
def healthcheck():
    return jsonify({"status": "ok"}), 200


@app.route("/service-worker.js")
def service_worker():
    return app.send_static_file("service-worker.js")


@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")


@app.route("/offline")
def offline():
    return app.send_static_file("offline.html")


@app.errorhandler(404)
def handle_404(error):
    if request.path.startswith("/reflections"):
        return jsonify({"status": "error", "message": str(error)}), 404
    return error, 404


@app.errorhandler(400)
def handle_400(error):
    if request.path.startswith("/reflections") or request.path.startswith("/add_reflection"):
        return jsonify({"status": "error", "message": str(error)}), 400
    return error, 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

