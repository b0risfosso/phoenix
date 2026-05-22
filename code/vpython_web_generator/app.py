#!/usr/bin/env python3
"""
Local webpage for generating VPython simulation seed ideas and VPython scripts.

Run:
    pip install -r requirements.txt
    export OPENAI_API_KEY="your_api_key_here"
    python app.py

Then open:
    http://127.0.0.1:5000
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
from typing import Any, Optional

from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from werkzeug.exceptions import HTTPException
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
RUN_LOG_DIR = OUTPUT_DIR / "run_logs"
OUTPUT_DIR.mkdir(exist_ok=True)
RUN_LOG_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

SEED_MODEL_DEFAULT = "gpt-5.1"
SIMULATION_MODEL_DEFAULT = "gpt-5.5"
SEED_TEMPERATURE_DEFAULT = 0.9

SEED_PROMPT_TEMPLATE = """You are generating 3D Python VPython simulation seed ideas.

The user will provide one input word or phrase:

[INPUT WORD OR PHRASE]

Your task is to create strong simulation inputs that can be plugged into this VPython simulation-building prompt:

“Make a 3D Python simulation of [OBJECTS / SCENE / SYSTEM].

The simulation should include:
- main objects
- how the objects interact
- what can move
- what is stationary
- what can attach, detach, collide, orbit, spill, mark, wrap, bounce, mix, transfer, etc.
- any visual details: color, texture, transparency, trails, labels, particles

Build the simulation in Python. The code should be self-contained and runnable in Python using VPython. Prefer light styling / colors / background over dark styling / colors / background.”

Generate the output in this exact style:

Here are strong **[INPUT WORD OR PHRASE] simulation inputs** you can plug into your prompt:

1. **[Simulation seed title]**
   [One sentence describing a 3D simulation idea with clear objects, movement, interactions, and visual behaviors.]

2. **[Simulation seed title]**
   [One sentence describing a different simulation idea.]

Continue until you have 20–25 numbered simulation seeds.

Rules:
- Keep every seed concrete and visually simulatable in 3D.
- Do not write abstract essays or explanations.
- Each seed must describe a scene, system, process, or interaction that can be animated.
- Prefer verbs like float, collide, attach, detach, orbit, pulse, split, merge, wrap, grow, dissolve, transfer, glow, scan, branch, condense, unfold, bounce, rotate, and replicate.
- Include both literal and metaphorical interpretations of the input when useful.
- Include microscopic, macroscopic, mechanical, natural, social, symbolic, and system-level possibilities when relevant.
- Include labels, trails, transparent objects, particles, meters, color-coded regions, glowing connections, and light backgrounds where appropriate.
- Do not generate Python code.
- Do not explain how you made the list."""

SIMULATION_PROMPT_TEMPLATE = """Make a 3D Python simulation of [OBJECTS / SCENE / SYSTEM].

The simulation should include:
- [main objects]
- [how the objects interact]
- [what can move]
- [what is stationary]
- [what can attach, detach, collide, orbit, spill, mark, wrap, bounce, mix, transfer, etc.]
- [any visual details: color, texture, transparency, trails, labels, particles]

think thoroughly through the structure of the simulation. however, you are not required to provide the answers/text to how the simulation will be outlined. instead, you must provide the updated python simulation file with implementation of all given the conditions/inquiries above.

Build the simulation in python. The code should be self-contained and runnable in Python using VPython. Provide the python simulation file.

Prefer light styling / colors / background over dark styling / colors / background

Could I program an AI to control this simulation?

Explain how to add an AI controller to the existing 3D Python simulation.

The AI should be able to:
- Read the simulation state.
- Choose actions for one or more objects.
- Move, rotate, attach, detach, collide, dip, orbit, organize, mark, spill, wrap, or interact depending on the simulation.
- Use a simple rule-based controller first.
- Optionally support a more advanced behavior system later.

Please explain:
1. What simulation state variables the AI needs.
2. What actions the AI can take.
3. How the AI chooses actions.
4. Where the AI controller code should be placed in the existing file.
5. How the AI can run automatically while still allowing human keyboard control.
6. How to pause, resume, or override the AI.
7. Provide example code that can be inserted into the simulation.

How can I make the AI more interesting and dynamic?

Add a more expressive AI behavior system to the simulation.

The AI should:
- Have multiple behavior modes.
- Switch between behaviors over time.
- React to the current simulation state.
- Avoid doing the same thing forever.
- Create visible, meaningful changes in the scene.
- Reset or loop the simulation when the state is halted, complete, empty, stable, or no longer changing.

Include:
1. A list of possible AI behavior modes.
2. A simple state machine for the AI.
3. A stagnation/completion detector.
4. A reset function.
5. A loop system that starts a new round after completion.
6. Example code that can be inserted into the existing simulation.
7. Suggestions for making the AI feel playful, ritual-like, chaotic, careful, curious, destructive, constructive, or artistic.

think thoroughly through these questions. however, you are not required to provide the answers/text to these questions. instead, you must provide the updated python simulation file with implementation of all given the conditions/inquiries above.

Return only the final Python source code. Do not wrap it in Markdown fences. Do not include explanations before or after the code.
"""


def require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in this terminal session.")


def build_seed_prompt(input_word_or_phrase: str) -> str:
    cleaned = input_word_or_phrase.strip()
    if not cleaned:
        raise ValueError("Input word or phrase cannot be empty.")
    return SEED_PROMPT_TEMPLATE.replace("[INPUT WORD OR PHRASE]", cleaned)


def build_simulation_prompt(scene_or_system: str) -> str:
    cleaned = scene_or_system.strip()
    if not cleaned:
        raise ValueError("Simulation seed cannot be empty.")
    return SIMULATION_PROMPT_TEMPLATE.replace("[OBJECTS / SCENE / SYSTEM]", cleaned)


def call_llm(prompt: str, model: str, temperature: Optional[float] = None) -> str:
    """Call the OpenAI Responses API and return text output.

    Some newer reasoning models reject custom temperature values. The UI keeps a
    temperature field for models that support it, but this function retries once
    without temperature when the API reports that the parameter is unsupported.
    """
    require_api_key()
    client = OpenAI()
    kwargs: dict[str, Any] = {"model": model, "input": prompt}
    if temperature is not None:
        kwargs["temperature"] = temperature

    try:
        response = client.responses.create(**kwargs)
    except Exception as exc:
        message = str(exc).lower()
        if temperature is not None and "temperature" in message and ("unsupported" in message or "not supported" in message or "does not support" in message):
            kwargs.pop("temperature", None)
            response = client.responses.create(**kwargs)
        else:
            raise

    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    # Defensive fallback for SDK/API versions that expose text differently.
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text_value = getattr(content, "text", None)
            if text_value:
                chunks.append(text_value)
    if chunks:
        return "\n".join(chunks)

    raise RuntimeError("The model returned no text output.")


def extract_python_source(text: str) -> str:
    match = re.search(r"```(?:python|py)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    source = match.group(1) if match else text
    return source.strip() + "\n"


def parse_seed_ideas(raw_text: str) -> list[dict[str, str]]:
    """Parse the numbered seed text into [{number, title, description, full_text}]."""
    pattern = re.compile(
        r"(?:^|\n)\s*(\d{1,2})\.\s+\*\*(.*?)\*\*\s*\n\s*(.*?)(?=\n\s*\d{1,2}\.\s+\*\*|\Z)",
        re.DOTALL,
    )
    seeds: list[dict[str, str]] = []
    for number, title, description in pattern.findall(raw_text):
        clean_description = " ".join(description.split())
        clean_title = " ".join(title.split())
        full_text = f"{clean_title}: {clean_description}"
        seeds.append(
            {
                "number": number,
                "title": clean_title,
                "description": clean_description,
                "full_text": full_text,
            }
        )
    return seeds


def slugify(text: str, fallback: str = "output") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:80] or fallback


def save_json(data: Any, filename_stem: str) -> str:
    file_id = uuid.uuid4().hex[:8]
    path = OUTPUT_DIR / f"{slugify(filename_stem)}-{file_id}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path.name


def save_text(text: str, filename_stem: str, suffix: str) -> str:
    file_id = uuid.uuid4().hex[:8]
    path = OUTPUT_DIR / f"{slugify(filename_stem)}-{file_id}{suffix}"
    path.write_text(text, encoding="utf-8")
    return path.name



def safe_output_path(filename: str, allowed_suffixes: tuple[str, ...] = (".json", ".py")) -> Path:
    """Return a safe path inside outputs/ for a saved output file."""
    if not filename or Path(filename).name != filename:
        abort(404)
    path = (OUTPUT_DIR / filename).resolve()
    if OUTPUT_DIR.resolve() not in path.parents or not path.exists() or not path.is_file():
        abort(404)
    if path.suffix.lower() not in allowed_suffixes:
        abort(404)
    return path


def safe_output_python_path(filename: str) -> Path:
    """Return a safe path inside outputs/ for a generated Python file."""
    return safe_output_path(filename, allowed_suffixes=(".py",))


def file_metadata(path: Path) -> dict[str, Any]:
    """Build metadata for the previous outputs page."""
    stat = path.stat()
    item: dict[str, Any] = {
        "filename": path.name,
        "kind": "seeds" if path.suffix.lower() == ".json" else "script",
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }

    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            item["title"] = data.get("phrase") or path.stem
            item["created_at"] = data.get("created_at") or item["modified_at"]
            item["summary"] = f"{len(data.get('seeds', []) or [])} parsed seed ideas"
        except Exception:
            item["title"] = path.stem
            item["created_at"] = item["modified_at"]
            item["summary"] = "Seed JSON file"
    else:
        item["title"] = path.stem
        item["created_at"] = item["modified_at"]
        item["summary"] = "Generated VPython Python script"
        item["run_url"] = f"/run/{path.name}"

    return item


def list_previous_outputs() -> list[dict[str, Any]]:
    """Return saved JSON seed files and generated Python scripts, newest first."""
    items: list[dict[str, Any]] = []
    for suffix in ("*.json", "*.py"):
        for path in OUTPUT_DIR.glob(suffix):
            if path.is_file():
                items.append(file_metadata(path))
    return sorted(items, key=lambda item: item.get("modified_at", ""), reverse=True)


def launch_vpython_script(filename: str) -> dict[str, str]:
    """Start a generated VPython script without blocking Flask."""
    script_path = safe_output_python_path(filename)
    run_id = uuid.uuid4().hex[:8]
    log_path = RUN_LOG_DIR / f"{script_path.stem}-{run_id}.log"
    log_file = log_path.open("w", encoding="utf-8")

    process = subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=str(OUTPUT_DIR),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        env=os.environ.copy(),
    )
    log_file.close()
    return {
        "run_id": run_id,
        "pid": str(process.pid),
        "log_file": log_path.name,
        "filename": filename,
    }


@app.errorhandler(Exception)
def handle_error(exc: Exception):
    status = exc.code if isinstance(exc, HTTPException) else 500
    message = exc.description if isinstance(exc, HTTPException) else str(exc)
    if not message:
        message = "Unexpected server error."
    return jsonify({"error": message}), status


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/previous")
def previous_outputs():
    return render_template("previous.html")


@app.get("/outputs/<path:filename>")
def output_file(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


@app.get("/api/previous")
def api_previous_outputs():
    return jsonify({"items": list_previous_outputs()})


@app.get("/api/previous/<path:filename>")
def api_previous_output_detail(filename: str):
    path = safe_output_path(filename)
    metadata = file_metadata(path)

    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"raw_text": path.read_text(encoding="utf-8"), "seeds": []}
        return jsonify({"metadata": metadata, "data": data})

    source = path.read_text(encoding="utf-8")
    return jsonify({"metadata": metadata, "source": source, "run_url": f"/run/{path.name}"})


@app.get("/run/<path:filename>")
def run_simulation(filename: str):
    run_info = launch_vpython_script(filename)
    return render_template("run.html", **run_info)


@app.post("/api/seeds")
def api_generate_seeds():
    payload = request.get_json(force=True)
    phrase = str(payload.get("phrase", "")).strip()
    model = str(payload.get("model") or SEED_MODEL_DEFAULT).strip()
    temperature_value = payload.get("temperature", SEED_TEMPERATURE_DEFAULT)
    save_output = bool(payload.get("save", True))

    temperature = float(temperature_value) if temperature_value not in (None, "") else SEED_TEMPERATURE_DEFAULT
    raw_text = call_llm(build_seed_prompt(phrase), model=model, temperature=temperature)
    seeds = parse_seed_ideas(raw_text)

    download = None
    if save_output:
        download = save_json(
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "phrase": phrase,
                "model": model,
                "temperature": temperature,
                "raw_text": raw_text,
                "seeds": seeds,
            },
            f"{phrase}-simulation-seeds",
        )

    return jsonify({"raw_text": raw_text, "seeds": seeds, "download": download})


@app.post("/api/simulation")
def api_generate_simulation():
    payload = request.get_json(force=True)
    seed = str(payload.get("seed", "")).strip()
    model = str(payload.get("model") or SIMULATION_MODEL_DEFAULT).strip()
    temperature_value = payload.get("temperature", None)
    save_output = bool(payload.get("save", True))

    temperature = None if temperature_value in (None, "") else float(temperature_value)
    raw_text = call_llm(build_simulation_prompt(seed), model=model, temperature=temperature)
    source = extract_python_source(raw_text)

    # Always save a runnable copy so the page can create an "Open and run" link.
    run_file = save_text(source, f"vpython-simulation-{seed}", ".py")

    download = run_file if save_output else None
    run_url = f"/run/{run_file}"

    return jsonify({"source": source, "download": download, "run_url": run_url})


@app.post("/api/batch")
def api_batch_generate():
    """Process two explicit queues in order.

    Queue 1: seed_requests contains short words/phrases. Each line generates and saves
    a seed JSON file.

    Queue 2: code_requests contains full simulation seed/scene descriptions. Each line
    generates and saves a runnable VPython script.

    The function is intentionally synchronous and ordered, so only one LLM call starts
    after the previous LLM call has finished.
    """
    payload = request.get_json(force=True)
    seed_requests = payload.get("seed_requests", [])
    code_requests = payload.get("code_requests", [])

    # Backward compatibility with the earlier single batch box format.
    legacy_requests = payload.get("requests", [])
    if legacy_requests and not seed_requests and not code_requests:
        seed_requests = [str(item.get("phrase", "")).strip() for item in legacy_requests if isinstance(item, dict) and item.get("phrase")]
        code_requests = [str(item.get("seed", "")).strip() for item in legacy_requests if isinstance(item, dict) and item.get("seed")]

    if not isinstance(seed_requests, list):
        raise ValueError("seed_requests must be a list.")
    if not isinstance(code_requests, list):
        raise ValueError("code_requests must be a list.")

    seed_requests = [str(item).strip() for item in seed_requests if str(item).strip()]
    code_requests = [str(item).strip() for item in code_requests if str(item).strip()]

    if not seed_requests and not code_requests:
        raise ValueError("Add at least one seed request or code request.")

    seed_model = str(payload.get("seed_model") or SEED_MODEL_DEFAULT).strip()
    simulation_model = str(payload.get("simulation_model") or SIMULATION_MODEL_DEFAULT).strip()
    seed_temperature_value = payload.get("seed_temperature", SEED_TEMPERATURE_DEFAULT)
    simulation_temperature_value = payload.get("simulation_temperature", None)
    save_seeds = bool(payload.get("save_seeds", True))
    save_simulations = bool(payload.get("save_simulations", True))

    seed_temperature = (
        SEED_TEMPERATURE_DEFAULT
        if seed_temperature_value in (None, "")
        else float(seed_temperature_value)
    )
    simulation_temperature = (
        None
        if simulation_temperature_value in (None, "")
        else float(simulation_temperature_value)
    )

    results: list[dict[str, Any]] = []
    index = 0

    for phrase in seed_requests:
        index += 1
        result: dict[str, Any] = {
            "index": index,
            "queue": "seeds",
            "label": phrase,
            "status": "started",
            "seed_download": None,
            "script_download": None,
            "run_url": None,
            "seed_count": 0,
        }
        try:
            raw_seed_text = call_llm(
                build_seed_prompt(phrase),
                model=seed_model,
                temperature=seed_temperature,
            )
            seeds = parse_seed_ideas(raw_seed_text)
            result["seed_count"] = len(seeds)
            result["raw_seed_text"] = raw_seed_text
            result["seeds"] = seeds

            if save_seeds:
                result["seed_download"] = save_json(
                    {
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                        "batch_index": index,
                        "queue": "seeds",
                        "phrase": phrase,
                        "model": seed_model,
                        "temperature": seed_temperature,
                        "raw_text": raw_seed_text,
                        "seeds": seeds,
                    },
                    f"batch-seeds-{index}-{phrase}-simulation-seeds",
                )

            result["status"] = "complete"
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)

        results.append(result)

    for seed in code_requests:
        index += 1
        result = {
            "index": index,
            "queue": "code",
            "label": seed,
            "status": "started",
            "seed_download": None,
            "script_download": None,
            "run_url": None,
            "seed_count": 0,
        }
        try:
            raw_simulation_text = call_llm(
                build_simulation_prompt(seed),
                model=simulation_model,
                temperature=simulation_temperature,
            )
            source = extract_python_source(raw_simulation_text)
            run_file = save_text(source, f"batch-code-{index}-vpython-simulation-{seed}", ".py")
            result["script_download"] = run_file if save_simulations else None
            result["run_url"] = f"/run/{run_file}"
            result["source_preview"] = source[:4000]
            result["source_length"] = len(source)
            result["status"] = "complete"
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)

        results.append(result)

    complete_count = sum(1 for item in results if item.get("status") == "complete")
    error_count = sum(1 for item in results if item.get("status") == "error")
    return jsonify({"results": results, "complete_count": complete_count, "error_count": error_count})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
