"""
Algebra Octopus v1
------------------
A VPython simulation of an organism that plays with algebra.

The octopus has multiple arms that reach for floating algebra terms. It tries to
balance a simple equation by moving terms between left and right trays,
canceling opposites, and isolating x.

Controls
- H: toggle help panel
- P: pause/resume
- R: reset round
- M: switch mode
- WASD: nudge octopus on the plane
- Space / C: move octopus up/down
- Arrow keys: pan camera target
- J/L: rotate camera left/right
- I/K: rotate camera up/down
- +/-: zoom camera

Requires:
    pip install vpython
Run:
    python algebra_octopus_v1.py
"""

from vpython import *
import random
import math
from dataclasses import dataclass

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Algebra Octopus v1",
    width=1200,
    height=760,
    background=vector(0.93, 0.96, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.45, -0.35, -0.82)
scene.up = vector(0, 1, 0)
scene.range = 13

WORLD_LIMIT = 10.5
GROUND_Y = -0.12
PAUSED = False
SHOW_HELP = True

# Math/equation state: left side and right side are lists of terms.
# term kind can be "x" or "const". coefficient may be negative.
@dataclass
class TermData:
    kind: str
    coeff: int
    side: str
    obj: object = None
    label: object = None
    held_by: int | None = None
    target: vector | None = None
    age: float = 0.0

# -----------------------------
# Utility functions
# -----------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-6:
        return fallback
    return norm(v)


def lerp_vec(a, b, t):
    return a + (b - a) * clamp(t, 0, 1)


def term_text(term: TermData):
    c = term.coeff
    if term.kind == "x":
        if c == 1:
            return "x"
        if c == -1:
            return "-x"
        return f"{c}x"
    return str(c)


def display_side(terms):
    if not terms:
        return "0"
    parts = []
    for t in terms:
        txt = term_text(t)
        if not parts:
            parts.append(txt)
        elif t.coeff >= 0:
            parts.append("+ " + txt)
        else:
            parts.append("- " + txt.replace("-", "", 1))
    return " ".join(parts)


def equation_text():
    left = [t for t in terms if t.side == "L"]
    right = [t for t in terms if t.side == "R"]
    return display_side(left) + "  =  " + display_side(right)


def evaluate_terms(side, x_value):
    total = 0
    for t in terms:
        if t.side != side:
            continue
        total += t.coeff * x_value if t.kind == "x" else t.coeff
    return total


def algebra_counts():
    lx = sum(t.coeff for t in terms if t.side == "L" and t.kind == "x")
    rx = sum(t.coeff for t in terms if t.side == "R" and t.kind == "x")
    lc = sum(t.coeff for t in terms if t.side == "L" and t.kind == "const")
    rc = sum(t.coeff for t in terms if t.side == "R" and t.kind == "const")
    return lx, lc, rx, rc


def current_solution_hint():
    # Rearrange: (lx-rx)x = rc-lc
    lx, lc, rx, rc = algebra_counts()
    a = lx - rx
    b = rc - lc
    if a == 0:
        return "no unique x" if b != 0 else "all x"
    val = b / a
    if abs(val - round(val)) < 1e-6:
        return f"x = {int(round(val))}"
    return f"x = {val:.2f}"


def make_mat(pos, size, color_value):
    base = box(pos=pos, size=size, color=color_value, opacity=0.55)
    rim1 = cylinder(pos=pos + vector(-size.x/2, 0.04, -size.z/2), axis=vector(size.x, 0, 0), radius=0.025, color=color.gray(0.45))
    rim2 = cylinder(pos=pos + vector(-size.x/2, 0.04, size.z/2), axis=vector(size.x, 0, 0), radius=0.025, color=color.gray(0.45))
    rim3 = cylinder(pos=pos + vector(-size.x/2, 0.04, -size.z/2), axis=vector(0, 0, size.z), radius=0.025, color=color.gray(0.45))
    rim4 = cylinder(pos=pos + vector(size.x/2, 0.04, -size.z/2), axis=vector(0, 0, size.z), radius=0.025, color=color.gray(0.45))
    return [base, rim1, rim2, rim3, rim4]


def make_term_visual(term: TermData, pos):
    hue = vector(0.35, 0.55, 1.0) if term.kind == "x" else vector(0.95, 0.72, 0.28)
    if term.coeff < 0:
        hue = vector(0.95, 0.42, 0.42)
    shape = sphere(pos=pos, radius=0.42 if term.kind == "x" else 0.34, color=hue, shininess=0.25)
    shape.emissive = False
    lbl = label(
        pos=pos + vector(0, 0.65, 0),
        text=term_text(term),
        height=15,
        color=color.black,
        box=False,
        opacity=0,
        billboard=True,
    )
    term.obj = shape
    term.label = lbl
    term.target = pos


def place_terms_neatly():
    left_terms = [t for t in terms if t.side == "L"]
    right_terms = [t for t in terms if t.side == "R"]
    for group, x_center in [(left_terms, -4.8), (right_terms, 4.8)]:
        for i, t in enumerate(group):
            row = i // 4
            col = i % 4
            x = x_center + (col - 1.5) * 1.2
            z = -1.2 + row * 1.1
            t.target = vector(x, 0.45, z)


def move_term_to_side(term: TermData, side):
    term.side = side
    place_terms_neatly()
    pulse_ring(vector(-4.8 if side == "L" else 4.8, 0.1, 0), vector(0.2, 0.8, 0.45))


def remove_term(term: TermData):
    if term.obj:
        term.obj.visible = False
    if term.label:
        term.label.visible = False
    if term in terms:
        terms.remove(term)
    place_terms_neatly()


def pulse_ring(pos, rgb):
    r = ring(pos=pos, axis=vector(0, 1, 0), radius=0.3, thickness=0.035, color=rgb, opacity=0.75)
    pulses.append({"obj": r, "age": 0.0})


def flash_text(txt, pos, rgb=vector(0.1, 0.2, 0.35)):
    lbl = label(pos=pos, text=txt, height=17, color=rgb, box=False, opacity=0, billboard=True)
    floaters.append({"obj": lbl, "age": 0.0, "base": vector(pos)})


# -----------------------------
# Static world
# -----------------------------
# Ground grid
box(pos=vector(0, GROUND_Y - 0.03, 0), size=vector(23, 0.04, 18), color=vector(0.88, 0.92, 0.95), opacity=0.9)
for x in range(-11, 12):
    curve(pos=[vector(x, GROUND_Y, -9), vector(x, GROUND_Y, 9)], color=vector(0.78, 0.84, 0.88), radius=0.006)
for z in range(-9, 10):
    curve(pos=[vector(-11, GROUND_Y, z), vector(11, GROUND_Y, z)], color=vector(0.78, 0.84, 0.88), radius=0.006)

# Equation trays
make_mat(vector(-4.8, 0.02, 0), vector(7.4, 0.08, 5.6), vector(0.72, 0.84, 1.0))
make_mat(vector(4.8, 0.02, 0), vector(7.4, 0.08, 5.6), vector(1.0, 0.86, 0.66))
label(pos=vector(-4.8, 0.25, -3.4), text="LEFT SIDE", height=18, color=color.black, box=False, opacity=0)
label(pos=vector(4.8, 0.25, -3.4), text="RIGHT SIDE", height=18, color=color.black, box=False, opacity=0)
label(pos=vector(0, 0.35, -0.1), text="=", height=40, color=color.black, box=False, opacity=0)

# Octopus body
body = sphere(pos=vector(0, 0.82, 4.0), radius=0.82, color=vector(0.55, 0.42, 0.95), shininess=0.35)
head = sphere(pos=body.pos + vector(0, 0.55, 0.05), radius=0.58, color=vector(0.62, 0.48, 1.0), shininess=0.35)
eye_l = sphere(pos=head.pos + vector(-0.22, 0.12, -0.47), radius=0.08, color=color.white)
eye_r = sphere(pos=head.pos + vector(0.22, 0.12, -0.47), radius=0.08, color=color.white)
pupil_l = sphere(pos=eye_l.pos + vector(0, 0, -0.055), radius=0.035, color=color.black)
pupil_r = sphere(pos=eye_r.pos + vector(0, 0, -0.055), radius=0.035, color=color.black)

arm_count = 8
arms = []
for i in range(arm_count):
    angle = 2 * math.pi * i / arm_count
    end = body.pos + vector(math.cos(angle) * 1.8, -0.15, math.sin(angle) * 1.0)
    arm = curve(pos=[body.pos, lerp_vec(body.pos, end, 0.5) + vector(0, -0.25, 0), end], color=vector(0.46, 0.32, 0.9), radius=0.07)
    tip = sphere(pos=end, radius=0.13, color=vector(0.72, 0.55, 1.0))
    arms.append({"curve": arm, "tip": tip, "target": end, "term": None, "cooldown": random.random() * 2.0})

# Labels
status = label(pos=vector(-10.8, 5.2, 0), text="", height=14, color=color.black, box=False, opacity=0, align="left")
help_label = label(pos=vector(7.1, 5.2, 0), text="", height=12, color=color.black, box=True, border=8, background=vector(0.98, 0.99, 1.0), opacity=0.72, align="left")
equation_label = label(pos=vector(0, 4.2, -2.5), text="", height=22, color=color.black, box=True, border=10, background=vector(1, 1, 1), opacity=0.65)

# Dynamic state
terms = []
pulses = []
floaters = []
mode_names = ["balance", "collect_x", "cancel", "isolate", "wander"]
mode_index = 0
mode = mode_names[mode_index]
clock = 0.0
round_id = 1
action_timer = 0.0
wander_goal = vector(0, 0.82, 4.0)
keys_down = set()


def reset_round():
    global terms, pulses, floaters, clock, action_timer, wander_goal, round_id
    for t in terms:
        if t.obj:
            t.obj.visible = False
        if t.label:
            t.label.visible = False
    for p in pulses:
        p["obj"].visible = False
    for f in floaters:
        f["obj"].visible = False
    terms = []
    pulses = []
    floaters = []
    clock = 0.0
    action_timer = 0.0
    body.pos = vector(0, 0.82, 4.0)
    head.pos = body.pos + vector(0, 0.55, 0.05)
    for obj, off in [(eye_l, vector(-0.22, 0.67, -0.42)), (eye_r, vector(0.22, 0.67, -0.42)), (pupil_l, vector(-0.22, 0.67, -0.475)), (pupil_r, vector(0.22, 0.67, -0.475))]:
        obj.pos = body.pos + off
    # Start with a solvable equation, varied per reset.
    # ax + b = c, where a in {1,2,3}; solution usually integer.
    a = random.choice([1, 2, 3])
    x_sol = random.choice([-3, -2, -1, 1, 2, 3, 4, 5])
    b = random.choice([-6, -4, -3, -2, 2, 3, 4, 6])
    c = a * x_sol + b
    raw = []
    raw.append(TermData("x", a, "L"))
    if b != 0:
        raw.append(TermData("const", b, "L"))
    raw.append(TermData("const", c, "R"))
    # Add cancelable decoys, so the octopus has visible play.
    if random.random() < 0.8:
        k = random.choice([1, 2, 3])
        raw.append(TermData("const", k, "L"))
        raw.append(TermData("const", -k, "L"))
    if random.random() < 0.5:
        raw.append(TermData("x", 1, "R"))
        raw.append(TermData("x", -1, "R"))
    terms.extend(raw)
    place_terms_neatly()
    for t in terms:
        jitter = vector(random.uniform(-0.25, 0.25), 0, random.uniform(-0.25, 0.25))
        make_term_visual(t, t.target + jitter)
    wander_goal = vector(random.uniform(-6, 6), 0.82, random.uniform(1.5, 6.3))
    round_id += 1
    flash_text("new equation", vector(0, 2.1, 2.3), vector(0.1, 0.25, 0.6))


def choose_cancel_pair():
    for side in ["L", "R"]:
        side_terms = [t for t in terms if t.side == side]
        for a in side_terms:
            for b in side_terms:
                if a is not b and a.kind == b.kind and a.coeff + b.coeff == 0:
                    return a, b
    return None


def choose_term_to_move():
    lx, lc, rx, rc = algebra_counts()
    # Prefer moving right-side x terms left, and left-side constants right.
    candidates = []
    for t in terms:
        score = 0
        if t.side == "R" and t.kind == "x":
            score += 6
        if t.side == "L" and t.kind == "const":
            score += 5
        if mode == "collect_x" and t.kind == "x":
            score += 3
        if mode == "isolate" and t.kind == "const":
            score += 3
        if mode == "balance":
            score += random.random() * 2
        if t.held_by is None and score > 0:
            candidates.append((score + random.random(), t))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def perform_algebra_action():
    pair = choose_cancel_pair()
    if pair and mode in ["balance", "cancel"]:
        a, b = pair
        pos = (a.obj.pos + b.obj.pos) * 0.5
        flash_text(f"cancel {term_text(a)} and {term_text(b)}", pos + vector(0, 1.2, 0), vector(0.55, 0.1, 0.1))
        pulse_ring(pos, vector(1.0, 0.35, 0.35))
        remove_term(a)
        remove_term(b)
        return
    t = choose_term_to_move()
    if not t:
        flash_text("balanced play", body.pos + vector(0, 1.6, 0), vector(0.1, 0.35, 0.2))
        return
    # Move across the equals sign: sign changes when crossing sides.
    old = t.side
    t.coeff *= -1
    move_term_to_side(t, "R" if old == "L" else "L")
    flash_text(f"move {term_text(t)}", t.target + vector(0, 1.2, 0), vector(0.15, 0.25, 0.55))


def update_octopus(dt):
    global wander_goal
    # Human nudging.
    move = vector(0, 0, 0)
    if "w" in keys_down:
        move.z -= 1
    if "s" in keys_down:
        move.z += 1
    if "a" in keys_down:
        move.x -= 1
    if "d" in keys_down:
        move.x += 1
    if " " in keys_down:
        move.y += 1
    if "c" in keys_down:
        move.y -= 1
    if mag(move) > 0:
        body.pos += safe_norm(move) * 3.0 * dt

    # Autonomous wandering near the equation trays.
    if mag(body.pos - wander_goal) < 0.55 or random.random() < 0.006:
        if mode == "wander":
            wander_goal = vector(random.uniform(-7.5, 7.5), 0.82, random.uniform(-2.3, 6.7))
        else:
            # Drift toward uncrowded terms and across both sides.
            if terms and random.random() < 0.7:
                focus = random.choice(terms).obj.pos
                wander_goal = vector(clamp(focus.x + random.uniform(-1.7, 1.7), -8, 8), 0.82, clamp(focus.z + random.uniform(0.8, 2.5), -2.5, 6.8))
            else:
                wander_goal = vector(random.uniform(-7.5, 7.5), 0.82, random.uniform(-2.0, 6.7))
    auto_dir = wander_goal - body.pos
    body.pos += safe_norm(auto_dir, vector(1, 0, 0)) * (1.15 if mode != "wander" else 1.55) * dt
    body.pos.x = clamp(body.pos.x, -WORLD_LIMIT, WORLD_LIMIT)
    body.pos.z = clamp(body.pos.z, -8.0, 8.0)
    body.pos.y = clamp(body.pos.y, 0.45, 2.6)

    head.pos = body.pos + vector(0, 0.55 + 0.05 * math.sin(clock * 2.6), 0.05)
    eye_l.pos = head.pos + vector(-0.22, 0.12, -0.47)
    eye_r.pos = head.pos + vector(0.22, 0.12, -0.47)
    pupil_l.pos = eye_l.pos + vector(0, 0, -0.055)
    pupil_r.pos = eye_r.pos + vector(0, 0, -0.055)


def update_arms(dt):
    # Assign arms to nearby/high-value terms.
    available = [t for t in terms if t.held_by is None]
    for i, arm in enumerate(arms):
        arm["cooldown"] -= dt
        if arm["term"] is None and arm["cooldown"] <= 0 and available:
            # Bias toward useful algebra terms but still let arms play.
            best = None
            best_score = -999
            for t in available:
                dist = mag(t.obj.pos - body.pos)
                score = -dist
                if t.side == "R" and t.kind == "x":
                    score += 2.0
                if t.side == "L" and t.kind == "const":
                    score += 1.5
                if random.random() < 0.25:
                    score += random.random() * 2
                if score > best_score:
                    best_score = score
                    best = t
            if best is not None:
                arm["term"] = best
                best.held_by = i
                available.remove(best)
        t = arm["term"]
        base_angle = 2 * math.pi * i / arm_count + 0.25 * math.sin(clock + i)
        idle_tip = body.pos + vector(math.cos(base_angle) * 1.6, -0.22 + 0.07 * math.sin(clock * 2 + i), math.sin(base_angle) * 1.1)
        if t is not None and t in terms:
            target = t.obj.pos + vector(0, 0.15, 0)
            if mag(target - arm["tip"].pos) < 0.25:
                # Arm briefly carries the term toward its layout target, then releases.
                t.obj.pos = lerp_vec(t.obj.pos, t.target, 0.08)
                t.label.pos = t.obj.pos + vector(0, 0.65, 0)
                if mag(t.obj.pos - t.target) < 0.18:
                    t.held_by = None
                    arm["term"] = None
                    arm["cooldown"] = random.uniform(0.8, 2.2)
            tip_goal = target
        else:
            if t is not None:
                arm["term"] = None
            tip_goal = idle_tip
        arm["tip"].pos = lerp_vec(arm["tip"].pos, tip_goal, 0.18)
        mid = lerp_vec(body.pos, arm["tip"].pos, 0.55) + vector(0, -0.35 - 0.08 * math.sin(clock * 2 + i), 0)
        arm["curve"].clear()
        arm["curve"].append(body.pos)
        arm["curve"].append(mid)
        arm["curve"].append(arm["tip"].pos)


def update_terms(dt):
    for t in list(terms):
        t.age += dt
        if t.held_by is None:
            t.obj.pos = lerp_vec(t.obj.pos, t.target, 0.045)
        # Gentle bobbing without changing target layout.
        t.obj.pos.y = 0.45 + 0.035 * math.sin(clock * 2.0 + t.age + t.coeff)
        t.label.pos = t.obj.pos + vector(0, 0.65, 0)
        # Highlight terms that are algebraically useful.
        useful = (t.side == "R" and t.kind == "x") or (t.side == "L" and t.kind == "const")
        if useful:
            t.obj.opacity = 0.95
            t.obj.radius = (0.42 if t.kind == "x" else 0.34) * (1.0 + 0.04 * math.sin(clock * 5))
        else:
            t.obj.opacity = 0.85


def update_effects(dt):
    for p in list(pulses):
        p["age"] += dt
        obj = p["obj"]
        obj.radius += dt * 1.6
        obj.opacity = max(0, 0.75 * (1 - p["age"] / 1.1))
        if p["age"] > 1.1:
            obj.visible = False
            pulses.remove(p)
    for f in list(floaters):
        f["age"] += dt
        f["obj"].pos = f["base"] + vector(0, f["age"] * 0.8, 0)
        if f["age"] > 1.5:
            f["obj"].visible = False
            floaters.remove(f)


def update_labels():
    equation_label.text = equation_text()
    lx, lc, rx, rc = algebra_counts()
    balance_error = abs(evaluate_terms("L", 2) - evaluate_terms("R", 2))
    status.text = (
        f"Algebra Octopus v1 | round {round_id}\n"
        f"mode: {mode}\n"
        f"equation: {equation_text()}\n"
        f"left: {lx}x + {lc}    right: {rx}x + {rc}\n"
        f"solution hint: {current_solution_hint()}\n"
        f"terms: {len(terms)} | action timer: {action_timer:.1f}\n"
        f"test balance at x=2 error: {balance_error}\n"
        f"P pause | M mode | R reset | H help"
    )
    if SHOW_HELP:
        help_label.visible = True
        help_label.text = (
            "Controls\n"
            "WASD: nudge octopus\n"
            "Space/C: up/down\n"
            "M: switch algebra mode\n"
            "P: pause/resume\n"
            "R: reset equation\n"
            "H: help\n"
            "Arrows: pan camera\n"
            "J/L and I/K: rotate view\n"
            "+/-: zoom\n\n"
            "Behavior\n"
            "Arms grab terms.\n"
            "Opposite terms cancel.\n"
            "Crossing '=' flips signs.\n"
            "Goal: isolate x."
        )
    else:
        help_label.visible = False


def handle_keydown(evt):
    global PAUSED, SHOW_HELP, mode_index, mode
    key = evt.key.lower()
    keys_down.add(key)
    if key == "p":
        PAUSED = not PAUSED
    elif key == "h":
        SHOW_HELP = not SHOW_HELP
    elif key == "r":
        reset_round()
    elif key == "m":
        mode_index = (mode_index + 1) % len(mode_names)
        mode = mode_names[mode_index]
        flash_text(f"mode: {mode}", body.pos + vector(0, 1.7, 0), vector(0.15, 0.2, 0.55))
    elif key == "left":
        scene.center.x -= 0.6
    elif key == "right":
        scene.center.x += 0.6
    elif key == "up":
        scene.center.z -= 0.6
    elif key == "down":
        scene.center.z += 0.6
    elif key == "j":
        scene.forward = rotate(scene.forward, angle=0.08, axis=vector(0, 1, 0))
    elif key == "l":
        scene.forward = rotate(scene.forward, angle=-0.08, axis=vector(0, 1, 0))
    elif key == "i":
        scene.forward = rotate(scene.forward, angle=0.06, axis=vector(1, 0, 0))
    elif key == "k":
        scene.forward = rotate(scene.forward, angle=-0.06, axis=vector(1, 0, 0))
    elif key in ["+", "="]:
        scene.range = max(5, scene.range * 0.92)
    elif key in ["-", "_"]:
        scene.range = min(24, scene.range * 1.08)


def handle_keyup(evt):
    key = evt.key.lower()
    if key in keys_down:
        keys_down.remove(key)


scene.bind("keydown", handle_keydown)
scene.bind("keyup", handle_keyup)

# Initialize
reset_round()

# -----------------------------
# Main loop
# -----------------------------
while True:
    rate(60)
    dt = 1 / 60
    if PAUSED:
        update_labels()
        continue
    clock += dt
    action_timer += dt

    # Action cadence changes by mode.
    interval = {
        "balance": 3.3,
        "collect_x": 2.9,
        "cancel": 2.2,
        "isolate": 2.7,
        "wander": 4.6,
    }[mode]
    if action_timer > interval:
        action_timer = 0.0
        perform_algebra_action()
        # When equation becomes too reduced, restart after a visible solved state.
        if len(terms) <= 2 and random.random() < 0.25:
            flash_text("solved / rebirth", vector(0, 2.4, 1.2), vector(0.1, 0.45, 0.2))

    # If the octopus has nearly isolated x, pause action briefly then reset later.
    lx, lc, rx, rc = algebra_counts()
    if len(terms) <= 2 and abs(lx - rx) > 0 and abs(lc) + abs(rx) == 0 and clock > 12:
        if random.random() < 0.008:
            reset_round()

    update_octopus(dt)
    update_arms(dt)
    update_terms(dt)
    update_effects(dt)
    update_labels()
