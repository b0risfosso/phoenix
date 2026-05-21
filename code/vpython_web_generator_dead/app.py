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
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from flask import Flask, jsonify, render_template, request, send_from_directory
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

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
    require_api_key()
    client = OpenAI()
    kwargs: dict[str, Any] = {"model": model, "input": prompt}
    if temperature is not None:
        kwargs["temperature"] = temperature
    response = client.responses.create(**kwargs)
    return response.output_text


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




@app.errorhandler(Exception)
def handle_error(exc: Exception):
    status = getattr(exc, "code", 500)
    message = str(exc) or "Unexpected server error."
    return jsonify({"error": message}), status


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/outputs/<path:filename>")
def output_file(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


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

    download = None
    if save_output:
        download = save_text(source, f"vpython-simulation-{seed}", ".py")

    return jsonify({"source": source, "download": download})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
