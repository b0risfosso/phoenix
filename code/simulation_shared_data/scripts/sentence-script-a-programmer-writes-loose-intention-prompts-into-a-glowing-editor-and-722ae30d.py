"""
Vibe Coding Studio

Story:
    vibe coding

Simulation seed:
    A programmer writes loose intention prompts into a glowing editor, and the
    code world reshapes itself based on mood, rhythm, and desired behavior.

Controls:
    Mouse       : drag / scroll to control camera
    Space       : pause / resume
    1           : calm mood
    2           : curious mood
    3           : intense mood
    4           : playful mood
    B           : cycle desired behavior
    P           : send a new intention prompt into the editor
    R           : reset studio
    C           : toggle camera follow
    Up / W      : increase rhythm speed
    Down / S    : decrease rhythm speed

Run:
    python vibe_coding_studio.py

Requires:
    pip install vpython
"""

from vpython import *
import math
import random

scene = canvas(
    title="Vibe Coding Studio",
    width=1200,
    height=780,
    background=vector(0.94, 0.96, 1.0),
    center=vector(0, 1.4, 0),
)
scene.forward = vector(-0.48, -0.30, -0.82)
scene.up = vector(0, 1, 0)
scene.range = 11.5
scene.userspin = True
scene.userzoom = True
scene.userpan = True


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def mix_color(a, b, t):
    return vector(lerp(a.x, b.x, t), lerp(a.y, b.y, t), lerp(a.z, b.z, t))


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m


PAPER = vector(0.95, 0.93, 0.86)
DESK = vector(0.64, 0.55, 0.42)
INK = vector(0.12, 0.13, 0.17)
SCREEN = vector(0.05, 0.08, 0.12)
EDITOR_GLOW = vector(0.42, 0.82, 1.0)
CALM = vector(0.34, 0.72, 0.95)
CURIOUS = vector(0.55, 0.85, 0.42)
INTENSE = vector(1.0, 0.36, 0.22)
PLAYFUL = vector(0.92, 0.42, 1.0)
GOLD = vector(1.0, 0.74, 0.24)
CODE_GREEN = vector(0.30, 1.0, 0.55)
NODE_BLUE = vector(0.25, 0.55, 1.0)
NODE_PURPLE = vector(0.63, 0.35, 1.0)

MOODS = [
    {"name": "calm", "color": CALM, "pulse": 0.55, "spread": 0.75},
    {"name": "curious", "color": CURIOUS, "pulse": 0.85, "spread": 1.00},
    {"name": "intense", "color": INTENSE, "pulse": 1.35, "spread": 1.25},
    {"name": "playful", "color": PLAYFUL, "pulse": 1.05, "spread": 1.45},
]

BEHAVIORS = [
    "grow a branching world",
    "make agents orbit",
    "turn rhythm into waves",
    "connect loose ideas",
    "debug the drifting pattern",
]

floor = box(pos=vector(0, -0.06, 0), size=vector(20, 0.10, 14), color=PAPER, opacity=0.95)
desk = box(pos=vector(-3.6, 0.55, 0), size=vector(5.2, 0.28, 3.3), color=DESK, opacity=0.96)
for x in [-5.7, -1.5]:
    for z in [-1.2, 1.2]:
        cylinder(pos=vector(x, -0.04, z), axis=vector(0, 1.08, 0), radius=0.055, color=vector(0.42, 0.34, 0.24))

chair = box(pos=vector(-6.35, 0.45, 0.0), size=vector(0.55, 0.70, 1.10), color=vector(0.28, 0.30, 0.34), opacity=0.90)
torso = ellipsoid(pos=vector(-5.75, 1.28, 0), length=0.52, height=1.02, width=0.46, color=vector(0.22, 0.28, 0.38))
head = sphere(pos=vector(-5.72, 2.04, 0), radius=0.24, color=vector(0.70, 0.53, 0.38))
arm_l = cylinder(pos=vector(-5.45, 1.45, -0.18), axis=vector(1.04, -0.42, -0.25), radius=0.045, color=vector(0.70, 0.53, 0.38))
arm_r = cylinder(pos=vector(-5.45, 1.45, 0.18), axis=vector(1.04, -0.42, 0.25), radius=0.045, color=vector(0.70, 0.53, 0.38))

keyboard = box(pos=vector(-4.25, 0.77, 0), size=vector(1.55, 0.06, 0.62), color=vector(0.08, 0.09, 0.10))
keys = []
for i in range(8):
    for j in range(3):
        key = box(pos=keyboard.pos + vector(-0.62 + i * 0.18, 0.055, -0.20 + j * 0.20), size=vector(0.11, 0.018, 0.08), color=vector(0.18, 0.20, 0.23))
        keys.append({"obj": key, "phase": random.random() * math.tau})

screen_back = box(pos=vector(-3.15, 1.62, 0), size=vector(0.12, 1.85, 2.95), color=vector(0.02, 0.025, 0.035))
screen_face = box(pos=vector(-3.22, 1.62, 0), size=vector(0.035, 1.65, 2.65), color=SCREEN, opacity=0.92)
screen_glow = box(pos=vector(-3.245, 1.62, 0), size=vector(0.018, 1.72, 2.75), color=EDITOR_GLOW, opacity=0.16, emissive=True)

editor_lines = []
for i in range(13):
    z = -1.08 + (i % 5) * 0.46
    y = 2.20 - i * 0.11
    line = box(pos=vector(-3.27, y, z), size=vector(0.018, 0.035, random.uniform(0.25, 0.72)), color=mix_color(CODE_GREEN, EDITOR_GLOW, random.random()), opacity=0.72, emissive=True)
    editor_lines.append({"obj": line, "phase": random.random() * math.tau, "length": line.size.z})

prompt_label = label(pos=vector(-3.42, 2.62, 0), text="intention prompt", height=11, box=False, color=vector(0.10, 0.28, 0.38))

prompt_tokens = []
for i in range(32):
    token = sphere(pos=vector(-3.1, 1.5, 0), radius=random.uniform(0.035, 0.075), color=EDITOR_GLOW, opacity=0.0, emissive=True)
    prompt_tokens.append({"obj": token, "phase": random.random() * math.tau, "delay": random.random(), "lane": random.uniform(-1.2, 1.2)})

world_origin = vector(2.4, 1.0, 0)
world_base = cylinder(pos=world_origin + vector(0, -0.55, 0), axis=vector(0, 0.08, 0), radius=3.35, color=vector(0.78, 0.84, 0.88), opacity=0.35)
core = sphere(pos=world_origin, radius=0.36, color=EDITOR_GLOW, emissive=True, opacity=0.92)
core_ring = ring(pos=world_origin, axis=vector(0, 1, 0), radius=0.72, thickness=0.025, color=EDITOR_GLOW, emissive=True, opacity=0.65)

nodes = []
for i in range(42):
    r = random.uniform(0.45, 2.75)
    angle = random.uniform(0, math.tau)
    height = random.uniform(-0.25, 1.75)
    node = sphere(pos=world_origin + vector(r * math.cos(angle), height, r * math.sin(angle)), radius=random.uniform(0.045, 0.115), color=mix_color(NODE_BLUE, NODE_PURPLE, random.random()), emissive=True, opacity=0.82)
    nodes.append({"obj": node, "r": r, "angle": angle, "height": height, "phase": random.random() * math.tau, "speed": random.uniform(0.25, 0.90), "target_r": r})

connections = []
for i in range(56):
    a = random.randrange(len(nodes))
    b = random.randrange(len(nodes))
    if a == b:
        b = (b + 1) % len(nodes)
    conn = cylinder(pos=nodes[a]["obj"].pos, axis=nodes[b]["obj"].pos - nodes[a]["obj"].pos, radius=0.010, color=vector(0.45, 0.78, 1.0), opacity=0.25, emissive=True)
    connections.append({"obj": conn, "a": a, "b": b, "phase": random.random() * math.tau})

branches = []
for i in range(28):
    base_angle = i * math.tau / 28
    start = world_origin + vector(0, -0.15, 0)
    axis = vector(math.cos(base_angle) * random.uniform(0.4, 1.6), random.uniform(0.25, 1.25), math.sin(base_angle) * random.uniform(0.4, 1.6))
    branch = cylinder(pos=start, axis=axis, radius=random.uniform(0.012, 0.028), color=CODE_GREEN, opacity=0.0, emissive=True)
    leaf = sphere(pos=start + axis, radius=random.uniform(0.035, 0.075), color=GOLD, opacity=0.0, emissive=True)
    branches.append({"obj": branch, "leaf": leaf, "angle": base_angle, "phase": random.random() * math.tau})

rhythm_waves = []
for i in range(10):
    wave = ring(pos=world_origin + vector(0, -0.45, 0), axis=vector(0, 1, 0), radius=0.25 + i * 0.24, thickness=0.014, color=EDITOR_GLOW, opacity=0.18, emissive=True)
    rhythm_waves.append({"obj": wave, "phase": i / 10.0})

bug_markers = []
for i in range(8):
    bug = box(pos=world_origin + vector(random.uniform(-2, 2), random.uniform(0, 1.6), random.uniform(-2, 2)), size=vector(0.16, 0.16, 0.16), color=vector(1.0, 0.18, 0.12), opacity=0.0, emissive=True)
    bug_markers.append({"obj": bug, "phase": random.random() * math.tau, "fixed": 0.0})

behavior_label = label(pos=world_origin + vector(0, 3.15, 0), text="", height=14, box=True, border=8, color=vector(0.08, 0.12, 0.18), background=vector(0.92, 0.97, 1.0), opacity=0.78)

mood_orbs = []
for i, mood in enumerate(MOODS):
    orb = sphere(pos=vector(-1.1 + i * 0.75, 0.20, -4.8), radius=0.16, color=mood["color"], emissive=True, opacity=0.45)
    mood_orbs.append(orb)

label(pos=vector(0.05, 0.55, -4.8), text="mood palette", height=10, box=False, color=vector(0.12, 0.18, 0.22))
label(pos=vector(0, 4.65, -4.8), text="Vibe Coding Studio", height=24, box=False, color=vector(0.06, 0.12, 0.20))
label(pos=vector(0, 4.22, -4.8), text="Loose intention prompts reshape a code world through mood, rhythm, and desired behavior.", height=12, box=False, color=vector(0.10, 0.22, 0.34))
status = label(pos=vector(-7.8, 3.55, -4.8), text="", height=12, box=True, border=8, color=vector(0.07, 0.13, 0.18), background=vector(0.93, 0.97, 1.0), opacity=0.78)
legend = label(pos=vector(7.5, 3.47, -4.8), text="Editor tokens carry loose prompts.\nThe code world changes shape by mood.\nNodes, branches, waves, and bugs respond to rhythm.", height=12, box=True, border=8, color=vector(0.07, 0.13, 0.18), background=vector(0.93, 0.97, 1.0), opacity=0.78)

paused = False
mood_index = 1
behavior_index = 0
rhythm_speed = 1.0
camera_follow = False
sim_t = 0.0
prompt_burst = 0.0
reshape_energy = 0.0


def reset_sim():
    global sim_t, rhythm_speed, prompt_burst, reshape_energy, mood_index, behavior_index
    sim_t = 0.0
    rhythm_speed = 1.0
    prompt_burst = 0.0
    reshape_energy = 0.0
    mood_index = 1
    behavior_index = 0
    for bug in bug_markers:
        bug["fixed"] = 0.0


def send_prompt():
    global prompt_burst, reshape_energy
    prompt_burst = 1.0
    reshape_energy = min(1.0, reshape_energy + 0.55)


def on_keydown(evt):
    global paused, mood_index, behavior_index, rhythm_speed, camera_follow
    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "1":
        mood_index = 0
        send_prompt()
    elif key == "2":
        mood_index = 1
        send_prompt()
    elif key == "3":
        mood_index = 2
        send_prompt()
    elif key == "4":
        mood_index = 3
        send_prompt()
    elif key == "b":
        behavior_index = (behavior_index + 1) % len(BEHAVIORS)
        send_prompt()
    elif key == "p":
        send_prompt()
    elif key == "r":
        reset_sim()
    elif key == "c":
        camera_follow = not camera_follow
    elif key in ("up", "w"):
        rhythm_speed = min(4.0, rhythm_speed + 0.25)
    elif key in ("down", "s"):
        rhythm_speed = max(0.15, rhythm_speed - 0.25)


scene.bind("keydown", on_keydown)

while True:
    rate(50)
    if paused:
        status.text = f"Paused\nMood: {MOODS[mood_index]['name']}\nBehavior: {BEHAVIORS[behavior_index]}\nRhythm: {rhythm_speed:.2f}x\nSpace resumes | R resets"
        continue

    dt = 0.018 * rhythm_speed
    sim_t += dt
    mood = MOODS[mood_index]
    mood_color = mood["color"]
    mood_pulse = mood["pulse"]
    mood_spread = mood["spread"]
    prompt_burst *= 0.965
    reshape_energy *= 0.988
    beat = 0.5 + 0.5 * math.sin(sim_t * (2.2 + mood_pulse))
    fast_beat = 0.5 + 0.5 * math.sin(sim_t * (6.0 + 2.5 * mood_pulse))

    screen_glow.color = mix_color(EDITOR_GLOW, mood_color, 0.55)
    screen_glow.opacity = 0.12 + 0.18 * beat + 0.28 * prompt_burst
    screen_face.color = mix_color(SCREEN, mood_color, 0.08 + 0.12 * beat)

    for line in editor_lines:
        obj = line["obj"]
        pulse = 0.5 + 0.5 * math.sin(sim_t * 3.0 + line["phase"])
        obj.size.z = line["length"] * (0.70 + 0.45 * pulse + 0.35 * prompt_burst)
        obj.color = mix_color(CODE_GREEN, mood_color, 0.55 * pulse)
        obj.opacity = 0.45 + 0.45 * pulse

    for k in keys:
        p = 0.5 + 0.5 * math.sin(sim_t * 8.0 + k["phase"])
        k["obj"].color = mix_color(vector(0.14, 0.15, 0.17), mood_color, 0.35 * p * (0.35 + prompt_burst))
    arm_l.axis = vector(1.04, -0.42 + 0.05 * math.sin(sim_t * 9.0), -0.25)
    arm_r.axis = vector(1.04, -0.42 + 0.05 * math.sin(sim_t * 8.3 + 1.1), 0.25)

    for token in prompt_tokens:
        obj = token["obj"]
        phase_pos = (sim_t * 0.18 + token["delay"] + prompt_burst * 0.25) % 1.0
        start = vector(-3.25, 1.6 + 0.55 * math.sin(token["phase"]), token["lane"])
        end = world_origin + vector(0.25 * math.sin(token["phase"]), 0.25 + 0.95 * math.sin(token["phase"] * 1.7) ** 2, 0.25 * math.cos(token["phase"]))
        arc = vector(0, 1.55 * math.sin(math.pi * phase_pos), 0)
        obj.pos = start * (1.0 - phase_pos) + end * phase_pos + arc
        visible_wave = max(0.0, math.sin(math.pi * phase_pos))
        obj.opacity = (0.10 + 0.70 * visible_wave) * (0.25 + 0.75 * prompt_burst)
        obj.radius = 0.025 + 0.075 * visible_wave * (0.4 + prompt_burst)
        obj.color = mix_color(EDITOR_GLOW, mood_color, 0.65)

    for i, orb in enumerate(mood_orbs):
        active = 1.0 if i == mood_index else 0.0
        orb.radius = 0.14 + 0.10 * active + 0.03 * beat
        orb.opacity = 0.30 + 0.55 * active
        orb.color = mix_color(MOODS[i]["color"], GOLD, 0.25 * fast_beat) if active else MOODS[i]["color"]

    core.color = mix_color(EDITOR_GLOW, mood_color, 0.72)
    core.radius = 0.32 + 0.18 * beat + 0.20 * reshape_energy
    core_ring.color = mix_color(mood_color, GOLD, 0.30 * reshape_energy)
    core_ring.radius = 0.68 + 0.22 * beat + 0.40 * reshape_energy
    core_ring.thickness = 0.018 + 0.025 * fast_beat
    core_ring.rotate(angle=dt * (0.6 + mood_pulse), axis=vector(0.2, 1, 0.1), origin=world_origin)

    branch_weight = 1.0 if behavior_index == 0 else 0.35
    orbit_weight = 1.0 if behavior_index == 1 else 0.45
    wave_weight = 1.0 if behavior_index == 2 else 0.35
    connect_weight = 1.0 if behavior_index == 3 else 0.45
    debug_weight = 1.0 if behavior_index == 4 else 0.25

    for i, n in enumerate(nodes):
        obj = n["obj"]
        n["angle"] += dt * n["speed"] * (0.25 + 0.80 * orbit_weight) * mood_pulse
        desired_r = n["r"] * (0.55 + 0.65 * mood_spread + 0.15 * math.sin(i + behavior_index))
        if behavior_index == 3:
            desired_r *= 0.75 + 0.25 * math.sin(sim_t + n["phase"]) ** 2
        if behavior_index == 4:
            desired_r *= 0.85 + 0.35 * math.sin(sim_t * 2 + n["phase"])
        n["target_r"] += (desired_r - n["target_r"]) * 0.025
        y_wave = n["height"] + wave_weight * 0.48 * math.sin(sim_t * 2.8 + n["phase"])
        pos = world_origin + vector(n["target_r"] * math.cos(n["angle"]), y_wave, n["target_r"] * math.sin(n["angle"]))
        if behavior_index == 0:
            pos.y += 0.30 * math.sin(n["target_r"] * 2.4 + sim_t)
        obj.pos = pos
        local_pulse = 0.5 + 0.5 * math.sin(sim_t * (3.0 + mood_pulse) + n["phase"])
        obj.radius = 0.035 + 0.080 * local_pulse + 0.030 * reshape_energy
        obj.color = mix_color(NODE_BLUE, mood_color, 0.70 * local_pulse)
        obj.opacity = 0.54 + 0.42 * local_pulse

    for conn in connections:
        a = nodes[conn["a"]]["obj"].pos
        b = nodes[conn["b"]]["obj"].pos
        conn["obj"].pos = a
        conn["obj"].axis = b - a
        pulse = 0.5 + 0.5 * math.sin(sim_t * 3.2 + conn["phase"])
        conn["obj"].radius = 0.006 + 0.015 * connect_weight * pulse
        conn["obj"].opacity = 0.08 + 0.42 * connect_weight * pulse
        conn["obj"].color = mix_color(EDITOR_GLOW, mood_color, 0.60 * pulse)

    for b in branches:
        pulse = 0.5 + 0.5 * math.sin(sim_t * 1.7 + b["phase"])
        grow = branch_weight * (0.35 + 0.65 * pulse) * (0.35 + 0.65 * reshape_energy)
        axis = vector(math.cos(b["angle"]) * (0.55 + 1.65 * grow), 0.25 + 1.30 * grow, math.sin(b["angle"]) * (0.55 + 1.65 * grow))
        b["obj"].pos = world_origin + vector(0, -0.20, 0)
        b["obj"].axis = axis
        b["obj"].opacity = 0.06 + 0.56 * grow
        b["obj"].radius = 0.010 + 0.026 * grow
        b["obj"].color = mix_color(CODE_GREEN, mood_color, 0.55 * grow)
        b["leaf"].pos = b["obj"].pos + axis
        b["leaf"].opacity = 0.08 + 0.66 * grow
        b["leaf"].radius = 0.025 + 0.080 * grow
        b["leaf"].color = mix_color(GOLD, mood_color, 0.35 * pulse)

    for w in rhythm_waves:
        phase = (sim_t * 0.20 * rhythm_speed + w["phase"]) % 1.0
        w["obj"].radius = 0.25 + 3.2 * phase * (0.65 + 0.35 * mood_spread)
        w["obj"].opacity = (0.38 * (1.0 - phase) * wave_weight) + 0.04
        w["obj"].color = mix_color(EDITOR_GLOW, mood_color, 0.70)
        w["obj"].thickness = 0.010 + 0.020 * (1.0 - phase)

    for bug in bug_markers:
        obj = bug["obj"]
        glitch = max(0.0, math.sin(sim_t * 1.4 + bug["phase"]))
        repair = debug_weight * (0.3 + 0.7 * fast_beat)
        bug["fixed"] += (repair - bug["fixed"]) * 0.035
        obj.opacity = debug_weight * glitch * (1.0 - 0.75 * bug["fixed"])
        obj.pos += vector(0.006 * math.sin(sim_t * 9 + bug["phase"]), 0.006 * math.cos(sim_t * 7 + bug["phase"]), 0.006 * math.sin(sim_t * 8 + bug["phase"]))
        if obj.opacity < 0.05 and random.random() < 0.003 * debug_weight:
            obj.pos = world_origin + vector(random.uniform(-2, 2), random.uniform(0, 1.7), random.uniform(-2, 2))

    world_base.color = mix_color(vector(0.78, 0.84, 0.88), mood_color, 0.22)
    world_base.opacity = 0.18 + 0.22 * beat
    behavior_label.text = f"desired behavior:\n{BEHAVIORS[behavior_index]}"
    behavior_label.color = mix_color(INK, mood_color, 0.35)
    behavior_label.background = mix_color(vector(0.92, 0.97, 1.0), mood_color, 0.13)

    if camera_follow:
        scene.center = world_origin + vector(0, 0.8, 0)
        scene.forward = safe_norm(world_origin - vector(7.0, 4.2, 8.8))
        scene.range = 7.2

    status.text = (
        f"Mood: {mood['name']}\n"
        f"Desired behavior: {BEHAVIORS[behavior_index]}\n"
        f"Rhythm speed: {rhythm_speed:.2f}x\n"
        f"Prompt burst: {int(prompt_burst * 100)}%\n"
        f"Reshape energy: {int(reshape_energy * 100)}%\n"
        f"Camera: {'follow world' if camera_follow else 'mouse'}\n"
        "1 calm | 2 curious | 3 intense | 4 playful\n"
        "P prompt | B behavior | Space pause | R reset"
    )
