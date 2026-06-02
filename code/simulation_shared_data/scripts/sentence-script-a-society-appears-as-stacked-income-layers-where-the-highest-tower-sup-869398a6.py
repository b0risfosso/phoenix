"""
Progressive Tax Tower
A VPython simulation of stacked income layers supporting a glowing public grid.

Scene behavior:
- Society is shown as stacked income layers from the lower half to the top 1%.
- The highest tower sends the strongest contribution streams into the public grid.
- The lower half sends tiny sparks that visibly cost their household energy.
- A policy dial cycles between normal contribution and bottom-half relief.

Controls:
- SPACE: pause / resume
- R: reset simulation
- B: toggle bottom-half tax relief
- G: toggle public grid animation
- UP/DOWN: increase/decrease overall tax intensity
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup: light styling
# -----------------------------
scene = canvas(
    title="Progressive Tax Tower — stacked income layers supporting a public grid",
    width=1200,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 4.5, 0),
    forward=vector(-0.45, -0.28, -0.84),
    range=12,
)
scene.caption = (
    "SPACE pause/resume | R reset | B toggle bottom-half relief | "
    "G toggle grid animation | UP/DOWN change tax intensity\n"
)

# -----------------------------
# Global parameters
# -----------------------------
paused = False
bottom_half_relief = False
grid_animation = True
tax_intensity = 1.0
sim_time = 0.0

random.seed(8)

# -----------------------------
# Materials / colors
# -----------------------------
COLORS = {
    "ground": vector(0.86, 0.91, 0.94),
    "grid": vector(0.18, 0.52, 0.88),
    "grid_dim": vector(0.62, 0.78, 0.90),
    "top": vector(1.0, 0.64, 0.18),
    "upper": vector(0.50, 0.74, 0.95),
    "middle": vector(0.58, 0.78, 0.58),
    "lower": vector(0.82, 0.72, 0.98),
    "house": vector(0.96, 0.88, 0.66),
    "spark": vector(1.0, 0.80, 0.26),
    "relief": vector(0.38, 0.82, 0.72),
    "stress": vector(0.95, 0.32, 0.24),
}

# -----------------------------
# Data model: income layers
# share is visual contribution weight, stress_cost is household cost per unit
# -----------------------------
layers = [
    {"name": "Bottom 50%", "x": -6.0, "height": 1.4, "width": 2.8, "color": COLORS["lower"], "share": 0.03, "stress_cost": 1.00, "households": 16},
    {"name": "Next 40%", "x": -2.4, "height": 2.5, "width": 2.5, "color": COLORS["middle"], "share": 0.31, "stress_cost": 0.45, "households": 12},
    {"name": "Top 9%", "x": 1.2, "height": 4.1, "width": 2.2, "color": COLORS["upper"], "share": 0.26, "stress_cost": 0.18, "households": 8},
    {"name": "Top 1%", "x": 4.9, "height": 6.2, "width": 1.8, "color": COLORS["top"], "share": 0.40, "stress_cost": 0.08, "households": 4},
]

# -----------------------------
# World objects
# -----------------------------
base = box(pos=vector(0, -0.12, 0), size=vector(15.8, 0.18, 6.2), color=COLORS["ground"])
back_panel = box(pos=vector(0, 4.0, 2.9), size=vector(15.8, 8.8, 0.08), color=vector(0.90, 0.94, 0.98), opacity=0.45)

# Public grid platform
public_grid_y = 7.2
grid_nodes = []
grid_lines = []
for gx in range(-5, 6, 2):
    for gz in range(-2, 3, 2):
        node = sphere(pos=vector(gx, public_grid_y, gz), radius=0.12, color=COLORS["grid"], emissive=True)
        grid_nodes.append(node)

for gx in range(-5, 5, 2):
    for gz in range(-2, 3, 2):
        grid_lines.append(cylinder(pos=vector(gx, public_grid_y, gz), axis=vector(2, 0, 0), radius=0.025, color=COLORS["grid_dim"], opacity=0.8))
for gx in range(-5, 6, 2):
    for gz in range(-2, 2, 2):
        grid_lines.append(cylinder(pos=vector(gx, public_grid_y, gz), axis=vector(0, 0, 2), radius=0.025, color=COLORS["grid_dim"], opacity=0.8))

grid_label = label(
    pos=vector(0, public_grid_y + 0.65, 0),
    text="PUBLIC GRID",
    height=18,
    color=vector(0.13, 0.30, 0.46),
    box=False,
    opacity=0,
)

# Layer objects
layer_objects = []
for layer in layers:
    x = layer["x"]
    h = layer["height"]
    w = layer["width"]
    tower = box(pos=vector(x, h / 2, 0), size=vector(w, h, 2.1), color=layer["color"], opacity=0.88)
    cap = box(pos=vector(x, h + 0.08, 0), size=vector(w + 0.18, 0.16, 2.25), color=layer["color"], opacity=0.95)
    name_label = label(pos=vector(x, -0.55, 0), text=layer["name"], height=13, color=vector(0.18, 0.22, 0.26), box=False, opacity=0)
    share_label = label(pos=vector(x, h + 0.45, 0), text="", height=12, color=vector(0.18, 0.22, 0.26), box=False, opacity=0)
    layer_objects.append({"layer": layer, "tower": tower, "cap": cap, "name_label": name_label, "share_label": share_label})

# Household energy bars and small houses for each layer
household_groups = []
for layer in layers:
    houses = []
    bars = []
    count = layer["households"]
    rows = 2 if count > 8 else 1
    cols = math.ceil(count / rows)
    start_x = layer["x"] - (cols - 1) * 0.22
    for i in range(count):
        row = i // cols
        col = i % cols
        hx = start_x + col * 0.44
        hz = -2.45 - row * 0.42
        energy = 1.0
        home = box(pos=vector(hx, 0.13, hz), size=vector(0.23, 0.26, 0.23), color=COLORS["house"])
        roof = pyramid(pos=vector(hx, 0.32, hz), size=vector(0.30, 0.22, 0.30), color=vector(0.78, 0.55, 0.42))
        bar_bg = box(pos=vector(hx, 0.62, hz), size=vector(0.25, 0.035, 0.035), color=vector(0.75, 0.78, 0.80), opacity=0.5)
        bar = box(pos=vector(hx, 0.62, hz), size=vector(0.25, 0.04, 0.04), color=COLORS["relief"], emissive=True)
        houses.append({"home": home, "roof": roof, "bar_bg": bar_bg, "bar": bar, "energy": energy, "phase": random.random() * 6.28})
    household_groups.append({"layer": layer, "houses": houses})

# Contribution streams from towers to public grid
streams = []
for idx, layer in enumerate(layers):
    x = layer["x"]
    h = layer["height"]
    stream_count = 1 if idx == 0 else 2 if idx == 1 else 3 if idx == 2 else 5
    for s in range(stream_count):
        offset = (s - (stream_count - 1) / 2) * 0.28
        start = vector(x + offset, h + 0.2, 0.15 * math.sin(s))
        end = vector(x * 0.55 + offset, public_grid_y - 0.15, -0.3 + 0.28 * s)
        axis = end - start
        radius = 0.025 + 0.11 * layer["share"]
        c = cylinder(pos=start, axis=axis, radius=radius, color=layer["color"], opacity=0.42, emissive=True)
        streams.append({"layer": layer, "obj": c, "base_radius": radius, "start": start, "end": end, "phase": random.random() * 6.28})

# Moving sparks riding along streams
sparks = []
for stream in streams:
    layer = stream["layer"]
    # More sparks from higher contribution layers; bottom half has few tiny sparks
    n = max(2, int(3 + layer["share"] * 28))
    for _ in range(n):
        p = random.random()
        sp = sphere(pos=stream["start"] + (stream["end"] - stream["start"]) * p, radius=0.045 + 0.05 * layer["share"], color=COLORS["spark"], emissive=True, opacity=0.9)
        sparks.append({"layer": layer, "stream": stream, "obj": sp, "p": p, "speed": 0.18 + layer["share"] * 0.7 + random.random() * 0.12, "phase": random.random() * 6.28})

# Lower-half cost particles: tiny sparks leaving households with visible stress pings
cost_sparks = []
for _ in range(18):
    obj = sphere(pos=vector(-6, 0.4, -2.5), radius=0.035, color=COLORS["stress"], emissive=True, opacity=0)
    cost_sparks.append({"obj": obj, "age": 999, "life": 1.0, "start": vector(0, 0, 0), "target": vector(0, 0, 0), "phase": random.random() * 6.28})

# Floating policy lever / relief shield
relief_shield = box(pos=vector(-6.0, 1.2, 0), size=vector(3.5, 2.4, 2.6), color=COLORS["relief"], opacity=0.0)
policy_label = label(pos=vector(-6.0, 2.85, 0), text="", height=13, color=vector(0.10, 0.28, 0.26), box=False, opacity=0)

treasury = sphere(pos=vector(0, public_grid_y + 0.15, 0), radius=0.45, color=vector(0.35, 0.70, 1.0), emissive=True, opacity=0.55)
treasury_label = label(pos=vector(0, public_grid_y + 1.15, 0), text="Treasury glow", height=12, color=vector(0.13, 0.30, 0.46), box=False, opacity=0)

# Readout panel
readout = label(
    pos=vector(0, 8.9, -2.7),
    text="",
    height=13,
    color=vector(0.08, 0.12, 0.16),
    box=True,
    background=vector(1, 1, 1),
    opacity=0.55,
)

# -----------------------------
# Helper functions
# -----------------------------
def active_share(layer):
    if bottom_half_relief and layer["name"] == "Bottom 50%":
        return 0.0
    return layer["share"] * tax_intensity


def total_revenue_share():
    return sum(active_share(layer) for layer in layers)


def reset_simulation():
    global sim_time, bottom_half_relief, tax_intensity, paused
    sim_time = 0.0
    bottom_half_relief = False
    tax_intensity = 1.0
    paused = False
    for group in household_groups:
        for h in group["houses"]:
            h["energy"] = 1.0
            h["bar"].size.x = 0.25
            h["bar"].color = COLORS["relief"]
    for cs in cost_sparks:
        cs["age"] = 999
        cs["obj"].opacity = 0


def keydown(evt):
    global paused, bottom_half_relief, grid_animation, tax_intensity
    key = evt.key
    if key == " ":
        paused = not paused
    elif key in ("r", "R"):
        reset_simulation()
    elif key in ("b", "B"):
        bottom_half_relief = not bottom_half_relief
    elif key in ("g", "G"):
        grid_animation = not grid_animation
    elif key == "up":
        tax_intensity = min(1.8, tax_intensity + 0.1)
    elif key == "down":
        tax_intensity = max(0.2, tax_intensity - 0.1)

scene.bind("keydown", keydown)


def launch_cost_spark():
    if bottom_half_relief:
        return
    idle = None
    for cs in cost_sparks:
        if cs["age"] > cs["life"]:
            idle = cs
            break
    if idle is None:
        return
    bottom_group = household_groups[0]
    h = random.choice(bottom_group["houses"])
    start = h["home"].pos + vector(0, 0.35, 0)
    target = vector(layers[0]["x"] + random.uniform(-0.7, 0.7), layers[0]["height"] + 0.25, random.uniform(-0.8, 0.8))
    idle["start"] = start
    idle["target"] = target
    idle["age"] = 0.0
    idle["life"] = random.uniform(0.8, 1.25)
    idle["obj"].radius = random.uniform(0.025, 0.045)
    idle["obj"].opacity = 0.85
    idle["obj"].pos = start


def update_households(dt):
    for group in household_groups:
        layer = group["layer"]
        contribution = active_share(layer)
        cost = contribution * layer["stress_cost"]
        for h in group["houses"]:
            # Energy drains with contribution cost, recovers slowly from wages/relief.
            recovery = 0.035 if layer["name"] != "Bottom 50%" else (0.080 if bottom_half_relief else 0.045)
            drain = 0.030 * cost
            h["energy"] += (recovery - drain) * dt
            h["energy"] += 0.005 * math.sin(sim_time * 2.0 + h["phase"])
            h["energy"] = max(0.08, min(1.0, h["energy"]))
            width = 0.25 * h["energy"]
            h["bar"].size.x = width
            h["bar"].pos.x = h["bar_bg"].pos.x - 0.125 + width / 2
            if h["energy"] < 0.35:
                h["bar"].color = COLORS["stress"]
            elif h["energy"] < 0.65:
                h["bar"].color = vector(1.0, 0.72, 0.26)
            else:
                h["bar"].color = COLORS["relief"]
            h["home"].opacity = 0.55 + 0.45 * h["energy"]
            h["roof"].opacity = 0.55 + 0.45 * h["energy"]


def update_streams(dt):
    total = total_revenue_share()
    for stream in streams:
        layer = stream["layer"]
        contribution = active_share(layer)
        pulse = 0.75 + 0.25 * math.sin(sim_time * 4.0 + stream["phase"])
        stream["obj"].radius = max(0.006, stream["base_radius"] * (0.25 + pulse * (0.45 + contribution * 1.8)))
        stream["obj"].opacity = 0.08 if contribution == 0 else min(0.82, 0.25 + contribution * 1.4)
        if contribution == 0:
            stream["obj"].color = COLORS["relief"]
        else:
            stream["obj"].color = layer["color"]

    for sp in sparks:
        contribution = active_share(sp["layer"])
        if contribution <= 0:
            sp["obj"].opacity = 0.0
            continue
        sp["obj"].opacity = min(1.0, 0.32 + contribution * 1.6)
        sp["p"] += dt * sp["speed"] * (0.4 + contribution * 1.4)
        if sp["p"] > 1.0:
            sp["p"] -= 1.0
        start = sp["stream"]["start"]
        end = sp["stream"]["end"]
        wobble = vector(0.05 * math.sin(sim_time * 5 + sp["phase"]), 0, 0.05 * math.cos(sim_time * 4 + sp["phase"]))
        sp["obj"].pos = start + (end - start) * sp["p"] + wobble
        sp["obj"].radius = 0.025 + 0.11 * contribution

    # Treasury and public grid brighten with total revenue.
    treasury.radius = 0.34 + 0.38 * total
    treasury.opacity = min(0.85, 0.30 + 0.65 * total)
    treasury.color = vector(0.22 + 0.30 * total, 0.62 + 0.25 * total, 1.0)


def update_grid(dt):
    total = total_revenue_share()
    for i, node in enumerate(grid_nodes):
        pulse = 0.5 + 0.5 * math.sin(sim_time * 3.2 + i * 0.57)
        if grid_animation:
            node.radius = 0.08 + 0.09 * total + 0.035 * pulse
            node.color = vector(0.18 + 0.24 * pulse, 0.46 + 0.25 * total, 0.82 + 0.12 * pulse)
        else:
            node.radius = 0.10 + 0.05 * total
    for i, line in enumerate(grid_lines):
        pulse = 0.5 + 0.5 * math.sin(sim_time * 2.4 + i)
        line.radius = 0.018 + 0.030 * total + (0.010 * pulse if grid_animation else 0)
        line.opacity = 0.35 + 0.55 * min(1.0, total)


def update_cost_sparks(dt):
    # Cost sparks show lower-half contribution: small but visibly extracted from household energy.
    if (not bottom_half_relief) and random.random() < 0.25:
        launch_cost_spark()
    for cs in cost_sparks:
        cs["age"] += dt
        if cs["age"] <= cs["life"]:
            p = cs["age"] / cs["life"]
            arc = vector(0, 0.45 * math.sin(math.pi * p), 0)
            cs["obj"].pos = cs["start"] + (cs["target"] - cs["start"]) * p + arc
            cs["obj"].opacity = 0.9 * (1 - p)
        else:
            cs["obj"].opacity = 0


def update_labels():
    total = total_revenue_share()
    for lo in layer_objects:
        layer = lo["layer"]
        contribution = active_share(layer)
        lo["share_label"].text = f"flow {contribution*100:.1f}%"
        if contribution == 0:
            lo["share_label"].color = COLORS["relief"]
        else:
            lo["share_label"].color = vector(0.18, 0.22, 0.26)
    relief_shield.opacity = 0.18 if bottom_half_relief else 0.0
    policy_label.text = "BOTTOM HALF RELIEF ON" if bottom_half_relief else "lower half still sends tiny costly sparks"
    policy_label.color = COLORS["relief"] if bottom_half_relief else COLORS["stress"]
    readout.text = (
        f"Progressivity dial: {tax_intensity:.1f}x\n"
        f"Total visible revenue flow: {total*100:.1f}%\n"
        f"Bottom-half contribution: {active_share(layers[0])*100:.1f}%\n"
        f"Mode: {'bottom-half taxes zeroed' if bottom_half_relief else 'baseline contribution'}"
    )


def update_towers(dt):
    for lo in layer_objects:
        layer = lo["layer"]
        contribution = active_share(layer)
        tremor = 0.02 * math.sin(sim_time * (2.0 + contribution * 6.0) + layer["x"])
        lo["tower"].pos.x = layer["x"] + tremor
        lo["cap"].pos.x = layer["x"] + tremor
        # Higher support layers glow more; bottom half dims under relief.
        glow = min(1.0, 0.45 + contribution * 1.5)
        if contribution == 0:
            lo["tower"].color = COLORS["relief"]
            lo["tower"].opacity = 0.35
            lo["cap"].opacity = 0.40
        else:
            lo["tower"].color = layer["color"] * glow + vector(1, 1, 1) * (1 - glow) * 0.25
            lo["tower"].opacity = 0.72 + min(0.2, contribution)
            lo["cap"].opacity = 0.82 + min(0.15, contribution)

# -----------------------------
# Main animation loop
# -----------------------------
dt = 1 / 60
while True:
    rate(60)
    if paused:
        continue
    sim_time += dt
    update_households(dt)
    update_streams(dt)
    update_grid(dt)
    update_cost_sparks(dt)
    update_towers(dt)
    update_labels()
