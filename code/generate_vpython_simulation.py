#!/usr/bin/env python3
"""
Generate a complete VPython simulation from a single scene/object/system input.

This script embeds the full prompt from prompt_1.docx, replaces the
[OBJECTS / SCENE / SYSTEM] placeholder, and sends the resulting prompt in
one LLM call.

Setup:
  pip install openai
  export OPENAI_API_KEY="your_api_key_here"

Examples:
  python generate_vpython_simulation.py \
    --scene "a solar system with planets, asteroid belts, and AI-controlled probes"

  python generate_vpython_simulation.py \
    --scene "marbles sorting themselves through ramps and gates" \
    --model gpt-5.5 \
    --output marble_sorting_simulation.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "The OpenAI Python SDK is not installed. Install it with: pip install openai"
    ) from exc


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
    """Replace the document placeholder with the user's scene/system input."""
    scene = scene.strip()
    if not scene:
        raise ValueError("Scene input cannot be empty.")
    return PROMPT_TEMPLATE.replace("[OBJECTS / SCENE / SYSTEM]", scene) + CODE_ONLY_SUFFIX


def extract_python_source(text: str) -> str:
    """
    If the model returns a fenced Python block despite the instruction,
    extract the first fenced Python block. Otherwise return the text as-is.
    """
    match = re.search(r"```(?:python|py)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    source = match.group(1) if match else text
    return source.strip() + "\n"


def call_llm(prompt: str, model: str, temperature: Optional[float]) -> str:
    """Make exactly one LLM call and return the generated text."""
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY is not set.")

    client = OpenAI()

    kwargs = {
        "model": model,
        "input": prompt,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    response = client.responses.create(**kwargs)
    return response.output_text


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a VPython simulation from the embedded uploaded-document prompt."
    )
    parser.add_argument(
        "--scene",
        "--objects-scene-system",
        dest="scene",
        help="Text that replaces [OBJECTS / SCENE / SYSTEM].",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.5",
        help="OpenAI model to call. Default: gpt-5.5",
    )
    parser.add_argument(
        "--output",
        default="generated_vpython_simulation.py",
        help="Path for the generated Python simulation file.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Optional sampling temperature. Omit to use the model/API default.",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print the filled prompt and exit without calling the LLM.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    scene = args.scene
    if not scene:
        scene = input("Describe [OBJECTS / SCENE / SYSTEM]: ").strip()

    try:
        prompt = build_prompt(scene)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.print_prompt:
        print(prompt)
        return 0

    try:
        generated_text = call_llm(prompt, args.model, args.temperature)
    except Exception as exc:
        print(f"LLM call failed: {exc}", file=sys.stderr)
        return 1

    source = extract_python_source(generated_text)
    output_path = Path(args.output)
    output_path.write_text(source, encoding="utf-8")

    print(f"Wrote generated VPython simulation to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
