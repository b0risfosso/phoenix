# Simulation Seed Reader + VPython Script Generator

This local web app is for reading saved simulation seed JSON files and generating VPython scripts linked to specific seed entries.

## Setup

```bash
cd simulation_seed_to_vpython_web_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your_api_key_here"
python app.py
```

To read the same generated seeds as the seed generator app, run both apps with the same shared data folder:

```bash
export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
```

Open:

```text
http://127.0.0.1:5001
```

## Workflow

1. Generate seeds in the seed generator app, or put saved seed JSON files in the shared seeds folder:

```text
$SIMULATION_SHARED_DATA_DIR/seeds/
```

If `SIMULATION_SHARED_DATA_DIR` is not set, both apps use:

```text
../simulation_shared_data/seeds/
```

2. Open the app.
3. Select a seed JSON file.
4. Read individual seed entries.
5. Click **Generate VPython script** on any seed.
6. The generated script is saved in:

```text
$SIMULATION_SHARED_DATA_DIR/scripts/
```

7. The seed-to-script link is saved in:

```text
$SIMULATION_SHARED_DATA_DIR/metadata/seed_script_links.json
```

## Script actions

Each linked script can be:

- opened/read in browser
- edited in browser
- downloaded
- opened and run locally

VPython usually opens its own browser visualization when the Python script starts.

## Seed JSON format

The app works best with the seed-only generator format:

```json
{
  "input_phrase": "water",
  "entries": [
    {
      "number": "1",
      "title": "Water Droplets Sorting by Surface Tension",
      "description": "Transparent droplets slide...",
      "seed": "Water Droplets Sorting by Surface Tension: Transparent droplets slide..."
    }
  ],
  "raw_output": "..."
}
```

It also tries to parse numbered Markdown seed lists from `raw_output`.
