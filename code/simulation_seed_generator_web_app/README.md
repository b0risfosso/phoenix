# Simulation Seed Generator Web App

This is a small local web app solely for generating VPython simulation seed ideas from one input word or phrase.

It does **not** generate Python simulation code. It only generates and stores simulation seed ideas.

## Setup

```bash
cd simulation_seed_generator_web_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your_api_key_here"
python app.py
```

To share seed data with the seed-to-VPython app, run both apps with the same shared data folder:

```bash
export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
```

Open:

```text
http://127.0.0.1:5000
```

## Features

- Generate 20–25 simulation seed ideas from one word or phrase.
- Display parsed seed cards.
- Display the full raw LLM output.
- Save outputs as JSON files.
- Browse previous saved outputs at `/previous`.
- Batch generation: one input phrase per line, processed sequentially.

## Output location

Saved JSON files are stored in the shared data folder:

```text
$SIMULATION_SHARED_DATA_DIR/seeds/
```

If `SIMULATION_SHARED_DATA_DIR` is not set, the app uses:

```text
../simulation_shared_data/seeds/
```

Each saved file contains:

- input phrase
- model
- temperature
- created timestamp
- parsed seed entries
- raw output
```
