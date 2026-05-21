#!/usr/bin/env python3
"""
Meaning Network — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python meaning_network_ai_simulation.py

Keyboard controls:
    H controls | A toggle AI | P pause | R reset | M cycle AI mode
    TAB select next node | SPACE activate selected word | N spill new word
    X detach link | Z repair/add link | C clear pulses/marks | O orbit node
    B metaphor-wrap selected | V mark selected | 1-6 relation theme pulse
    W/S forward/back | D right | Q/E down/up | arrows pan camera | J/L/I/K rotate
    +/- speed. Click a word node to select and activate it.

The simulation shows words as nodes and synonym, antonym, category, cause,
effect, and metaphor links as colored edges. Activating a word sends pulses
through related meanings. A rule-based AI state machine reads the scene,
chooses actions, changes behavior modes, detects stagnation/completion, and
starts a new round when the network becomes stable, empty, sparse, or complete.
"""

from vpython import canvas, vector, sphere, cylinder, box, ring, label, color, rate, mag, norm, cross, curve, arrow, local_light
from dataclasses import dataclass, field
import random as rnd
import math

# ----------------------------- Scene ---------------------------------------
scene = canvas(title="Meaning Network — semantic pulses and expressive AI", width=1280, height=820,
               background=vector(0.94, 0.97, 1.0), center=vector(0, 0, 0))
scene.forward = vector(-0.35, -0.25, -1.0)
scene.up = vector(0, 1, 0)
scene.range = 17
scene.userspin = True
scene.userzoom = True
local_light(pos=vector(6, 7, 6), color=vector(0.8, 0.85, 1.0))
local_light(pos=vector(-8, -4, 5), color=vector(0.6, 0.75, 0.95))
box(pos=vector(0, -5.8, 0), size=vector(32, 0.04, 24), color=vector(0.86, 0.91, 0.96), opacity=0.45)
status = label(pos=vector(0, 8.2, 0), text="Meaning Network | H controls", height=14,
               color=vector(0.12, 0.14, 0.22), box=False, opacity=0)
legend = label(pos=vector(-15, 6.3, 0), height=10, color=vector(0.13, 0.15, 0.2), box=True,
               border=8, background=vector(1, 1, 1), opacity=0.38,
               text="Link colors:\nsynonym blue | antonym red | category green\ncause orange | effect violet | metaphor gold")

# ----------------------------- Config --------------------------------------
LINK_COLORS = {
    "synonym": vector(0.20, 0.47, 0.95), "antonym": vector(0.95, 0.25, 0.24),
    "category": vector(0.20, 0.68, 0.36), "cause": vector(0.95, 0.55, 0.18),
    "effect": vector(0.58, 0.38, 0.95), "metaphor": vector(0.98, 0.76, 0.22)
}
RELATION_TYPES = ["synonym", "antonym", "category", "cause", "effect", "metaphor"]
NODE_BASE = vector(0.72, 0.78, 0.86)
NODE_SELECTED = vector(0.18, 0.34, 0.92)
NODE_MARKED = vector(0.15, 0.66, 0.43)
NODE_HOT = vector(1.0, 0.84, 0.16)
WORDS = ["light", "bright", "dark", "shadow", "sun", "star", "fire", "warmth", "growth", "tree", "root",
         "branch", "idea", "thought", "memory", "dream", "hope", "fear", "risk", "change", "motion", "river",
         "time", "path", "home", "city", "machine", "heart", "storm", "voice", "music", "silence", "seed",
         "flower", "mirror", "ocean"]
INITIAL_LINKS = [
    ("light", "bright", "synonym"), ("light", "dark", "antonym"), ("dark", "shadow", "category"),
    ("sun", "star", "category"), ("sun", "light", "cause"), ("fire", "warmth", "cause"),
    ("warmth", "growth", "effect"), ("growth", "tree", "effect"), ("tree", "root", "category"),
    ("tree", "branch", "category"), ("root", "idea", "metaphor"), ("branch", "thought", "metaphor"),
    ("thought", "idea", "synonym"), ("memory", "thought", "cause"), ("dream", "hope", "cause"),
    ("fear", "risk", "cause"), ("risk", "change", "cause"), ("change", "motion", "effect"),
    ("motion", "river", "metaphor"), ("river", "time", "metaphor"), ("time", "memory", "cause"),
    ("path", "home", "effect"), ("city", "machine", "metaphor"), ("heart", "home", "metaphor"),
    ("storm", "fear", "metaphor"), ("voice", "music", "category"), ("music", "silence", "antonym"),
    ("seed", "flower", "effect"), ("seed", "hope", "metaphor"), ("mirror", "memory", "metaphor"),
    ("ocean", "dream", "metaphor"), ("ocean", "storm", "cause")]

# ----------------------------- Helpers -------------------------------------
def clamp(x, lo, hi): return max(lo, min(hi, x))
def rand_vec(s=1.0): return vector(rnd.uniform(-s, s), rnd.uniform(-s, s), rnd.uniform(-s, s))
def safe_norm(v, fallback=vector(1, 0, 0)): return fallback if mag(v) < 1e-6 else v / mag(v)
def lerp(a, b, t): return a * (1 - t) + b * t
def key_for(a, b, rel): return tuple(sorted([a, b])) + (rel,)
def shell_point(r=7.0):
    th, ph = rnd.uniform(0, 2 * math.pi), rnd.uniform(-0.65, 0.65)
    return vector(r * math.cos(th) * math.cos(ph), r * math.sin(ph), r * math.sin(th) * math.cos(ph))

# ----------------------------- Data ----------------------------------------
@dataclass
class MeaningNode:
    word: str
    pos: vector
    vel: vector = field(default_factory=lambda: vector(0, 0, 0))
    activation: float = 0.0
    selected: bool = False
    marked: bool = False
    orbiting: bool = False
    orbit_angle: float = 0.0
    orbit_radius: float = 1.0
    body: object = None
    text: object = None
    halo: object = None
    trail: object = None

@dataclass
class MeaningLink:
    a: str
    b: str
    relation: str
    strength: float = 1.0
    active: float = 0.0
    body: object = None
    arrow_body: object = None

@dataclass
class Pulse:
    a: str
    b: str
    relation: str
    t: float = 0.0
    speed: float = 0.85
    strength: float = 1.0
    body: object = None
    trail: object = None

@dataclass
class Marker:
    pos: vector
    life: float
    body: object

@dataclass
class AIController:
    enabled: bool = True
    mode: str = "curious"
    timer: float = 0.0
    action_timer: float = 0.0
    last_signature: float = 0.0
    stable_time: float = 0.0
    completion_time: float = 0.0
    loop_count: int = 1
    focus_word: str = "light"
    recent_modes: list = field(default_factory=list)

nodes, links, link_lookup, pulses, markers = {}, [], set(), [], []
selected_index, selected_word = 0, None
paused, sim_speed, theme_filter, sim_time = False, 1.0, None, 0.0
keys_down = set()
manual_velocity = vector(0, 0, 0)
ai = AIController()
AI_MODES = ["curious", "constructive", "careful", "chaotic", "ritual", "artistic", "destructive", "playful"]

# ----------------------------- Build objects -------------------------------
def create_node(word, pos=None):
    if word in nodes: return nodes[word]
    pos = shell_point(rnd.uniform(4.5, 8.8)) if pos is None else pos
    n = MeaningNode(word=word, pos=pos, vel=rand_vec(0.025), orbit_radius=max(2.0, mag(pos)))
    n.body = sphere(pos=pos, radius=0.36, color=NODE_BASE, opacity=0.92, shininess=0.65)
    n.text = label(pos=pos + vector(0, 0.62, 0), text=word, height=10, color=vector(0.1, 0.13, 0.2),
                   box=True, background=vector(1, 1, 1), border=5, opacity=0.35)
    n.halo = ring(pos=pos, axis=vector(0, 1, 0), radius=0.55, thickness=0.025,
                  color=LINK_COLORS["metaphor"], opacity=0.0)
    n.trail = curve(color=vector(0.35, 0.50, 0.95), radius=0.018)
    nodes[word] = n
    return n

def create_link(a, b, relation, strength=1.0):
    if a == b or a not in nodes or b not in nodes: return None
    k = key_for(a, b, relation)
    if k in link_lookup: return None
    link_lookup.add(k)
    axis = nodes[b].pos - nodes[a].pos
    if mag(axis) < 1e-6: axis = vector(1, 0, 0)
    body = cylinder(pos=nodes[a].pos, axis=axis, radius=0.035, color=LINK_COLORS[relation], opacity=0.28)
    arr = None
    if relation in ("cause", "effect"):
        arr = arrow(pos=nodes[a].pos + axis * 0.52, axis=safe_norm(axis) * 0.45,
                    shaftwidth=0.07, color=LINK_COLORS[relation], opacity=0.45)
    lk = MeaningLink(a, b, relation, strength, 0.0, body, arr)
    links.append(lk)
    return lk

def destroy_link(lk):
    if lk.body: lk.body.visible = False
    if lk.arrow_body: lk.arrow_body.visible = False
    link_lookup.discard(key_for(lk.a, lk.b, lk.relation))
    if lk in links: links.remove(lk)

def add_marker(pos, col=NODE_MARKED, life=4.0):
    markers.append(Marker(pos, life, ring(pos=pos, axis=vector(0, 1, 0), radius=0.75,
                                          thickness=0.025, color=col, opacity=0.7)))

def spawn_pulse(a, b, relation, strength=1.0):
    col = LINK_COLORS[relation]
    body = sphere(pos=nodes[a].pos, radius=0.16 + 0.05 * clamp(strength, 0, 2), color=col, opacity=0.95, emissive=True)
    tr = curve(color=col, radius=0.012)
    pulses.append(Pulse(a, b, relation, 0.0, 0.58 + 0.25 * strength, strength, body, tr))

def activate_node(word, amount=1.0, relation_filter=None):
    if word not in nodes: return
    n = nodes[word]
    n.activation = clamp(n.activation + amount, 0, 3.0)
    add_marker(n.pos, NODE_HOT, 1.8)
    for lk in list(links):
        other = lk.b if lk.a == word else (lk.a if lk.b == word else None)
        if other and (relation_filter is None or lk.relation == relation_filter):
            lk.active = clamp(lk.active + 1.0, 0, 2.5)
            spawn_pulse(word, other, lk.relation, amount * lk.strength)

def set_selected(word):
    global selected_word, selected_index
    if not nodes: return
    if word not in nodes: word = list(nodes.keys())[0]
    selected_word = word
    selected_index = list(nodes.keys()).index(word)
    for w, n in nodes.items(): n.selected = (w == word)

def select_next():
    global selected_index
    names = list(nodes.keys())
    if names:
        selected_index = (selected_index + 1) % len(names)
        set_selected(names[selected_index])

def spill_new_meaning(base_word=None):
    unused = [w for w in WORDS if w not in nodes]
    word = unused[0] if unused else "meaning_" + str(len(nodes) + 1)
    pos = nodes[base_word].pos + rand_vec(2.2) + vector(0, rnd.uniform(0.4, 1.4), 0) if base_word in nodes else shell_point()
    create_node(word, pos)
    existing = [w for w in nodes if w != word]
    for _ in range(rnd.randint(1, 3)):
        create_link(word, rnd.choice(existing), rnd.choice(RELATION_TYPES), rnd.uniform(0.55, 1.25))
    set_selected(word)
    activate_node(word, 1.2)

def repair_random_link():
    if len(nodes) < 2: return
    names = list(nodes.keys())
    for _ in range(35):
        a, b = rnd.sample(names, 2)
        rel = rnd.choice(RELATION_TYPES)
        if key_for(a, b, rel) not in link_lookup:
            create_link(a, b, rel, rnd.uniform(0.5, 1.2))
            activate_node(a, 0.65, rel)
            return

def detach_random_link():
    if links: destroy_link(sorted(links, key=lambda lk: lk.active + rnd.random())[0])

def mark_node(word):
    if word in nodes:
        nodes[word].marked = True
        add_marker(nodes[word].pos, NODE_MARKED, 5.5)

def wrap_node(word):
    if word in nodes:
        nodes[word].marked = True
        nodes[word].halo.opacity = 0.85
        nodes[word].halo.color = LINK_COLORS["metaphor"]
        add_marker(nodes[word].pos, LINK_COLORS["metaphor"], 4.0)

def toggle_orbit(word):
    if word in nodes:
        n = nodes[word]
        n.orbiting = not n.orbiting
        n.orbit_radius = max(1.2, mag(n.pos))
        n.orbit_angle = math.atan2(n.pos.z, n.pos.x)

def clear_visuals():
    for p in pulses:
        p.body.visible = False
        p.trail.visible = False
    pulses.clear()
    for m in markers: m.body.visible = False
    markers.clear()
    for n in nodes.values():
        n.activation, n.marked, n.orbiting, n.halo.opacity = 0.0, False, False, 0.0
        n.trail.visible = False
        n.trail = curve(color=vector(0.35, 0.50, 0.95), radius=0.018)

def network_signature():
    return sum(n.activation for n in nodes.values()) * 2.7 + sum(mag(n.vel) for n in nodes.values()) * 9 + len(links) * 0.55 + len(pulses) * 1.7 + sum(1 for n in nodes.values() if n.marked) * 0.8

def reset_simulation(seed=None):
    global nodes, links, link_lookup, pulses, markers, selected_index, selected_word, sim_time, theme_filter
    if seed is not None: rnd.seed(seed)
    for p in pulses:
        p.body.visible = False; p.trail.visible = False
    for m in markers: m.body.visible = False
    for lk in links:
        lk.body.visible = False
        if lk.arrow_body: lk.arrow_body.visible = False
    for n in nodes.values():
        n.body.visible = False; n.text.visible = False; n.halo.visible = False; n.trail.visible = False
    nodes, links, link_lookup, pulses, markers = {}, [], set(), [], []
    theme_filter, sim_time = None, 0.0
    for i, word in enumerate(WORDS[:24]):
        ang = 2 * math.pi * i / 24.0
        r = 6.5 + 1.5 * math.sin(i * 1.71)
        create_node(word, vector(r * math.cos(ang), 2.2 * math.sin(i * 0.67), r * math.sin(ang)))
    for a, b, rel in INITIAL_LINKS:
        if a in nodes and b in nodes: create_link(a, b, rel, rnd.uniform(0.7, 1.25))
    set_selected("light")
    activate_node("light", 1.8)
    ai.mode, ai.timer, ai.action_timer, ai.stable_time, ai.completion_time, ai.focus_word = "curious", 0, 0, 0, 0, "light"
    ai.last_signature = network_signature()

# ----------------------------- Dynamics ------------------------------------
def update_links():
    for lk in links:
        a, b = nodes[lk.a], nodes[lk.b]
        axis = b.pos - a.pos
        if mag(axis) < 1e-6: axis = vector(0.01, 0, 0)
        lk.body.pos, lk.body.axis = a.pos, axis
        lk.body.opacity = clamp(0.18 + lk.active * 0.25, 0.12, 0.85)
        lk.body.radius = 0.025 + 0.025 * clamp(lk.active, 0, 2)
        if lk.arrow_body:
            lk.arrow_body.pos = a.pos + axis * 0.52
            lk.arrow_body.axis = safe_norm(axis) * 0.45
            lk.arrow_body.opacity = clamp(0.28 + lk.active * 0.22, 0.2, 0.9)
        lk.active *= 0.985

def apply_force_layout(dt):
    names = list(nodes.keys())
    for i in range(len(names)):
        ni = nodes[names[i]]
        for j in range(i + 1, len(names)):
            nj = nodes[names[j]]
            delta = ni.pos - nj.pos
            d = max(0.6, mag(delta))
            f = delta / d * (0.16 / (d * d))
            ni.vel += f * dt; nj.vel -= f * dt
    ideals = {"synonym": 2.0, "antonym": 4.8, "category": 3.2, "cause": 3.7, "effect": 3.7, "metaphor": 5.5}
    for lk in links:
        a, b = nodes[lk.a], nodes[lk.b]
        delta = b.pos - a.pos
        d = max(0.1, mag(delta))
        direction = delta / d
        f = direction * ((d - ideals.get(lk.relation, 3.5)) * 0.035)
        a.vel += f * dt; b.vel -= f * dt
        if lk.relation == "metaphor":
            swirl = cross(direction, vector(0, 1, 0))
            if mag(swirl) > 1e-4: a.vel += norm(swirl) * 0.018 * dt; b.vel -= norm(swirl) * 0.018 * dt
        elif lk.relation == "antonym":
            a.vel += vector(0, 0.012, 0) * dt; b.vel -= vector(0, 0.012, 0) * dt
    for n in nodes.values(): n.vel += -n.pos * 0.006 * dt

def update_nodes(dt):
    global manual_velocity
    for n in nodes.values():
        if n.orbiting:
            n.orbit_angle += dt * (0.28 + 0.05 * n.activation)
            target = vector(n.orbit_radius * math.cos(n.orbit_angle), 1.3 * math.sin(n.orbit_angle * 0.7), n.orbit_radius * math.sin(n.orbit_angle))
            n.vel += (target - n.pos) * 0.06 * dt
        if n.selected and mag(manual_velocity) > 0: n.vel += manual_velocity * dt
        n.vel *= 0.965; n.pos += n.vel * dt
        for axis in ["x", "y", "z"]:
            lim = 6.5 if axis == "y" else 10.5
            val = getattr(n.pos, axis)
            if abs(val) > lim:
                setattr(n.pos, axis, clamp(val, -lim, lim)); setattr(n.vel, axis, -0.25 * getattr(n.vel, axis))
        n.activation *= 0.992
        base = NODE_SELECTED if n.selected else (NODE_MARKED if n.marked else NODE_BASE)
        glow = clamp(n.activation / 2.4, 0, 1)
        n.body.color = lerp(base, NODE_HOT, glow)
        n.body.radius = 0.35 + 0.12 * glow + (0.05 if n.selected else 0)
        n.body.pos = n.pos
        n.text.pos = n.pos + vector(0, 0.62 + 0.12 * glow, 0)
        n.text.height = 10 + (2 if n.selected else 0)
        n.halo.pos = n.pos
        n.halo.axis = vector(math.sin(sim_time * 0.5), 1, math.cos(sim_time * 0.5))
        if n.marked: n.halo.opacity = max(n.halo.opacity, 0.38)
        elif n.halo.opacity > 0: n.halo.opacity *= 0.985
        if n.activation > 0.35:
            n.trail.append(pos=n.pos)
            if n.trail.npoints > 80: n.trail.pop(0)
    manual_velocity = vector(0, 0, 0)

def update_pulses(dt):
    alive = []
    for p in pulses:
        if p.a not in nodes or p.b not in nodes:
            p.body.visible = False; p.trail.visible = False; continue
        p.t += dt * p.speed
        a, b = nodes[p.a], nodes[p.b]
        p.body.pos = lerp(a.pos, b.pos, clamp(p.t, 0, 1))
        p.body.opacity = clamp(1.05 - p.t * 0.8, 0, 1)
        p.body.radius = 0.13 + 0.08 * math.sin(p.t * math.pi)
        p.trail.append(pos=p.body.pos)
        if p.trail.npoints > 20: p.trail.pop(0)
        if p.t >= 1.0:
            b.activation = clamp(b.activation + 0.55 * p.strength, 0, 3.0)
            p.body.visible = False; p.trail.visible = False
            if rnd.random() < 0.22 * p.strength: activate_node(p.b, 0.35 * p.strength)
        else: alive.append(p)
    pulses[:] = alive

def update_markers(dt):
    alive = []
    for m in markers:
        m.life -= dt
        if m.life <= 0: m.body.visible = False
        else:
            m.body.radius += 0.16 * dt
            m.body.opacity = clamp(m.life / 4.0, 0, 0.8)
            alive.append(m)
    markers[:] = alive

def detect_collisions():
    names = list(nodes.keys())
    for i in range(len(names)):
        a = nodes[names[i]]
        if a.activation < 0.75: continue
        for j in range(i + 1, len(names)):
            b = nodes[names[j]]
            if b.activation > 0.75 and mag(a.pos - b.pos) < 0.82 and rnd.random() < 0.025:
                add_marker((a.pos + b.pos) * 0.5, LINK_COLORS["metaphor"], 2.0)
                if key_for(a.word, b.word, "metaphor") not in link_lookup and rnd.random() < 0.5: create_link(a.word, b.word, "metaphor", 0.65)
                spawn_pulse(a.word, b.word, "metaphor", 0.75)

# ----------------------------- AI ------------------------------------------
def get_state_for_ai():
    hot = sorted(nodes, key=lambda w: nodes[w].activation, reverse=True)
    return {"node_count": len(nodes), "link_count": len(links), "pulse_count": len(pulses), "hot_nodes": hot[:5],
            "avg_activation": sum(n.activation for n in nodes.values()) / max(1, len(nodes)),
            "stable_time": ai.stable_time, "completion_time": ai.completion_time, "selected": selected_word}

def ai_choose_mode(st):
    if st["node_count"] < 10 or st["link_count"] < max(6, st["node_count"] // 2): return "constructive"
    if st["stable_time"] > 8: return "chaotic"
    if st["completion_time"] > 5: return "destructive"
    if st["pulse_count"] > 28: return "careful"
    if st["avg_activation"] < 0.18: return "curious"
    choices = [m for m in AI_MODES if m not in ai.recent_modes[-2:]] or AI_MODES[:]
    return rnd.choice(choices)

def ai_focus(st):
    if st["hot_nodes"] and rnd.random() < 0.45: return rnd.choice(st["hot_nodes"])
    if selected_word and rnd.random() < 0.25: return selected_word
    return rnd.choice(list(nodes.keys())) if nodes else None

def ai_action(mode, st):
    word = ai_focus(st)
    if not word: return
    ai.focus_word = word
    if mode == "curious":
        activate_node(word, rnd.uniform(0.7, 1.3), rnd.choice([None, None, "metaphor", "category", "cause"])); mark_node(word); nodes[word].vel += rand_vec(0.25)
    elif mode == "constructive":
        spill_new_meaning(word) if st["node_count"] < len(WORDS) and rnd.random() < 0.55 else repair_random_link(); activate_node(ai.focus_word, 0.9)
    elif mode == "careful":
        for n in nodes.values(): n.vel *= 0.72; n.activation *= 0.96
        if st["hot_nodes"]: activate_node(st["hot_nodes"][0], 0.35)
        repair_random_link()
    elif mode == "chaotic":
        for n in nodes.values(): n.vel += rand_vec(0.19)
        for _ in range(3): activate_node(rnd.choice(list(nodes.keys())), rnd.uniform(0.45, 1.0))
        if rnd.random() < 0.35: spill_new_meaning(word)
    elif mode == "ritual":
        rel = RELATION_TYPES[int(sim_time * 0.45) % len(RELATION_TYPES)]
        activate_node(word, 1.0, rel); wrap_node(word)
        for lk in links:
            if lk.relation == rel: lk.active = max(lk.active, 0.8)
    elif mode == "artistic":
        wrap_node(word); nodes[word].orbiting = True; nodes[word].activation = max(nodes[word].activation, 1.1)
        if rnd.random() < 0.4: repair_random_link()
    elif mode == "destructive":
        if links and rnd.random() < 0.78: detach_random_link()
        activate_node(word, 0.8); nodes[word].vel += rand_vec(0.45)
    elif mode == "playful":
        nodes[word].vel += rand_vec(0.55) + vector(0, rnd.uniform(0.05, 0.35), 0); activate_node(word, 1.1)
        if rnd.random() < 0.3: toggle_orbit(word)

def ai_update(dt):
    if not ai.enabled or paused: return
    ai.timer += dt; ai.action_timer += dt
    sig = network_signature()
    ai.stable_time = ai.stable_time + dt if abs(sig - ai.last_signature) < 0.08 else max(0, ai.stable_time - dt * 0.35)
    ai.last_signature = sig
    all_spilled = len(nodes) >= len(WORDS)
    low_activity = sum(n.activation for n in nodes.values()) < max(2.2, len(nodes) * 0.08)
    sparse_links = len(links) < max(4, len(nodes) // 3)
    ai.completion_time = ai.completion_time + dt if ((all_spilled and low_activity and not pulses) or sparse_links) else max(0, ai.completion_time - dt * 0.4)
    if ai.completion_time > 10 or ai.stable_time > 18 or len(nodes) == 0:
        ai.loop_count += 1; reset_simulation(seed=1000 + ai.loop_count)
        ai.mode = rnd.choice(["curious", "constructive", "ritual", "artistic"]); ai.recent_modes.clear(); return
    st = get_state_for_ai()
    if ai.timer > rnd.uniform(5.0, 9.0):
        ai.mode = ai_choose_mode(st); ai.recent_modes.append(ai.mode); ai.recent_modes[:] = ai.recent_modes[-5:]; ai.timer = 0.0
    cadence = {"curious": 1.35, "constructive": 1.8, "careful": 2.0, "chaotic": 0.75, "ritual": 1.15,
               "artistic": 1.55, "destructive": 1.25, "playful": 0.9}.get(ai.mode, 1.5)
    if ai.action_timer > cadence: ai_action(ai.mode, st); ai.action_timer = 0.0

# ----------------------------- Controls ------------------------------------
def print_controls(): print(__doc__)

def on_keydown(evt):
    global paused, sim_speed, theme_filter
    k = evt.key; keys_down.add(k)
    if k in ("h", "H"): print_controls()
    elif k in ("p", "P"): paused = not paused
    elif k in ("r", "R"): reset_simulation()
    elif k in ("m", "M"): ai.mode = AI_MODES[(AI_MODES.index(ai.mode) + 1) % len(AI_MODES)] if ai.mode in AI_MODES else AI_MODES[0]; ai.timer = 0
    elif k in ("a", "A"): ai.enabled = not ai.enabled
    elif k in ("n", "N"): spill_new_meaning(selected_word)
    elif k in ("x", "X"): detach_random_link()
    elif k in ("z", "Z"): repair_random_link()
    elif k in ("c", "C"): clear_visuals()
    elif k in ("o", "O"): toggle_orbit(selected_word)
    elif k in ("b", "B"): wrap_node(selected_word)
    elif k in ("v", "V"): mark_node(selected_word)
    elif k == " ": activate_node(selected_word, 1.5, theme_filter)
    elif k == "tab": select_next()
    elif k in ("+", "="): sim_speed = clamp(sim_speed * 1.25, 0.15, 5.0)
    elif k in ("-", "_"): sim_speed = clamp(sim_speed / 1.25, 0.15, 5.0)
    elif k in ("1", "2", "3", "4", "5", "6"):
        theme_filter = RELATION_TYPES[int(k) - 1]
        activate_node(selected_word, 1.4, theme_filter)

def on_keyup(evt):
    if evt.key in keys_down: keys_down.remove(evt.key)

def on_click(evt):
    picked = scene.mouse.pick
    for w, n in nodes.items():
        if picked == n.body:
            set_selected(w); activate_node(w, 0.9, theme_filter); return

scene.bind("keydown", on_keydown); scene.bind("keyup", on_keyup); scene.bind("click", on_click)

def update_keyboard_motion(dt):
    global manual_velocity
    forward = safe_norm(vector(scene.forward.x, 0, scene.forward.z), vector(0, 0, -1))
    right = safe_norm(cross(forward, vector(0, 1, 0)), vector(1, 0, 0))
    move = vector(0, 0, 0)
    if "w" in keys_down or "W" in keys_down: move += forward
    if "s" in keys_down or "S" in keys_down: move -= forward
    if not ai.enabled and ("a" in keys_down or "A" in keys_down): move -= right
    if "d" in keys_down or "D" in keys_down: move += right
    if "q" in keys_down or "Q" in keys_down: move -= vector(0, 1, 0)
    if "e" in keys_down or "E" in keys_down: move += vector(0, 1, 0)
    manual_velocity = safe_norm(move) * 1.8 if mag(move) > 0 else vector(0, 0, 0)
    pan = vector(0, 0, 0)
    if "left" in keys_down: pan -= right * 0.10
    if "right" in keys_down: pan += right * 0.10
    if "up" in keys_down: pan += vector(0, 0.10, 0)
    if "down" in keys_down: pan -= vector(0, 0.10, 0)
    scene.center += pan * dt * 18
    if "j" in keys_down or "J" in keys_down: scene.forward = scene.forward.rotate(angle=0.018 * dt * 60, axis=vector(0, 1, 0))
    if "l" in keys_down or "L" in keys_down: scene.forward = scene.forward.rotate(angle=-0.018 * dt * 60, axis=vector(0, 1, 0))
    cam_axis = safe_norm(cross(scene.forward, scene.up), vector(1, 0, 0))
    if "i" in keys_down or "I" in keys_down: scene.forward = scene.forward.rotate(angle=0.014 * dt * 60, axis=cam_axis)
    if "k" in keys_down or "K" in keys_down: scene.forward = scene.forward.rotate(angle=-0.014 * dt * 60, axis=cam_axis)

def update_status():
    st = get_state_for_ai(); theme = theme_filter if theme_filter else "all"
    status.text = (f"Round {ai.loop_count} | AI {'ON' if ai.enabled else 'OFF'}:{ai.mode} | "
                   f"{'PAUSED' if paused else 'running'} | selected: {selected_word} | "
                   f"nodes {st['node_count']} links {st['link_count']} pulses {st['pulse_count']} | theme {theme} | speed {sim_speed:.2f}x")

# ----------------------------- Main loop -----------------------------------
reset_simulation()
while True:
    rate(60)
    dt = (1.0 / 60.0) * sim_speed
    update_keyboard_motion(dt)
    if not paused:
        sim_time += dt
        ai_update(dt)
        apply_force_layout(dt)
        update_nodes(dt)
        update_links()
        update_pulses(dt)
        update_markers(dt)
        detect_collisions()
    else:
        update_nodes(0.0); update_links(); update_markers(0.0)
    update_status()
