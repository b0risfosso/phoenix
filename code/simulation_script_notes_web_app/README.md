# Simulation Script Notes Web App

This local web app displays generated VPython scripts and lets you attach editable notes to each script.

It is designed to read the same shared data folder used by the seed generator and seed-to-VPython apps.

## Setup

```bash
cd simulation_script_notes_web_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
python app.py
```

Open:

```text
http://127.0.0.1:5002
```

## Shared data

The app reads scripts from:

```text
$SIMULATION_SHARED_DATA_DIR/scripts/
```

and stores notes in:

```text
$SIMULATION_SHARED_DATA_DIR/metadata/script_notes.json
```

If `SIMULATION_SHARED_DATA_DIR` is not set, it uses:

```text
../simulation_shared_data/
```

## Features

- Browse generated `.py` scripts.
- Search by script filename or note text.
- Filter scripts with or without notes.
- Open a script in the browser.
- Copy script source.
- Download script source.
- Open and run the local VPython script.
- Add two kinds of notes to scripts:
  - core sentence notes
  - next sentence notes
- Edit notes and change their note kind.
- Delete notes.
- Filter scripts by note kind.
- Open each next sentence note as its own branch page.
- Treat the next sentence as a new branch core sentence.
- Manually add a script to a branch by pasting/writing Python source.
- Save that manual script as a new `.py` file linked to the branch.
- Store branch tree data in `$SIMULATION_SHARED_DATA_DIR/metadata/sentence_branches.json`.
- Export all notes as JSON at `/api/export-notes`.

## Suggested workflow

Run the apps on separate ports:

```text
Seed generator:       http://127.0.0.1:5000
Seed-to-VPython:     http://127.0.0.1:5001
Script notes:        http://127.0.0.1:5002
```


## Branch workflow

1. Open a script.
2. Add a **Next sentence note**.
3. Click **Open as branch core sentence** on that note.
4. The next sentence opens as a new branch page.
5. On the branch page, the next sentence becomes the branch's core sentence.
6. Generate a new VPython script from the branch, or attach an existing script filename.
7. The branch tree is stored in:

```text
$SIMULATION_SHARED_DATA_DIR/metadata/sentence_branches.json
```
