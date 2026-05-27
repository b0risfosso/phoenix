#!/usr/bin/env python3
from __future__ import annotations

import csv, json, os, re, subprocess, sys, uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from flask import Flask, jsonify, render_template, request, send_from_directory

APP_DIR = Path(__file__).resolve().parent
SHARED_DATA_DIR = Path(os.environ.get("SIMULATION_SHARED_DATA_DIR", APP_DIR.parent / "simulation_shared_data")).expanduser().resolve()
SCRIPTS_DIR = SHARED_DATA_DIR / "scripts"
METADATA_DIR = SHARED_DATA_DIR / "metadata"
CSV_RUNS_DIR = SHARED_DATA_DIR / "csv_runs"
TREE_FILE = METADATA_DIR / "core_sentence_tree.json"
CSV_LINKS_FILE = METADATA_DIR / "csv_script_links.json"
CSV_RUN_INDEX_FILE = METADATA_DIR / "csv_run_index.json"

for directory in (SCRIPTS_DIR, METADATA_DIR, CSV_RUNS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)

CSV_RECORDER_TEMPLATE = """from vpython import *
import csv, json, os, time
from datetime import datetime
from pathlib import Path

RUN_SECONDS = int(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
FPS = 30
OUTPUT_DIR = Path(os.environ.get("SIMULATION_CSV_OUTPUT_DIR", ".")).expanduser().resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RUN_ID = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d-%H%M%S"))
CSV_PATH = OUTPUT_DIR / f"{RUN_ID}-simulation-state.csv"
META_PATH = OUTPUT_DIR / f"{RUN_ID}-metadata.json"

scene = canvas(title="CSV State Recorder Run", background=color.white)
agent = sphere(pos=vector(-3, 0, 0), radius=0.25, color=color.blue, make_trail=True)
target = sphere(pos=vector(3, 0, 0), radius=0.35, color=color.green)
velocity = vector(0.055, 0.025, 0)

start = time.time()
frame = 0

with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "run_id", "frame", "elapsed_seconds",
        "agent_x", "agent_y", "agent_z",
        "velocity_x", "velocity_y", "velocity_z",
        "distance_to_target", "event"
    ])
    writer.writeheader()

    while True:
        rate(FPS)
        elapsed = time.time() - start
        if elapsed >= RUN_SECONDS:
            break

        frame += 1
        agent.pos += velocity
        event = ""

        if abs(agent.pos.x) > 3.2:
            velocity.x *= -1
            event = "x_bounce"
        if abs(agent.pos.y) > 1.7:
            velocity.y *= -1
            event = "y_bounce"

        writer.writerow({
            "run_id": RUN_ID,
            "frame": frame,
            "elapsed_seconds": round(elapsed, 4),
            "agent_x": round(agent.pos.x, 5),
            "agent_y": round(agent.pos.y, 5),
            "agent_z": round(agent.pos.z, 5),
            "velocity_x": round(velocity.x, 5),
            "velocity_y": round(velocity.y, 5),
            "velocity_z": round(velocity.z, 5),
            "distance_to_target": round(mag(agent.pos - target.pos), 5),
            "event": event,
        })
        f.flush()

metadata = {
    "run_id": RUN_ID,
    "csv_path": str(CSV_PATH),
    "run_seconds": RUN_SECONDS,
    "fps": FPS,
    "frames_recorded": frame,
    "completed_at": datetime.now().isoformat(timespec="seconds"),
}
META_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print(f"CSV saved to: {CSV_PATH}")
"""

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def slugify(text: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:max_len].strip("-") or "csv-recorder"

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

def load_tree() -> dict[str, Any]:
    tree = load_json(TREE_FILE, {"nodes": {}, "root_id": "root"})
    if not isinstance(tree, dict):
        tree = {"nodes": {}, "root_id": "root"}
    tree.setdefault("nodes", {})
    return tree

def load_links() -> dict[str, Any]:
    data = load_json(CSV_LINKS_FILE, {"links": {}})
    if not isinstance(data, dict):
        data = {"links": {}}
    if not isinstance(data.get("links"), dict):
        data["links"] = {}
    return data

def save_links(data: dict[str, Any]) -> None:
    save_json(CSV_LINKS_FILE, data)

def load_run_index() -> dict[str, Any]:
    data = load_json(CSV_RUN_INDEX_FILE, {"runs": []})
    if not isinstance(data, dict):
        data = {"runs": []}
    if not isinstance(data.get("runs"), list):
        data["runs"] = []
    return data

def save_run_index(data: dict[str, Any]) -> None:
    save_json(CSV_RUN_INDEX_FILE, data)

def script_info(filename: str) -> dict[str, Any]:
    path = safe_resolve(SCRIPTS_DIR, filename)
    if not path.exists():
        raise FileNotFoundError(filename)
    stat = path.stat()
    return {
        "filename": path.name,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "download_url": f"/outputs/scripts/{path.name}",
        "view_url": f"/script/{path.name}",
        "run_csv_url": f"/run-csv/{path.name}",
    }

def read_source(filename: str) -> str:
    path = safe_resolve(SCRIPTS_DIR, filename)
    if not path.exists():
        raise FileNotFoundError(filename)
    return path.read_text(encoding="utf-8")

def write_source(filename: str, source: str) -> None:
    path = safe_resolve(SCRIPTS_DIR, filename)
    if not path.exists():
        raise FileNotFoundError(filename)
    path.write_text(source.rstrip() + "\n", encoding="utf-8")

def sentence_path(node_id: str) -> list[dict[str, str]]:
    tree = load_tree()
    nodes = tree.get("nodes", {})
    path, seen, current = [], set(), node_id
    while current and current not in seen:
        seen.add(current)
        node = nodes.get(current)
        if not node:
            break
        path.append({"node_id": current, "title": str(node.get("title", "")), "sentence": str(node.get("sentence", ""))})
        current = node.get("parent_id")
    path.reverse()
    return path

def story_text(path: list[dict[str, str]]) -> str:
    return " ".join(item.get("sentence", "").strip() for item in path if item.get("sentence", "").strip())

def count_runs_for_script(script_filename: str) -> int:
    return sum(1 for run in load_run_index().get("runs", []) if isinstance(run, dict) and run.get("script_filename") == script_filename)

def recent_runs_for_script(script_filename: str, limit: int = 12) -> list[dict[str, Any]]:
    runs = [run for run in load_run_index().get("runs", []) if isinstance(run, dict) and run.get("script_filename") == script_filename]
    return list(reversed(runs[-limit:]))

def csv_children(parent_filename: str) -> list[dict[str, Any]]:
    records = load_links().get("links", {}).get(parent_filename, [])
    output = []
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict):
            continue
        child = record.get("child_filename", "")
        item = {
            "id": record.get("id", ""),
            "parent_filename": parent_filename,
            "child_filename": child,
            "relationship": record.get("relationship", ""),
            "note": record.get("note", ""),
            "created_at": record.get("created_at", ""),
            "missing": True,
            "run_count": count_runs_for_script(child),
        }
        try:
            item.update(script_info(child))
            item["missing"] = False
        except Exception:
            pass
        output.append(item)
    return output

def find_story_scripts() -> list[dict[str, Any]]:
    tree = load_tree()
    stories = []
    for node_id, node in tree.get("nodes", {}).items():
        scripts = []
        for record in node.get("scripts", []) if isinstance(node.get("scripts", []), list) else []:
            if not isinstance(record, dict) or not record.get("filename"):
                continue
            filename = record.get("filename")
            try:
                info = script_info(filename)
                info["script_note"] = record.get("note", "")
                info["csv_child_count"] = len(csv_children(filename))
                scripts.append(info)
            except Exception:
                scripts.append({"filename": filename, "missing": True, "script_note": record.get("note", ""), "csv_child_count": 0})
        path = sentence_path(node_id)
        stories.append({
            "node_id": node_id,
            "title": node.get("title", "") or "Untitled story",
            "sentence": node.get("sentence", ""),
            "story_path": path,
            "story": story_text(path),
            "scripts": scripts,
            "script_count": len(scripts),
        })
    return stories

def csv_file_info(path: Path) -> dict[str, Any]:
    stat = path.stat()
    row_count, headers = 0, []
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            row_count = sum(1 for _ in reader)
    except Exception:
        pass
    return {"filename": path.name, "size_bytes": stat.st_size, "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"), "row_count": row_count, "headers": headers, "download_url": f"/outputs/csv_runs/{path.parent.name}/{path.name}"}

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/script/<path:filename>", methods=["GET"])
def script_page(filename: str):
    return render_template("script.html", filename=filename)

@app.route("/run-csv/<path:filename>", methods=["GET"])
def run_csv_page(filename: str):
    return render_template("run_csv.html", filename=filename)

@app.route("/api/data-location", methods=["GET"])
def api_data_location():
    return jsonify({"ok": True, "shared_data_dir": str(SHARED_DATA_DIR), "scripts_dir": str(SCRIPTS_DIR), "csv_runs_dir": str(CSV_RUNS_DIR), "tree_file": str(TREE_FILE), "csv_links_file": str(CSV_LINKS_FILE), "csv_run_index_file": str(CSV_RUN_INDEX_FILE)})


def build_story_tree_items() -> dict[str, Any]:
    tree = load_tree()
    nodes = tree.get("nodes", {})
    items: dict[str, Any] = {}

    for node_id, node in nodes.items():
        scripts = []
        for record in node.get("scripts", []) if isinstance(node.get("scripts", []), list) else []:
            if not isinstance(record, dict):
                continue
            filename = record.get("filename", "")
            if not filename:
                continue
            try:
                info = script_info(filename)
                info["script_note"] = record.get("note", "")
                info["csv_child_count"] = len(csv_children(filename))
                scripts.append(info)
            except Exception:
                scripts.append({
                    "filename": filename,
                    "missing": True,
                    "script_note": record.get("note", ""),
                    "csv_child_count": 0,
                })

        path = sentence_path(node_id)
        items[node_id] = {
            "node_id": node_id,
            "title": node.get("title", "") or "Untitled sentence",
            "sentence": node.get("sentence", ""),
            "parent_id": node.get("parent_id"),
            "children": node.get("children", []) if isinstance(node.get("children", []), list) else [],
            "story_path": path,
            "story": story_text(path),
            "scripts": scripts,
            "script_count": len(scripts),
            "created_at": node.get("created_at", ""),
            "updated_at": node.get("updated_at", ""),
        }

    roots = [
        node_id for node_id, item in items.items()
        if not item.get("parent_id") or item.get("parent_id") not in items
    ]

    return {
        "root_ids": roots,
        "nodes": items,
        "node_count": len(items),
        "scripted_node_count": sum(1 for item in items.values() if item.get("script_count", 0) > 0),
    }


@app.route("/api/story-tree", methods=["GET"])
def api_story_tree():
    try:
        query = request.args.get("q", "").strip().lower()
        scripted_only = request.args.get("scripted", "false").lower() == "true"
        data = build_story_tree_items()
        nodes = data["nodes"]

        if query or scripted_only:
            keep = set()

            def include_ancestors(node_id: str) -> None:
                current = node_id
                seen = set()
                while current and current not in seen and current in nodes:
                    seen.add(current)
                    keep.add(current)
                    current = nodes[current].get("parent_id")

            def include_descendants(node_id: str) -> None:
                if node_id not in nodes or node_id in keep:
                    # Still traverse children already kept.
                    pass
                keep.add(node_id)
                for child_id in nodes.get(node_id, {}).get("children", []):
                    if child_id in nodes:
                        include_descendants(child_id)

            for node_id, item in nodes.items():
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
                    include_ancestors(node_id)
                    # For search results, include children so the visible branch context remains useful.
                    if query:
                        for child_id in item.get("children", []):
                            if child_id in nodes:
                                keep.add(child_id)

            nodes = {node_id: item for node_id, item in nodes.items() if node_id in keep}
            for item in nodes.values():
                item["children"] = [child_id for child_id in item.get("children", []) if child_id in nodes]

            roots = [
                node_id for node_id, item in nodes.items()
                if not item.get("parent_id") or item.get("parent_id") not in nodes
            ]
            data = {
                "root_ids": roots,
                "nodes": nodes,
                "node_count": len(nodes),
                "scripted_node_count": sum(1 for item in nodes.values() if item.get("script_count", 0) > 0),
            }

        return jsonify({"ok": True, **data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/stories", methods=["GET"])
def api_stories():
    try:
        query = request.args.get("q", "").strip().lower()
        scripted_only = request.args.get("scripted", "false").lower() == "true"
        stories = find_story_scripts()
        if scripted_only:
            stories = [story for story in stories if story.get("script_count", 0) > 0]
        if query:
            stories = [story for story in stories if query in " ".join([story.get("title",""), story.get("sentence",""), story.get("story",""), " ".join(script.get("filename","") for script in story.get("scripts", []))]).lower()]
        return jsonify({"ok": True, "items": stories})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/script/<path:filename>", methods=["GET"])
def api_script(filename: str):
    try:
        return jsonify({"ok": True, "script": script_info(filename), "source": read_source(filename), "csv_children": csv_children(filename), "recent_runs": recent_runs_for_script(filename), "csv_recorder_template": CSV_RECORDER_TEMPLATE})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404

@app.route("/api/script/<path:filename>", methods=["POST"])
def api_update_script(filename: str):
    try:
        payload = request.get_json(force=True) or {}
        write_source(filename, str(payload.get("source", "")))
        return jsonify({"ok": True, "script": script_info(filename)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/script/<path:parent_filename>/csv-child", methods=["POST"])
def api_add_csv_child(parent_filename: str):
    try:
        script_info(parent_filename)
        payload = request.get_json(force=True) or {}
        source = str(payload.get("source", "")).strip()
        if not source:
            return jsonify({"ok": False, "error": "CSV child script source is required."}), 400
        requested = str(payload.get("filename", "")).strip()
        if requested:
            child_name = f"{slugify(requested.replace('.py',''), 90)}.py"
        else:
            child_name = f"{slugify(Path(parent_filename).stem, 52)}-csv-recorder-{uuid.uuid4().hex[:8]}.py"
        child_path = SCRIPTS_DIR / child_name
        if child_path.exists():
            child_path = SCRIPTS_DIR / f"{child_path.stem}-{uuid.uuid4().hex[:6]}.py"
        child_path.write_text(source.rstrip() + "\n", encoding="utf-8")
        data = load_links()
        records = data.setdefault("links", {}).setdefault(parent_filename, [])
        if not isinstance(records, list):
            records = []
            data["links"][parent_filename] = records
        record = {"id": uuid.uuid4().hex[:10], "parent_filename": parent_filename, "child_filename": child_path.name, "relationship": "csv recorder", "note": str(payload.get("note","")).strip(), "created_at": now_iso(), "manual_entry": True, "purpose": "csv_storage"}
        records.append(record)
        save_links(data)
        return jsonify({"ok": True, "record": record, "child": script_info(child_path.name), "csv_children": csv_children(parent_filename)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/script/<path:parent_filename>/link-existing-csv", methods=["POST"])
def api_link_existing_csv(parent_filename: str):
    try:
        script_info(parent_filename)
        payload = request.get_json(force=True) or {}
        child = str(payload.get("child_filename", "")).strip()
        if not child:
            return jsonify({"ok": False, "error": "child_filename is required."}), 400
        script_info(child)
        data = load_links()
        records = data.setdefault("links", {}).setdefault(parent_filename, [])
        record = {"id": uuid.uuid4().hex[:10], "parent_filename": parent_filename, "child_filename": child, "relationship": "csv recorder", "note": str(payload.get("note", "")).strip(), "created_at": now_iso(), "manual_entry": False, "purpose": "csv_storage"}
        records.append(record)
        save_links(data)
        return jsonify({"ok": True, "record": record, "csv_children": csv_children(parent_filename)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/csv-link/<path:parent_filename>/<link_id>", methods=["DELETE"])
def api_unlink(parent_filename: str, link_id: str):
    try:
        data = load_links()
        records = data.get("links", {}).get(parent_filename, [])
        data["links"][parent_filename] = [r for r in records if not (isinstance(r, dict) and r.get("id") == link_id)]
        save_links(data)
        return jsonify({"ok": True, "csv_children": csv_children(parent_filename)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/run-csv/<path:filename>", methods=["POST"])
def api_run_csv(filename: str):
    try:
        script_path = safe_resolve(SCRIPTS_DIR, filename)
        if not script_path.exists():
            raise FileNotFoundError(filename)
        payload = request.get_json(force=True) or {}
        run_seconds = int(payload.get("run_seconds", 60) or 60)
        timeout_seconds = max(run_seconds + 45, 75)
        run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(Path(filename).stem, 40)}-{uuid.uuid4().hex[:6]}"
        run_dir = CSV_RUNS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        log_path = run_dir / f"{run_id}.log"
        env = os.environ.copy()
        env["SIMULATION_CSV_OUTPUT_DIR"] = str(run_dir)
        env["SIMULATION_CSV_RUN_ID"] = run_id
        env["SIMULATION_CSV_RUN_SECONDS"] = str(run_seconds)
        with log_path.open("w", encoding="utf-8") as log:
            log.write(f"Running CSV script: {script_path}\nRun ID: {run_id}\nStarted: {now_iso()}\nOutput directory: {run_dir}\n\n")
            log.flush()
            process = subprocess.run([sys.executable, str(script_path)], cwd=str(SCRIPTS_DIR), stdout=log, stderr=subprocess.STDOUT, timeout=timeout_seconds, env=env)
        csv_files = [csv_file_info(path) for path in sorted(run_dir.glob("*.csv"))]
        metadata_files = [{"filename": path.name, "download_url": f"/outputs/csv_runs/{run_id}/{path.name}"} for path in sorted(run_dir.glob("*.json"))]
        record = {"run_id": run_id, "script_filename": filename, "run_seconds": run_seconds, "started_at": now_iso(), "returncode": process.returncode, "run_dir": str(run_dir), "log_url": f"/outputs/csv_runs/{run_id}/{log_path.name}", "csv_files": csv_files, "metadata_files": metadata_files}
        index = load_run_index()
        index.setdefault("runs", []).append(record)
        save_run_index(index)
        return jsonify({"ok": True, "run": record})
    except subprocess.TimeoutExpired as exc:
        return jsonify({"ok": False, "error": f"CSV run timed out: {exc}"}), 500
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/runs", methods=["GET"])
def api_runs():
    try:
        script_filename = request.args.get("script", "").strip()
        runs = load_run_index().get("runs", [])
        if script_filename:
            runs = [run for run in runs if isinstance(run, dict) and run.get("script_filename") == script_filename]
        return jsonify({"ok": True, "items": list(reversed(runs))})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/outputs/scripts/<path:filename>", methods=["GET"])
def download_script(filename: str):
    return send_from_directory(SCRIPTS_DIR, filename, as_attachment=True)

@app.route("/outputs/csv_runs/<path:filename>", methods=["GET"])
def download_csv_run_file(filename: str):
    return send_from_directory(CSV_RUNS_DIR, filename, as_attachment=False)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5007, debug=True)
