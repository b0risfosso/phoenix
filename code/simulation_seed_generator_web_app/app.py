#!/usr/bin/env python3
"""
Simulation Seed Generator Web App

A small local Flask web app for generating VPython simulation seed ideas
from one input word or phrase.

Run:
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    export OPENAI_API_KEY="your_api_key_here"
    python app.py

Open:
    http://127.0.0.1:5000

Shared data:
    By default, generated seed JSON files are saved to:
        ../simulation_shared_data/seeds/

    To force both apps to use a specific shared folder:
        export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory
from openai import OpenAI


APP_DIR = Path(__file__).resolve().parent

# Shared data folder.
# Both apps read/write this same folder by default:
#     ../simulation_shared_data/
# Override with:
#     export SIMULATION_SHARED_DATA_DIR="/absolute/path/to/shared/data"
SHARED_DATA_DIR = Path(
    os.environ.get("SIMULATION_SHARED_DATA_DIR", APP_DIR.parent / "simulation_shared_data")
).expanduser().resolve()

OUTPUT_DIR = SHARED_DATA_DIR
SEEDS_DIR = OUTPUT_DIR / "seeds"

SEEDS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_MODEL = os.environ.get("OPENAI_SEED_MODEL", "gpt-5.1")
DEFAULT_TEMPERATURE = float(os.environ.get("OPENAI_SEED_TEMPERATURE", "0.9"))

app = Flask(__name__)


PROMPT_TEMPLATE = """You are generating 3D Python VPython simulation seed ideas.

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


def slugify(text: str, max_len: int = 64) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    if not slug:
        slug = "simulation-seeds"
    return slug[:max_len].strip("-") or "simulation-seeds"


def build_prompt(input_word_or_phrase: str) -> str:
    cleaned = input_word_or_phrase.strip()
    if not cleaned:
        raise ValueError("Input word or phrase cannot be empty.")
    return PROMPT_TEMPLATE.replace("[INPUT WORD OR PHRASE]", cleaned)


def call_llm(prompt: str, model: str, temperature: float | None) -> str:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI()

    kwargs: dict[str, Any] = {
        "model": model,
        "input": prompt,
    }

    if temperature is not None:
        kwargs["temperature"] = temperature

    try:
        response = client.responses.create(**kwargs)
    except Exception as exc:
        message = str(exc).lower()
        if "temperature" in message and "unsupported" in message:
            kwargs.pop("temperature", None)
            response = client.responses.create(**kwargs)
        else:
            raise

    return response.output_text


def parse_seed_entries(text: str) -> list[dict[str, str]]:
    """
    Parse numbered markdown-like seed output into structured items.
    Keeps the full raw output too, so parsing is helpful but not required.
    """
    entries: list[dict[str, str]] = []

    # Matches:
    # 1. **Title**
    #    Description...
    pattern = re.compile(
        r"^\s*(\d+)\.\s+\*\*(.*?)\*\*\s*\n\s*(.*?)(?=^\s*\d+\.\s+\*\*|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )

    for match in pattern.finditer(text):
        number = match.group(1).strip()
        title = re.sub(r"\s+", " ", match.group(2).strip())
        description = re.sub(r"\s+", " ", match.group(3).strip())
        if title or description:
            entries.append(
                {
                    "number": number,
                    "title": title,
                    "description": description,
                    "seed": f"{title}: {description}".strip(": "),
                }
            )

    return entries


def save_seed_output(input_phrase: str, model: str, temperature: float | None, output_text: str) -> Path:
    now = datetime.now()
    uid = uuid.uuid4().hex[:8]
    filename = f"{now.strftime('%Y%m%d-%H%M%S')}-{slugify(input_phrase)}-{uid}.json"
    path = SEEDS_DIR / filename

    data = {
        "kind": "simulation_seed_output",
        "input_phrase": input_phrase,
        "model": model,
        "temperature": temperature,
        "created_at": now.isoformat(timespec="seconds"),
        "entries": parse_seed_entries(output_text),
        "raw_output": output_text,
    }

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_seed_file(filename: str) -> dict[str, Any]:
    path = (SEEDS_DIR / filename).resolve()
    if not str(path).startswith(str(SEEDS_DIR.resolve())):
        raise ValueError("Invalid filename.")
    if not path.exists():
        raise FileNotFoundError(filename)
    return json.loads(path.read_text(encoding="utf-8"))


@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
@app.route("/index.html", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/previous", methods=["GET"])
def previous():
    return render_template("previous.html")


@app.route("/api/generate-seeds", methods=["POST"])
def api_generate_seeds():
    try:
        payload = request.get_json(force=True) or {}
        input_phrase = str(payload.get("input_phrase", "")).strip()
        model = str(payload.get("model") or DEFAULT_MODEL).strip()
        temperature_value = payload.get("temperature", DEFAULT_TEMPERATURE)
        save_output = bool(payload.get("save_output", True))

        if not input_phrase:
            return jsonify({"ok": False, "error": "Input word or phrase is required."}), 400

        temperature: float | None
        if temperature_value in ("", None):
            temperature = None
        else:
            temperature = float(temperature_value)

        prompt = build_prompt(input_phrase)
        output_text = call_llm(prompt, model=model, temperature=temperature)
        entries = parse_seed_entries(output_text)

        saved_filename = None
        download_url = None

        if save_output:
            saved_path = save_seed_output(input_phrase, model, temperature, output_text)
            saved_filename = saved_path.name
            download_url = f"/outputs/seeds/{saved_filename}"

        return jsonify(
            {
                "ok": True,
                "input_phrase": input_phrase,
                "model": model,
                "temperature": temperature,
                "raw_output": output_text,
                "entries": entries,
                "saved_filename": saved_filename,
                "download_url": download_url,
            }
        )

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/batch-generate-seeds", methods=["POST"])
def api_batch_generate_seeds():
    """
    Process many seed-generation requests sequentially.
    Each non-empty line is treated as one input phrase.
    """
    try:
        payload = request.get_json(force=True) or {}
        text = str(payload.get("input_phrases", "")).strip()
        model = str(payload.get("model") or DEFAULT_MODEL).strip()
        temperature_value = payload.get("temperature", DEFAULT_TEMPERATURE)
        save_output = bool(payload.get("save_output", True))

        phrases = [line.strip() for line in text.splitlines() if line.strip()]
        if not phrases:
            return jsonify({"ok": False, "error": "Enter at least one input phrase."}), 400

        if temperature_value in ("", None):
            temperature = None
        else:
            temperature = float(temperature_value)

        results = []
        for input_phrase in phrases:
            try:
                prompt = build_prompt(input_phrase)
                output_text = call_llm(prompt, model=model, temperature=temperature)
                entries = parse_seed_entries(output_text)

                saved_filename = None
                download_url = None
                if save_output:
                    saved_path = save_seed_output(input_phrase, model, temperature, output_text)
                    saved_filename = saved_path.name
                    download_url = f"/outputs/seeds/{saved_filename}"

                results.append(
                    {
                        "ok": True,
                        "input_phrase": input_phrase,
                        "raw_output": output_text,
                        "entries": entries,
                        "saved_filename": saved_filename,
                        "download_url": download_url,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "ok": False,
                        "input_phrase": input_phrase,
                        "error": str(exc),
                    }
                )

        return jsonify({"ok": True, "results": results})

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/previous-seeds", methods=["GET"])
def api_previous_seeds():
    try:
        items = []
        for path in sorted(SEEDS_DIR.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                items.append(
                    {
                        "filename": path.name,
                        "input_phrase": data.get("input_phrase", ""),
                        "created_at": data.get("created_at", ""),
                        "model": data.get("model", ""),
                        "entry_count": len(data.get("entries", [])),
                        "download_url": f"/outputs/seeds/{path.name}",
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
        data = load_seed_file(filename)
        return jsonify({"ok": True, "filename": filename, "data": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.route("/outputs/seeds/<path:filename>", methods=["GET"])
def download_seed_file(filename: str):
    return send_from_directory(SEEDS_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
