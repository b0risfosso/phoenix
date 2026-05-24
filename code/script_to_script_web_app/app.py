#!/usr/bin/env python3
from __future__ import annotations

import json, os, re, subprocess, sys, uuid
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
SCRIPT_LINKS_FILE = METADATA_DIR / "script_to_script_links.json"

for d in (SCRIPTS_DIR, METADATA_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def slugify(text: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:max_len].strip("-") or "manual-script"

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
    return tree if isinstance(tree, dict) else {"nodes": {}, "root_id": "root"}

def load_links() -> dict[str, Any]:
    data = load_json(SCRIPT_LINKS_FILE, {"links": {}})
    if not isinstance(data, dict):
        data = {"links": {}}
    if not isinstance(data.get("links"), dict):
        data["links"] = {}
    return data

def save_links(data: dict[str, Any]) -> None:
    save_json(SCRIPT_LINKS_FILE, data)

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

def sentence_path(node_id: str) -> list[dict[str, str]]:
    tree = load_tree()
    nodes = tree.get("nodes", {})
    path, seen, cur = [], set(), node_id
    while cur and cur not in seen:
        seen.add(cur)
        node = nodes.get(cur)
        if not node:
            break
        path.append({"node_id": cur, "title": str(node.get("title","")), "sentence": str(node.get("sentence",""))})
        cur = node.get("parent_id")
    path.reverse()
    return path

def story_text(path: list[dict[str, str]]) -> str:
    return " ".join(item.get("sentence","").strip() for item in path if item.get("sentence","").strip())

def find_sentence_nodes_for_script(filename: str) -> list[dict[str, Any]]:
    tree = load_tree()
    nodes = tree.get("nodes", {})
    matches = []
    for node_id, node in nodes.items():
        for record in node.get("scripts", []) if isinstance(node.get("scripts", []), list) else []:
            if isinstance(record, dict) and record.get("filename") == filename:
                path = sentence_path(node_id)
                matches.append({
                    "node_id": node_id,
                    "title": node.get("title",""),
                    "sentence": node.get("sentence",""),
                    "parent_id": node.get("parent_id"),
                    "script_note": record.get("note",""),
                    "script_record_id": record.get("id",""),
                    "created_at": record.get("created_at",""),
                    "story_path": path,
                    "story": story_text(path),
                })
    return matches

def read_source(filename: str) -> str:
    path = safe_resolve(SCRIPTS_DIR, filename)
    if not path.exists():
        raise FileNotFoundError(filename)
    return path.read_text(encoding="utf-8")

def save_child_script(parent_filename: str, source: str, requested_name: str = "") -> Path:
    if requested_name.strip():
        filename = f"{slugify(requested_name.replace('.py',''),90)}.py"
    else:
        filename = f"{slugify(Path(parent_filename).stem,50)}-child-{uuid.uuid4().hex[:8]}.py"
    path = SCRIPTS_DIR / filename
    if path.exists():
        path = SCRIPTS_DIR / f"{path.stem}-{uuid.uuid4().hex[:6]}.py"
    path.write_text(source.rstrip() + "\n", encoding="utf-8")
    return path

def linked_children(parent_filename: str) -> list[dict[str, Any]]:
    records = load_links().get("links", {}).get(parent_filename, [])
    out = []
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict):
            continue
        child = record.get("child_filename","")
        item = {"id": record.get("id",""), "parent_filename": parent_filename, "child_filename": child,
                "relationship": record.get("relationship",""), "note": record.get("note",""),
                "created_at": record.get("created_at",""), "missing": True}
        try:
            item.update(script_info(child)); item["missing"] = False
        except Exception:
            pass
        out.append(item)
    return out

def linked_parents(child_filename: str) -> list[dict[str, Any]]:
    data = load_links().get("links", {})
    out = []
    for parent, records in data.items():
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict) and record.get("child_filename") == child_filename:
                item = {"id": record.get("id",""), "parent_filename": parent, "relationship": record.get("relationship",""),
                        "note": record.get("note",""), "created_at": record.get("created_at",""), "missing": True}
                try:
                    item.update(script_info(parent)); item["missing"] = False
                except Exception:
                    pass
                out.append(item)
    return out

@app.route("/", methods=["GET"])
@app.route("/scripts", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/script/<path:filename>", methods=["GET"])
def script_page(filename: str):
    return render_template("script.html", filename=filename)

@app.route("/api/data-location", methods=["GET"])
def api_data_location():
    return jsonify({"ok": True, "shared_data_dir": str(SHARED_DATA_DIR), "scripts_dir": str(SCRIPTS_DIR),
                    "tree_file": str(TREE_FILE), "script_links_file": str(SCRIPT_LINKS_FILE)})


@app.route("/api/stories", methods=["GET"])
def api_stories():
    """
    Story-first home page data.
    Groups script links by sentence/story from the core sentence tree.
    Scripts not tied to any sentence are returned as unassigned story cards.
    """
    try:
        query = request.args.get("q", "").strip().lower()
        tree = load_tree()
        nodes = tree.get("nodes", {})
        used_script_names = set()
        stories = []

        for node_id, node in nodes.items():
            scripts = node.get("scripts", [])
            if not isinstance(scripts, list):
                scripts = []

            script_items = []
            for record in scripts:
                if not isinstance(record, dict):
                    continue
                filename = record.get("filename", "")
                if not filename:
                    continue

                used_script_names.add(filename)
                try:
                    info = script_info(filename)
                    info["script_note"] = record.get("note", "")
                    info["script_record_id"] = record.get("id", "")
                    info["child_count"] = len(linked_children(filename))
                    info["parent_count"] = len(linked_parents(filename))
                    script_items.append(info)
                except Exception:
                    script_items.append(
                        {
                            "filename": filename,
                            "missing": True,
                            "script_note": record.get("note", ""),
                            "script_record_id": record.get("id", ""),
                            "child_count": 0,
                            "parent_count": 0,
                        }
                    )

            path = sentence_path(node_id)
            story = story_text(path)

            if query:
                text_blob = " ".join(
                    [
                        str(node.get("title", "")),
                        str(node.get("sentence", "")),
                        story,
                        " ".join(item.get("filename", "") for item in script_items),
                    ]
                ).lower()
                if query not in text_blob:
                    continue

            stories.append(
                {
                    "node_id": node_id,
                    "title": node.get("title", "") or "Untitled story",
                    "sentence": node.get("sentence", ""),
                    "story": story,
                    "story_path": path,
                    "script_count": len(script_items),
                    "scripts": script_items,
                    "parent_id": node.get("parent_id"),
                    "children": node.get("children", []),
                }
            )

        # Include scripts that exist but are not tied to a sentence node.
        unassigned_scripts = []
        for path in sorted(SCRIPTS_DIR.glob("*.py"), reverse=True):
            if path.name in used_script_names:
                continue
            if query and query not in path.name.lower():
                continue
            try:
                info = script_info(path.name)
                info["child_count"] = len(linked_children(path.name))
                info["parent_count"] = len(linked_parents(path.name))
                unassigned_scripts.append(info)
            except Exception:
                continue

        if unassigned_scripts:
            stories.append(
                {
                    "node_id": "",
                    "title": "Scripts not tied to a sentence",
                    "sentence": "",
                    "story": "These scripts exist in the shared scripts folder but are not currently attached to a sentence node.",
                    "story_path": [],
                    "script_count": len(unassigned_scripts),
                    "scripts": unassigned_scripts,
                    "parent_id": None,
                    "children": [],
                    "unassigned": True,
                }
            )

        stories.sort(key=lambda item: (item.get("unassigned", False), item.get("title", "")))
        return jsonify({"ok": True, "items": stories})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/scripts", methods=["GET"])
def api_scripts():
    try:
        query = request.args.get("q","").strip().lower()
        linked_filter = request.args.get("linked","all").strip().lower()
        links = load_links().get("links", {})
        linked_names = set(links.keys())
        for records in links.values():
            if isinstance(records, list):
                linked_names.update(record.get("child_filename") for record in records if isinstance(record, dict) and record.get("child_filename"))
        items = []
        for path in sorted(SCRIPTS_DIR.glob("*.py"), reverse=True):
            try:
                info = script_info(path.name)
                nodes = find_sentence_nodes_for_script(path.name)
                info["sentence_count"] = len(nodes)
                info["child_count"] = len(linked_children(path.name))
                info["parent_count"] = len(linked_parents(path.name))
                info["is_linked"] = path.name in linked_names
                if query and query not in path.name.lower() and not any(query in n.get("sentence","").lower() for n in nodes):
                    continue
                if linked_filter == "linked" and not info["is_linked"]:
                    continue
                if linked_filter == "unlinked" and info["is_linked"]:
                    continue
                items.append(info)
            except Exception:
                pass
        return jsonify({"ok": True, "items": items})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/script/<path:filename>", methods=["GET"])
def api_script(filename: str):
    try:
        info = script_info(filename)
        nodes = find_sentence_nodes_for_script(filename)
        return jsonify({"ok": True, "script": info, "source": read_source(filename),
                        "primary_sentence": nodes[0] if nodes else None, "sentence_nodes": nodes,
                        "children": linked_children(filename), "parents": linked_parents(filename)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404

@app.route("/api/script/<path:filename>", methods=["POST"])
def api_update_script(filename: str):
    try:
        payload = request.get_json(force=True) or {}
        path = safe_resolve(SCRIPTS_DIR, filename)
        if not path.exists():
            raise FileNotFoundError(filename)
        path.write_text(str(payload.get("source","")).rstrip() + "\n", encoding="utf-8")
        return jsonify({"ok": True, "script": script_info(path.name)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/script/<path:parent_filename>/manual-child", methods=["POST"])
def api_manual_child(parent_filename: str):
    try:
        script_info(parent_filename)
        payload = request.get_json(force=True) or {}
        source = str(payload.get("source","")).strip()
        if not source:
            return jsonify({"ok": False, "error": "Manual child script source is required."}), 400
        child_path = save_child_script(parent_filename, source, str(payload.get("filename","")).strip())
        data = load_links()
        records = data.setdefault("links", {}).setdefault(parent_filename, [])
        if not isinstance(records, list):
            records = []
            data["links"][parent_filename] = records
        record = {"id": uuid.uuid4().hex[:10], "parent_filename": parent_filename, "child_filename": child_path.name,
                  "relationship": str(payload.get("relationship","")).strip(), "note": str(payload.get("note","")).strip(),
                  "created_at": now_iso(), "manual_entry": True}
        records.append(record)
        save_links(data)
        return jsonify({"ok": True, "record": record, "child": script_info(child_path.name), "children": linked_children(parent_filename)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/script/<path:parent_filename>/link-existing", methods=["POST"])
def api_link_existing(parent_filename: str):
    try:
        script_info(parent_filename)
        payload = request.get_json(force=True) or {}
        child = str(payload.get("child_filename","")).strip()
        if not child:
            return jsonify({"ok": False, "error": "child_filename is required."}), 400
        script_info(child)
        data = load_links()
        records = data.setdefault("links", {}).setdefault(parent_filename, [])
        record = {"id": uuid.uuid4().hex[:10], "parent_filename": parent_filename, "child_filename": child,
                  "relationship": str(payload.get("relationship","")).strip(), "note": str(payload.get("note","")).strip(),
                  "created_at": now_iso(), "manual_entry": False}
        records.append(record)
        save_links(data)
        return jsonify({"ok": True, "record": record, "children": linked_children(parent_filename)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/script-link/<path:parent_filename>/<link_id>", methods=["DELETE"])
def api_unlink(parent_filename: str, link_id: str):
    try:
        data = load_links()
        records = data.get("links", {}).get(parent_filename, [])
        data["links"][parent_filename] = [r for r in records if not (isinstance(r, dict) and r.get("id") == link_id)]
        save_links(data)
        return jsonify({"ok": True, "children": linked_children(parent_filename)})
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
    app.run(host="127.0.0.1", port=5006, debug=True)
