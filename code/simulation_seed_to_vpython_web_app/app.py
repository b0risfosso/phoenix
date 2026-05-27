#!/usr/bin/env python3
"""
Simulation Seed Reader + VPython Script Generator Web App

Purpose:
    Read saved simulation seed JSON files, display individual simulation seeds,
    generate VPython Python scripts from selected seeds, and link generated
    scripts back to their source seed.

Run:
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    export OPENAI_API_KEY="your_api_key_here"
    python app.py

Open:
    http://127.0.0.1:5001

Shared data:
    By default, this app reads generated seed JSON files from:
        ../simulation_shared_data/seeds/

    To force both apps to use a specific shared folder:
        export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
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
from openai import OpenAI


APP_DIR = Path(__file__).resolve().parent

# Shared data folder.
# This app reads generated seed JSON files from the same shared folder used by
# the simulation seed generator app.
# Default:
#     ../simulation_shared_data/
# Override:
#     export SIMULATION_SHARED_DATA_DIR="/absolute/path/to/shared/data"
SHARED_DATA_DIR = Path(
    os.environ.get("SIMULATION_SHARED_DATA_DIR", APP_DIR.parent / "simulation_shared_data")
).expanduser().resolve()

OUTPUT_DIR = SHARED_DATA_DIR
SEEDS_DIR = OUTPUT_DIR / "seeds"
SCRIPTS_DIR = OUTPUT_DIR / "scripts"
METADATA_DIR = OUTPUT_DIR / "metadata"
LOGS_DIR = OUTPUT_DIR / "logs"

for directory in (SEEDS_DIR, SCRIPTS_DIR, METADATA_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

LINKS_FILE = METADATA_DIR / "seed_script_links.json"

DEFAULT_MODEL = os.environ.get("OPENAI_SCRIPT_MODEL", "gpt-5.5")
DEFAULT_TEMPERATURE_RAW = os.environ.get("OPENAI_SCRIPT_TEMPERATURE", "")
DEFAULT_TEMPERATURE = None if DEFAULT_TEMPERATURE_RAW == "" else float(DEFAULT_TEMPERATURE_RAW)

app = Flask(__name__)


PROMPT_TEMPLATE = """Make a 3D Python simulation of [OBJECTS / SCENE / SYSTEM].

The simulation should include:
- [main objects]
- [how the objects interact]
- [what can move]
- [what is stationary]
- [what can attach, detach, collide, orbit, spill, mark, wrap, bounce, mix, transfer, etc.]
- [any visual details: color, texture, transparency, trails, labels, particles]

Think thoroughly through the structure of the simulation. However, do not provide an outline or explanation. Instead, provide the final updated Python simulation file that implements the simulation.

Build the simulation in Python. The code must be self-contained and runnable in Python using VPython. Provide only the Python simulation file.

Prefer light styling / colors / background over dark styling / colors / background.

VPython compatibility requirements:
- Use `from vpython import *`.
- Do not use `torus(...)`.
- If a torus-like object, circular band, rim, orbit ring, donut shape, ring marker, or loop is needed, use `ring(...)` instead.
- Avoid naming any variable `ring`, because that can shadow VPython's `ring(...)` constructor.
- Avoid unsupported VPython object assumptions.
- Keep the code runnable as a normal `.py` file.

CSV logging compatibility requirements for the story branching / CSV storage web apps:
- The generated simulation must support optional CSV state logging during runs.
- The script must read these environment variables:
  - `SIMULATION_CSV_OUTPUT_DIR`
  - `SIMULATION_CSV_RUN_ID`
  - `SIMULATION_CSV_RUN_SECONDS`
- Default run length must be 60 seconds when `SIMULATION_CSV_RUN_SECONDS` is not provided.
- If `SIMULATION_CSV_OUTPUT_DIR` is provided, save CSV output inside that directory.
- If `SIMULATION_CSV_RUN_ID` is provided, include it in the CSV filename.
- If no web-app output directory is provided, fall back to `SIM_STATE_CSV_PATH` if set.
- If neither `SIMULATION_CSV_OUTPUT_DIR` nor `SIM_STATE_CSV_PATH` is set, save a CSV file beside the script.
- The CSV filename should include the run id when available.
- Do not hardcode duration-specific labels such as `180s`.
- Use generic labels such as `CSV recording complete` or `saved run data`.
- The script should create parent directories for CSV output if needed.
- The script should flush CSV writes periodically.
- The script should close the CSV file cleanly.
- The script should stop automatically after the configured run length when CSV logging is active.
- The script should still be viewable/runnable normally when no CSV environment variables are provided.

CSV implementation requirements:
- Import `csv`, `os`, and `datetime` or `time` as needed.
- Create a CSV header row.
- Record repeated simulation state snapshots.
- Include useful state columns such as:
  - `run_id`
  - `frame`
  - `elapsed_seconds`
  - positions of important objects
  - velocities or movement vectors when applicable
  - current AI mode or behavior mode if present
  - collision/attachment/orbit/marking/transfer counts when applicable
  - any simulation-specific fields that make the run meaningful
- Keep the CSV storage logic simple and robust.
- Do not require pandas or external data libraries.
- Make CSV logging compatible with this pattern:

```python
CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
_csv_output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
_csv_run_id = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

if _csv_output_dir:
    CSV_OUTPUT_PATH = os.path.join(_csv_output_dir, f"{_csv_run_id}-simulation-state.csv")
else:
    CSV_OUTPUT_PATH = os.environ.get(
        "SIM_STATE_CSV_PATH",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{_csv_run_id}-simulation-state.csv")
    )
```

Could I program an AI to control this simulation?

Add an AI controller to the 3D Python simulation.

The AI should be able to:
- Read the simulation state.
- Choose actions for one or more objects.
- Move, rotate, attach, detach, collide, dip, orbit, organize, mark, spill, wrap, or interact depending on the simulation.
- Use a simple rule-based controller first.
- Optionally support a more advanced behavior system later.

Implement:
1. Simulation state variables the AI needs.
2. Actions the AI can take.
3. How the AI chooses actions.
4. Where the AI controller code belongs in the file.
5. How the AI can run automatically while still allowing human keyboard control.
6. How to pause, resume, or override the AI.
7. Example code directly integrated into the simulation.

How can I make the AI more interesting and dynamic?

Add a more expressive AI behavior system to the simulation.

The AI should:
- Have multiple behavior modes.
- Switch between behaviors over time.
- React to the current simulation state.
- Avoid doing the same thing forever.
- Create visible, meaningful changes in the scene.
- Reset or loop the simulation when the state is halted, complete, empty, stable, or no longer changing.

Include in the actual code:
1. A list of possible AI behavior modes.
2. A simple state machine for the AI.
3. A stagnation/completion detector.
4. A reset function.
5. A loop system that starts a new round after completion.
6. Behavior that can feel playful, ritual-like, chaotic, careful, curious, destructive, constructive, or artistic.

Think thoroughly through these requirements. Do not provide explanations. Return the final Python source code only.
"""

# CSV prompt compatibility: generated scripts are instructed to support SIMULATION_CSV_OUTPUT_DIR, SIMULATION_CSV_RUN_ID, and SIMULATION_CSV_RUN_SECONDS.
CODE_ONLY_SUFFIX = """

Return only the final Python source code. Do not wrap it in Markdown fences. Do not include explanations before or after the code.
"""


def slugify(text: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    if not slug:
        slug = "simulation"
    return slug[:max_len].strip("-") or "simulation"


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


def load_links() -> dict[str, list[dict[str, Any]]]:
    data = load_json_file(LINKS_FILE, {})
    if not isinstance(data, dict):
        return {}
    return data


def save_links(data: dict[str, list[dict[str, Any]]]) -> None:
    save_json_file(LINKS_FILE, data)


def seed_key(seed_file: str, seed_number: str) -> str:
    return f"{seed_file}::{seed_number}"


def normalize_seed_entries(data: dict[str, Any]) -> list[dict[str, str]]:
    """
    Accept the JSON format from the seed-only app, but also tolerate simple
    JSON lists or manually-created files.
    """
    entries = data.get("entries")
    if isinstance(entries, list):
        normalized = []
        for index, entry in enumerate(entries, start=1):
            if isinstance(entry, dict):
                number = str(entry.get("number") or index)
                title = str(entry.get("title") or f"Seed {number}").strip()
                description = str(entry.get("description") or entry.get("seed") or "").strip()
                seed_text = str(entry.get("seed") or f"{title}: {description}".strip(": ")).strip()
            else:
                number = str(index)
                title = f"Seed {number}"
                description = str(entry).strip()
                seed_text = description
            normalized.append(
                {
                    "number": number,
                    "title": title,
                    "description": description,
                    "seed": seed_text,
                }
            )
        return normalized

    raw_output = str(data.get("raw_output") or "")
    return parse_seed_entries(raw_output)


def parse_seed_entries(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    pattern = re.compile(
        r"^\s*(\d+)\.\s+\*\*(.*?)\*\*\s*\n\s*(.*?)(?=^\s*\d+\.\s+\*\*|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(text):
        number = match.group(1).strip()
        title = re.sub(r"\s+", " ", match.group(2).strip())
        description = re.sub(r"\s+", " ", match.group(3).strip())
        entries.append(
            {
                "number": number,
                "title": title,
                "description": description,
                "seed": f"{title}: {description}".strip(": "),
            }
        )
    return entries


def build_script_prompt(seed_text: str) -> str:
    cleaned = seed_text.strip()
    if not cleaned:
        raise ValueError("Simulation seed cannot be empty.")
    return PROMPT_TEMPLATE.replace("[OBJECTS / SCENE / SYSTEM]", cleaned) + CODE_ONLY_SUFFIX


def extract_python_source(text: str) -> str:
    match = re.search(
        r"```(?:python|py)?\s*(.*?)```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    source = match.group(1) if match else text
    return source.strip() + "\n"


def call_llm(prompt: str, model: str, temperature: float | None) -> str:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI()
    kwargs: dict[str, Any] = {"model": model, "input": prompt}
    if temperature is not None:
        kwargs["temperature"] = temperature

    try:
        response = client.responses.create(**kwargs)
    except Exception as exc:
        message = str(exc).lower()
        if "temperature" in message and ("unsupported" in message or "not support" in message):
            kwargs.pop("temperature", None)
            response = client.responses.create(**kwargs)
        else:
            raise

    return response.output_text


def save_script(source: str, seed_text: str) -> Path:
    now = datetime.now()
    filename = f"vpython-simulation-{slugify(seed_text, 70)}-{uuid.uuid4().hex[:8]}.py"
    path = SCRIPTS_DIR / filename
    path.write_text(source, encoding="utf-8")
    return path


def get_script_info(filename: str) -> dict[str, Any]:
    path = safe_resolve(SCRIPTS_DIR, filename)
    if not path.exists():
        raise FileNotFoundError(filename)
    stat = path.stat()
    return {
        "filename": path.name,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "download_url": f"/outputs/scripts/{path.name}",
        "open_url": f"/script/{path.name}",
        "edit_url": f"/editor/{path.name}",
        "run_url": f"/run/{path.name}",
    }


@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
@app.route("/index.html", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/data-location", methods=["GET"])
def api_data_location():
    return jsonify(
        {
            "ok": True,
            "shared_data_dir": str(SHARED_DATA_DIR),
            "seeds_dir": str(SEEDS_DIR),
            "scripts_dir": str(SCRIPTS_DIR),
            "metadata_dir": str(METADATA_DIR),
        }
    )


@app.route("/script/<path:filename>", methods=["GET"])
def script_view(filename: str):
    return render_template("script.html", filename=filename)


@app.route("/editor/<path:filename>", methods=["GET"])
def editor_view(filename: str):
    return render_template("editor.html", filename=filename)


@app.route("/api/seeds", methods=["GET"])
def api_seeds():
    try:
        items = []
        for path in sorted(SEEDS_DIR.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                entries = normalize_seed_entries(data)
                items.append(
                    {
                        "filename": path.name,
                        "input_phrase": data.get("input_phrase") or data.get("title") or path.stem,
                        "created_at": data.get("created_at", ""),
                        "model": data.get("model", ""),
                        "entry_count": len(entries),
                    }
                )
            except Exception:
                continue
        return jsonify({"ok": True, "items": items})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/seed-file/<path:filename>", methods=["GET"])
def api_seed_file(filename: str):
    try:
        path = safe_resolve(SEEDS_DIR, filename)
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = normalize_seed_entries(data)
        links = load_links()

        linked_entries = []
        for entry in entries:
            key = seed_key(filename, str(entry["number"]))
            script_records = []
            for record in links.get(key, []):
                script_filename = record.get("script_filename")
                if not script_filename:
                    continue
                try:
                    info = get_script_info(script_filename)
                    info.update(
                        {
                            "created_at": record.get("created_at", ""),
                            "model": record.get("model", ""),
                        }
                    )
                    script_records.append(info)
                except Exception:
                    continue
            entry_copy = dict(entry)
            entry_copy["scripts"] = script_records
            linked_entries.append(entry_copy)

        return jsonify(
            {
                "ok": True,
                "filename": filename,
                "input_phrase": data.get("input_phrase") or data.get("title") or path.stem,
                "created_at": data.get("created_at", ""),
                "raw_output": data.get("raw_output", ""),
                "entries": linked_entries,
            }
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.route("/api/generate-script", methods=["POST"])
def api_generate_script():
    try:
        payload = request.get_json(force=True) or {}
        seed_file = str(payload.get("seed_file", "")).strip()
        seed_number = str(payload.get("seed_number", "")).strip()
        seed_text = str(payload.get("seed_text", "")).strip()
        model = str(payload.get("model") or DEFAULT_MODEL).strip()
        temperature_value = payload.get("temperature", DEFAULT_TEMPERATURE)

        if not seed_file:
            return jsonify({"ok": False, "error": "seed_file is required."}), 400
        if not seed_number:
            return jsonify({"ok": False, "error": "seed_number is required."}), 400
        if not seed_text:
            return jsonify({"ok": False, "error": "seed_text is required."}), 400

        if temperature_value in ("", None):
            temperature = None
        else:
            temperature = float(temperature_value)

        prompt = build_script_prompt(seed_text)
        generated_text = call_llm(prompt=prompt, model=model, temperature=temperature)
        source = extract_python_source(generated_text)
        script_path = save_script(source, seed_text)

        links = load_links()
        key = seed_key(seed_file, seed_number)
        links.setdefault(key, [])
        links[key].append(
            {
                "script_filename": script_path.name,
                "seed_file": seed_file,
                "seed_number": seed_number,
                "seed_text": seed_text,
                "model": model,
                "temperature": temperature,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        save_links(links)

        info = get_script_info(script_path.name)
        info["source"] = source

        return jsonify(
            {
                "ok": True,
                "script": info,
                "seed_file": seed_file,
                "seed_number": seed_number,
            }
        )

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/scripts", methods=["GET"])
def api_scripts():
    try:
        items = [get_script_info(path.name) for path in sorted(SCRIPTS_DIR.glob("*.py"), reverse=True)]
        return jsonify({"ok": True, "items": items})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/script/<path:filename>", methods=["GET"])
def api_script(filename: str):
    try:
        path = safe_resolve(SCRIPTS_DIR, filename)
        return jsonify({"ok": True, "filename": path.name, "source": path.read_text(encoding="utf-8")})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.route("/api/script/<path:filename>", methods=["POST"])
def api_update_script(filename: str):
    try:
        payload = request.get_json(force=True) or {}
        source = str(payload.get("source", ""))
        save_as_copy = bool(payload.get("save_as_copy", False))

        original_path = safe_resolve(SCRIPTS_DIR, filename)
        if save_as_copy:
            new_name = f"{original_path.stem}-edited-{uuid.uuid4().hex[:6]}.py"
            target_path = SCRIPTS_DIR / new_name
        else:
            target_path = original_path

        target_path.write_text(source, encoding="utf-8")
        return jsonify({"ok": True, "script": get_script_info(target_path.name)})
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


@app.route("/outputs/scripts/<path:filename>", methods=["GET"])
def download_script(filename: str):
    return send_from_directory(SCRIPTS_DIR, filename, as_attachment=True)


@app.route("/outputs/logs/<path:filename>", methods=["GET"])
def download_log(filename: str):
    return send_from_directory(LOGS_DIR, filename, as_attachment=False)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
