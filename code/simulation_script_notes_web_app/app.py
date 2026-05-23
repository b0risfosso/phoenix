#!/usr/bin/env python3
"""
Simulation Script Notes Web App

Purpose:
    Display generated VPython scripts, attach core/next sentence notes, and branch next sentences into pages where scripts can be added manually.

Shared data:
    By default this app reads from:
        ../simulation_shared_data/

    This matches the shared-data seed generator and seed-to-VPython apps.

    Override with:
        export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"

Run:
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python app.py

Open:
    http://127.0.0.1:5002
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory


APP_DIR = Path(__file__).resolve().parent

# Shared folder used by the seed generator and seed-to-VPython apps.
SHARED_DATA_DIR = Path(
    os.environ.get("SIMULATION_SHARED_DATA_DIR", APP_DIR.parent / "simulation_shared_data")
).expanduser().resolve()

OUTPUT_DIR = SHARED_DATA_DIR
SCRIPTS_DIR = OUTPUT_DIR / "scripts"
METADATA_DIR = OUTPUT_DIR / "metadata"
LOGS_DIR = OUTPUT_DIR / "logs"
NOTES_FILE = METADATA_DIR / "script_notes.json"
BRANCHES_FILE = METADATA_DIR / "sentence_branches.json"

for directory in (SCRIPTS_DIR, METADATA_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)




def safe_resolve(base_dir: Path, filename: str) -> Path:
    path = (base_dir / filename).resolve()
    if not str(path).startswith(str(base_dir.resolve())):
        raise ValueError("Invalid filename.")
    return path


def load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_notes() -> dict[str, Any]:
    data = load_json_file(NOTES_FILE, {})
    return data if isinstance(data, dict) else {}


def save_notes(data: dict[str, Any]) -> None:
    save_json_file(NOTES_FILE, data)


def load_branches() -> dict[str, Any]:
    data = load_json_file(BRANCHES_FILE, {"branches": {}})
    if not isinstance(data, dict):
        return {"branches": {}}
    if not isinstance(data.get("branches"), dict):
        data["branches"] = {}
    return data


def save_branches(data: dict[str, Any]) -> None:
    save_json_file(BRANCHES_FILE, data)


def branch_id_for(script_filename: str, note_id: str) -> str:
    raw = f"{script_filename}::{note_id}"
    return uuid.uuid5(uuid.NAMESPACE_URL, raw).hex[:16]


def get_note_by_id(script_filename: str, note_id: str) -> dict[str, Any] | None:
    notes = load_notes().get(script_filename, [])
    if not isinstance(notes, list):
        return None
    for note in notes:
        if isinstance(note, dict) and note.get("id") == note_id:
            return note
    return None


def get_or_create_branch(script_filename: str, note_id: str) -> dict[str, Any]:
    script_path = safe_resolve(SCRIPTS_DIR, script_filename)
    if not script_path.exists():
        raise FileNotFoundError(script_filename)

    note = get_note_by_id(script_filename, note_id)
    if not note:
        raise FileNotFoundError("Note not found.")
    if normalize_note_type(note.get("note_type", "")) != "next_sentence":
        raise ValueError("Only next sentence notes can become branch pages.")

    branches_data = load_branches()
    branches = branches_data.setdefault("branches", {})
    bid = branch_id_for(script_filename, note_id)

    if bid not in branches:
        branches[bid] = {
            "branch_id": bid,
            "parent_script_filename": script_filename,
            "parent_note_id": note_id,
            "core_sentence": note.get("text", ""),
            "title": note.get("title", "") or "Branch core sentence",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "scripts": [],
            "notes": [],
        }
        save_branches(branches_data)
    else:
        # Keep the branch core sentence synced to the source next sentence unless user has edited it later.
        branches[bid].setdefault("core_sentence", note.get("text", ""))
        branches[bid].setdefault("title", note.get("title", "") or "Branch core sentence")
        branches[bid].setdefault("scripts", [])
        branches[bid].setdefault("notes", [])
        save_branches(branches_data)

    return branches[bid]


ALLOWED_NOTE_TYPES = {"core_sentence", "next_sentence"}


def normalize_note_type(value: str) -> str:
    value = str(value or "").strip()
    if value not in ALLOWED_NOTE_TYPES:
        return "core_sentence"
    return value


def note_type_label(note_type: str) -> str:
    note_type = normalize_note_type(note_type)
    return "Core sentence" if note_type == "core_sentence" else "Next sentence"


def script_info(path: Path) -> dict[str, Any]:
    stat = path.stat()
    notes = load_notes().get(path.name, [])
    if not isinstance(notes, list):
        notes = []
    return {
        "filename": path.name,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "note_count": len(notes),
        "view_url": f"/script/{path.name}",
        "download_url": f"/outputs/scripts/{path.name}",
        "run_url": f"/run/{path.name}",
    }




def slugify(text: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    if not slug:
        slug = "branch-script"
    return slug[:max_len].strip("-") or "branch-script"


def save_branch_script(source: str, branch: dict[str, Any], requested_name: str = "") -> Path:
    core = str(branch.get("core_sentence") or branch.get("title") or "branch-script")
    if requested_name.strip():
        base_name = slugify(requested_name.replace(".py", ""), 90)
        filename = f"{base_name}.py"
    else:
        filename = f"branch-vpython-{slugify(core, 70)}-{uuid.uuid4().hex[:8]}.py"

    path = SCRIPTS_DIR / filename
    if path.exists():
        path = SCRIPTS_DIR / f"{path.stem}-{uuid.uuid4().hex[:6]}.py"
    path.write_text(source, encoding="utf-8")
    return path

@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
@app.route("/index.html", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/script/<path:filename>", methods=["GET"])
def script_detail(filename: str):
    return render_template("script.html", filename=filename)


@app.route("/api/data-location", methods=["GET"])
def api_data_location():
    return jsonify(
        {
            "ok": True,
            "shared_data_dir": str(SHARED_DATA_DIR),
            "scripts_dir": str(SCRIPTS_DIR),
            "metadata_dir": str(METADATA_DIR),
            "notes_file": str(NOTES_FILE),
        }
    )


@app.route("/api/scripts", methods=["GET"])
def api_scripts():
    try:
        query = request.args.get("q", "").strip().lower()
        note_filter = request.args.get("notes", "all").strip().lower()
        note_type_filter = request.args.get("type", "all").strip().lower()

        paths = sorted(SCRIPTS_DIR.glob("*.py"), reverse=True)
        items = []

        all_notes = load_notes()

        for path in paths:
            item = script_info(path)
            script_notes = all_notes.get(path.name, [])
            if not isinstance(script_notes, list):
                script_notes = []

            if query:
                content_matches = query in path.name.lower()
                note_matches = any(query in str(note.get("text", "")).lower() for note in script_notes if isinstance(note, dict))
                if not content_matches and not note_matches:
                    continue

            if note_filter == "with-notes" and not script_notes:
                continue
            if note_filter == "without-notes" and script_notes:
                continue

            if note_type_filter in ALLOWED_NOTE_TYPES:
                if not any(normalize_note_type(note.get("note_type", "")) == note_type_filter for note in script_notes if isinstance(note, dict)):
                    continue

            core_count = sum(1 for note in script_notes if isinstance(note, dict) and normalize_note_type(note.get("note_type", "")) == "core_sentence")
            next_count = sum(1 for note in script_notes if isinstance(note, dict) and normalize_note_type(note.get("note_type", "")) == "next_sentence")
            item["core_sentence_note_count"] = core_count
            item["next_sentence_note_count"] = next_count

            items.append(item)

        return jsonify({"ok": True, "items": items})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/script/<path:filename>", methods=["GET"])
def api_script(filename: str):
    try:
        path = safe_resolve(SCRIPTS_DIR, filename)
        if not path.exists():
            raise FileNotFoundError(filename)

        source = path.read_text(encoding="utf-8")
        info = script_info(path)

        notes = load_notes().get(path.name, [])
        if not isinstance(notes, list):
            notes = []

        return jsonify(
            {
                "ok": True,
                "script": info,
                "source": source,
                "notes": notes,
            }
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.route("/api/script/<path:filename>/notes", methods=["POST"])
def api_add_note(filename: str):
    try:
        path = safe_resolve(SCRIPTS_DIR, filename)
        if not path.exists():
            raise FileNotFoundError(filename)

        payload = request.get_json(force=True) or {}
        text = str(payload.get("text", "")).strip()
        title = str(payload.get("title", "")).strip()
        tags_raw = str(payload.get("tags", "")).strip()
        note_type = normalize_note_type(str(payload.get("note_type", "core_sentence")))

        if not text:
            return jsonify({"ok": False, "error": "Note text is required."}), 400

        tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()]

        notes_data = load_notes()
        notes = notes_data.setdefault(path.name, [])
        if not isinstance(notes, list):
            notes = []
            notes_data[path.name] = notes

        note = {
            "id": uuid.uuid4().hex[:10],
            "note_type": note_type,
            "note_type_label": note_type_label(note_type),
            "title": title,
            "text": text,
            "tags": tags,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

        notes.append(note)
        save_notes(notes_data)

        return jsonify({"ok": True, "note": note, "notes": notes})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/script/<path:filename>/notes/<note_id>", methods=["POST"])
def api_update_note(filename: str, note_id: str):
    try:
        path = safe_resolve(SCRIPTS_DIR, filename)
        if not path.exists():
            raise FileNotFoundError(filename)

        payload = request.get_json(force=True) or {}
        text = str(payload.get("text", "")).strip()
        title = str(payload.get("title", "")).strip()
        tags_raw = str(payload.get("tags", "")).strip()
        note_type = normalize_note_type(str(payload.get("note_type", "core_sentence")))

        if not text:
            return jsonify({"ok": False, "error": "Note text is required."}), 400

        tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()]

        notes_data = load_notes()
        notes = notes_data.get(path.name, [])
        if not isinstance(notes, list):
            notes = []

        for note in notes:
            if isinstance(note, dict) and note.get("id") == note_id:
                note["note_type"] = note_type
                note["note_type_label"] = note_type_label(note_type)
                note["title"] = title
                note["text"] = text
                note["tags"] = tags
                note["updated_at"] = datetime.now().isoformat(timespec="seconds")
                save_notes(notes_data)
                return jsonify({"ok": True, "note": note, "notes": notes})

        return jsonify({"ok": False, "error": "Note not found."}), 404
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/script/<path:filename>/notes/<note_id>", methods=["DELETE"])
def api_delete_note(filename: str, note_id: str):
    try:
        path = safe_resolve(SCRIPTS_DIR, filename)
        if not path.exists():
            raise FileNotFoundError(filename)

        notes_data = load_notes()
        notes = notes_data.get(path.name, [])
        if not isinstance(notes, list):
            notes = []

        new_notes = [note for note in notes if not (isinstance(note, dict) and note.get("id") == note_id)]
        notes_data[path.name] = new_notes
        save_notes(notes_data)

        return jsonify({"ok": True, "notes": new_notes})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/export-notes", methods=["GET"])
def api_export_notes():
    try:
        return jsonify(
            {
                "ok": True,
                "exported_at": datetime.now().isoformat(timespec="seconds"),
                "shared_data_dir": str(SHARED_DATA_DIR),
                "notes": load_notes(),
            }
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/run/<path:filename>", methods=["GET"])
def run_script(filename: str):
    try:
        script_path = safe_resolve(SCRIPTS_DIR, filename)
        if not script_path.exists():
            return f"Script not found: {filename}", 404

        log_path = LOGS_DIR / f"{script_path.stem}-{uuid.uuid4().hex[:6]}.log"

        with log_path.open("w", encoding="utf-8") as log:
            log.write(f"Running: {script_path}\n")
            log.write(f"Started: {datetime.now().isoformat(timespec='seconds')}\n\n")
            log.flush()

            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(SCRIPTS_DIR),
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

        return render_template(
            "run.html",
            filename=script_path.name,
            pid=process.pid,
            log_filename=log_path.name,
        )
    except Exception as exc:
        return f"Run failed: {exc}", 500




@app.route("/branch/<branch_id>", methods=["GET"])
def branch_detail(branch_id: str):
    return render_template("branch.html", branch_id=branch_id)


@app.route("/branch/from-note/<path:script_filename>/<note_id>", methods=["GET"])
def branch_from_note(script_filename: str, note_id: str):
    try:
        branch = get_or_create_branch(script_filename, note_id)
        return render_template("branch.html", branch_id=branch["branch_id"])
    except Exception as exc:
        return f"Could not open branch: {exc}", 404


@app.route("/api/branch/<branch_id>", methods=["GET"])
def api_branch(branch_id: str):
    try:
        branches_data = load_branches()
        branch = branches_data.get("branches", {}).get(branch_id)
        if not branch:
            return jsonify({"ok": False, "error": "Branch not found."}), 404

        parent_script = branch.get("parent_script_filename", "")
        parent_note_id = branch.get("parent_note_id", "")
        parent_note = get_note_by_id(parent_script, parent_note_id) if parent_script and parent_note_id else None

        script_items = []
        for script_record in branch.get("scripts", []):
            if not isinstance(script_record, dict):
                continue
            script_filename = script_record.get("filename")
            if not script_filename:
                continue
            try:
                path = safe_resolve(SCRIPTS_DIR, script_filename)
                if not path.exists():
                    continue
                info = script_info(path)
                info["branch_script_id"] = script_record.get("id", "")
                info["created_at"] = script_record.get("created_at", "")
                info["generation_instruction"] = script_record.get("generation_instruction", "")
                info["note"] = script_record.get("note", "")
                info["manual_entry"] = script_record.get("manual_entry", False)
                script_items.append(info)
            except Exception:
                continue

        return jsonify(
            {
                "ok": True,
                "branch": branch,
                "parent_note": parent_note,
                "scripts": script_items,
            }
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/branch/<branch_id>", methods=["POST"])
def api_update_branch(branch_id: str):
    try:
        payload = request.get_json(force=True) or {}
        core_sentence = str(payload.get("core_sentence", "")).strip()
        title = str(payload.get("title", "")).strip()

        if not core_sentence:
            return jsonify({"ok": False, "error": "Core sentence is required."}), 400

        branches_data = load_branches()
        branch = branches_data.get("branches", {}).get(branch_id)
        if not branch:
            return jsonify({"ok": False, "error": "Branch not found."}), 404

        branch["core_sentence"] = core_sentence
        branch["title"] = title
        branch["updated_at"] = datetime.now().isoformat(timespec="seconds")
        save_branches(branches_data)

        return jsonify({"ok": True, "branch": branch})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500



@app.route("/api/branch/<branch_id>/manual-script", methods=["POST"])
def api_branch_manual_script(branch_id: str):
    try:
        payload = request.get_json(force=True) or {}
        source = str(payload.get("source", "")).strip()
        requested_name = str(payload.get("filename", "")).strip()
        note = str(payload.get("note", "")).strip()

        if not source:
            return jsonify({"ok": False, "error": "Script source is required."}), 400

        branches_data = load_branches()
        branch = branches_data.get("branches", {}).get(branch_id)
        if not branch:
            return jsonify({"ok": False, "error": "Branch not found."}), 404

        script_path = save_branch_script(source + "\n", branch, requested_name)

        record = {
            "id": uuid.uuid4().hex[:10],
            "filename": script_path.name,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "manual_entry": True,
            "note": note,
        }
        branch.setdefault("scripts", []).append(record)
        branch["updated_at"] = datetime.now().isoformat(timespec="seconds")
        save_branches(branches_data)

        return jsonify(
            {
                "ok": True,
                "script": script_info(script_path),
                "branch": branch,
            }
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/branches", methods=["GET"])

def api_branches():
    try:
        branches_data = load_branches()
        items = []
        for branch in branches_data.get("branches", {}).values():
            if not isinstance(branch, dict):
                continue
            items.append(
                {
                    "branch_id": branch.get("branch_id", ""),
                    "title": branch.get("title", ""),
                    "core_sentence": branch.get("core_sentence", ""),
                    "parent_script_filename": branch.get("parent_script_filename", ""),
                    "script_count": len(branch.get("scripts", []) if isinstance(branch.get("scripts"), list) else []),
                    "created_at": branch.get("created_at", ""),
                    "updated_at": branch.get("updated_at", ""),
                    "url": f"/branch/{branch.get('branch_id', '')}",
                }
            )
        items.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
        return jsonify({"ok": True, "items": items})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/outputs/scripts/<path:filename>", methods=["GET"])
def download_script(filename: str):
    return send_from_directory(SCRIPTS_DIR, filename, as_attachment=True)


@app.route("/outputs/logs/<path:filename>", methods=["GET"])
def download_log(filename: str):
    return send_from_directory(LOGS_DIR, filename, as_attachment=False)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=True)
