# VPython Simulation Web Generator

This local Flask web app turns the two-script workflow into a webpage:

1. Enter one word or phrase.
2. Generate 20–25 VPython simulation seed ideas.
3. Click or edit a seed.
4. Generate a complete VPython Python script.
5. Download the seed JSON or generated `.py` file.
6. Open the generated simulation in a new tab and start it from the browser.
7. Use the **Previous outputs** page to view saved seed JSON files and saved Python scripts.
8. On **Previous outputs**, open a saved seed list and use each seed entry to generate a linked script or open an already linked script.
9. Use the **Batch queues** section to send separate seed-generation and code-generation batches sequentially.

## Setup

```bash
cd vpython_web_generator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your_api_key_here"
python app.py
```

Open this URL in a browser:

```text
http://127.0.0.1:5000
```

## Linked previous outputs

The **Previous outputs** page now links saved simulation seeds to generated scripts.

- Open a saved seed JSON file.
- Read the parsed seed list.
- Each seed card shows any linked Python scripts.
- Click **Open script** to display the saved Python source.
- Click **Open and run** to launch a linked script in a new tab.
- Click **Generate script from this seed** when no script exists yet, or when you want a new script variation.

New links are stored in `outputs/metadata/seed_script_links.json`, so the visible output library stays focused on seed JSON files and Python scripts. The app also tries to infer links for older generated scripts by matching script filenames against seed text.

## Batch queues

The generator page includes two separate batch entries:

1. **Batch entry 1: generate simulation seeds** — enter one word or phrase per line.
2. **Batch entry 2: generate VPython code** — enter one complete simulation seed or scene description per line.

Click **Run both queues sequentially**. The Flask backend processes the seed queue first and the code queue second with normal Python `for` loops, so only one LLM call is made at a time.

Batch behavior:

- Seed lines generate saved JSON seed files when **Save seed JSON files** is enabled.
- Code lines generate saved Python scripts when **Save Python scripts** is enabled.
- Each generated Python script gets an **Open and run simulation** link.
- If one item fails, later items still continue.

## Notes

- The webpage itself does not expose your API key. The key stays in the terminal environment where Flask is running.
- Generated seed lists are saved as JSON in `outputs/` when the checkbox is enabled.
- Generated VPython scripts are saved as `.py` files in `outputs/` when the checkbox is enabled.
- The app also saves a runnable copy of each generated simulation so it can create an **Open and run simulation** link.
- The **Previous outputs** page at `http://127.0.0.1:5000/previous` lists saved `.json` seed files and `.py` scripts from `outputs/`, displays their contents, links seeds to scripts, and provides download/run links.
- Clicking **Open and run simulation** starts the generated Python file as a local process. VPython usually opens its own browser window or tab for the 3D canvas.
- To run a generated simulation manually, install VPython and run the downloaded script:

```bash
pip install vpython
python outputs/generated_file_name.py
```


## Editing generated VPython scripts

Generated Python scripts can be edited in the browser.

Ways to open the editor:

- After generating one script, click **Edit script** next to the download/run links.
- On **Previous outputs**, select a saved Python script and click **Edit script**.
- On **Previous outputs**, open a saved seed file, find a linked script, and click **Edit**.

The editor page lets you:

- Modify the saved Python source in a large textarea.
- Save changes back to the same `.py` file.
- Save the edited version as a new copy.
- Download the script.
- Open and run the edited simulation in a new tab.

Saved edits are written to the local `outputs/` folder.

## Script variations

Generated Python scripts can now have one or more linked variations.

Ways to open the variation page:

- After generating a script, click **Build variations**.
- On **Previous outputs**, select a saved Python script and click **Build variations**.
- In the script editor, click **Build variations**.
- From a linked seed card, click **Variations** for any saved script.

The variation page shows:

- The original script source.
- Download, edit, and run links for the original script.
- A variation request box for describing what should change.
- A manual variation editor for saving hand-edited code as a variation.
- A list of saved variations linked to the original script.

Variation records are stored in `outputs/metadata/script_variations.json`. The generated variation `.py` files are saved in `outputs/` and can also be opened, edited, downloaded, run, or used as the basis for further variations.
