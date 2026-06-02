"""
Septillion Market Engine - fixed / optimized VPython version

A vast economy appears as a living machine of glowing trade routes, with currencies,
goods, labor, energy, and information flowing between millions of moving nodes.

Fix notes:
- The original version could freeze right after object initialization because it created
  too many trail-enabled moving packets and updated many curve properties every frame.
- This version keeps the same visual idea but uses a lighter visible sample, no automatic
  packet trails, precomputed route connectivity, and slower UI/stat updates.

Run:
    python septillion_market_engine_fixed.py
"""

from vpython import *
import math
import random
import time

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Septillion Market Engine - fixed",
    width=1280,
    height=760,
    background=vector(0.94, 0.96, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.42, -0.24, -1.0)
scene.range = 28

random.seed(12)

# -----------------------------
# Configuration - deliberately moderate for VPython stability
# -----------------------------
CLUSTER_COUNT = 9
NODES_PER_CLUSTER = 12
VISIBLE_NODE_COUNT = CLUSTER_COUNT * NODES_PER_CLUSTER
ROUTE_COUNT = 46
PACKET_COUNT = 120

FLOW_TYPES = {
    "currency": {"color": vector(1.00, 0.78, 0.20), "radius": 0.115, "speed": 0.021, "value": 7.0},
    "goods": {"color": vector(0.18, 0.58, 1.00), "radius": 0.125, "speed": 0.015, "value": 4.0},
    "labor": {"color": vector(0.78, 0.34, 1.00), "radius": 0.110, "speed": 0.013, "value": 3.5},
    "energy": {"color": vector(1.00, 0.24, 0.12), "radius": 0.135, "speed": 0.027, "value": 8.5},
    "information": {"color": vector(0.10, 0.88, 0.62), "radius": 0.090, "speed": 0.034, "value": 5.2},
}
FLOW_NAMES = list(FLOW_TYPES.keys())

# -----------------------------
# Helpers
# -----------------------------
def clamp(x, low, high):
    return max(low, min(high, x))


def lerp(a, b, t):
    return a * (1.0 - t) + b * t


def unit_or_zero(v):
    m = mag(v)
    if m <= 1e-9:
        return vector(0, 0, 0)
    return v / m


def random_perpendicular(v):
    base_axis = unit_or_zero(v)
    axis = cross(base_axis, vector(0, 1, 0))
    if mag(axis) < 0.01:
        axis = cross(base_axis, vector(1, 0, 0))
    axis = unit_or_zero(axis)
    return rotate(axis, angle=random.uniform(0, 2 * math.pi), axis=base_axis)


def bezier_point(pa, control, pb, t):
    return lerp(lerp(pa, control, t), lerp(control, pb, t), t)

# -----------------------------
# Cluster layout
# -----------------------------
cluster_labels = [
    "Currency", "Goods", "Labor", "Energy", "Information",
    "Industry", "Housing", "Food", "Compute"
]
cluster_centers = []
for i in range(CLUSTER_COUNT):
    angle = 2 * math.pi * i / CLUSTER_COUNT
    radius = 15.5 + 1.8 * math.sin(i * 1.7)
    y = 4.0 * math.sin(i * 2.3)
    cluster_centers.append(vector(radius * math.cos(angle), y, radius * math.sin(angle)))

# Central engine
core = sphere(pos=vector(0, 0, 0), radius=2.18, color=vector(1.0, 0.82, 0.25), emissive=True)
core_shell = sphere(pos=vector(0, 0, 0), radius=3.20, color=vector(0.35, 0.72, 1.0), opacity=0.12)
core_ring_a = ring(pos=vector(0, 0, 0), axis=vector(0, 1, 0), radius=4.0, thickness=0.045, color=vector(1.0, 0.75, 0.25), opacity=0.55)
core_ring_b = ring(pos=vector(0, 0, 0), axis=vector(1, 0.15, 0), radius=4.7, thickness=0.04, color=vector(0.15, 0.75, 1.0), opacity=0.45)
core_ring_c = ring(pos=vector(0, 0, 0), axis=vector(0.2, 0, 1), radius=5.35, thickness=0.035, color=vector(0.25, 1.0, 0.68), opacity=0.38)

# -----------------------------
# Nodes
# -----------------------------
nodes = []
node_visuals = []
node_ledgers = []
node_cluster_id = []
node_base_offsets = []

for c, center in enumerate(cluster_centers):
    ring(pos=center, axis=unit_or_zero(center), radius=2.75, thickness=0.035, color=vector(0.55, 0.70, 1.0), opacity=0.22)
    label(
        pos=center + vector(0, 3.25, 0),
        text=cluster_labels[c],
        height=9,
        box=False,
        opacity=0,
        color=vector(0.10, 0.14, 0.22),
    )

    tangent = unit_or_zero(cross(center, vector(0, 1, 0)))
    if mag(tangent) < 0.01:
        tangent = vector(1, 0, 0)
    normal = unit_or_zero(center)
    binormal = unit_or_zero(cross(normal, tangent))

    for j in range(NODES_PER_CLUSTER):
        local_angle = 2 * math.pi * j / NODES_PER_CLUSTER + random.uniform(-0.20, 0.20)
        local_r = random.uniform(0.65, 2.35)
        local_y = random.uniform(-1.10, 1.10)
        offset = tangent * (math.cos(local_angle) * local_r) + binormal * (math.sin(local_angle) * local_r) + vector(0, local_y, 0)
        pos = center + offset
        starting_color = lerp(vector(0.22, 0.42, 0.92), vector(1.0, 0.80, 0.25), random.random())
        node = sphere(pos=pos, radius=random.uniform(0.17, 0.30), color=starting_color, emissive=True)
        nodes.append({"pos": pos, "wealth": random.uniform(30, 120), "stress": 0.0})
        node_visuals.append(node)
        node_ledgers.append({name: random.uniform(3, 20) for name in FLOW_NAMES})
        node_cluster_id.append(c)
        node_base_offsets.append(offset)

# Structural ribs to the engine
for center in cluster_centers:
    curve(pos=[center * 0.82, center * 0.36, vector(0, 0, 0)], radius=0.022, color=vector(0.45, 0.56, 0.82), opacity=0.18)

# -----------------------------
# Routes
# -----------------------------
routes = []
route_curves = []
connected_routes = [[] for _ in range(VISIBLE_NODE_COUNT)]

cluster_members = []
for c in range(CLUSTER_COUNT):
    cluster_members.append([i for i, cid in enumerate(node_cluster_id) if cid == c])

for _ in range(ROUTE_COUNT):
    if random.random() < 0.74:
        a_cluster = random.randrange(CLUSTER_COUNT)
        b_cluster = (a_cluster + random.choice([1, 2, 3, 4, 5])) % CLUSTER_COUNT
        a = random.choice(cluster_members[a_cluster])
        b = random.choice(cluster_members[b_cluster])
    else:
        c = random.randrange(CLUSTER_COUNT)
        a, b = random.sample(cluster_members[c], 2)

    pa = nodes[a]["pos"]
    pb = nodes[b]["pos"]
    mid = (pa + pb) * 0.5
    outward = unit_or_zero(mid)
    control = mid + outward * random.uniform(2.0, 6.0) + random_perpendicular(pb - pa) * random.uniform(-1.0, 1.0)
    flow_type = random.choice(FLOW_NAMES)
    route = {
        "a": a,
        "b": b,
        "control": control,
        "flow_type": flow_type,
        "traffic": random.uniform(0.05, 0.45),
        "phase": random.uniform(0, 2 * math.pi),
    }
    routes.append(route)
    route_index = len(routes) - 1
    connected_routes[a].append(route_index)
    connected_routes[b].append(route_index)

    pts = []
    for k in range(15):
        t = k / 14.0
        pts.append(bezier_point(pa, control, pb, t))
    route_curves.append(curve(pos=pts, radius=0.020, color=FLOW_TYPES[flow_type]["color"], opacity=0.20))

# -----------------------------
# Packets - no make_trail; trails are the biggest VPython startup/runtime cost here
# -----------------------------
packets = []
for _ in range(PACKET_COUNT):
    route_index = random.randrange(len(routes))
    route = routes[route_index]
    flow_type = random.choice(FLOW_NAMES if random.random() < 0.35 else [route["flow_type"]])
    f = FLOW_TYPES[flow_type]
    body = sphere(pos=vector(0, 0, 0), radius=f["radius"] * random.uniform(0.85, 1.25), color=f["color"], emissive=True)
    packet = {
        "body": body,
        "route": route_index,
        "flow_type": flow_type,
        "t": random.random(),
        "speed": f["speed"] * random.uniform(0.75, 1.45),
        "direction": 1 if random.random() < 0.78 else -1,
        "value": f["value"] * random.uniform(0.7, 1.8),
    }
    body.pos = bezier_point(nodes[route["a"]]["pos"], route["control"], nodes[route["b"]]["pos"], packet["t"])
    packets.append(packet)

# -----------------------------
# HUD and legend
# -----------------------------
status = label(
    pos=vector(-23, 12, 0),
    text="SEPTILLION MARKET ENGINE\ninitializing flows...",
    height=11,
    box=True,
    border=8,
    opacity=0.75,
    color=vector(0.05, 0.07, 0.11),
    background=vector(0.96, 0.97, 1.0),
)

legend_y = -11.0
for n, name in enumerate(FLOW_NAMES):
    f = FLOW_TYPES[name]
    sphere(pos=vector(-24, legend_y - n * 1.1, 0), radius=0.18, color=f["color"], emissive=True)
    label(pos=vector(-22.8, legend_y - n * 1.1, 0), text=name, height=9, box=False, opacity=0, color=vector(0.08, 0.10, 0.16))

# -----------------------------
# Economy mechanics
# -----------------------------
def route_position(route, t):
    return bezier_point(nodes[route["a"]]["pos"], route["control"], nodes[route["b"]]["pos"], t)


def deliver_packet(packet):
    route = routes[packet["route"]]
    receiving_node = route["b"] if packet["direction"] > 0 else route["a"]
    sending_node = route["a"] if packet["direction"] > 0 else route["b"]
    flow_type = packet["flow_type"]
    value = packet["value"]

    node_ledgers[receiving_node][flow_type] += value
    node_ledgers[sending_node][flow_type] = max(0.0, node_ledgers[sending_node][flow_type] - value * 0.35)
    nodes[receiving_node]["wealth"] += value * 0.45
    nodes[sending_node]["wealth"] += value * 0.10

    total_resources = sum(node_ledgers[receiving_node].values())
    nodes[receiving_node]["stress"] += clamp(total_resources / 900.0, 0.01, 0.08)

    connected = connected_routes[receiving_node]
    if connected and random.random() < 0.84:
        packet["route"] = random.choice(connected)
        new_route = routes[packet["route"]]
        packet["direction"] = 1 if new_route["a"] == receiving_node else -1
    else:
        packet["route"] = random.randrange(len(routes))
        packet["direction"] = 1 if random.random() < 0.78 else -1

    packet["t"] = 0.0 if packet["direction"] > 0 else 1.0

    if random.random() < 0.16:
        packet["flow_type"] = random.choice(FLOW_NAMES)
    f = FLOW_TYPES[packet["flow_type"]]
    packet["speed"] = f["speed"] * random.uniform(0.75, 1.45)
    packet["value"] = f["value"] * random.uniform(0.7, 1.8)
    packet["body"].color = f["color"]
    packet["body"].radius = f["radius"] * random.uniform(0.85, 1.25)


def update_nodes(elapsed):
    for i, data in enumerate(nodes):
        c = node_cluster_id[i]
        center = cluster_centers[c]
        wealth = data["wealth"]
        stress = data["stress"]
        breathing = 0.22 * math.sin(elapsed * 0.65 + i * 0.47)
        axis = unit_or_zero(center)
        orbital = rotate(node_base_offsets[i], angle=0.09 * math.sin(elapsed * 0.17 + c), axis=axis)
        desired = center + orbital * (1.0 + breathing * 0.15 + clamp(wealth / 900.0, 0.0, 0.18))
        desired += axis * stress * 1.6
        data["pos"] = lerp(data["pos"], desired, 0.035)
        data["wealth"] *= 0.9992
        data["stress"] *= 0.985

        visual = node_visuals[i]
        visual.pos = data["pos"]
        brightness = clamp(data["wealth"] / 190.0, 0.25, 1.35)
        calm_color = vector(0.24, 0.52, 1.0)
        stress_color = vector(1.0, 0.25, 0.08)
        visual.color = lerp(calm_color, stress_color, clamp(stress, 0.0, 1.0)) * brightness
        visual.radius = 0.17 + clamp(wealth / 900.0, 0.0, 0.20) + clamp(stress, 0.0, 0.65) * 0.11


def update_routes(elapsed, frame):
    # Important fix: route curves are not rebuilt or heavily mutated every frame.
    # Only a rotating subset gets a light radius/opacity pulse.
    if frame % 3 != 0:
        return
    start_index = (frame // 3) % len(routes)
    for offset in range(0, len(routes), 6):
        idx = (start_index + offset) % len(routes)
        r = routes[idx]
        r["traffic"] *= 0.985
        pulse = 0.5 + 0.5 * math.sin(elapsed * 1.6 + r["phase"])
        route_curves[idx].radius = clamp(0.016 + r["traffic"] * 0.020 + pulse * 0.004, 0.014, 0.045)
        route_curves[idx].opacity = clamp(0.12 + r["traffic"] * 0.22 + pulse * 0.04, 0.10, 0.42)


def update_packets():
    for packet in packets:
        packet["t"] += packet["speed"] * packet["direction"]
        routes[packet["route"]]["traffic"] += 0.0020 * packet["value"]

        if packet["t"] >= 1.0 or packet["t"] <= 0.0:
            deliver_packet(packet)

        route = routes[packet["route"]]
        packet["body"].pos = route_position(route, clamp(packet["t"], 0.0, 1.0))


def calculate_totals():
    totals = {name: 0.0 for name in FLOW_NAMES}
    wealth_total = 0.0
    stress_total = 0.0
    for i in range(len(nodes)):
        wealth_total += nodes[i]["wealth"]
        stress_total += nodes[i]["stress"]
        for name in FLOW_NAMES:
            totals[name] += node_ledgers[i][name]
    route_flow = sum(r["traffic"] for r in routes)
    return totals, wealth_total, stress_total, route_flow

# -----------------------------
# Main loop
# -----------------------------
start_time = time.time()
frame = 0

while True:
    rate(45)
    elapsed = time.time() - start_time
    frame += 1

    update_nodes(elapsed)
    update_routes(elapsed, frame)
    update_packets()

    if frame % 720 == 0:
        shock_cluster = random.randrange(CLUSTER_COUNT)
        for i, cid in enumerate(node_cluster_id):
            if cid == shock_cluster:
                nodes[i]["stress"] += random.uniform(0.10, 0.35)
                nodes[i]["wealth"] += random.uniform(4, 24)
        for r in routes:
            if node_cluster_id[r["a"]] == shock_cluster or node_cluster_id[r["b"]] == shock_cluster:
                r["traffic"] += random.uniform(0.25, 0.75)

    totals, wealth_total, stress_total, route_flow = calculate_totals()
    throughput = clamp(route_flow / 12.0, 0.0, 1.8)
    stress_level = clamp(stress_total / 16.0, 0.0, 1.0)
    heartbeat = 1.0 + 0.08 * math.sin(elapsed * (2.1 + throughput)) + throughput * 0.06

    core.radius = 2.05 * heartbeat
    core.color = lerp(vector(1.0, 0.82, 0.24), vector(1.0, 0.26, 0.08), stress_level)
    core_shell.radius = 3.15 + throughput * 0.95 + stress_level * 0.45
    core_shell.opacity = 0.10 + throughput * 0.06
    core_ring_a.rotate(angle=0.009 + throughput * 0.008, axis=vector(0, 1, 0), origin=vector(0, 0, 0))
    core_ring_b.rotate(angle=-0.007 - stress_level * 0.010, axis=vector(1, 0.15, 0), origin=vector(0, 0, 0))
    core_ring_c.rotate(angle=0.005 + throughput * 0.005, axis=vector(0.2, 0, 1), origin=vector(0, 0, 0))

    if frame % 30 == 0:
        dominant = max(totals.items(), key=lambda kv: kv[1])[0]
        status.text = (
            "SEPTILLION MARKET ENGINE\n"
            f"visible actors: {VISIBLE_NODE_COUNT:,} nodes / represents millions\n"
            f"routes: {ROUTE_COUNT:,}    moving flows: {PACKET_COUNT:,}\n"
            f"total market value: {wealth_total:,.0f} simulated units\n"
            f"route throughput: {route_flow:,.2f}\n"
            f"system stress: {stress_total:,.2f}\n"
            f"dominant flow: {dominant}\n\n"
            "Packets are trades, jobs, shipments, watts, and signals."
        )
