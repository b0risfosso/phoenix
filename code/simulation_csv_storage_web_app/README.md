# Simulation CSV Storage Web App

Workflow:

```text
story -> main script -> manually entered CSV child script -> run CSV child -> stored CSV files
```

Run:

```bash
cd simulation_csv_storage_web_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
python app.py
```

Open:

```text
http://127.0.0.1:5007
```

CSV outputs are stored in:

```text
$SIMULATION_SHARED_DATA_DIR/csv_runs/
```

CSV recorder links:

```text
$SIMULATION_SHARED_DATA_DIR/metadata/csv_script_links.json
```

Run index:

```text
$SIMULATION_SHARED_DATA_DIR/metadata/csv_run_index.json
```

## Story tree home page

The home page now displays stories as a hierarchy. Core/root sentences appear above next-sentence branches. Branches support expand/collapse, expand all, collapse all, search, and scripted-only filtering.
