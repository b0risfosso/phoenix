"""
The Code That Feels Its Way Forward
VPython simulation based on the seed:

A script begins incomplete, then grows by intuition: each new line appears only
after the simulation responds to the previous one.

Controls:
- Space: pause/resume
- N: force next intuitive line
- R: reset
- C: cycle camera view
- Up/Down: increase/decrease intuition speed

Light styling. No CSV logging.
"""

from vpython import *
import math
import random

scene = canvas(
    title="The Code That Feels Its Way Forward",
    width=1200,
    height=760,
    background=vector(0.92, 0.96, 1.0),
    center=vector(0, 1.2, 0),
    forward=vector(-0.45, -0.22, -0.86),
    range=18,
)

scene.caption = """
The Code That Feels Its Way Forward
A script grows by intuition: every new line appears after the simulation responds.
Space pause/resume | N next line | R reset | C camera | Up/Down intuition speed
"""

PAPER = vector(0.98, 0.97, 0.92)
INK = vector(0.08, 0.10, 0.16)
GUIDE = vector(0.65, 0.76, 0.90)
BLUE = vector(0.20, 0.52, 0.95)
CYAN = vector(0.22, 0.82, 0.92)
GREEN = vector(0.25, 0.70, 0.36)
GOLD = vector(1.0, 0.68, 0.18)
ORANGE = vector(1.0, 0.43, 0.16)
PURPLE = vector(0.58, 0.42, 0.92)
PINK = vector(1.0, 0.45, 0.70)
GRAY = vector(0.70, 0.75, 0.80)
SHADOW = vector(0.74, 0.80, 0.86)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    t = clamp(t, 0, 1)
    return a + (b - a) * t


def rand_vec(scale=1.0):
    a = random.uniform(0, 2 * math.pi)
    r = random.uniform(0.2, 1.0) * scale
    return vector(r * math.cos(a), random.uniform(-0.3, 0.8) * scale, r * math.sin(a))


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-6:
        return fallback
    return v / m


def rotate_y(v, a):
    ca = math.cos(a)
    sa = math.sin(a)
    return vector(v.x * ca + v.z * sa, v.y, -v.x * sa + v.z * ca)


desk = box(pos=vector(0, -4.2, 0), size=vector(36, 0.28, 24), color=vector(0.86, 0.89, 0.84))

grid_lines = []
for x in range(-16, 17, 4):
    grid_lines.append(curve(pos=[vector(x, -4.02, -10), vector(x, -4.02, 10)], radius=0.01, color=GUIDE, opacity=0.18))
for z in range(-10, 11, 4):
    grid_lines.append(curve(pos=[vector(-16, -4.01, z), vector(16, -4.01, z)], radius=0.01, color=GUIDE, opacity=0.18))

panel_shadow = box(pos=vector(-7.0, 0.75, 0.25), size=vector(7.2, 9.8, 0.08), color=SHADOW, opacity=0.23)
panel = box(pos=vector(-7.2, 1.0, 0), size=vector(7.2, 9.8, 0.28), color=PAPER, opacity=0.96)

header = label(pos=vector(-9.8, 5.6, 0.25), text="unfinished_script.py", height=12, box=False, color=INK, opacity=0)
cursor = box(pos=vector(-10.25, 4.55, 0.32), size=vector(0.09, 0.32, 0.05), color=ORANGE, opacity=0.85)

field_ring = ring(pos=vector(4.3, 0.7, 0), axis=vector(0, 1, 0), radius=3.2, thickness=0.035, color=GUIDE, opacity=0.42)
field_core = sphere(pos=vector(4.3, 0.7, 0), radius=0.35, color=CYAN, opacity=0.78, emissive=True)
intuition_orb = sphere(pos=vector(0.2, 5.3, 0), radius=0.42, color=PURPLE, opacity=0.74, emissive=True)
intuition_halo = ring(pos=intuition_orb.pos, axis=vector(0, 1, 0), radius=0.72, thickness=0.025, color=PURPLE, opacity=0.32)

base_lines = [
    "scene = canvas()",
    "state = unfinished",
    "while feeling_forward:",
]

possible_lines = [
    {"text": "    listen_to_motion()", "kind": "listen"},
    {"text": "    spawn_point(where=curiosity)", "kind": "point"},
    {"text": "    connect_nearest_signals()", "kind": "connect"},
    {"text": "    brighten_if_path_works()", "kind": "brighten"},
    {"text": "    bend_line_toward_response()", "kind": "bend"},
    {"text": "    let_error_become_orbit()", "kind": "orbit"},
    {"text": "    grow_shape_from_previous_line()", "kind": "shape"},
    {"text": "    pulse_when_pattern_answers()", "kind": "pulse"},
    {"text": "    rewrite_direction_from_feedback()", "kind": "rewrite"},
    {"text": "    keep_what_feels_alive()", "kind": "alive"},
    {"text": "    split_uncertainty_into_options()", "kind": "split"},
    {"text": "    return next_intuition", "kind": "return"},
]

line_labels = []
current_lines = []
line_kinds = []
max_visible_lines = 17


def add_code_label(text, row, active=False):
    y = 4.65 - row * 0.52
    color_value = ORANGE if active else INK
    return label(pos=vector(-10.35, y, 0.35), text=text, height=10, box=False, color=color_value, opacity=0, align="left")


def redraw_code_labels(active_index=-1):
    global line_labels
    for lbl in line_labels:
        lbl.visible = False
    line_labels = []
    visible = current_lines[-max_visible_lines:]
    start_line_num = max(0, len(current_lines) - max_visible_lines)
    for i, text in enumerate(visible):
        global_idx = start_line_num + i
        line_no = f"{global_idx + 1:02d}  "
        line_labels.append(add_code_label(line_no + text, i, active=(global_idx == active_index)))
    if line_labels:
        cursor.pos = line_labels[-1].pos + vector(-0.16, -0.34, -0.03)

particles = []
connections = []
pulses = []
orbits = []
shape_blocks = []
response_arcs = []
ghost_options = []


class CodeParticle:
    def __init__(self, pos, color_value, kind):
        self.vel = rand_vec(0.035)
        self.kind = kind
        self.age = 0
        self.obj = sphere(pos=pos, radius=random.uniform(0.08, 0.18), color=color_value, opacity=0.78, emissive=True)
        self.trail = curve(pos=[pos, pos + vector(0.001, 0, 0)], radius=0.012, color=color_value, opacity=0.25)

    def update(self, dt, t):
        to_center = field_core.pos - self.obj.pos
        tangent = vector(-to_center.z, 0.2 * math.sin(t + self.age), to_center.x)
        self.vel += safe_norm(to_center) * 0.0018 + safe_norm(tangent) * 0.0012
        self.vel *= 0.992
        self.obj.pos += self.vel
        self.age += dt
        self.obj.radius = 0.08 + 0.05 * math.sin(t * 2.2 + self.age + len(particles))
        self.obj.opacity = 0.50 + 0.34 * (0.5 + 0.5 * math.sin(t * 1.7 + self.age))
        if self.trail.npoints > 26:
            self.trail.clear()
            self.trail.append(pos=self.obj.pos)
        self.trail.append(pos=self.obj.pos)


class SignalPulse:
    def __init__(self, origin, color_value):
        self.age = 0
        self.obj = ring(pos=vector(origin.x, origin.y, origin.z), axis=vector(0, 1, 0), radius=0.22, thickness=0.025, color=color_value, opacity=0.56)

    def update(self, dt):
        self.age += dt
        fade = clamp(1 - self.age / 2.2, 0, 1)
        self.obj.radius = 0.22 + self.age * 2.1
        self.obj.opacity = 0.52 * fade
        self.obj.thickness = 0.016 + 0.018 * fade
        return self.age < 2.2

    def hide(self):
        self.obj.visible = False


class OrbitingError:
    def __init__(self, phase):
        self.phase = phase
        self.radius = random.uniform(2.0, 3.4)
        self.height = random.uniform(-0.7, 1.3)
        self.obj = sphere(pos=field_core.pos + vector(self.radius, self.height, 0), radius=0.13, color=PINK, opacity=0.72, emissive=True)
        self.line = curve(pos=[field_core.pos, self.obj.pos], radius=0.01, color=PINK, opacity=0.16)

    def update(self, t):
        a = t * (0.55 + 0.08 * self.radius) + self.phase
        wobble = 0.28 * math.sin(t * 1.7 + self.phase)
        self.obj.pos = field_core.pos + vector(self.radius * math.cos(a), self.height + wobble, self.radius * math.sin(a))
        self.line.clear()
        self.line.append(pos=field_core.pos)
        self.line.append(pos=self.obj.pos)


class FloatingOption:
    def __init__(self, text, index):
        self.age = 0
        self.index = index
        self.obj = label(pos=field_core.pos + vector(random.uniform(-2.4, 2.4), random.uniform(1.6, 3.2), random.uniform(-1.8, 1.8)), text=text, height=9, box=False, color=PURPLE, opacity=0)

    def update(self, dt, t):
        self.age += dt
        self.obj.pos.y += 0.006 * math.sin(t * 1.4 + self.index)
        self.obj.opacity = 0
        return self.age < 2.8

    def hide(self):
        self.obj.visible = False


def emit_panel_to_field(color_value):
    start = vector(-3.9, random.uniform(-2.0, 4.3), 0.35)
    end = field_core.pos + rand_vec(1.1)
    arc = curve(pos=[start, (start + end) * 0.5 + vector(0, 1.4, random.uniform(-0.5, 0.5)), end], radius=0.018, color=color_value, opacity=0.42)
    response_arcs.append({"obj": arc, "age": 0.0})


def add_connection_if_possible(color_value):
    if len(particles) < 2:
        return
    a = random.choice(particles)
    b = random.choice(particles)
    if a is b:
        return
    line = curve(pos=[a.obj.pos, b.obj.pos], radius=0.015, color=color_value, opacity=0.35)
    connections.append({"line": line, "a": a, "b": b, "age": 0.0})


def create_shape_from_particles(color_value):
    center = field_core.pos + rand_vec(1.4)
    block = box(pos=center, size=vector(random.uniform(0.35, 0.75), random.uniform(0.18, 0.50), random.uniform(0.35, 0.75)), color=color_value, opacity=0.52)
    shape_blocks.append({"obj": block, "age": 0.0, "spin": random.uniform(-0.03, 0.03)})


def choose_next_line():
    n = len(particles)
    c = len(connections)
    o = len(orbits)
    s = len(shape_blocks)
    if n < 4:
        preferred = ["point", "listen"]
    elif c < max(1, n // 4):
        preferred = ["connect", "bend"]
    elif o < 2 and random.random() < 0.25:
        preferred = ["orbit"]
    elif s < 4 and random.random() < 0.30:
        preferred = ["shape"]
    elif random.random() < 0.20:
        preferred = ["split", "rewrite"]
    elif random.random() < 0.35:
        preferred = ["pulse", "brighten"]
    else:
        preferred = ["alive", "return", "listen", "point"]
    options = [line for line in possible_lines if line["kind"] in preferred] or possible_lines
    if line_kinds:
        options = [line for line in options if line["kind"] != line_kinds[-1]] or options
    return random.choice(options)


def apply_line_effect(kind):
    color_map = {
        "listen": CYAN,
        "point": BLUE,
        "connect": GREEN,
        "brighten": GOLD,
        "bend": PURPLE,
        "orbit": PINK,
        "shape": ORANGE,
        "pulse": CYAN,
        "rewrite": PURPLE,
        "alive": GREEN,
        "split": PINK,
        "return": GOLD,
    }
    color_value = color_map.get(kind, CYAN)
    emit_panel_to_field(color_value)
    if kind in ["listen", "point", "alive", "return"]:
        for _ in range(random.randint(1, 3)):
            particles.append(CodeParticle(field_core.pos + rand_vec(random.uniform(0.8, 2.8)), color_value, kind))
    if kind in ["connect", "bend", "rewrite", "alive"]:
        for _ in range(random.randint(1, 3)):
            add_connection_if_possible(color_value)
    if kind in ["pulse", "brighten", "listen", "return"]:
        pulses.append(SignalPulse(field_core.pos, color_value))
    if kind == "orbit":
        orbits.append(OrbitingError(random.uniform(0, 2 * math.pi)))
    if kind == "shape":
        create_shape_from_particles(color_value)
    if kind == "split":
        for i, option in enumerate(["maybe curve", "maybe pulse", "maybe orbit"]):
            ghost_options.append(FloatingOption(option, i))
    field_core.color = lerp(field_core.color, color_value, 0.45)
    intuition_orb.color = color_value


def add_next_intuitive_line():
    line = choose_next_line()
    current_lines.append(line["text"])
    line_kinds.append(line["kind"])
    redraw_code_labels(active_index=len(current_lines) - 1)
    apply_line_effect(line["kind"])


for text in base_lines:
    current_lines.append(text)
    line_kinds.append("base")
redraw_code_labels(active_index=len(current_lines) - 1)

status_label = label(pos=vector(1.2, 6.1, -4.7), text="", height=13, box=False, color=INK, opacity=0)
feedback_label = label(pos=vector(4.4, -3.1, 4.2), text="", height=11, box=False, color=INK, opacity=0)
intuition_back = box(pos=vector(4.4, -3.65, 4.2), size=vector(5.8, 0.18, 0.12), color=GRAY, opacity=0.55)
intuition_fill = box(pos=vector(1.55, -3.65, 4.28), size=vector(0.1, 0.32, 0.16), color=PURPLE, opacity=0.85)

paused = False
camera_mode = 0
intuition_speed = 1.0
time_since_line = 0.0
next_line_interval = 2.1
sim_time = 0.0


def clear_dynamic_objects():
    for p in particles:
        p.obj.visible = False
        p.trail.visible = False
    particles.clear()
    for item in connections:
        item["line"].visible = False
    connections.clear()
    for p in pulses:
        p.hide()
    pulses.clear()
    for o in orbits:
        o.obj.visible = False
        o.line.visible = False
    orbits.clear()
    for item in shape_blocks:
        item["obj"].visible = False
    shape_blocks.clear()
    for item in response_arcs:
        item["obj"].visible = False
    response_arcs.clear()
    for item in ghost_options:
        item.hide()
    ghost_options.clear()


def reset_simulation():
    global current_lines, line_kinds, time_since_line, sim_time, intuition_speed
    clear_dynamic_objects()
    current_lines = []
    line_kinds = []
    for text in base_lines:
        current_lines.append(text)
        line_kinds.append("base")
    redraw_code_labels(active_index=len(current_lines) - 1)
    field_core.pos = vector(4.3, 0.7, 0)
    field_core.color = CYAN
    field_core.radius = 0.35
    field_ring.radius = 3.2
    intuition_orb.color = PURPLE
    intuition_speed = 1.0
    time_since_line = 0.0
    sim_time = 0.0


def on_keydown(evt):
    global paused, camera_mode, intuition_speed
    key = evt.key
    if key == " ":
        paused = not paused
    elif key in ["r", "R"]:
        reset_simulation()
    elif key in ["n", "N"]:
        add_next_intuitive_line()
    elif key in ["c", "C"]:
        camera_mode = (camera_mode + 1) % 3
    elif key == "up":
        intuition_speed = clamp(intuition_speed + 0.18, 0.35, 2.8)
    elif key == "down":
        intuition_speed = clamp(intuition_speed - 0.18, 0.35, 2.8)


scene.bind("keydown", on_keydown)

while True:
    rate(60)
    if paused:
        continue

    dt = 1.0 / 60.0
    sim_time += dt
    time_since_line += dt * intuition_speed

    dynamic_activity = len(particles) * 0.05 + len(connections) * 0.03 + len(pulses) * 0.08 + len(orbits) * 0.10
    interval = clamp(next_line_interval - dynamic_activity, 0.85, 2.4)
    if time_since_line > interval and len(current_lines) < 44:
        add_next_intuitive_line()
        time_since_line = 0.0

    cursor.opacity = 0.20 + 0.75 * (0.5 + 0.5 * math.sin(sim_time * 8.0))

    for i, lbl in enumerate(line_labels):
        if i == len(line_labels) - 1:
            lbl.color = lerp(INK, ORANGE, 0.5 + 0.5 * math.sin(sim_time * 5.0))
        else:
            lbl.color = INK

    for p in particles:
        p.update(dt, sim_time)

    live_connections = []
    for item in connections:
        item["age"] += dt
        a = item["a"]
        b = item["b"]
        item["line"].clear()
        item["line"].append(pos=a.obj.pos)
        mid = (a.obj.pos + b.obj.pos) * 0.5 + vector(0, 0.18 * math.sin(sim_time * 2 + item["age"]), 0)
        item["line"].append(pos=mid)
        item["line"].append(pos=b.obj.pos)
        item["line"].opacity = 0.20 + 0.22 * (0.5 + 0.5 * math.sin(sim_time * 2.2 + item["age"]))
        if item["age"] < 18:
            live_connections.append(item)
        else:
            item["line"].visible = False
    connections[:] = live_connections

    live_pulses = []
    for p in pulses:
        if p.update(dt):
            live_pulses.append(p)
        else:
            p.hide()
    pulses[:] = live_pulses

    for o in orbits:
        o.update(sim_time)

    live_shapes = []
    for item in shape_blocks:
        item["age"] += dt
        item["obj"].rotate(angle=item["spin"], axis=vector(0, 1, 0))
        item["obj"].opacity = 0.34 + 0.24 * (0.5 + 0.5 * math.sin(sim_time * 1.3 + item["age"]))
        if item["age"] < 26:
            live_shapes.append(item)
        else:
            item["obj"].visible = False
    shape_blocks[:] = live_shapes

    live_arcs = []
    for item in response_arcs:
        item["age"] += dt
        fade = clamp(1 - item["age"] / 1.8, 0, 1)
        item["obj"].opacity = 0.42 * fade
        item["obj"].radius = 0.012 + 0.018 * fade
        if item["age"] < 1.8:
            live_arcs.append(item)
        else:
            item["obj"].visible = False
    response_arcs[:] = live_arcs

    live_options = []
    for option in ghost_options:
        if option.update(dt, sim_time):
            live_options.append(option)
        else:
            option.hide()
    ghost_options[:] = live_options

    activity = clamp((len(particles) + len(connections) + len(orbits) * 2 + len(shape_blocks)) / 34.0, 0, 1)
    field_core.radius = 0.35 + 0.26 * activity + 0.05 * math.sin(sim_time * 4.0)
    field_core.pos = vector(4.3 + 0.18 * math.sin(sim_time * 0.8), 0.7 + 0.15 * math.sin(sim_time * 1.2), 0.12 * math.cos(sim_time * 0.7))
    field_ring.pos = field_core.pos
    field_ring.radius = 3.2 + 0.45 * activity + 0.08 * math.sin(sim_time * 2.4)
    field_ring.opacity = 0.26 + 0.28 * activity
    field_ring.rotate(angle=0.01 + 0.015 * activity, axis=vector(0, 1, 0))

    intuition_orb.pos = vector(0.2 + 0.35 * math.sin(sim_time * 0.9), 5.25 + 0.18 * math.sin(sim_time * 1.7), 0.5 * math.cos(sim_time * 0.8))
    intuition_halo.pos = intuition_orb.pos
    intuition_halo.radius = 0.72 + 0.12 * math.sin(sim_time * 3.0)
    intuition_halo.rotate(angle=0.035, axis=vector(0, 1, 0))

    fill = clamp(time_since_line / max(0.1, interval), 0, 1)
    intuition_fill.size.x = 5.6 * fill
    intuition_fill.pos.x = 1.6 + intuition_fill.size.x / 2.0
    intuition_fill.color = lerp(PURPLE, GOLD, fill)

    last_kind = line_kinds[-1] if line_kinds else "base"
    status_label.text = f"lines written: {len(current_lines)}\nlast response: {last_kind}\nvisible activity: {activity:.2f}"
    feedback_label.text = f"the simulation responds first\nthen the next line appears\nintuition speed: {intuition_speed:.2f}"

    for i, line in enumerate(grid_lines):
        line.opacity = 0.12 + 0.08 * (0.5 + 0.5 * math.sin(sim_time * 0.5 + i))

    if camera_mode == 0:
        scene.center = vector(0, 1.1, 0)
        scene.forward = vector(-0.45, -0.22, -0.86)
        scene.range = 18
    elif camera_mode == 1:
        scene.center = vector(-5.8, 0.9, 0)
        scene.forward = vector(-0.12, -0.08, -0.99)
        scene.range = 8.2
    else:
        scene.center = field_core.pos
        scene.forward = vector(-0.70, -0.28, -0.66)
        scene.range = 8.8
