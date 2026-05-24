#!/usr/bin/env python3
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


def slugify(text: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (slug[:max_len].strip("-") or "sentence-script")


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


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_tree() -> dict[str, Any]:
    return {
        "version": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "root_id": "root",
        "nodes": {
            "root": {
                "id": "root",
                "kind": "core_sentence",
                "sentence": "Create a core sentence to begin the simulation story tree.",
                "title": "Root core sentence",
                "parent_id": None,
                "children": [],
                "scripts": [],
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        },
    }


def load_tree() -> dict[str, Any]:
    tree = load_json(TREE_FILE, None)
    if not isinstance(tree, dict) or not isinstance(tree.get("nodes"), dict):
        tree = default_tree()
        save_tree(tree)
    return tree


def save_tree(tree: dict[str, Any]) -> None:
    tree["updated_at"] = now_iso()
    save_json(TREE_FILE, tree)


def get_node(tree: dict[str, Any], node_id: str) -> dict[str, Any]:
    node = tree.get("nodes", {}).get(node_id)
    if not node:
        raise FileNotFoundError("Sentence node not found.")
    return node


def node_summary(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node.get("id", ""),
        "kind": node.get("kind", "core_sentence"),
        "sentence": node.get("sentence", ""),
        "title": node.get("title", ""),
        "parent_id": node.get("parent_id"),
        "children": node.get("children", []),
        "script_count": len(node.get("scripts", []) if isinstance(node.get("scripts"), list) else []),
        "created_at": node.get("created_at", ""),
        "updated_at": node.get("updated_at", ""),
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


def story_text_from_path(path: list[dict[str, Any]]) -> str:
    return " ".join(
        str(item.get("sentence", "")).strip()
        for item in path
        if str(item.get("sentence", "")).strip()
    )


def script_info(filename: str) -> dict[str, Any]:
    path = safe_resolve(SCRIPTS_DIR, filename)
    if not path.exists():
        raise FileNotFoundError(filename)
    stat = path.stat()
    return {
        "filename": path.name,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "view_url": f"/script/{path.name}",
        "download_url": f"/outputs/scripts/{path.name}",
        "run_url": f"/run/{path.name}",
    }


def save_manual_script(source: str, node: dict[str, Any], requested_name: str = "") -> Path:
    if requested_name.strip():
        filename = f"{slugify(requested_name.replace('.py', ''), 90)}.py"
    else:
        filename = f"sentence-script-{slugify(node.get('sentence', ''), 70)}-{uuid.uuid4().hex[:8]}.py"
    path = SCRIPTS_DIR / filename
    if path.exists():
        path = SCRIPTS_DIR / f"{path.stem}-{uuid.uuid4().hex[:6]}.py"
    path.write_text(source.rstrip() + "\n", encoding="utf-8")
    return path


@app.route("/", methods=["GET"])
@app.route("/tree", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/node/<node_id>", methods=["GET"])
def node_page(node_id: str):
    return render_template("node.html", node_id=node_id)


@app.route("/script/<path:filename>", methods=["GET"])
def script_page(filename: str):
    return render_template("script.html", filename=filename)


@app.route("/api/data-location", methods=["GET"])
def api_data_location():
    return jsonify({"ok": True, "shared_data_dir": str(SHARED_DATA_DIR), "scripts_dir": str(SCRIPTS_DIR), "tree_file": str(TREE_FILE)})


@app.route("/api/tree", methods=["GET"])
def api_tree():
    try:
        tree = load_tree()
        return jsonify({"ok": True, "root_id": tree.get("root_id"), "nodes": {nid: node_summary(n) for nid, n in tree.get("nodes", {}).items()}})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/node/<node_id>", methods=["GET"])
def api_node(node_id: str):
    try:
        tree = load_tree()
        node = get_node(tree, node_id)
        children = [node_summary(tree["nodes"][cid]) for cid in node.get("children", []) if cid in tree["nodes"]]
        parent = node_summary(tree["nodes"][node["parent_id"]]) if node.get("parent_id") in tree["nodes"] else None
        scripts = []
        for record in node.get("scripts", []):
            if isinstance(record, dict) and record.get("filename"):
                try:
                    info = script_info(record["filename"])
                    info["script_node_id"] = record.get("id", "")
                    info["note"] = record.get("note", "")
                    info["created_at"] = record.get("created_at", "")
                    scripts.append(info)
                except Exception:
                    pass
        path = sentence_path(tree, node_id)
        return jsonify({
            "ok": True,
            "node": node_summary(node),
            "parent": parent,
            "children": children,
            "scripts": scripts,
            "path": path,
            "story": story_text_from_path(path),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.route("/api/node", methods=["POST"])
def api_create_root_node():
    try:
        payload = request.get_json(force=True) or {}
        sentence = str(payload.get("sentence", "")).strip()
        title = str(payload.get("title", "")).strip()
        if not sentence:
            return jsonify({"ok": False, "error": "Core sentence is required."}), 400
        tree = load_tree()
        node_id = uuid.uuid4().hex[:12]
        tree["nodes"][node_id] = {
            "id": node_id,
            "kind": "core_sentence",
            "sentence": sentence,
            "title": title or "Core sentence",
            "parent_id": None,
            "children": [],
            "scripts": [],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        save_tree(tree)
        return jsonify({"ok": True, "node": node_summary(tree["nodes"][node_id])})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/node/<node_id>", methods=["POST"])
def api_update_node(node_id: str):
    try:
        payload = request.get_json(force=True) or {}
        sentence = str(payload.get("sentence", "")).strip()
        title = str(payload.get("title", "")).strip()
        if not sentence:
            return jsonify({"ok": False, "error": "Sentence is required."}), 400
        tree = load_tree()
        node = get_node(tree, node_id)
        node["sentence"] = sentence
        node["title"] = title
        node["updated_at"] = now_iso()
        save_tree(tree)
        return jsonify({"ok": True, "node": node_summary(node)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/node/<node_id>/next", methods=["POST"])
def api_add_next_sentence(node_id: str):
    try:
        payload = request.get_json(force=True) or {}
        sentence = str(payload.get("sentence", "")).strip()
        title = str(payload.get("title", "")).strip()
        if not sentence:
            return jsonify({"ok": False, "error": "Next sentence is required."}), 400
        tree = load_tree()
        parent = get_node(tree, node_id)
        child_id = uuid.uuid4().hex[:12]
        child = {
            "id": child_id,
            "kind": "core_sentence",
            "sentence": sentence,
            "title": title or "Next sentence branch",
            "parent_id": node_id,
            "children": [],
            "scripts": [],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        tree["nodes"][child_id] = child
        parent.setdefault("children", []).append(child_id)
        parent["updated_at"] = now_iso()
        save_tree(tree)
        return jsonify({"ok": True, "node": node_summary(child), "parent": node_summary(parent)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/node/<node_id>/script", methods=["POST"])
def api_add_script_to_node(node_id: str):
    try:
        payload = request.get_json(force=True) or {}
        source = str(payload.get("source", "")).strip()
        filename = str(payload.get("filename", "")).strip()
        note = str(payload.get("note", "")).strip()
        if not source:
            return jsonify({"ok": False, "error": "Script source is required."}), 400
        tree = load_tree()
        node = get_node(tree, node_id)
        path = save_manual_script(source, node, filename)
        record = {"id": uuid.uuid4().hex[:10], "filename": path.name, "note": note, "created_at": now_iso(), "manual_entry": True}
        node.setdefault("scripts", []).append(record)
        node["updated_at"] = now_iso()
        save_tree(tree)
        return jsonify({"ok": True, "script": script_info(path.name), "node": node_summary(node)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/script/<path:filename>", methods=["GET"])
def api_script(filename: str):
    try:
        path = safe_resolve(SCRIPTS_DIR, filename)
        if not path.exists():
            raise FileNotFoundError(filename)
        return jsonify({"ok": True, "script": script_info(path.name), "source": path.read_text(encoding="utf-8")})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.route("/api/script/<path:filename>", methods=["POST"])
def api_update_script(filename: str):
    try:
        payload = request.get_json(force=True) or {}
        source = str(payload.get("source", ""))
        path = safe_resolve(SCRIPTS_DIR, filename)
        path.write_text(source.rstrip() + "\n", encoding="utf-8")
        return jsonify({"ok": True, "script": script_info(path.name)})
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
    app.run(host="127.0.0.1", port=5003, debug=True)
