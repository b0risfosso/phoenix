# VPython Simulation Web Generator

This local Flask web app turns the two-script workflow into a webpage:

1. Enter one word or phrase.
2. Generate 20–25 VPython simulation seed ideas.
3. Click or edit a seed.
4. Generate a complete VPython Python script.
5. Download the seed JSON or generated `.py` file.

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

## Notes

- The webpage itself does not expose your API key. The key stays in the terminal environment where Flask is running.
- Generated seed lists are saved as JSON in `outputs/` when the checkbox is enabled.
- Generated VPython scripts are saved as `.py` files in `outputs/` when the checkbox is enabled.
- To run a generated simulation, install VPython and run the downloaded script:

```bash
pip install vpython
python outputs/generated_file_name.py
```
