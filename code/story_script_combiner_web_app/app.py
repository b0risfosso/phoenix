#!/usr/bin/env python3
from __future__ import annotations

import csv
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
SHARED_DATA_DIR = Path(
    os.environ.get("SIMULATION_SHARED_DATA_DIR")
    or os.environ.get("SHARED_DATA_DIR")
    or (APP_DIR.parent / "simulation_shared_data")
).expanduser().resolve()

SCRIPTS_DIR = SHARED_DATA_DIR / "scripts"
METADATA_DIR = SHARED_DATA_DIR / "metadata"
LOGS_DIR = SHARED_DATA_DIR / "logs"
CSV_RUNS_DIR = SHARED_DATA_DIR / "csv_runs"

TREE_FILE = METADATA_DIR / "core_sentence_tree.json"
COMBINE_INDEX_FILE = METADATA_DIR / "combined_story_script_index.json"
CSV_RUN_INDEX_FILE = METADATA_DIR / "csv_run_index.json"

for directory in (SCRIPTS_DIR, METADATA_DIR, LOGS_DIR, CSV_RUNS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(text: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:max_len].strip("-") or "combined-story"


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
                "sentence": "Create stories in the core sentence branching app first.",
                "title": "Root story",
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
    tree.setdefault("nodes", {})
    tree.setdefault("root_id", "root")
    return tree


def save_tree(tree: dict[str, Any]) -> None:
    tree["updated_at"] = now_iso()
    save_json(TREE_FILE, tree)


def node_summary(node: dict[str, Any]) -> dict[str, Any]:
    scripts = node.get("scripts", [])
    if not isinstance(scripts, list):
        scripts = []
    children = node.get("children", [])
    if not isinstance(children, list):
        children = []
    return {
        "id": node.get("id", ""),
        "kind": node.get("kind", "core_sentence"),
        "title": node.get("title", ""),
        "sentence": node.get("sentence", ""),
        "parent_id": node.get("parent_id"),
        "children": children,
        "script_count": len(scripts),
        "combined_from": node.get("combined_from", []),
        "created_at": node.get("created_at", ""),
        "updated_at": node.get("updated_at", ""),
    }


def sentence_path(tree: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    nodes = tree.get("nodes", {})
    path = []
    seen = set()
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
    return " ".join(
        str(item.get("sentence", "")).strip()
        for item in path
        if str(item.get("sentence", "")).strip()
    )


def ordered_node_ids(tree: dict[str, Any]) -> list[str]:
    nodes = tree.get("nodes", {})
    roots = [node_id for node_id, node in nodes.items() if not node.get("parent_id")]
    ordered = []
    seen = set()

    def visit(node_id: str) -> None:
        if node_id in seen:
            return
        seen.add(node_id)
        ordered.append(node_id)
        for child_id in nodes.get(node_id, {}).get("children", []):
            if child_id in nodes:
                visit(child_id)

    for root_id in roots:
        visit(root_id)
    for node_id in nodes:
        if node_id not in seen:
            visit(node_id)
    return ordered


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
        "csv_run_count": len(recent_runs_for_script(path.name)),
    }


def get_node_scripts(node: dict[str, Any]) -> list[dict[str, Any]]:
    scripts = []
    for record in node.get("scripts", []):
        if not isinstance(record, dict):
            continue
        filename = record.get("filename", "")
        if not filename:
            continue
        try:
            info = script_info(filename)
            info["script_node_id"] = record.get("id", "")
            info["note"] = record.get("note", "")
            info["created_at"] = record.get("created_at", "")
            scripts.append(info)
        except Exception:
            scripts.append({
                "filename": filename,
                "missing": True,
                "script_node_id": record.get("id", ""),
                "note": record.get("note", ""),
                "created_at": record.get("created_at", ""),
            })
    return scripts


def save_script_source(source: str, requested_name: str, fallback_name: str) -> Path:
    if requested_name.strip():
        filename = requested_name.strip()
        if not filename.endswith(".py"):
            filename += ".py"
        filename = f"{slugify(filename.replace('.py', ''), 90)}.py"
    else:
        filename = f"{slugify(fallback_name, 70)}-{uuid.uuid4().hex[:8]}.py"

    path = SCRIPTS_DIR / filename
    if path.exists():
        path = SCRIPTS_DIR / f"{path.stem}-{uuid.uuid4().hex[:6]}.py"
    path.write_text(source.rstrip() + "\n", encoding="utf-8")
    return path


def load_combine_index() -> dict[str, Any]:
    data = load_json(COMBINE_INDEX_FILE, {"combined": []})
    if not isinstance(data, dict):
        data = {"combined": []}
    if not isinstance(data.get("combined"), list):
        data["combined"] = []
    return data


def save_combine_index(data: dict[str, Any]) -> None:
    save_json(COMBINE_INDEX_FILE, data)


def load_run_index() -> dict[str, Any]:
    data = load_json(CSV_RUN_INDEX_FILE, {"runs": []})
    if not isinstance(data, dict):
        data = {"runs": []}
    if not isinstance(data.get("runs"), list):
        data["runs"] = []
    return data


def save_run_index(data: dict[str, Any]) -> None:
    save_json(CSV_RUN_INDEX_FILE, data)


def csv_file_info(path: Path) -> dict[str, Any]:
    stat = path.stat()
    row_count = 0
    headers = []
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            row_count = sum(1 for _ in reader)
    except Exception:
        pass
    run_id = path.parent.name
    return {
        "filename": path.name,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "row_count": row_count,
        "headers": headers,
        "download_url": f"/outputs/csv_runs/{run_id}/{path.name}",
    }


def recent_runs_for_script(script_filename: str, limit: int = 20) -> list[dict[str, Any]]:
    runs = [
        run for run in load_run_index().get("runs", [])
        if isinstance(run, dict) and run.get("script_filename") == script_filename
    ]
    refreshed = []
    for run in reversed(runs[-limit:]):
        item = dict(run)
        if item.get("save_csv") and item.get("run_dir"):
            run_dir = Path(item["run_dir"])
            if run_dir.exists():
                item["csv_files"] = [csv_file_info(path) for path in sorted(run_dir.glob("*.csv"))]
        refreshed.append(item)
    return refreshed


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/combine", methods=["GET"])
def combine_page():
    ids = request.args.get("ids", "")
    node_ids = [item for item in ids.split(",") if item.strip()]
    return render_template("combine.html", node_ids=node_ids)


@app.route("/script/<path:filename>", methods=["GET"])
def script_page(filename: str):
    return render_template("script.html", filename=filename)


@app.route("/run/<path:filename>", methods=["GET"])
def run_page(filename: str):
    return render_template("run.html", filename=filename)


@app.route("/api/data-location", methods=["GET"])
def api_data_location():
    return jsonify({
        "ok": True,
        "shared_data_dir": str(SHARED_DATA_DIR),
        "scripts_dir": str(SCRIPTS_DIR),
        "metadata_dir": str(METADATA_DIR),
        "logs_dir": str(LOGS_DIR),
        "csv_runs_dir": str(CSV_RUNS_DIR),
        "tree_file": str(TREE_FILE),
        "combine_index_file": str(COMBINE_INDEX_FILE),
        "csv_run_index_file": str(CSV_RUN_INDEX_FILE),
    })


@app.route("/api/story-tree", methods=["GET"])
def api_story_tree():
    try:
        query = request.args.get("q", "").strip().lower()
        scripted_only = request.args.get("scripted", "false").lower() == "true"
        tree = load_tree()
        nodes = tree.get("nodes", {})
        result_nodes = {}

        for node_id, node in nodes.items():
            path = sentence_path(tree, node_id)
            summary = node_summary(node)
            summary["story_path"] = path
            summary["story"] = story_text(path)
            summary["scripts"] = get_node_scripts(node)
            summary["depth"] = max(0, len(path) - 1)
            result_nodes[node_id] = summary

        if query or scripted_only:
            keep = set()

            def keep_ancestors(candidate_id: str) -> None:
                current_id = candidate_id
                seen = set()
                while current_id and current_id not in seen and current_id in result_nodes:
                    seen.add(current_id)
                    keep.add(current_id)
                    current_id = result_nodes[current_id].get("parent_id")

            for node_id, item in result_nodes.items():
                script_names = " ".join(script.get("filename", "") for script in item.get("scripts", []))
                blob = " ".join([
                    item.get("title", ""),
                    item.get("sentence", ""),
                    item.get("story", ""),
                    script_names,
                ]).lower()
                query_match = (not query) or query in blob
                script_match = (not scripted_only) or item.get("script_count", 0) > 0
                if query_match and script_match:
                    keep_ancestors(node_id)
                    if query:
                        for child_id in item.get("children", []):
                            if child_id in result_nodes:
                                keep.add(child_id)

            result_nodes = {node_id: item for node_id, item in result_nodes.items() if node_id in keep}
            for item in result_nodes.values():
                item["children"] = [child_id for child_id in item.get("children", []) if child_id in result_nodes]

        root_ids = [
            node_id for node_id, item in result_nodes.items()
            if not item.get("parent_id") or item.get("parent_id") not in result_nodes
        ]

        return jsonify({
            "ok": True,
            "root_ids": root_ids,
            "nodes": result_nodes,
            "node_count": len(result_nodes),
            "scripted_node_count": sum(1 for item in result_nodes.values() if item.get("script_count", 0) > 0),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/stories-by-ids", methods=["POST"])
def api_stories_by_ids():
    try:
        payload = request.get_json(force=True) or {}
        ids = payload.get("ids", [])
        if not isinstance(ids, list):
            ids = []
        tree = load_tree()
        items = []
        for node_id in ids:
            node = tree.get("nodes", {}).get(str(node_id))
            if not node:
                continue
            path = sentence_path(tree, str(node_id))
            summary = node_summary(node)
            summary["story_path"] = path
            summary["story"] = story_text(path)
            summary["scripts"] = get_node_scripts(node)
            items.append(summary)
        return jsonify({"ok": True, "items": items})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/combine", methods=["POST"])
def api_combine():
    try:
        payload = request.get_json(force=True) or {}
        source_ids = payload.get("source_ids", [])
        if not isinstance(source_ids, list):
            source_ids = []
        source_ids = [str(item) for item in source_ids if str(item).strip()]
        if len(source_ids) < 2:
            return jsonify({"ok": False, "error": "Select at least two source stories."}), 400

        title = str(payload.get("title", "")).strip() or "Combined story"
        combined_story = str(payload.get("combined_story", "")).strip()
        script_source = str(payload.get("script_source", "")).strip()
        script_filename = str(payload.get("script_filename", "")).strip()
        script_note = str(payload.get("script_note", "")).strip()

        if not combined_story:
            return jsonify({"ok": False, "error": "Combined story is required."}), 400
        if not script_source:
            return jsonify({"ok": False, "error": "Combined script source is required."}), 400

        tree = load_tree()
        missing = [node_id for node_id in source_ids if node_id not in tree.get("nodes", {})]
        if missing:
            return jsonify({"ok": False, "error": f"Missing source node ids: {', '.join(missing)}"}), 404

        combined_id = uuid.uuid4().hex[:12]
        script_path = save_script_source(script_source, script_filename, f"combined-story-script-{title}")

        script_record = {
            "id": uuid.uuid4().hex[:10],
            "filename": script_path.name,
            "note": script_note or "Manual combined script",
            "created_at": now_iso(),
            "manual_entry": True,
            "combined_from": source_ids,
        }

        node = {
            "id": combined_id,
            "kind": "combined_story",
            "title": title,
            "sentence": combined_story,
            "parent_id": None,
            "children": [],
            "scripts": [script_record],
            "combined_from": source_ids,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        tree.setdefault("nodes", {})[combined_id] = node
        save_tree(tree)

        combine_index = load_combine_index()
        combine_record = {
            "id": uuid.uuid4().hex[:10],
            "combined_node_id": combined_id,
            "combined_script_filename": script_path.name,
            "source_node_ids": source_ids,
            "title": title,
            "created_at": now_iso(),
        }
        combine_index.setdefault("combined", []).append(combine_record)
        save_combine_index(combine_index)

        return jsonify({
            "ok": True,
            "node": node_summary(node),
            "script": script_info(script_path.name),
            "combine_record": combine_record,
        })
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
        if not path.exists():
            raise FileNotFoundError(filename)
        path.write_text(source.rstrip() + "\n", encoding="utf-8")
        return jsonify({"ok": True, "script": script_info(path.name)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/run/<path:filename>", methods=["POST"])
def api_run_script(filename: str):
    try:
        script_path = safe_resolve(SCRIPTS_DIR, filename)
        if not script_path.exists():
            return jsonify({"ok": False, "error": f"Script not found: {filename}"}), 404

        payload = request.get_json(force=True) or {}
        save_csv = bool(payload.get("save_csv", False))
        run_seconds = int(float(payload.get("run_seconds", 60) or 60))
        run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(script_path.stem, 40)}-{uuid.uuid4().hex[:6]}"

        if save_csv:
            run_dir = CSV_RUNS_DIR / run_id
            log_url = f"/outputs/csv_runs/{run_id}/{run_id}.log"
        else:
            run_dir = LOGS_DIR / "non_csv_runs"
            log_url = f"/outputs/logs/non_csv_runs/{run_id}.log"

        run_dir.mkdir(parents=True, exist_ok=True)
        log_path = run_dir / f"{run_id}.log"

        env = os.environ.copy()
        env["SIMULATION_CSV_RUN_SECONDS"] = str(run_seconds)
        if save_csv:
            env["SIMULATION_CSV_OUTPUT_DIR"] = str(run_dir)
            env["SIMULATION_CSV_RUN_ID"] = run_id
        else:
            env.pop("SIMULATION_CSV_OUTPUT_DIR", None)
            env.pop("SIMULATION_CSV_RUN_ID", None)

        with log_path.open("w", encoding="utf-8") as log:
            log.write(f"Running: {script_path}\n")
            log.write(f"Started: {now_iso()}\n")
            log.write(f"Run ID: {run_id}\n")
            log.write(f"Save CSV: {save_csv}\n")
            log.write(f"Run seconds: {run_seconds}\n")
            if save_csv:
                log.write(f"CSV output directory: {run_dir}\n")
            log.write("\n")
            log.flush()

            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(SCRIPTS_DIR),
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=env,
            )

        record = {
            "run_id": run_id,
            "script_filename": script_path.name,
            "save_csv": save_csv,
            "run_seconds": run_seconds,
            "started_at": now_iso(),
            "pid": process.pid,
            "run_dir": str(run_dir) if save_csv else "",
            "log_path": str(log_path),
            "log_url": log_url,
            "csv_files": [],
        }
        index = load_run_index()
        index.setdefault("runs", []).append(record)
        save_run_index(index)
        return jsonify({"ok": True, "run": record})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/runs", methods=["GET"])
def api_runs():
    try:
        script_filename = request.args.get("script", "").strip()
        runs = load_run_index().get("runs", [])
        if script_filename:
            runs = [run for run in runs if isinstance(run, dict) and run.get("script_filename") == script_filename]

        refreshed = []
        for run in runs:
            if not isinstance(run, dict):
                continue
            item = dict(run)
            if item.get("save_csv") and item.get("run_dir"):
                run_dir = Path(item["run_dir"])
                if run_dir.exists():
                    item["csv_files"] = [csv_file_info(path) for path in sorted(run_dir.glob("*.csv"))]
            refreshed.append(item)

        return jsonify({"ok": True, "items": list(reversed(refreshed))})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/outputs/scripts/<path:filename>", methods=["GET"])
def download_script(filename: str):
    return send_from_directory(SCRIPTS_DIR, filename, as_attachment=True)


@app.route("/outputs/csv_runs/<path:filename>", methods=["GET"])
def download_csv_run_file(filename: str):
    return send_from_directory(CSV_RUNS_DIR, filename, as_attachment=False)


@app.route("/outputs/logs/<path:filename>", methods=["GET"])
def download_log_file(filename: str):
    return send_from_directory(LOGS_DIR, filename, as_attachment=False)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5009, debug=True)
