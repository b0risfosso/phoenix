#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import os
import re
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
TREE_FILE = METADATA_DIR / "core_sentence_tree.json"
NEXT_BATCHES_FILE = METADATA_DIR / "next_sentence_generation_batches.json"

for directory in (SCRIPTS_DIR, METADATA_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)

NEXT_SENTENCE_PROMPT = """You are generating possible next sentences for an evolving 3D simulation seed.

The input describes the current system. Generate next-sentence options that could determine how the system evolves.

Guidelines:
- Do not directly reference the input, the simulation, the story, or earlier sentences.
- Do not write explanations.
- Each output must be a single sentence.
- Each sentence should add a new simulation-ready behavior.
- Focus on movement, interaction, cause/effect, visible state changes, environmental changes, feedback loops, repair, failure, learning, stress, growth, decay, attraction, repulsion, merging, splitting, trails, signals, or resource flow.
- Make the suggestions varied: some should add complexity, some should add conflict, some should add visual detail, and some should add long-term evolution.
- Keep the language direct and usable as a continuation sentence.
- Avoid repeating the same mechanism across suggestions.
- Produce 20 numbered options.

Input:
{input_text}

Output:
Possible next sentences:

1.
2.
3.
...
20.
"""

SCRIPT_MODIFICATION_PROMPT = """You are modifying an existing Python source script.

Inputs:

SOURCE SCRIPT:

```python
{source_script}
```

MODIFIER SENTENCE:
{modifier_sentence}

Task:
Modify the source script so it visibly builds out the behavior described in the modifier sentence.

Requirements:

1. Preserve the original script’s main structure, controls, visual style, and existing behaviors unless they directly conflict with the requested modification.
2. Add the new behavior as an integrated system, not as a separate unrelated demo.
3. The behavior from the modifier sentence should be visible, active, and meaningfully affect the simulation.
4. Make the new behavior prevalent enough that it can be observed within the first few seconds of running the script.
5. Avoid removing existing features unless removal is necessary to make the new behavior work.
6. Keep the code self-contained and runnable as a single Python file.
7. Do not require external assets, external data files, or internet access.
8. If the script uses VPython, keep using VPython.
9. If the script uses VPython, use `ring(...)` instead of `torus(...)`.
10. Avoid naming variables after VPython object constructors such as `sphere`, `box`, `curve`, `ring`, `label`, or `arrow`.
11. If adding trails, markers, or paths, avoid relying on unsupported attributes such as `curve.points`.
12. Add comments near the new code explaining the new behavior.
13. Add or update on-screen labels/status text if helpful so the new behavior is understandable while the simulation runs.
14. Keep keyboard/mouse controls working if they already exist.
15. If the simulation has reset behavior, update the reset logic so the new behavior resets cleanly.
16. If the simulation has pause/resume behavior, ensure the new behavior respects pause/resume.
17. Make the modification robust against common runtime errors such as empty lists, division by zero, missing attributes, or objects being deleted.
18. Do not output explanations before the code.
19. Output only the full updated Python script inside one Python code block.

Modification strategy:

* First identify the main entities, update loop, reset logic, controls, and rendering objects in the source script.
* Decide what state variables are needed for the modifier behavior.
* Add visual objects, colors, trails, particles, forces, signals, labels, or state transitions as needed.
* Integrate the new behavior into the existing update loop.
* Tune the behavior so it is obvious but does not freeze, overwhelm, or destabilize the simulation.
* Ensure the final script runs without syntax errors.

Output format:

```python
# full updated script here
```
"""

def extract_python_code_block(raw_text: str) -> str:
    match = re.search(r"```(?:python|py)?\s*([\s\S]*?)```", raw_text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip() + "\n"
    return raw_text.strip() + "\n"



def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def slugify(text: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:max_len].strip("-") or "sentence"

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
        "sentence": node.get("sentence", ""),
        "title": node.get("title", ""),
        "parent_id": node.get("parent_id"),
        "children": children,
        "script_count": len(scripts),
        "created_at": node.get("created_at", ""),
        "updated_at": node.get("updated_at", ""),
        "generated_from": node.get("generated_from", ""),
        "generation_batch_id": node.get("generation_batch_id", ""),
    }

def get_node(tree: dict[str, Any], node_id: str) -> dict[str, Any]:
    node = tree.get("nodes", {}).get(node_id)
    if not node:
        raise FileNotFoundError("Sentence node not found.")
    return node

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

def ordered_node_ids(tree: dict[str, Any]) -> list[str]:
    nodes = tree.get("nodes", {})
    roots = [node_id for node_id, node in nodes.items() if not node.get("parent_id")]
    ordered: list[str] = []
    seen: set[str] = set()
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

def parse_numbered_sentences(raw_text: str) -> list[str]:
    options = []
    for line in raw_text.splitlines():
        line = line.strip()
        match = re.match(r"^(?:\d+[\).:\-]\s*)(.+)$", line)
        if match:
            options.append(match.group(1).strip().strip('"').strip("'"))
    clean = []
    seen = set()
    for option in options:
        option = re.sub(r"\s+", " ", option).strip()
        if not option:
            continue
        key = option.lower()
        if key in seen:
            continue
        seen.add(key)
        clean.append(option)
    return clean[:20]

def generate_next_sentences_with_llm(input_text: str) -> tuple[list[str], str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Export it before running generation.")
    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError("The openai package is not installed. Run: pip install openai") from exc
    prompt = NEXT_SENTENCE_PROMPT.format(input_text=input_text.strip())
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Return only the numbered next-sentence options requested by the user."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.9,
    )
    raw = response.choices[0].message.content or ""
    options = parse_numbered_sentences(raw)
    if not options:
        raise RuntimeError("The LLM returned no parseable next sentences.")
    return options, raw


def generate_modified_script_with_llm(source_script: str, modifier_sentence: str) -> tuple[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Export it before running script modification.")

    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError("The openai package is not installed. Run: pip install openai") from exc

    prompt = SCRIPT_MODIFICATION_PROMPT.format(
        source_script=source_script,
        modifier_sentence=modifier_sentence.strip(),
    )
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Return only the updated Python script inside one Python code block.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.45,
    )

    raw = response.choices[0].message.content or ""
    source = extract_python_code_block(raw)

    if not source.strip():
        raise RuntimeError("The LLM returned no script source.")

    try:
        ast.parse(source)
    except SyntaxError as exc:
        raise RuntimeError(f"The modified script has a syntax error: {exc}") from exc

    return source, raw


def find_available_scripts_for_node(tree: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    """Return scripts from the node, its ancestors, and siblings/children for source selection."""
    nodes = tree.get("nodes", {})
    available: list[dict[str, Any]] = []
    seen_files: set[str] = set()

    def add_node_scripts(candidate_id: str, relationship: str) -> None:
        candidate = nodes.get(candidate_id)
        if not candidate:
            return
        for info in get_node_scripts(candidate):
            filename = info.get("filename", "")
            if not filename or info.get("missing") or filename in seen_files:
                continue
            info = dict(info)
            info["node_id"] = candidate_id
            info["node_title"] = candidate.get("title", "")
            info["node_sentence"] = candidate.get("sentence", "")
            info["relationship"] = relationship
            available.append(info)
            seen_files.add(filename)

    # Current node.
    add_node_scripts(node_id, "current sentence")

    # Ancestors, nearest first.
    current_id = nodes.get(node_id, {}).get("parent_id")
    while current_id and current_id in nodes:
        add_node_scripts(current_id, "ancestor source script")
        current_id = nodes[current_id].get("parent_id")

    # Children.
    for child_id in nodes.get(node_id, {}).get("children", []):
        add_node_scripts(child_id, "child branch script")

    return available


def save_generation_batch(batch: dict[str, Any]) -> None:
    data = load_json(NEXT_BATCHES_FILE, {"batches": []})
    if not isinstance(data, dict):
        data = {"batches": []}
    if not isinstance(data.get("batches"), list):
        data["batches"] = []
    data["batches"].append(batch)
    save_json(NEXT_BATCHES_FILE, data)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/story/<node_id>", methods=["GET"])
def story_page(node_id: str):
    return render_template("story.html", node_id=node_id)

@app.route("/script/<path:filename>", methods=["GET"])
def script_page(filename: str):
    return render_template("script.html", filename=filename)

@app.route("/api/data-location", methods=["GET"])
def api_data_location():
    return jsonify({"ok": True, "shared_data_dir": str(SHARED_DATA_DIR), "scripts_dir": str(SCRIPTS_DIR), "metadata_dir": str(METADATA_DIR), "tree_file": str(TREE_FILE), "next_batches_file": str(NEXT_BATCHES_FILE)})


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
            summary["depth"] = max(0, len(path) - 1)
            summary["scripts"] = get_node_scripts(node)
            result_nodes[node_id] = summary

        if query or scripted_only:
            keep = set()

            def keep_ancestors(candidate_id):
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
                query_match = (not query) or (query in blob)
                script_match = (not scripted_only) or (item.get("script_count", 0) > 0)

                if query_match and script_match:
                    keep_ancestors(node_id)
                    if query:
                        for child_id in item.get("children", []):
                            if child_id in result_nodes:
                                keep.add(child_id)

            result_nodes = {
                node_id: item
                for node_id, item in result_nodes.items()
                if node_id in keep
            }

            for item in result_nodes.values():
                item["children"] = [
                    child_id for child_id in item.get("children", [])
                    if child_id in result_nodes
                ]

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


@app.route("/api/stories", methods=["GET"])
def api_stories():
    try:
        query = request.args.get("q", "").strip().lower()
        scripted_only = request.args.get("scripted", "false").lower() == "true"
        tree = load_tree()
        items = []
        for node_id in ordered_node_ids(tree):
            node = tree["nodes"].get(node_id)
            if not node:
                continue
            path = sentence_path(tree, node_id)
            summary = node_summary(node)
            summary["story_path"] = path
            summary["story"] = story_text(path)
            summary["depth"] = max(0, len(path) - 1)
            if scripted_only and summary["script_count"] == 0:
                continue
            if query:
                blob = " ".join([summary.get("title", ""), summary.get("sentence", ""), summary.get("story", "")]).lower()
                if query not in blob:
                    continue
            items.append(summary)
        return jsonify({"ok": True, "items": items})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/tree", methods=["GET"])
def api_tree():
    try:
        tree = load_tree()
        return jsonify({"ok": True, "root_id": tree.get("root_id"), "nodes": {nid: node_summary(n) for nid, n in tree.get("nodes", {}).items()}, "ordered_ids": ordered_node_ids(tree)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/story/<node_id>", methods=["GET"])
def api_story(node_id: str):
    try:
        tree = load_tree()
        node = get_node(tree, node_id)
        path = sentence_path(tree, node_id)
        children = []
        for child_id in node.get("children", []):
            child = tree.get("nodes", {}).get(child_id)
            if child:
                child_summary = node_summary(child)
                child_summary["scripts"] = get_node_scripts(child)
                children.append(child_summary)
        return jsonify({"ok": True, "node": node_summary(node), "story_path": path, "story": story_text(path), "children": children, "scripts": get_node_scripts(node)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404

@app.route("/api/story/<node_id>/generate-next", methods=["POST"])
def api_generate_next(node_id: str):
    try:
        payload = request.get_json(force=True) or {}
        use_full_story = bool(payload.get("use_full_story", True))
        custom_input = str(payload.get("input_text", "")).strip()
        tree = load_tree()
        parent = get_node(tree, node_id)
        path = sentence_path(tree, node_id)
        input_text = custom_input or (story_text(path) if use_full_story else str(parent.get("sentence", "")).strip())
        if not input_text:
            return jsonify({"ok": False, "error": "No sentence/story text available for generation."}), 400
        options, raw = generate_next_sentences_with_llm(input_text)
        batch_id = uuid.uuid4().hex[:10]
        created_nodes = []
        for index, sentence in enumerate(options, start=1):
            child_id = uuid.uuid4().hex[:12]
            child = {"id": child_id, "kind": "core_sentence", "sentence": sentence, "title": f"Generated next sentence {index}", "parent_id": node_id, "children": [], "scripts": [], "created_at": now_iso(), "updated_at": now_iso(), "generated_from": "automated_next_sentence_branching_web_app", "generation_batch_id": batch_id, "generation_index": index}
            tree["nodes"][child_id] = child
            parent.setdefault("children", []).append(child_id)
            created_nodes.append(node_summary(child))
        parent["updated_at"] = now_iso()
        save_tree(tree)
        batch = {"id": batch_id, "parent_node_id": node_id, "created_at": now_iso(), "input_text": input_text, "raw_output": raw, "created_node_ids": [item["id"] for item in created_nodes], "options": options}
        save_generation_batch(batch)
        return jsonify({"ok": True, "batch": batch, "created_nodes": created_nodes, "parent": node_summary(parent)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/story/<node_id>/manual-next", methods=["POST"])
def api_manual_next(node_id: str):
    try:
        payload = request.get_json(force=True) or {}
        sentence = str(payload.get("sentence", "")).strip()
        title = str(payload.get("title", "")).strip()
        if not sentence:
            return jsonify({"ok": False, "error": "Next sentence is required."}), 400
        tree = load_tree()
        parent = get_node(tree, node_id)
        child_id = uuid.uuid4().hex[:12]
        child = {"id": child_id, "kind": "core_sentence", "sentence": sentence, "title": title or "Manual next sentence", "parent_id": node_id, "children": [], "scripts": [], "created_at": now_iso(), "updated_at": now_iso(), "generated_from": "manual_entry"}
        tree["nodes"][child_id] = child
        parent.setdefault("children", []).append(child_id)
        parent["updated_at"] = now_iso()
        save_tree(tree)
        return jsonify({"ok": True, "node": node_summary(child), "parent": node_summary(parent)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.route("/api/story/<node_id>/script", methods=["POST"])
def api_add_script(node_id: str):
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


@app.route("/api/story/<node_id>/available-source-scripts", methods=["GET"])
def api_available_source_scripts(node_id: str):
    try:
        tree = load_tree()
        get_node(tree, node_id)
        return jsonify({"ok": True, "items": find_available_scripts_for_node(tree, node_id)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.route("/api/story/<node_id>/modify-script", methods=["POST"])
def api_modify_script_for_story(node_id: str):
    try:
        payload = request.get_json(force=True) or {}
        source_filename = str(payload.get("source_filename", "")).strip()
        requested_name = str(payload.get("filename", "")).strip()
        note = str(payload.get("note", "")).strip()
        custom_modifier = str(payload.get("modifier_sentence", "")).strip()

        if not source_filename:
            return jsonify({"ok": False, "error": "source_filename is required."}), 400

        tree = load_tree()
        node = get_node(tree, node_id)
        modifier_sentence = custom_modifier or str(node.get("sentence", "")).strip()

        if not modifier_sentence:
            return jsonify({"ok": False, "error": "Modifier sentence is empty."}), 400

        source_path = safe_resolve(SCRIPTS_DIR, source_filename)
        if not source_path.exists():
            return jsonify({"ok": False, "error": f"Source script not found: {source_filename}"}), 404

        source_script = source_path.read_text(encoding="utf-8")
        modified_source, raw_output = generate_modified_script_with_llm(source_script, modifier_sentence)

        if requested_name:
            output_name = requested_name
        else:
            output_name = f"{Path(source_filename).stem}-modified-by-{slugify(modifier_sentence, 38)}.py"

        output_path = save_manual_script(modified_source, node, output_name)

        record = {
            "id": uuid.uuid4().hex[:10],
            "filename": output_path.name,
            "note": note or f"Automated modification of {source_filename}",
            "created_at": now_iso(),
            "manual_entry": False,
            "generated_from": "automated_script_modification",
            "source_filename": source_filename,
            "modifier_sentence": modifier_sentence,
        }
        node.setdefault("scripts", []).append(record)
        node["updated_at"] = now_iso()
        save_tree(tree)

        batch_data = load_json(NEXT_BATCHES_FILE, {"batches": []})
        if not isinstance(batch_data, dict):
            batch_data = {"batches": []}
        batch_data.setdefault("script_modifications", [])
        batch_data["script_modifications"].append({
            "id": record["id"],
            "node_id": node_id,
            "source_filename": source_filename,
            "output_filename": output_path.name,
            "modifier_sentence": modifier_sentence,
            "created_at": record["created_at"],
            "raw_output": raw_output,
        })
        save_json(NEXT_BATCHES_FILE, batch_data)

        return jsonify({
            "ok": True,
            "script": script_info(output_path.name),
            "node": node_summary(node),
            "record": record,
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

@app.route("/outputs/scripts/<path:filename>", methods=["GET"])
def download_script(filename: str):
    return send_from_directory(SCRIPTS_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5008, debug=True)
