# Sentence / Simulation Cycle Web App

Cycles through every sentence node and tied simulation script for 10 seconds by default.

Run:

```bash
cd sentence_simulation_cycle_web_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
python app.py
```

Open:

```text
http://127.0.0.1:5004
```

Reads:

```text
$SIMULATION_SHARED_DATA_DIR/metadata/core_sentence_tree.json
$SIMULATION_SHARED_DATA_DIR/scripts/
```

Controls include play/pause, previous, next, reload, seconds per item, script preview, and optional auto-open first script.

- Added an **Only show sentences with scripts attached** toggle for filtering the cycle queue.
