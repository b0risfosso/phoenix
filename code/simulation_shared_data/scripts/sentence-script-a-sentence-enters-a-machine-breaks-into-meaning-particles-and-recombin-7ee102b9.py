from vpython import *
import random
import math

# Prompt-to-World Compiler
# A sentence enters a machine, breaks into meaning particles, and recombines
# into moving objects, forces, colors, and interactions.

scene = canvas(
    title="Prompt-to-World Compiler",
    width=1200,
    height=720,
    background=vector(0.93, 0.96, 1.0),
    center=vector(0, 0, 0),
)
scene.camera.pos = vector(0, 7, 18)
scene.camera.axis = vector(0, -5, -18)
scene.range = 10

# ---------- Helpers ----------

def clamp(x, a, b):
    return max(a, min(b, x))


def soft_color(base, pulse=0.0):
    return vector(
        clamp(base.x + pulse, 0, 1),
        clamp(base.y + pulse, 0, 1),
        clamp(base.z + pulse, 0, 1),
    )


def make_label(text, pos, height=12, col=vector(0.15, 0.18, 0.22), box=False):
    return label(
        text=text,
        pos=pos,
        height=height,
        color=col,
        box=box,
        opacity=0,
        line=False,
    )


# ---------- Palette ----------
ink = vector(0.12, 0.15, 0.18)
blue = vector(0.18, 0.45, 0.92)
teal = vector(0.0, 0.68, 0.72)
green = vector(0.18, 0.70, 0.35)
yellow = vector(0.95, 0.72, 0.20)
orange = vector(0.95, 0.42, 0.18)
red = vector(0.88, 0.16, 0.18)
purple = vector(0.55, 0.32, 0.86)
soft_gray = vector(0.72, 0.77, 0.82)

particle_colors = [blue, teal, green, yellow, orange, red, purple]

# ---------- Title and dashboard ----------
title = make_label("Prompt-to-World Compiler", vector(0, 5.7, 0), 22, ink)
subtitle = make_label(
    "sentence  →  meaning particles  →  moving world",
    vector(0, 5.15, 0),
    13,
    vector(0.25, 0.30, 0.36),
)
status = make_label("Booting compiler...", vector(0, -5.25, 0), 14, ink)
metrics = make_label("", vector(6.1, 4.85, 0), 11, vector(0.20, 0.22, 0.25))
mode_label = make_label("", vector(-6.1, 4.85, 0), 11, vector(0.20, 0.22, 0.25))

# ---------- World floor and lanes ----------
floor = box(pos=vector(0, -4.25, 0), size=vector(16, 0.08, 7), color=vector(0.86, 0.91, 0.95))
input_lane = box(pos=vector(-5.8, 0, 0), size=vector(3.4, 0.05, 0.15), color=vector(0.65, 0.72, 0.82))
output_lane = box(pos=vector(5.75, 0, 0), size=vector(3.8, 0.05, 0.15), color=vector(0.65, 0.72, 0.82))

for x in [-6.9, -5.8, -4.7, 4.4, 5.55, 6.7]:
    box(pos=vector(x, -0.15, 0), size=vector(0.05, 0.25, 0.75), color=soft_gray)

# ---------- Compiler machine ----------
machine_body = box(pos=vector(0, 0, 0), size=vector(3.4, 2.7, 2.0), color=vector(0.80, 0.86, 0.91))
machine_front = box(pos=vector(0, 0, 1.03), size=vector(2.8, 1.9, 0.08), color=vector(0.94, 0.97, 0.99))
input_slot = box(pos=vector(-1.75, 0.25, 0), size=vector(0.12, 0.65, 1.4), color=vector(0.18, 0.22, 0.30))
output_slot = box(pos=vector(1.75, 0.25, 0), size=vector(0.12, 0.65, 1.4), color=vector(0.18, 0.22, 0.30))
core = sphere(pos=vector(0, 0.25, 1.12), radius=0.42, color=blue, emissive=True)
core_ring = ring(pos=core.pos, axis=vector(0, 0, 1), radius=0.68, thickness=0.035, color=teal, emissive=True)
scan_bar = box(pos=vector(-1.0, 0.95, 1.18), size=vector(0.16, 0.18, 0.08), color=yellow, emissive=True)

# Internal gear-like rings using supported ring primitive
rings = []
for i, r in enumerate([0.55, 0.82, 1.08]):
    rings.append(
        ring(
            pos=vector(0, -0.65, 1.13 + i * 0.015),
            axis=vector(0, 0, 1),
            radius=r,
            thickness=0.026,
            color=[purple, teal, orange][i],
            emissive=True,
        )
    )

# ---------- Input sentence ----------
sentence_text = "vibe coding: a prompt becomes a world"
sentence_card = box(pos=vector(-7.2, 0.8, 0), size=vector(3.9, 0.72, 0.08), color=vector(1, 1, 1))
sentence_label = make_label(sentence_text, sentence_card.pos + vector(0, 0.02, 0.25), 10, ink)

# ---------- Meaning particles ----------
words = ["vibe", "coding", "prompt", "meaning", "motion", "force", "color", "world"]
particles = []
for i, word in enumerate(words):
    angle = 2 * math.pi * i / len(words)
    col = particle_colors[i % len(particle_colors)]
    p = sphere(pos=vector(0, 0.25, 0), radius=0.12, color=col, emissive=True, visible=False)
    p.word = word
    p.base_color = col
    p.seed_angle = angle
    p.target = vector(1.7 * math.cos(angle), 0.25 + 0.9 * math.sin(angle), 1.25)
    p.vel = vector(0, 0, 0)
    p.lbl = make_label(word, p.pos + vector(0, 0.28, 0), 9, col)
    p.lbl.visible = False
    particles.append(p)

# ---------- Output world objects ----------
world_objects = []
force_arrows = []
interaction_lines = []

# Source words become different object classes
object_specs = [
    ("object", sphere, vector(4.0, -1.6, 0.1), green),
    ("force", cone, vector(5.0, -1.25, -0.6), orange),
    ("color", box, vector(6.0, -1.5, 0.45), purple),
    ("motion", sphere, vector(4.7, -2.55, 0.85), blue),
    ("interaction", cylinder, vector(5.9, -2.45, -0.55), teal),
]

# Build invisible output objects now; reveal after compilation
for name, shape, pos, col in object_specs:
    if shape == sphere:
        obj = sphere(pos=pos, radius=0.36, color=col, emissive=True, visible=False)
    elif shape == cone:
        obj = cone(pos=pos, axis=vector(0.8, 0.2, 0), radius=0.28, color=col, emissive=True, visible=False)
    elif shape == box:
        obj = box(pos=pos, size=vector(0.65, 0.65, 0.65), color=col, visible=False)
    else:
        obj = cylinder(pos=pos, axis=vector(0.7, 0.28, 0.15), radius=0.16, color=col, emissive=True, visible=False)
    obj.name = name
    obj.origin = vector(pos.x, pos.y, pos.z)
    obj.phase = random.uniform(0, 2 * math.pi)
    obj.base_color = col
    world_objects.append(obj)

for i, obj in enumerate(world_objects):
    arr = arrow(
        pos=obj.pos,
        axis=vector(0.55, 0.35 + 0.1 * i, 0),
        shaftwidth=0.045,
        color=yellow if i % 2 == 0 else orange,
        visible=False,
    )
    force_arrows.append(arr)

for i in range(len(world_objects)):
    a = world_objects[i]
    b = world_objects[(i + 1) % len(world_objects)]
    ln = curve(pos=[a.pos, b.pos], radius=0.025, color=vector(0.45, 0.58, 0.72), visible=False)
    interaction_lines.append(ln)

# ---------- Floating code tokens ----------
code_tokens = []
for i, token in enumerate(["parse()", "embed()", "bind()", "simulate()", "render()"]):
    lbl = make_label(token, vector(-0.6 + i * 0.3, 1.85 + 0.12 * math.sin(i), 0.5), 8, vector(0.25, 0.35, 0.45))
    lbl.visible = False
    code_tokens.append(lbl)

# ---------- Flow particles for path ----------
flow = []
for i in range(18):
    s = sphere(pos=vector(-7.0 + random.random() * 1.8, -0.25 + random.uniform(-0.1, 0.1), random.uniform(-0.15, 0.15)),
               radius=0.045, color=soft_gray, emissive=True)
    s.offset = random.random() * 10
    flow.append(s)

# ---------- Round system ----------
round_index = 0
round_start = 0.0
round_duration = 32.0
compiled_count = 0
catchy_phrases = [
    "a prompt becomes a world",
    "meaning becomes matter",
    "syntax becomes motion",
    "vibe becomes behavior",
    "language starts moving",
]


def reset_round(t):
    global round_index, round_start, compiled_count, sentence_text
    round_index += 1
    round_start = t
    compiled_count = 0
    sentence_text = "vibe coding: " + catchy_phrases[round_index % len(catchy_phrases)]
    sentence_label.text = sentence_text
    sentence_card.pos = vector(-7.4, 0.8, 0)
    sentence_label.pos = sentence_card.pos + vector(0, 0.02, 0.25)
    for i, p in enumerate(particles):
        angle = 2 * math.pi * i / len(particles) + random.uniform(-0.35, 0.35)
        p.visible = False
        p.lbl.visible = False
        p.pos = vector(0, 0.25, 0)
        p.target = vector(1.45 * math.cos(angle), 0.25 + 0.95 * math.sin(angle), 1.25)
        p.seed_angle = angle
        p.radius = 0.12
    for obj in world_objects:
        obj.visible = False
        obj.pos = obj.origin + vector(random.uniform(-0.25, 0.25), random.uniform(-0.15, 0.15), random.uniform(-0.1, 0.1))
    for arr in force_arrows:
        arr.visible = False
    for ln in interaction_lines:
        ln.visible = False
    for lbl in code_tokens:
        lbl.visible = False

reset_round(0)

# ---------- Animation update functions ----------
def update_flow(t):
    for i, s in enumerate(flow):
        phase = (t * 0.45 + s.offset) % 10
        if phase < 4.6:
            x = -7.2 + phase * 1.18
            y = -0.25 + 0.06 * math.sin(t * 2.0 + i)
        else:
            x = 1.2 + (phase - 4.6) * 1.08
            y = -0.25 + 0.06 * math.sin(t * 2.0 + i)
        s.pos = vector(x, y, s.pos.z)
        s.color = particle_colors[i % len(particle_colors)] if 3.1 < phase < 6.6 else soft_gray


def update_sentence_card(progress):
    if progress < 0.22:
        a = progress / 0.22
        sentence_card.pos = vector(-7.4 + 5.55 * a, 0.8 - 0.55 * a, 0)
        sentence_card.visible = True
        sentence_label.visible = True
    elif progress < 0.30:
        a = (progress - 0.22) / 0.08
        sentence_card.size = vector(3.9 * (1 - 0.65 * a), 0.72 * (1 - 0.55 * a), 0.08)
        sentence_card.color = soft_color(vector(1, 1, 1), -0.08 * a)
    else:
        sentence_card.visible = False
        sentence_label.visible = False
        sentence_card.size = vector(3.9, 0.72, 0.08)
        sentence_card.color = vector(1, 1, 1)


def update_particles(t, progress):
    global compiled_count
    if progress < 0.28:
        for p in particles:
            p.visible = False
            p.lbl.visible = False
        return

    if progress < 0.56:
        local = (progress - 0.28) / 0.28
        status.text = "Parsing sentence into meaning particles"
        for i, p in enumerate(particles):
            p.visible = True
            p.lbl.visible = True
            swirl = vector(
                math.cos(t * 2.2 + p.seed_angle) * (0.35 + local),
                math.sin(t * 2.5 + p.seed_angle) * (0.28 + 0.4 * local),
                1.1 + 0.18 * math.sin(t + i),
            )
            p.pos = vector(0, 0.25, 0.08) * (1 - local) + p.target * local + swirl * 0.15
            p.radius = 0.11 + 0.04 * math.sin(t * 5 + i) ** 2
            p.color = soft_color(p.base_color, 0.08 * math.sin(t * 4 + i))
            p.lbl.pos = p.pos + vector(0, 0.32, 0)
    elif progress < 0.78:
        local = (progress - 0.56) / 0.22
        status.text = "Recombining particles into objects, forces, colors, and motion"
        for i, p in enumerate(particles):
            p.visible = True
            p.lbl.visible = local < 0.65
            target = vector(4.25 + (i % 4) * 0.65, -1.05 - (i // 4) * 0.85, random.uniform(-0.15, 0.15))
            p.pos = p.pos * 0.88 + target * 0.12 + vector(0, 0.07 * math.sin(t * 6 + i), 0)
            p.radius = 0.13 + 0.02 * math.sin(t * 4 + i)
            p.lbl.pos = p.pos + vector(0, 0.26, 0)
        reveal = int(local * len(world_objects) + 1)
        compiled_count = max(compiled_count, reveal)
        for i, obj in enumerate(world_objects):
            obj.visible = i < reveal
            force_arrows[i].visible = i < reveal
        for i, ln in enumerate(interaction_lines):
            ln.visible = i < reveal - 1
    else:
        for p in particles:
            p.visible = False
            p.lbl.visible = False


def update_world(t, progress):
    world_active = progress > 0.62
    if not world_active:
        return

    for i, obj in enumerate(world_objects):
        if not obj.visible:
            continue
        pulse = math.sin(t * 2.4 + obj.phase)
        orbit = vector(
            0.32 * math.cos(t * 0.9 + obj.phase),
            0.22 * math.sin(t * 1.3 + obj.phase),
            0.18 * math.sin(t * 0.7 + obj.phase),
        )
        obj.pos = obj.origin + orbit
        obj.color = soft_color(obj.base_color, 0.06 * max(0, pulse))
        if hasattr(obj, "axis"):
            if obj.name == "force":
                obj.axis = vector(0.75 + 0.2 * math.sin(t), 0.22 + 0.18 * math.cos(t * 1.4), 0)
            elif obj.name == "interaction":
                obj.axis = vector(0.62 + 0.25 * math.cos(t), 0.34, 0.24 * math.sin(t * 1.1))
        if hasattr(obj, "size"):
            scale = 0.62 + 0.08 * math.sin(t * 2.3 + i)
            obj.size = vector(scale, scale, scale)

        arr = force_arrows[i]
        arr.pos = obj.pos + vector(0, 0.15, 0)
        arr.axis = vector(
            0.42 + 0.3 * math.cos(t * 1.2 + i),
            0.25 + 0.25 * math.sin(t * 1.5 + i),
            0,
        )

    for i, ln in enumerate(interaction_lines):
        if not ln.visible:
            continue
        a = world_objects[i]
        b = world_objects[(i + 1) % len(world_objects)]
        # Avoid curve.points usage; recreate the short link by clearing then appending.
        ln.clear()
        mid = (a.pos + b.pos) * 0.5 + vector(0, 0.12 * math.sin(t * 3 + i), 0)
        ln.append(pos=a.pos)
        ln.append(pos=mid)
        ln.append(pos=b.pos)


def update_machine(t, progress):
    core.color = soft_color(blue, 0.12 * math.sin(t * 5))
    core.radius = 0.42 + 0.04 * math.sin(t * 4)
    core_ring.rotate(angle=0.025, axis=vector(0, 0, 1), origin=core_ring.pos)
    for i, r in enumerate(rings):
        r.rotate(angle=(0.015 + i * 0.012) * ((-1) ** i), axis=vector(0, 0, 1), origin=r.pos)
    scan_bar.pos.x = -1.15 + 2.3 * ((math.sin(t * 2.6) + 1) / 2)
    scan_bar.color = yellow if progress < 0.62 else green
    for i, lbl in enumerate(code_tokens):
        lbl.visible = 0.24 < progress < 0.75
        lbl.pos.y = 1.78 + 0.17 * math.sin(t * 1.8 + i)
        lbl.color = particle_colors[(i + round_index) % len(particle_colors)]


def update_dashboard(t, progress):
    if progress < 0.24:
        phase = "INPUT"
        status.text = "Feeding sentence into compiler"
    elif progress < 0.56:
        phase = "PARSE"
    elif progress < 0.78:
        phase = "COMPILE"
    else:
        phase = "WORLD RUNNING"
        status.text = "The generated world is now moving under its own rules"

    meaning_density = int(100 * clamp((progress - 0.25) / 0.45, 0, 1))
    world_coherence = int(100 * clamp((progress - 0.56) / 0.34, 0, 1))
    force_balance = int(60 + 25 * math.sin(t * 0.7) + 12 * math.sin(t * 1.6))
    force_balance = clamp(force_balance, 0, 100)
    metrics.text = (
        f"Round: {round_index}\n"
        f"Meaning density: {meaning_density}%\n"
        f"World coherence: {world_coherence}%\n"
        f"Force balance: {force_balance}%\n"
        f"Compiled forms: {min(compiled_count, len(world_objects))}/{len(world_objects)}"
    )
    mode_label.text = (
        f"Phase: {phase}\n"
        f"Input: vibe coding\n"
        f"Particles: {len(particles)}\n"
        f"No external assets"
    )


# ---------- Keyboard controls ----------
paused = False
speed_scale = 1.0
show_labels = True

help_label = make_label(
    "Keys: SPACE pause/resume | R new round | + / - speed | L labels",
    vector(0, -5.75, 0),
    10,
    vector(0.28, 0.31, 0.36),
)


def on_keydown(evt):
    global paused, speed_scale, show_labels
    key = evt.key
    if key == " ":
        paused = not paused
    elif key in ["r", "R"]:
        reset_round(sim_time)
    elif key in ["+", "="]:
        speed_scale = clamp(speed_scale + 0.25, 0.25, 3.0)
    elif key in ["-", "_"]:
        speed_scale = clamp(speed_scale - 0.25, 0.25, 3.0)
    elif key in ["l", "L"]:
        show_labels = not show_labels
        title.visible = show_labels
        subtitle.visible = show_labels
        status.visible = show_labels
        metrics.visible = show_labels
        mode_label.visible = show_labels
        help_label.visible = show_labels

scene.bind("keydown", on_keydown)

# ---------- Main loop ----------
sim_time = 0.0
dt = 0.025

while True:
    rate(60)
    if paused:
        status.text = "Paused"
        continue

    sim_time += dt * speed_scale
    progress = (sim_time - round_start) / round_duration
    if progress >= 1.0:
        reset_round(sim_time)
        progress = 0.0

    update_flow(sim_time)
    update_sentence_card(progress)
    update_particles(sim_time, progress)
    update_world(sim_time, progress)
    update_machine(sim_time, progress)
    update_dashboard(sim_time, progress)
