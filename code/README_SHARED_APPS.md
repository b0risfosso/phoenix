# Shared Data Setup

Both apps now use the same shared data folder.

Default shared folder, when both app folders are next to each other:

```text
../simulation_shared_data/
```

Recommended explicit setup:

```bash
export SIMULATION_SHARED_DATA_DIR="/Users/b/phoenix/code/simulation_shared_data"
```

Run the seed generator app on port 5000:

```bash
cd simulation_seed_generator_web_app
python app.py
```

Run the seed-to-VPython app on port 5001 in another terminal:

```bash
cd simulation_seed_to_vpython_web_app
python app.py
```

Generated seeds from the seed generator app will appear in the seed-to-VPython app because both use:

```text
$SIMULATION_SHARED_DATA_DIR/seeds/
```
