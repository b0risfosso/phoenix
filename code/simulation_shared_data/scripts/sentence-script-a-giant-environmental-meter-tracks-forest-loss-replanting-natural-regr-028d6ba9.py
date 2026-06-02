"""
Zero Deforestation Gauge
A VPython simulation of a giant environmental meter tracking forest loss,
replanting, natural regrowth, and protection strength while holding the
deforestation needle close to zero.

Run with:
    python zero_deforestation_gauge.py

Controls:
    Space  : pause / resume
    L      : add a short forest-loss pressure spike
    R      : trigger extra replanting
    P      : strengthen protection
    N      : encourage natural regrowth
    C      : reset the simulation
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup: light styling
# -----------------------------
scene.title = "Zero Deforestation Gauge"
scene.width = 1180
scene.height = 760
scene.background = vector(0.88, 0.94, 0.98)
scene.center = vector(0, 0.6, 0)
scene.range = 11.5
scene.forward = vector(0, -0.25, -1)

# VPython HTML caption
scene.caption = """
<b>Zero Deforestation Gauge</b><br>
A giant environmental meter tracks forest loss, replanting, natural regrowth, and protection strength.<br>
Controls: <b>Space</b> pause/resume | <b>L</b> loss spike | <b>R</b> replant | <b>P</b> protect | <b>N</b> regrow | <b>C</b> reset<br><br>
"""

# -----------------------------
# Colors
# -----------------------------
GREEN = vector(0.12, 0.55, 0.20)
LIGHT_GREEN = vector(0.35, 0.78, 0.32)
DARK_GREEN = vector(0.05, 0.34, 0.12)
BROWN = vector(0.46, 0.26, 0.10)
TAN = vector(0.78, 0.65, 0.45)
RED = vector(0.92, 0.20, 0.16)
ORANGE = vector(0.95, 0.52, 0.16)
BLUE = vector(0.16, 0.42, 0.82)
CYAN = vector(0.22, 0.72, 0.85)
PURPLE = vector(0.45, 0.30, 0.78)
GRAY = vector(0.54, 0.58, 0.60)
DARK = vector(0.10, 0.13, 0.16)
WHITE = vector(1, 1, 1)

# -----------------------------
# Utility functions
# -----------------------------
def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def lerp(a, b, t):
    return a + (b - a) * t


def make_text(txt, pos, height=0.32, color=DARK, align="center", billboard=False):
    return label(
        text=txt,
        pos=pos,
        height=height,
        color=color,
        box=False,
        opacity=0,
        align=align,
        billboard=billboard,
    )


def make_tree(x, z, scale=1.0, mature=True):
    trunk_h = 0.45 * scale if mature else 0.24 * scale
    trunk_r = 0.055 * scale if mature else 0.035 * scale
    crown_r = 0.28 * scale if mature else 0.16 * scale
    y_base = -2.15
    trunk = cylinder(
        pos=vector(x, y_base, z),
        axis=vector(0, trunk_h, 0),
        radius=trunk_r,
        color=BROWN,
    )
    crown_color = GREEN if mature else LIGHT_GREEN
    crown = cone(
        pos=vector(x, y_base + trunk_h * 0.72, z),
        axis=vector(0, crown_r * 1.8, 0),
        radius=crown_r,
        color=crown_color,
    )
    crown2 = cone(
        pos=vector(x, y_base + trunk_h * 0.72 + crown_r * 0.65, z),
        axis=vector(0, crown_r * 1.45, 0),
        radius=crown_r * 0.78,
        color=crown_color * 0.95,
    )
    return {"trunk": trunk, "crown": crown, "crown2": crown2, "age": 1.0 if mature else 0.0, "x": x, "z": z}


def set_tree_visible(tree, visible):
    tree["trunk"].visible = visible
    tree["crown"].visible = visible
    tree["crown2"].visible = visible


def grow_tree(tree, dt, rate):
    if tree["age"] >= 1.0:
        return
    tree["age"] = clamp(tree["age"] + dt * rate, 0, 1)
    age = tree["age"]
    s = 0.45 + 0.55 * age
    tree["trunk"].axis = vector(0, 0.45 * s, 0)
    tree["trunk"].radius = 0.055 * s
    tree["crown"].axis = vector(0, 0.50 * s, 0)
    tree["crown"].radius = 0.18 + 0.10 * age
    tree["crown2"].axis = vector(0, 0.40 * s, 0)
    tree["crown2"].radius = 0.12 + 0.10 * age
    new_color = LIGHT_GREEN * (1 - age) + GREEN * age
    tree["crown"].color = new_color
    tree["crown2"].color = new_color * 0.95

# -----------------------------
# Ground / map base
# -----------------------------
ground = box(pos=vector(0, -2.22, 0), size=vector(14.5, 0.10, 6.2), color=vector(0.72, 0.88, 0.64))
map_panel = box(pos=vector(0, -2.28, 0), size=vector(14.9, 0.06, 6.6), color=vector(0.58, 0.76, 0.50))
river = curve(color=vector(0.32, 0.62, 0.86), radius=0.055)
for i in range(90):
    x = -7.0 + i * 14.0 / 89
    z = 1.25 * math.sin(i * 0.19) - 0.45 * math.sin(i * 0.055)
    river.append(vector(x, -2.13, z))

# Protected region rings use ring(), not torus().
protected_rings = []
for x, z, rx, rz in [(-4.6, -0.8, 1.9, 1.25), (-0.8, 1.25, 1.55, 1.05), (3.8, -0.55, 2.05, 1.35)]:
    r = ring(pos=vector(x, -2.03, z), axis=vector(0, 1, 0), radius=rx, thickness=0.035, color=BLUE, opacity=0.35)
    protected_rings.append(r)
    # A second perpendicular ring gives the protected zone a visible footprint.
    r2 = ring(pos=vector(x, -2.028, z), axis=vector(0, 1, 0), radius=rz, thickness=0.025, color=CYAN, opacity=0.28)
    protected_rings.append(r2)

# -----------------------------
# Forest grid
# -----------------------------
random.seed(11)
trees = []
stumps = []
seedlings = []

for row in range(7):
    for col in range(17):
        x = -6.5 + col * 0.82 + random.uniform(-0.16, 0.16)
        z = -2.55 + row * 0.82 + random.uniform(-0.16, 0.16)
        if abs(z - (1.25 * math.sin((x + 7.0) * 0.19 * 89 / 14.0))) < 0.26:
            continue
        scale = random.uniform(0.78, 1.18)
        trees.append(make_tree(x, z, scale=scale, mature=True))

for _ in range(14):
    x = random.uniform(-6.6, 6.6)
    z = random.uniform(-2.5, 2.5)
    stump = cylinder(pos=vector(x, -2.12, z), axis=vector(0, 0.12, 0), radius=0.09, color=TAN, visible=False)
    stumps.append({"obj": stump, "timer": 0})

# -----------------------------
# Gauge construction
# -----------------------------
gauge_center = vector(0, 3.0, 0)
gauge_radius = 3.0

back = cylinder(pos=gauge_center + vector(0, 0, -0.08), axis=vector(0, 0, 0.08), radius=3.35, color=WHITE, opacity=0.98)
rim = ring(pos=gauge_center, axis=vector(0, 0, 1), radius=3.12, thickness=0.055, color=GRAY)
inner_rim = ring(pos=gauge_center + vector(0, 0, 0.01), axis=vector(0, 0, 1), radius=2.47, thickness=0.025, color=vector(0.72, 0.76, 0.78))

# Arc segments showing danger / zero zone / restoration.
arc_segments = []
arc_specs = [
    (-145, -92, RED),
    (-92, -35, ORANGE),
    (-35, 35, LIGHT_GREEN),
    (35, 92, BLUE),
    (92, 145, PURPLE),
]
for start_deg, end_deg, col in arc_specs:
    steps = 26
    c = curve(color=col, radius=0.09)
    for i in range(steps + 1):
        a = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        c.append(gauge_center + vector(gauge_radius * math.sin(a), gauge_radius * math.cos(a), 0.08))
    arc_segments.append(c)

# Tick marks and labels.
for deg, text_value in [(-140, "LOSS"), (-70, "RISK"), (0, "ZERO"), (70, "REPAIR"), (140, "PROTECT")]:
    a = math.radians(deg)
    outer = gauge_center + vector(gauge_radius * math.sin(a), gauge_radius * math.cos(a), 0.12)
    inner = gauge_center + vector((gauge_radius - 0.32) * math.sin(a), (gauge_radius - 0.32) * math.cos(a), 0.12)
    curve(pos=[inner, outer], color=DARK, radius=0.025)
    make_text(text_value, gauge_center + vector((gauge_radius + 0.52) * math.sin(a), (gauge_radius + 0.52) * math.cos(a), 0.15), height=0.22, color=DARK)

make_text("ZERO DEFORESTATION GAUGE", gauge_center + vector(0, 3.85, 0.12), height=0.34, color=DARK)
make_text("forest loss balanced by replanting, regrowth, and protection", gauge_center + vector(0, -3.55, 0.12), height=0.20, color=vector(0.22, 0.25, 0.28))

needle_base = sphere(pos=gauge_center + vector(0, 0, 0.22), radius=0.19, color=DARK)
needle = cylinder(pos=gauge_center + vector(0, 0, 0.18), axis=vector(0, 2.35, 0), radius=0.045, color=RED)
needle_tip = cone(pos=gauge_center + vector(0, 2.20, 0.18), axis=vector(0, 0.42, 0), radius=0.13, color=RED)
zero_marker = cylinder(pos=gauge_center + vector(0, 0, 0.10), axis=vector(0, 2.80, 0), radius=0.012, color=LIGHT_GREEN, opacity=0.55)

# -----------------------------
# Metric bars
# -----------------------------
bar_origin = vector(-7.2, 2.05, 0)
bar_gap = 0.55
metrics = {
    "loss": {"label": "Forest loss pressure", "color": RED, "value": 0.11},
    "replant": {"label": "Replanting effort", "color": LIGHT_GREEN, "value": 0.54},
    "regrowth": {"label": "Natural regrowth", "color": GREEN, "value": 0.47},
    "protection": {"label": "Protection strength", "color": BLUE, "value": 0.62},
}
bar_objs = {}
for idx, key in enumerate(metrics):
    y = bar_origin.y - idx * bar_gap
    make_text(metrics[key]["label"], vector(bar_origin.x, y + 0.05, 0.2), height=0.18, color=DARK, align="left")
    bg = box(pos=vector(bar_origin.x + 2.15, y, 0.05), size=vector(2.55, 0.16, 0.05), color=vector(0.82, 0.86, 0.84))
    fg = box(pos=vector(bar_origin.x + 0.88, y, 0.10), size=vector(0.08, 0.20, 0.08), color=metrics[key]["color"])
    val_label = make_text("0%", vector(bar_origin.x + 3.55, y - 0.04, 0.18), height=0.17, color=DARK, align="left")
    bar_objs[key] = {"fg": fg, "label": val_label}

status_label = make_text("Deforestation needle: near zero", vector(0, -3.55, 0), height=0.28, color=DARK)
score_label = make_text("", vector(4.0, 2.2, 0.1), height=0.25, color=DARK, align="left")

# -----------------------------
# Flow particles between systems and gauge
# -----------------------------
particles = []
flow_specs = [
    (vector(-5.9, -1.8, 0.25), vector(-1.2, 1.1, 0.25), RED, "loss"),
    (vector(-2.6, -1.9, 0.25), vector(-0.5, 1.2, 0.25), LIGHT_GREEN, "replant"),
    (vector(1.6, -2.0, 0.25), vector(0.5, 1.2, 0.25), GREEN, "regrowth"),
    (vector(5.4, -1.75, 0.25), vector(1.2, 1.1, 0.25), BLUE, "protection"),
]
for i in range(52):
    start, end, col, key = random.choice(flow_specs)
    p = sphere(pos=start, radius=random.uniform(0.035, 0.065), color=col, opacity=0.78)
    particles.append({"obj": p, "start": start, "end": end, "color": col, "key": key, "phase": random.random(), "speed": random.uniform(0.16, 0.42)})

# -----------------------------
# Simulation state
# -----------------------------
paused = False
time_value = 0.0
loss_spike_timer = 0.0
extra_replant_timer = 0.0
extra_protect_timer = 0.0
extra_regrowth_timer = 0.0
needle_angle = 0.0


def reset_simulation():
    global time_value, loss_spike_timer, extra_replant_timer, extra_protect_timer, extra_regrowth_timer, needle_angle
    time_value = 0.0
    loss_spike_timer = 0.0
    extra_replant_timer = 0.0
    extra_protect_timer = 0.0
    extra_regrowth_timer = 0.0
    needle_angle = 0.0
    metrics["loss"]["value"] = 0.11
    metrics["replant"]["value"] = 0.54
    metrics["regrowth"]["value"] = 0.47
    metrics["protection"]["value"] = 0.62
    for tree in trees:
        set_tree_visible(tree, True)
        tree["age"] = 1.0
        tree["crown"].color = GREEN
        tree["crown2"].color = GREEN * 0.95
    for stump in stumps:
        stump["obj"].visible = False
        stump["timer"] = 0
    for sapling in seedlings:
        set_tree_visible(sapling, False)
    seedlings.clear()


def keydown(evt):
    global paused, loss_spike_timer, extra_replant_timer, extra_protect_timer, extra_regrowth_timer
    k = evt.key.lower()
    if k == " ":
        paused = not paused
    elif k == "l":
        loss_spike_timer = 5.0
    elif k == "r":
        extra_replant_timer = 6.0
    elif k == "p":
        extra_protect_timer = 6.0
    elif k == "n":
        extra_regrowth_timer = 6.0
    elif k == "c":
        reset_simulation()

scene.bind("keydown", keydown)


def update_bar(key):
    val = clamp(metrics[key]["value"], 0, 1)
    width = 2.55 * val
    fg = bar_objs[key]["fg"]
    fg.size.x = max(0.04, width)
    fg.pos.x = bar_origin.x + 0.88 + width / 2
    bar_objs[key]["label"].text = f"{int(val * 100):02d}%"


def update_needle(target_score, dt):
    global needle_angle
    # target_score is roughly -1 loss through +1 restoration/protection.
    target_angle = clamp(target_score, -1, 1) * math.radians(90)
    needle_angle += (target_angle - needle_angle) * min(1, dt * 2.8)
    axis = vector(2.35 * math.sin(needle_angle), 2.35 * math.cos(needle_angle), 0)
    needle.axis = axis
    needle.color = LIGHT_GREEN if abs(math.degrees(needle_angle)) < 12 else (ORANGE if abs(math.degrees(needle_angle)) < 42 else RED)
    needle_tip.pos = needle.pos + axis * 0.94
    needle_tip.axis = norm(axis) * 0.42
    needle_tip.color = needle.color


def damage_one_tree():
    visible_trees = [t for t in trees if t["trunk"].visible]
    if not visible_trees:
        return
    tree = random.choice(visible_trees)
    set_tree_visible(tree, False)
    hidden_stumps = [s for s in stumps if not s["obj"].visible]
    if hidden_stumps:
        stump = random.choice(hidden_stumps)
        stump["obj"].pos = vector(tree["x"], -2.12, tree["z"])
        stump["obj"].visible = True
        stump["timer"] = 9.0


def plant_seedling():
    # Prefer recovering a stump location. Otherwise plant in open forest.
    visible_stumps = [s for s in stumps if s["obj"].visible]
    if visible_stumps:
        s = random.choice(visible_stumps)
        x, z = s["obj"].pos.x + random.uniform(-0.08, 0.08), s["obj"].pos.z + random.uniform(-0.08, 0.08)
        s["obj"].visible = False
        s["timer"] = 0
    else:
        x, z = random.uniform(-6.7, 6.7), random.uniform(-2.55, 2.55)
    sapling = make_tree(x, z, scale=random.uniform(0.65, 0.9), mature=False)
    seedlings.append(sapling)


def pulse_protected_zones(strength):
    for i, r in enumerate(protected_rings):
        phase = time_value * 2.2 + i * 0.8
        r.opacity = 0.22 + 0.38 * strength + 0.08 * math.sin(phase)
        r.thickness = 0.022 + 0.035 * strength + 0.008 * math.sin(phase * 1.3)
        r.color = BLUE * (0.70 + 0.25 * strength) + CYAN * 0.25

# -----------------------------
# Main loop
# -----------------------------
dt = 0.025
while True:
    rate(40)
    if paused:
        continue

    time_value += dt

    if loss_spike_timer > 0:
        loss_spike_timer -= dt
    if extra_replant_timer > 0:
        extra_replant_timer -= dt
    if extra_protect_timer > 0:
        extra_protect_timer -= dt
    if extra_regrowth_timer > 0:
        extra_regrowth_timer -= dt

    seasonal = 0.5 + 0.5 * math.sin(time_value * 0.45)
    enforcement_wave = 0.5 + 0.5 * math.sin(time_value * 0.33 + 1.2)

    # Loss pressure is real but small; protection and restoration push it back.
    target_loss = 0.11 + 0.035 * seasonal
    if loss_spike_timer > 0:
        target_loss += 0.30 * (loss_spike_timer / 5.0)

    target_replant = 0.54 + 0.12 * math.sin(time_value * 0.38 + 0.4)
    if extra_replant_timer > 0:
        target_replant += 0.28 * (extra_replant_timer / 6.0)

    target_regrowth = 0.48 + 0.12 * math.sin(time_value * 0.30 + 2.0)
    if extra_regrowth_timer > 0:
        target_regrowth += 0.25 * (extra_regrowth_timer / 6.0)

    target_protection = 0.62 + 0.10 * enforcement_wave
    if extra_protect_timer > 0:
        target_protection += 0.24 * (extra_protect_timer / 6.0)

    for key, target in [
        ("loss", target_loss),
        ("replant", target_replant),
        ("regrowth", target_regrowth),
        ("protection", target_protection),
    ]:
        metrics[key]["value"] = lerp(metrics[key]["value"], clamp(target, 0, 1), dt * 1.4)
        update_bar(key)

    loss = metrics["loss"]["value"]
    replant = metrics["replant"]["value"]
    regrowth = metrics["regrowth"]["value"]
    protection = metrics["protection"]["value"]

    # Zero-deforestation balance: restoration and protection offset forest-loss pressure.
    offset_power = 0.40 * replant + 0.34 * regrowth + 0.42 * protection
    net_deforestation = clamp(loss - offset_power, -0.45, 0.55)
    gauge_score = -net_deforestation * 1.8
    update_needle(gauge_score, dt)

    # Visible ecological effects.
    if random.random() < dt * (0.16 + 0.55 * loss) and loss > 0.18:
        damage_one_tree()
    if random.random() < dt * (0.22 + 0.95 * replant):
        plant_seedling()
    for tree in seedlings:
        grow_tree(tree, dt, 0.10 + 0.22 * regrowth)
    if len(seedlings) > 80:
        old = seedlings.pop(0)
        # Convert old seedling into a persistent mature tree with low object growth overhead.
        old["age"] = 1.0
        trees.append(old)

    for stump in stumps:
        if stump["obj"].visible:
            stump["timer"] -= dt * (0.45 + regrowth)
            stump["obj"].opacity = clamp(stump["timer"] / 9.0, 0.18, 1.0)
            if stump["timer"] <= 0:
                stump["obj"].visible = False
                plant_seedling()

    pulse_protected_zones(protection)

    # Animate information/effort particles flowing into the gauge.
    for p in particles:
        speed_boost = 0.3 + metrics[p["key"]]["value"]
        p["phase"] = (p["phase"] + dt * p["speed"] * speed_boost) % 1.0
        q = p["phase"]
        start, end = p["start"], p["end"]
        curve_lift = vector(0, 1.1 * math.sin(math.pi * q), 0)
        wiggle = vector(0.0, 0.0, 0.15 * math.sin(time_value * 4 + q * 8))
        p["obj"].pos = start * (1 - q) + end * q + curve_lift + wiggle
        p["obj"].opacity = 0.35 + 0.5 * math.sin(math.pi * q)
        p["obj"].radius = 0.025 + 0.045 * metrics[p["key"]]["value"]

    # Labels and status.
    net_percent = net_deforestation * 100
    if abs(net_percent) < 4:
        status = "Deforestation needle: near zero"
        status_col = GREEN
    elif net_percent > 0:
        status = "Loss pressure rising: restoration response needed"
        status_col = ORANGE
    else:
        status = "Forest recovery surplus: regrowth expanding"
        status_col = BLUE
    status_label.text = status
    status_label.color = status_col
    score_label.text = (
        f"Net deforestation pressure: {net_percent:+.1f}%\n"
        f"Offset power: {offset_power * 100:.1f}%\n"
        f"Protected zones: {int(protection * 100)}%\n"
        f"Living trees displayed: {sum(1 for t in trees if t['trunk'].visible) + len(seedlings)}"
    )

    # Gentle map breathing to show living forest system.
    ground.color = vector(0.68, 0.84, 0.59) * (0.97 + 0.03 * math.sin(time_value * 0.55))
