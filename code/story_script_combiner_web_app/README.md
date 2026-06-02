# Story Script Combiner Web App

This app combines existing stories/scripts using manual entry only.

## Workflow

```text
select 2+ stories -> open combine page -> manually enter combined story -> manually enter combined script -> save -> run with optional CSV output
```

## Run

```bash
cd story_script_combiner_web_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
python app.py
```

Open:

```text
http://127.0.0.1:5009
```

## Shared data

Reads/writes:

```text
$SIMULATION_SHARED_DATA_DIR/metadata/core_sentence_tree.json
$SIMULATION_SHARED_DATA_DIR/scripts/
$SIMULATION_SHARED_DATA_DIR/csv_runs/
```

Combined records are indexed at:

```text
$SIMULATION_SHARED_DATA_DIR/metadata/combined_story_script_index.json
```

CSV run records are indexed at:

```text
$SIMULATION_SHARED_DATA_DIR/metadata/csv_run_index.json
```

## Notes

All entries are manual. This app does not generate story text or script text.
