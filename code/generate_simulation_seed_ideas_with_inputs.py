#!/usr/bin/env python3
"""
Generate VPython simulation seed ideas from one input word or phrase.

Edit the USER SETTINGS section below, then run:

    python generate_simulation_seed_ideas_with_inputs.py

You can also override the in-file settings from the command line:

    python generate_simulation_seed_ideas_with_inputs.py --input "water"
    python generate_simulation_seed_ideas_with_inputs.py --input "traffic flow" --save --output ./outputs/traffic_flow_seeds.txt

Setup:
    pip install openai
    export OPENAI_API_KEY="your_api_key_here"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from openai import OpenAI


# =============================================================================
# USER SETTINGS
# =============================================================================

# Put your input word or phrase here.
INPUT_WORD_OR_PHRASE = "water"

# Model used for the single LLM call.
MODEL = "gpt-5.1"

# Sampling temperature.
TEMPERATURE = 0.9

# Save the generated seed list to a file?
SAVE_OUTPUT = False

# File location used when SAVE_OUTPUT is True.
OUTPUT_FILE_PATH = "/Users/b/phoenix/seeds/water_simulation_seeds.txt"

# Print the completed prompt instead of calling the LLM.
DRY_RUN = False

# Print the completed prompt before the LLM call.
PRINT_PROMPT = False


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


def build_prompt(input_word_or_phrase: str) -> str:
    """Return the completed prompt with the user's phrase inserted."""
    cleaned_input = input_word_or_phrase.strip()
    if not cleaned_input:
        raise ValueError("INPUT_WORD_OR_PHRASE cannot be empty.")

    return PROMPT_TEMPLATE.replace("[INPUT WORD OR PHRASE]", cleaned_input)


def call_llm(prompt: str, model: str, temperature: float) -> str:
    """Send the completed prompt in one LLM call and return the generated text."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it before running this script."
        )

    client = OpenAI()

    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=temperature,
    )

    return response.output_text


def save_text(text: str, output_path: str | Path) -> Path:
    """Save text to the requested file path, creating folders if needed."""
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate 20–25 VPython simulation seed ideas from one input phrase."
    )
    parser.add_argument(
        "--input",
        "--input-word-or-phrase",
        dest="input_word_or_phrase",
        default=None,
        help="Overrides INPUT_WORD_OR_PHRASE from the USER SETTINGS section.",
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
        help="Save generated output to a file.",
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
        help="Optional file path for saving the generated output.",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print the completed prompt before calling the model.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the prompt without calling the model.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_word_or_phrase = args.input_word_or_phrase or INPUT_WORD_OR_PHRASE
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
        prompt = build_prompt(input_word_or_phrase)

        if print_prompt or dry_run:
            print("\n===== COMPLETED PROMPT =====\n")
            print(prompt)
            print("\n===== END PROMPT =====\n")

        if dry_run:
            return 0

        output_text = call_llm(
            prompt=prompt,
            model=model,
            temperature=temperature,
        )

        print(output_text)

        if should_save:
            saved_path = save_text(output_text, output_path)
            print(f"\nSaved output to: {saved_path}")

        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
