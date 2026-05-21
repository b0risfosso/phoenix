#!/usr/bin/env python3
"""
Generate a complete VPython simulation from a scene/object/system input.

Edit the USER SETTINGS section below, then run:

    python generate_vpython_simulation_with_inputs.py

You can also override the in-file settings from the command line:

    python generate_vpython_simulation_with_inputs.py --scene "marbles sorting themselves through ramps and gates"
    python generate_vpython_simulation_with_inputs.py --scene "a solar system with AI probes" --save --output ./outputs/solar_ai.py

Setup:
    pip install openai
    export OPENAI_API_KEY="your_api_key_here"
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional

from openai import OpenAI


# =============================================================================
# USER SETTINGS
# =============================================================================

# Put the simulation subject here.
SCENE_OR_SYSTEM = "a solar system with planets, asteroid belts, and AI-controlled probes"

# Model used for the single LLM call.
MODEL = "gpt-5.5"

# Optional sampling temperature. Use None to use the model/API default.
TEMPERATURE: Optional[float] = None

# Save the generated VPython simulation source code to a file?
SAVE_OUTPUT = True

# File location used when SAVE_OUTPUT is True.
OUTPUT_FILE_PATH = "./generated_vpython_simulation.py"

# Print the completed prompt instead of calling the LLM.
DRY_RUN = False

# Print the completed prompt before the LLM call.
PRINT_PROMPT = False


PROMPT_TEMPLATE = """Make a 3D Python simulation of [OBJECTS / SCENE / SYSTEM].

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
"""


CODE_ONLY_SUFFIX = """

Return only the final Python source code. Do not wrap it in Markdown fences. Do not include explanations before or after the code.
"""


def build_prompt(scene: str) -> str:
    """Replace the document placeholder with the scene/system input."""
    cleaned_scene = scene.strip()
    if not cleaned_scene:
        raise ValueError("SCENE_OR_SYSTEM cannot be empty.")

    return PROMPT_TEMPLATE.replace("[OBJECTS / SCENE / SYSTEM]", cleaned_scene) + CODE_ONLY_SUFFIX


def extract_python_source(text: str) -> str:
    """
    If the model returns a fenced Python block despite the instruction,
    extract the first fenced Python block. Otherwise return the text as-is.
    """
    match = re.search(
        r"```(?:python|py)?\s*(.*?)```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    source = match.group(1) if match else text
    return source.strip() + "\n"


def call_llm(prompt: str, model: str, temperature: Optional[float]) -> str:
    """Make exactly one LLM call and return the generated text."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it before running this script."
        )

    client = OpenAI()

    kwargs: dict[str, object] = {
        "model": model,
        "input": prompt,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    response = client.responses.create(**kwargs)
    return response.output_text


def save_text(text: str, output_path: str | Path) -> Path:
    """Save text to the requested file path, creating folders if needed."""
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a VPython simulation from the embedded prompt."
    )
    parser.add_argument(
        "--scene",
        "--objects-scene-system",
        dest="scene",
        default=None,
        help="Overrides SCENE_OR_SYSTEM from the USER SETTINGS section.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Overrides MODEL from the USER SETTINGS section.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Overrides TEMPERATURE from the USER SETTINGS section.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save generated simulation source code to a file.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save generated output, even if SAVE_OUTPUT is True.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional file path for saving the generated Python simulation.",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print the filled prompt before calling the LLM.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the prompt without calling the model.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    scene = args.scene or SCENE_OR_SYSTEM
    model = args.model or MODEL
    temperature = TEMPERATURE if args.temperature is None else args.temperature
    output_path = args.output or Path(OUTPUT_FILE_PATH)

    should_save = SAVE_OUTPUT
    if args.save:
        should_save = True
    if args.no_save:
        should_save = False

    dry_run = DRY_RUN or args.dry_run
    print_prompt = PRINT_PROMPT or args.print_prompt

    try:
        prompt = build_prompt(scene)

        if print_prompt or dry_run:
            print("\n===== COMPLETED PROMPT =====\n")
            print(prompt)
            print("\n===== END PROMPT =====\n")

        if dry_run:
            return 0

        generated_text = call_llm(prompt, model, temperature)
        source = extract_python_source(generated_text)

        print(source)

        if should_save:
            saved_path = save_text(source, output_path)
            print(f"\nSaved generated VPython simulation to: {saved_path}")

        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
