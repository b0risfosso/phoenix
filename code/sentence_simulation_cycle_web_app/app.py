#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, send_from_directory

APP_DIR = Path(__file__).resolve().parent
SHARED_DATA_DIR = Path(os.environ.get("SIMULATION_SHARED_DATA_DIR", APP_DIR.parent / "simulation_shared_data")).expanduser().resolve()
SCRIPTS_DIR = SHARED_DATA_DIR / "scripts"
METADATA_DIR = SHARED_DATA_DIR / "metadata"
LOGS_DIR = SHARED_DATA_DIR / "logs"
TREE_FILE = METADATA_DIR / "core_sentence_tree.json"

for directory in (SCRIPTS_DIR, METADATA_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_resolve(base_dir: Path, filename: str) -> Path:
    path = (base_dir / filename).resolve()
    if not str(path).startswith(str(base_dir.resolve())):
        raise ValueError("Invalid filename.")
    return path


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def default_tree() -> dict[str, Any]:
    return {
        "root_id": "root",
        "nodes": {
            "root": {
                "id": "root",
                "title": "No tree found",
                "sentence": "No shared sentence tree found. Create sentences in the core sentence branch app first.",
                "parent_id": None,
                "children": [],
                "scripts": [],
            }
        },
    }


def load_tree() -> dict[str, Any]:
    tree = load_json(TREE_FILE, None)
    if not isinstance(tree, dict) or not isinstance(tree.get("nodes"), dict):
        return default_tree()
    return tree


def node_summary(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node.get("id", ""),
        "title": node.get("title", ""),
        "sentence": node.get("sentence", ""),
        "parent_id": node.get("parent_id"),
        "children": node.get("children", []),
    }


def sentence_path(tree: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    nodes = tree.get("nodes", {})
    path: list[dict[str, Any]] = []
    seen: set[str] = set()
    current_id = node_id
    while current_id and current_id not in seen:
        seen.add(current_id)
        node = nodes.get(current_id)
        if not node:
            break
        path.append(node_summary(node))
        current_id = node.get("parent_id")
    path.reverse()
    return path


def story_text(path: list[dict[str, Any]]) -> str:
    return " ".join(str(item.get("sentence", "")).strip() for item in path if str(item.get("sentence", "")).strip())


def script_info(record: dict[str, Any]) -> dict[str, Any] | None:
    filename = record.get("filename", "")
    if not filename:
        return None
    try:
        path = safe_resolve(SCRIPTS_DIR, filename)
        if not path.exists():
            return {"filename": filename, "missing": True, "note": record.get("note", ""), "created_at": record.get("created_at", "")}
        stat = path.stat()
        return {
            "filename": path.name,
            "missing": False,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "note": record.get("note", ""),
            "created_at": record.get("created_at", ""),
            "view_url": f"/script/{path.name}",
            "download_url": f"/outputs/scripts/{path.name}",
            "run_url": f"/run/{path.name}",
        }
    except Exception:
        return None


def ordered_node_ids(tree: dict[str, Any]) -> list[str]:
    nodes = tree.get("nodes", {})
    roots = [node_id for node_id, node in nodes.items() if not node.get("parent_id")]
    ordered: list[str] = []
    def visit(node_id: str) -> None:
        if node_id in ordered:
            return
        ordered.append(node_id)
        for child_id in nodes.get(node_id, {}).get("children", []):
            if child_id in nodes:
                visit(child_id)
    for root_id in roots:
        visit(root_id)
    for node_id in nodes:
        if node_id not in ordered:
            visit(node_id)
    return ordered


def build_cycle_items() -> list[dict[str, Any]]:
    tree = load_tree()
    nodes = tree.get("nodes", {})
    items = []
    for index, node_id in enumerate(ordered_node_ids(tree), start=1):
        node = nodes.get(node_id, {})
        path = sentence_path(tree, node_id)
        scripts = []
        for record in node.get("scripts", []):
            if isinstance(record, dict):
                info = script_info(record)
                if info:
                    scripts.append(info)
        items.append({
            "index": index,
            "node_id": node_id,
            "title": node.get("title", "") or f"Sentence {index}",
            "sentence": node.get("sentence", ""),
            "parent_id": node.get("parent_id"),
            "children": node.get("children", []),
            "path": path,
            "story": story_text(path),
            "scripts": scripts,
            "script_count": len(scripts),
        })
    return items


@app.route("/", methods=["GET"])
@app.route("/cycle", methods=["GET"])
def cycle_page():
    return render_template("cycle.html")


@app.route("/script/<path:filename>", methods=["GET"])
def script_page(filename: str):
    return render_template("script.html", filename=filename)


@app.route("/api/data-location", methods=["GET"])
def api_data_location():
    return jsonify({"ok": True, "shared_data_dir": str(SHARED_DATA_DIR), "tree_file": str(TREE_FILE), "scripts_dir": str(SCRIPTS_DIR)})


@app.route("/api/cycle-items", methods=["GET"])
def api_cycle_items():
    try:
        return jsonify({"ok": True, "items": build_cycle_items()})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/script/<path:filename>", methods=["GET"])
def api_script(filename: str):
    try:
        path = safe_resolve(SCRIPTS_DIR, filename)
        if not path.exists():
            raise FileNotFoundError(filename)
        return jsonify({"ok": True, "filename": path.name, "source": path.read_text(encoding="utf-8")})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.route("/run/<path:filename>", methods=["GET"])
def run_script(filename: str):
    try:
        script_path = safe_resolve(SCRIPTS_DIR, filename)
        if not script_path.exists():
            return f"Script not found: {filename}", 404
        log_path = LOGS_DIR / f"{script_path.stem}-{uuid.uuid4().hex[:6]}.log"
        with log_path.open("w", encoding="utf-8") as log:
            log.write(f"Running: {script_path}\nStarted: {now_iso()}\n\n")
            log.flush()
            process = subprocess.Popen([sys.executable, str(script_path)], cwd=str(SCRIPTS_DIR), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        return render_template("run.html", filename=script_path.name, pid=process.pid, log_filename=log_path.name)
    except Exception as exc:
        return f"Run failed: {exc}", 500


@app.route("/outputs/scripts/<path:filename>", methods=["GET"])
def download_script(filename: str):
    return send_from_directory(SCRIPTS_DIR, filename, as_attachment=True)


@app.route("/outputs/logs/<path:filename>", methods=["GET"])
def download_log(filename: str):
    return send_from_directory(LOGS_DIR, filename, as_attachment=False)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5004, debug=True)
