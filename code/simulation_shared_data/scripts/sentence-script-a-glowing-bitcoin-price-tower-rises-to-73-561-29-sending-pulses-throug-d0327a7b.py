"""
Seventy-Three Thousand Signal
A VPython simulation of a glowing Bitcoin price tower rising to $73,561.29,
sending pulses through miners, traders, wallets, and exchange nodes.

Run with:
    python seventy_three_thousand_signal.py

Requires:
    pip install vpython
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup: light styling
# -----------------------------
scene = canvas(
    title="Seventy-Three Thousand Signal — Bitcoin Network Pulse",
    width=1200,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 4.2, 0),
)
scene.forward = vector(-0.55, -0.35, -0.75)
scene.range = 16

# -----------------------------
# Colors
# -----------------------------
BTC_ORANGE = vector(1.0, 0.55, 0.04)
BTC_GOLD = vector(1.0, 0.78, 0.16)
SOFT_BLUE = vector(0.35, 0.55, 1.0)
SOFT_GREEN = vector(0.25, 0.75, 0.45)
SOFT_PURPLE = vector(0.62, 0.42, 0.95)
SOFT_RED = vector(0.95, 0.38, 0.30)
DARK_TEXT = vector(0.12, 0.14, 0.18)
GRID_COLOR = vector(0.73, 0.80, 0.88)

# -----------------------------
# Ground and grid
# -----------------------------
ground = box(
    pos=vector(0, -0.08, 0),
    size=vector(28, 0.08, 22),
    color=vector(0.90, 0.94, 0.98),
)

for x in range(-14, 15, 2):
    curve(
        pos=[vector(x, 0.01, -11), vector(x, 0.01, 11)],
        color=GRID_COLOR,
        radius=0.012,
    )
for z in range(-10, 11, 2):
    curve(
        pos=[vector(-14, 0.012, z), vector(14, 0.012, z)],
        color=GRID_COLOR,
        radius=0.012,
    )

# -----------------------------
# Price tower
# -----------------------------
TOWER_MAX_HEIGHT = 10.8
PRICE_TARGET = 73561.29

tower_base = cylinder(
    pos=vector(0, 0, 0),
    axis=vector(0, 0.35, 0),
    radius=1.25,
    color=vector(0.30, 0.32, 0.38),
)

tower = cylinder(
    pos=vector(0, 0.35, 0),
    axis=vector(0, 0.2, 0),
    radius=0.95,
    color=BTC_ORANGE,
    emissive=True,
)

inner_core = cylinder(
    pos=vector(0, 0.45, 0),
    axis=vector(0, 0.1, 0),
    radius=0.43,
    color=BTC_GOLD,
    emissive=True,
)

halo_rings = []
for i in range(6):
    r = ring(
        pos=vector(0, 0.4 + i * 1.55, 0),
        axis=vector(0, 1, 0),
        radius=1.28 + 0.08 * i,
        thickness=0.035,
        color=BTC_GOLD,
        emissive=True,
        opacity=0.45,
    )
    halo_rings.append(r)

price_label = label(
    pos=vector(0, 12.2, 0),
    text="$0.00\n#Bitcoin",
    height=26,
    color=vector(0.05, 0.06, 0.08),
    box=False,
    opacity=0,
)

status_label = label(
    pos=vector(-11.8, 8.8, 0),
    text="Network awaiting signal",
    height=15,
    color=DARK_TEXT,
    box=True,
    border=8,
    background=vector(1, 1, 1),
    opacity=0.7,
)

legend = label(
    pos=vector(10.5, 8.2, 0),
    text="Miners: blue\nTraders: red\nWallets: green\nExchanges: purple",
    height=13,
    color=DARK_TEXT,
    box=True,
    border=8,
    background=vector(1, 1, 1),
    opacity=0.72,
)

# -----------------------------
# Network nodes
# -----------------------------
node_groups = [
    ("Miner", SOFT_BLUE, 7, 7.0),
    ("Trader", SOFT_RED, 8, 9.0),
    ("Wallet", SOFT_GREEN, 12, 11.0),
    ("Exchange", SOFT_PURPLE, 5, 12.5),
]

nodes = []
connections = []
angle_offset = 0.0

for group_name, group_color, count, radius in node_groups:
    for i in range(count):
        angle = angle_offset + (2 * math.pi * i / count) + random.uniform(-0.10, 0.10)
        x = radius * math.cos(angle)
        z = radius * math.sin(angle)
        y = 0.34 + random.uniform(0, 0.55)
        n = sphere(
            pos=vector(x, y, z),
            radius=0.26 if group_name != "Exchange" else 0.36,
            color=group_color,
            emissive=True,
        )
        node_label = label(
            pos=n.pos + vector(0, 0.55, 0),
            text=group_name,
            height=9,
            color=DARK_TEXT,
            box=False,
            opacity=0,
        )
        nodes.append({
            "kind": group_name,
            "body": n,
            "base_pos": vector(x, y, z),
            "color": group_color,
            "label": node_label,
            "phase": random.uniform(0, 2 * math.pi),
            "energy": 0.15,
        })
        c = curve(
            pos=[vector(0, 0.38, 0), n.pos],
            color=vector(0.72, 0.78, 0.86),
            radius=0.018,
            opacity=0.26,
        )
        connections.append({"curve": c, "node": n, "base_radius": 0.018})
    angle_offset += math.pi / 5

# -----------------------------
# Decorative blockchain blocks
# -----------------------------
blocks = []
for i in range(12):
    b = box(
        pos=vector(-8.5 + i * 1.55, 0.35, -8.5),
        size=vector(0.95, 0.42, 0.65),
        color=vector(1.0, 0.83, 0.30),
        emissive=True,
        opacity=0.82,
    )
    blocks.append(b)
    if i > 0:
        curve(pos=[blocks[i - 1].pos, b.pos], color=BTC_GOLD, radius=0.045, opacity=0.50)

chain_label = label(
    pos=vector(0, 1.2, -8.5),
    text="Confirmed blocks carry the pulse beneath the market grid",
    height=12,
    color=DARK_TEXT,
    box=False,
    opacity=0,
)

# -----------------------------
# Pulses
# -----------------------------
pulses = []
MAX_PULSES = 70


def create_pulse(target_node, color, kind="network"):
    start_y = max(1.5, tower.axis.y * 0.84 + 0.35)
    start = vector(0, start_y, 0)
    pulse = sphere(
        pos=start,
        radius=0.12,
        color=color,
        emissive=True,
        opacity=0.95,
    )
    pulses.append({
        "body": pulse,
        "start": start,
        "target": target_node.pos,
        "age": 0.0,
        "life": random.uniform(1.4, 2.25),
        "kind": kind,
    })


def create_vertical_price_pulse(y):
    pulse = ring(
        pos=vector(0, y, 0),
        axis=vector(0, 1, 0),
        radius=1.05,
        thickness=0.035,
        color=BTC_GOLD,
        emissive=True,
        opacity=0.65,
    )
    pulses.append({
        "body": pulse,
        "start": vector(0, y, 0),
        "target": vector(0, y + 0.6, 0),
        "age": 0.0,
        "life": 0.85,
        "kind": "ring",
    })

# -----------------------------
# Controls
# -----------------------------
paused = False
speed_multiplier = 1.0
show_labels = True
show_connections = True
pulse_mode = True
manual_burst_requested = False

controls_text = label(
    pos=vector(0, -0.25, 10.8),
    text=(
        "Controls: SPACE pause | R reset | + / - speed | B burst | "
        "L labels | C connections | P pulses | arrow keys rotate view"
    ),
    height=12,
    color=DARK_TEXT,
    box=True,
    border=8,
    background=vector(1, 1, 1),
    opacity=0.70,
)


def reset_simulation():
    global t, price_fraction, price_value, pulse_timer, ring_timer, manual_burst_requested
    t = 0.0
    price_fraction = 0.0
    price_value = 0.0
    pulse_timer = 0.0
    ring_timer = 0.0
    manual_burst_requested = False
    tower.axis = vector(0, 0.2, 0)
    inner_core.axis = vector(0, 0.1, 0)
    tower.color = BTC_ORANGE
    inner_core.color = BTC_GOLD
    for p in pulses[:]:
        p["body"].visible = False
        pulses.remove(p)
    for node in nodes:
        node["energy"] = 0.15
        node["body"].radius = 0.26 if node["kind"] != "Exchange" else 0.36
        node["body"].pos = node["base_pos"]
        node["label"].pos = node["body"].pos + vector(0, 0.55, 0)
    status_label.text = "Network awaiting signal"


def keydown(evt):
    global paused, speed_multiplier, show_labels, show_connections, pulse_mode, manual_burst_requested
    k = evt.key
    if k == " ":
        paused = not paused
    elif k in ["r", "R"]:
        reset_simulation()
    elif k in ["+", "="]:
        speed_multiplier = min(3.0, speed_multiplier + 0.2)
    elif k in ["-", "_"]:
        speed_multiplier = max(0.2, speed_multiplier - 0.2)
    elif k in ["l", "L"]:
        show_labels = not show_labels
        for node in nodes:
            node["label"].visible = show_labels
    elif k in ["c", "C"]:
        show_connections = not show_connections
        for c in connections:
            c["curve"].visible = show_connections
    elif k in ["p", "P"]:
        pulse_mode = not pulse_mode
    elif k in ["b", "B"]:
        manual_burst_requested = True
    elif k == "left":
        scene.forward = rotate(scene.forward, angle=0.10, axis=vector(0, 1, 0))
    elif k == "right":
        scene.forward = rotate(scene.forward, angle=-0.10, axis=vector(0, 1, 0))
    elif k == "up":
        scene.forward = rotate(scene.forward, angle=0.08, axis=vector(1, 0, 0))
    elif k == "down":
        scene.forward = rotate(scene.forward, angle=-0.08, axis=vector(1, 0, 0))


scene.bind("keydown", keydown)

# -----------------------------
# Main animation
# -----------------------------
t = 0.0
price_fraction = 0.0
price_value = 0.0
pulse_timer = 0.0
ring_timer = 0.0

while True:
    rate(60)
    if paused:
        continue

    dt = 1.0 / 60.0 * speed_multiplier
    t += dt

    # Smooth rise toward the target price tower height.
    price_fraction = min(1.0, price_fraction + 0.0022 * speed_multiplier)
    eased = 1 - (1 - price_fraction) ** 3
    tower_height = 0.2 + eased * TOWER_MAX_HEIGHT
    price_value = eased * PRICE_TARGET

    tower.axis = vector(0, tower_height, 0)
    inner_core.axis = vector(0, max(0.1, tower_height * 0.97), 0)
    inner_core.pos = vector(0, 0.45, 0)

    glow = 0.55 + 0.45 * math.sin(t * 5.0) ** 2
    tower.color = BTC_ORANGE * glow + BTC_GOLD * (1 - glow) * 0.35
    inner_core.radius = 0.38 + 0.08 * math.sin(t * 6.2) ** 2

    price_label.pos = vector(0, tower_height + 1.4, 0)
    price_label.text = f"${price_value:,.2f}\n#Bitcoin"

    if price_fraction < 0.33:
        status_label.text = "Price tower forming: miners wake first"
    elif price_fraction < 0.66:
        status_label.text = "Network pressure rising: traders and wallets react"
    elif price_fraction < 1.0:
        status_label.text = "Signal nearing $73,561.29: exchanges brighten"
    else:
        status_label.text = "$73,561.29 reached: pulses circulate through the network"

    # Halo rings climb and expand around the tower.
    for i, hr in enumerate(halo_rings):
        y = 0.8 + ((t * 0.75 + i * 1.35) % max(2.0, tower_height + 1.4))
        hr.pos = vector(0, min(y, tower_height + 0.55), 0)
        hr.radius = 1.1 + 0.12 * i + 0.18 * math.sin(t * 1.8 + i)
        hr.opacity = 0.18 + 0.38 * price_fraction
        hr.visible = y < tower_height + 0.8

    # Nodes orbit slightly and react to energy.
    for idx, node in enumerate(nodes):
        body = node["body"]
        base = node["base_pos"]
        wobble = vector(
            0.16 * math.sin(t * 0.9 + node["phase"]),
            0.16 * math.sin(t * 1.4 + node["phase"]),
            0.16 * math.cos(t * 1.1 + node["phase"]),
        )
        body.pos = base + wobble
        node["energy"] *= 0.985
        base_radius = 0.26 if node["kind"] != "Exchange" else 0.36
        body.radius = base_radius + 0.20 * node["energy"]
        node["label"].pos = body.pos + vector(0, 0.55 + 0.16 * node["energy"], 0)
        node["label"].visible = show_labels

    # Connections brighten according to tower growth.
    for ci, con in enumerate(connections):
        con["curve"].clear()
        con["curve"].append(vector(0, 0.38 + tower_height * 0.05, 0))
        con["curve"].append(con["node"].pos)
        con["curve"].radius = 0.014 + 0.016 * price_fraction + 0.006 * math.sin(t * 3 + ci) ** 2
        con["curve"].opacity = 0.16 + 0.34 * price_fraction
        con["curve"].visible = show_connections

    # Blockchain blocks pulse in sequence.
    active_block = int((t * 1.8) % len(blocks))
    for i, b in enumerate(blocks):
        if i == active_block:
            b.size = vector(1.08, 0.55, 0.78)
            b.color = BTC_GOLD
        else:
            b.size = vector(0.95, 0.42, 0.65)
            b.color = vector(1.0, 0.80, 0.26)

    # Automatic and manual pulse creation.
    pulse_timer += dt
    ring_timer += dt
    pulse_interval = max(0.08, 0.48 - 0.32 * price_fraction)

    if pulse_mode and pulse_timer >= pulse_interval:
        pulse_timer = 0.0
        target = random.choice(nodes)["body"]
        create_pulse(target, BTC_GOLD if random.random() < 0.55 else BTC_ORANGE)

    if pulse_mode and ring_timer >= 0.95:
        ring_timer = 0.0
        create_vertical_price_pulse(random.uniform(0.9, max(1.1, tower_height)))

    if manual_burst_requested:
        manual_burst_requested = False
        for node in random.sample(nodes, min(18, len(nodes))):
            create_pulse(node["body"], BTC_GOLD)
        for yy in [1.2, 2.4, 3.6, 4.8, 6.0, 7.2]:
            create_vertical_price_pulse(min(yy, tower_height + 0.2))

    # Update moving pulses.
    for p in pulses[:]:
        p["age"] += dt
        u = p["age"] / p["life"]
        if u >= 1.0:
            if p["kind"] == "network":
                # deposit energy into the closest node
                closest_node = min(nodes, key=lambda n: mag(n["body"].pos - p["body"].pos))
                closest_node["energy"] = min(1.0, closest_node["energy"] + 0.6)
            p["body"].visible = False
            pulses.remove(p)
            continue

        if p["kind"] == "network":
            # Arc out from tower to node.
            start = p["start"]
            target = p["target"]
            mid_lift = vector(0, 1.8 * math.sin(math.pi * u), 0)
            p["body"].pos = start * (1 - u) + target * u + mid_lift
            p["body"].radius = 0.10 + 0.11 * math.sin(math.pi * u)
            p["body"].opacity = 0.95 * (1 - 0.45 * u)
        else:
            p["body"].radius = 1.05 + 3.8 * u
            p["body"].opacity = 0.65 * (1 - u)
            p["body"].pos = p["start"] + vector(0, 0.25 * math.sin(math.pi * u), 0)

    # Keep pulse count bounded for performance.
    while len(pulses) > MAX_PULSES:
        old = pulses.pop(0)
        old["body"].visible = False
