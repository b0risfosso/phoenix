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

from flask import Flask, jsonify, render_template, render_template_string, request, send_from_directory

APP_DIR = Path(__file__).resolve().parent
SHARED_DATA_DIR = Path(os.environ.get("SIMULATION_SHARED_DATA_DIR", APP_DIR.parent / "simulation_shared_data")).expanduser().resolve()
SCRIPTS_DIR = SHARED_DATA_DIR / "scripts"
METADATA_DIR = SHARED_DATA_DIR / "metadata"
LOGS_DIR = SHARED_DATA_DIR / "logs"
CSV_RUNS_DIR = SHARED_DATA_DIR / "csv_runs"

TREE_FILE = METADATA_DIR / "core_sentence_tree.json"
CSV_RUN_INDEX_FILE = METADATA_DIR / "csv_run_index.json"

for directory in (SCRIPTS_DIR, METADATA_DIR, LOGS_DIR, CSV_RUNS_DIR):
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
    headers: list[str] = []

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

    refreshed: list[dict[str, Any]] = []
    for run in reversed(runs[-limit:]):
        run_copy = dict(run)
        if run_copy.get("save_csv") and run_copy.get("run_dir"):
            run_dir = Path(run_copy["run_dir"])
            if run_dir.exists():
                run_copy["csv_files"] = [
                    csv_file_info(path)
                    for path in sorted(run_dir.glob("*.csv"))
                ]
        refreshed.append(run_copy)

    return refreshed



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
        "csv_run_count": len(recent_runs_for_script(path.name)),
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
    return jsonify({
        "ok": True,
        "shared_data_dir": str(SHARED_DATA_DIR),
        "scripts_dir": str(SCRIPTS_DIR),
        "metadata_dir": str(METADATA_DIR),
        "logs_dir": str(LOGS_DIR),
        "csv_runs_dir": str(CSV_RUNS_DIR),
        "tree_file": str(TREE_FILE),
        "csv_run_index_file": str(CSV_RUN_INDEX_FILE),
    })


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


RUN_PAGE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Run Simulation</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="/static/styles.css">
  <style>
    .run-layout { padding: 24px 34px 60px; }
    .run-card { max-width: 900px; }
    .checkline { display: flex; gap: 8px; align-items: center; font-weight: 500; margin: 14px 0; }
    .run-card code { background: #f3f4f6; padding: 2px 5px; border-radius: 6px; }
    .run-result-card { border: 1px solid #e5e7eb; background: #fbfdff; border-radius: 14px; padding: 14px; margin: 12px 0; }
    .run-result-card h3 { margin: 0 0 8px; }
  </style>
</head>
<body>
  <header class="site-header">
    <div>
      <h1>Run Simulation</h1>
      <p>{{ filename }}</p>
    </div>
    <nav>
      <a href="/">Tree</a>
      <a href="/script/{{ filename }}">Edit script</a>
      <a href="/outputs/scripts/{{ filename }}">Download script</a>
    </nav>
  </header>

  <main class="run-layout">
    <section class="panel run-card">
      <h2>Run options</h2>
      <p class="small">
        The main script is assumed to support CSV output when these environment variables are provided:
        <code>SIMULATION_CSV_OUTPUT_DIR</code>,
        <code>SIMULATION_CSV_RUN_ID</code>,
        <code>SIMULATION_CSV_RUN_SECONDS</code>.
      </p>

      <label class="checkline">
        <input id="saveCsvCheck" type="checkbox" checked>
        Save CSV output for this run
      </label>

      <label for="runSeconds">Run seconds</label>
      <input id="runSeconds" type="number" min="1" value="60">

      <div class="actions">
        <button id="runBtn">Run simulation</button>
      </div>

      <p id="runStatus" class="status"></p>

      <h2>Started run</h2>
      <div id="runResult"></div>

      <hr>

      <h2>Recent runs</h2>
      <div id="recentRuns" class="cards"></div>
    </section>
  </main>

  <script>
    const filename = {{ filename_json|safe }};

    function setStatus(message, isError = false) {
      const el = document.getElementById("runStatus");
      el.textContent = message || "";
      el.classList.toggle("error", isError);
    }

    function makeLink(href, text, target = "_blank") {
      const a = document.createElement("a");
      a.href = href;
      a.textContent = text;
      if (target) a.target = target;
      return a;
    }

    async function fetchJson(url, options = {}) {
      const res = await fetch(url, options);
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Request failed.");
      return data;
    }

    function renderRunCard(run) {
      const card = document.createElement("article");
      card.className = "run-result-card";

      const h = document.createElement("h3");
      h.textContent = run.run_id || "Run";
      card.appendChild(h);

      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = `save_csv=${run.save_csv} • run_seconds=${run.run_seconds} • pid=${run.pid || ""} • ${run.started_at || ""}`;
      card.appendChild(meta);

      if (run.log_url) {
        const p = document.createElement("p");
        p.appendChild(makeLink(run.log_url, "Open log"));
        card.appendChild(p);
      }

      if (run.run_dir) {
        const p = document.createElement("p");
        p.className = "meta";
        p.textContent = `CSV output directory: ${run.run_dir}`;
        card.appendChild(p);
      }

      if (run.csv_files && run.csv_files.length) {
        for (const csv of run.csv_files) {
          const p = document.createElement("p");
          p.append(
            makeLink(csv.download_url, csv.filename),
            document.createTextNode(` • ${csv.row_count || 0} rows • ${csv.size_bytes || 0} bytes`)
          );
          card.appendChild(p);
        }
      }

      return card;
    }

    function renderRecent(runs) {
      const box = document.getElementById("recentRuns");
      box.innerHTML = "";

      if (!runs || !runs.length) {
        box.textContent = "No recent indexed runs.";
        return;
      }

      for (const run of runs) {
        box.appendChild(renderRunCard(run));
      }
    }

    async function loadRecent() {
      const data = await fetchJson(`/api/runs?script=${encodeURIComponent(filename)}`);
      renderRecent(data.items || []);
    }

    async function runSimulation() {
      try {
        setStatus("Starting simulation process...");
        document.getElementById("runBtn").disabled = true;

        const data = await fetchJson(`/api/run/${encodeURIComponent(filename)}`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            save_csv: document.getElementById("saveCsvCheck").checked,
            run_seconds: Number(document.getElementById("runSeconds").value || 60)
          })
        });

        const box = document.getElementById("runResult");
        box.innerHTML = "";
        box.appendChild(renderRunCard(data.run));
        setStatus("Simulation process started.");
        await loadRecent();
      } catch (error) {
        setStatus(error.message, true);
      } finally {
        document.getElementById("runBtn").disabled = false;
      }
    }

    document.getElementById("runBtn").addEventListener("click", runSimulation);
    loadRecent().catch(error => setStatus(error.message, true));
  </script>
</body>
</html>
"""


@app.route("/run/<path:filename>", methods=["GET"])
def run_script_page(filename: str):
    try:
        script_path = safe_resolve(SCRIPTS_DIR, filename)
        if not script_path.exists():
            return f"Script not found: {filename}", 404
        return render_template_string(
            RUN_PAGE_HTML,
            filename=script_path.name,
            filename_json=json.dumps(script_path.name),
        )
    except Exception as exc:
        return f"Run page failed: {exc}", 500


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
            log.write(f"Running: {script_path}\\n")
            log.write(f"Started: {now_iso()}\\n")
            log.write(f"Run ID: {run_id}\\n")
            log.write(f"Save CSV: {save_csv}\\n")
            log.write(f"Run seconds: {run_seconds}\\n")
            if save_csv:
                log.write(f"CSV output directory: {run_dir}\\n")
            log.write("\\n")
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
            runs = [
                run for run in runs
                if isinstance(run, dict) and run.get("script_filename") == script_filename
            ]

        refreshed: list[dict[str, Any]] = []
        for run in runs:
            if not isinstance(run, dict):
                continue
            run_copy = dict(run)
            if run_copy.get("save_csv") and run_copy.get("run_dir"):
                run_dir = Path(run_copy["run_dir"])
                if run_dir.exists():
                    run_copy["csv_files"] = [
                        csv_file_info(path)
                        for path in sorted(run_dir.glob("*.csv"))
                    ]
            refreshed.append(run_copy)

        return jsonify({"ok": True, "items": list(reversed(refreshed))})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500




@app.route("/outputs/csv_runs/<path:filename>", methods=["GET"])
def download_csv_run_file(filename: str):
    return send_from_directory(CSV_RUNS_DIR, filename, as_attachment=False)


@app.route("/outputs/scripts/<path:filename>", methods=["GET"])
def download_script(filename: str):
    return send_from_directory(SCRIPTS_DIR, filename, as_attachment=True)


@app.route("/outputs/logs/<path:filename>", methods=["GET"])
def download_log(filename: str):
    return send_from_directory(LOGS_DIR, filename, as_attachment=False)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5003, debug=True)
