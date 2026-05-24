# Core Sentence Branch Script Web App

This app is centered on:

```text
Core sentence → next sentence branch → new core sentence → scripts tied to that sentence
```

Run:

```bash
cd core_sentence_branch_script_web_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
python app.py
```

Open:

```text
http://127.0.0.1:5003
```

Tree data is stored in:

```text
$SIMULATION_SHARED_DATA_DIR/metadata/core_sentence_tree.json
```

Scripts are stored in:

```text
$SIMULATION_SHARED_DATA_DIR/scripts/
```

## Added UI behavior

- The sentence node page includes a **Story** panel.
- The Story panel concatenates all sentences from the root/core sentence to the current node into one paragraph.
- The tree page supports branch expand/collapse.
- Use **Expand all** and **Collapse all** on the tree page.
