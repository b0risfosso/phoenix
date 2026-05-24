# Script-to-Script Web App

Shows sentence, story, and script. Allows manual child scripts to be created and attached to a parent script.

Run:

```bash
cd script_to_script_web_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
python app.py
```

Open `http://127.0.0.1:5006`.

Links are stored at `$SIMULATION_SHARED_DATA_DIR/metadata/script_to_script_links.json`.

## Story-first home page

The home page now shows stories first. Each story card displays the sentence/story path and linked scripts. Select a linked script to open its script-to-script detail page.
