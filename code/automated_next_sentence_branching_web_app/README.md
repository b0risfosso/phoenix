# Automated Next Sentence Branching Web App

Reads the shared core sentence tree, lets you select a story/sentence, generates 20 possible next sentences with an LLM, and saves each generated next sentence as a child node in the same shared tree.

Run:

```bash
cd automated_next_sentence_branching_web_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
export OPENAI_API_KEY="your_api_key_here"
python app.py
```

Open:

```text
http://127.0.0.1:5008
```

Generated child nodes are saved in:

```text
$SIMULATION_SHARED_DATA_DIR/metadata/core_sentence_tree.json
```

Manual scripts attached to next sentences are saved in:

```text
$SIMULATION_SHARED_DATA_DIR/scripts/
```

## Automated script modification

Each next-sentence branch can generate a modified script from an existing source script. The app sends the source script plus the branch sentence to the script-modification prompt, saves the returned Python file in the shared scripts folder, and attaches it to the branch node.

Source scripts are selected from the current story node and its ancestor nodes.

## Story tree home page

The home page displays root/core sentences and next-sentence branches as an expandable tree with per-branch expand/collapse plus Expand all and Collapse all.
