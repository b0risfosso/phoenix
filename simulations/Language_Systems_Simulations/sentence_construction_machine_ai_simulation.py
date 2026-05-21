#!/usr/bin/env python3
"""
Sentence Construction Machine — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python sentence_construction_machine_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset simulation / start new round
    M       cycle AI behavior mode
    N       spawn one noun token
    V       spawn one verb token
    J       spawn one adjective token
    O       spawn one preposition token
    D       detach the last assembled word
    C       clear temporary markers
    S       spill a burst of random words
    1-4     send selected/nearest token toward sentence slots
    + / =   increase simulation speed
    - / _   decrease simulation speed
    H       print controls

Scene concept:
    A grammar factory assembles readable sentences. Nouns, verbs, adjectives, and
    prepositions travel on colored conveyor tracks, collide with grammar gates,
    snap into ordered sentence slots, detach when grammar is reshuffled, and form
    a readable sentence on a central platform. The AI controller reads the scene
    state, chooses behavior modes, moves and organizes tokens, marks targets,
    spills new words, repairs broken sentences, loops new rounds, and prevents
    the machine from becoming halted or repetitive.
"""

from vpython import *
import random
import math
import time

# ----------------------------- Scene Setup -----------------------------

scene = canvas(
    title="Sentence Construction Machine — VPython AI Grammar Factory",
    width=1260,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0.65, 0),
)
scene.forward = vector(-0.35, -0.24, -1)
scene.range = 12

WORLD_BOUNDS = 10.5
SIM_SPEED = 1.0
PAUSED = False
AI_ENABLED = True
AI_MODE_INDEX = 0
AI_MODES = [
    "constructive",
    "careful",
    "playful",
    "curious",
    "artistic",
    "chaotic",
    "ritual",
    "destructive",
]
AI_MODE = AI_MODES[AI_MODE_INDEX]

random.seed()

# ----------------------------- Word Data -----------------------------

WORD_BANK = {
    "ADJ": ["bright", "quiet", "curious", "small", "blue", "quick", "gentle", "strange"],
    "NOUN": ["fox", "robot", "river", "artist", "cloud", "machine", "bird", "student"],
    "VERB": ["builds", "chases", "finds", "carries", "draws", "opens", "studies", "moves"],
    "PREP": ["near", "under", "beside", "through", "around", "above", "inside", "toward"],
}

PART_COLORS = {
    "ADJ": vector(0.42, 0.66, 1.00),
    "NOUN": vector(0.32, 0.78, 0.52),
    "VERB": vector(1.00, 0.58, 0.38),
    "PREP": vector(0.78, 0.55, 1.00),
}

PART_LABELS = {
    "ADJ": "adjective",
    "NOUN": "noun",
    "VERB": "verb",
    "PREP": "preposition",
}

# Sentence template:
# [ADJ] [NOUN] [VERB] [PREP] [ADJ] [NOUN]
SLOTS = [
    {"part": "ADJ", "optional": True,  "name": "descriptor"},
    {"part": "NOUN", "optional": False, "name": "subject"},
    {"part": "VERB", "optional": False, "name": "action"},
    {"part": "PREP", "optional": True,  "name": "relation"},
    {"part": "ADJ", "optional": True,  "name": "object descriptor"},
    {"part": "NOUN", "optional": True,  "name": "object"},
]

SLOT_POSITIONS = [
    vector(-5.2, 0.36, 0.0),
    vector(-3.15, 0.36, 0.0),
    vector(-1.05, 0.36, 0.0),
    vector(1.05, 0.36, 0.0),
    vector(3.15, 0.36, 0.0),
    vector(5.2, 0.36, 0.0),
]

TRACKS = {
    "ADJ":  {"z": -4.4, "x0": -8.5, "x1": 8.5, "speed": 1.10},
    "NOUN": {"z": -2.6, "x0": -8.8, "x1": 8.8, "speed": 0.92},
    "VERB": {"z": 2.6,  "x0": 8.8,  "x1": -8.8, "speed": 0.98},
    "PREP": {"z": 4.4,  "x0": 8.5,  "x1": -8.5, "speed": 1.18},
}

tokens = []
slot_tokens = [None for _ in SLOTS]
particles = []
markers = []
sentence_history = []
selected_token = None

# ----------------------------- Visual Foundation -----------------------------

floor = box(
    pos=vector(0, -0.08, 0),
    size=vector(22, 0.12, 13),
    color=vector(0.88, 0.93, 0.96),
)

platform = box(
    pos=vector(0, 0.08, 0),
    size=vector(12.8, 0.24, 1.55),
    color=vector(0.98, 0.93, 0.78),
)

platform_label = label(
    pos=vector(0, 1.22, 0),
    text="Sentence Assembly Platform",
    height=18,
    color=vector(0.25, 0.25, 0.25),
    box=False,
)

sentence_display = label(
    pos=vector(0, 2.15, 0),
    text="sentence: —",
    height=24,
    color=vector(0.1, 0.16, 0.22),
    box=True,
    border=10,
    background=vector(1, 1, 1),
    opacity=0.82,
)

status_display = label(
    pos=vector(-8.7, 3.2, -5.4),
    text="",
    height=13,
    color=vector(0.1, 0.18, 0.28),
    box=True,
    border=8,
    background=vector(1, 1, 1),
    opacity=0.74,
)

controls_display = label(
    pos=vector(7.25, 3.15, -5.4),
    text="Press H for controls",
    height=12,
    color=vector(0.15, 0.15, 0.15),
    box=True,
    border=7,
    background=vector(1, 1, 1),
    opacity=0.70,
)

slot_boxes = []
slot_name_labels = []
gate_objects = []

for i, slot in enumerate(SLOTS):
    pos = SLOT_POSITIONS[i]
    slot_color = PART_COLORS[slot["part"]]
    slot_box = box(
        pos=vector(pos.x, 0.18, pos.z),
        size=vector(1.62, 0.13, 1.22),
        color=slot_color,
        opacity=0.28,
    )
    slot_boxes.append(slot_box)
    slot_name_labels.append(
        label(
            pos=vector(pos.x, 0.97, pos.z + 0.08),
            text=f"{i+1}: {slot['part']}",
            height=12,
            color=vector(0.12, 0.12, 0.12),
            box=False,
        )
    )

for part, info in TRACKS.items():
    z = info["z"]
    x_mid = (info["x0"] + info["x1"]) / 2
    length = abs(info["x1"] - info["x0"]) + 1.2
    box(
        pos=vector(x_mid, 0.01, z),
        size=vector(length, 0.10, 0.55),
        color=PART_COLORS[part],
        opacity=0.42,
    )
    for k in range(8):
        x = -7.4 + k * 2.1
        cylinder(
            pos=vector(x, 0.1, z - 0.31),
            axis=vector(0, 0, 0.62),
            radius=0.055,
            color=vector(0.52, 0.55, 0.58),
        )
    label(
        pos=vector(-9.55, 0.75, z),
        text=PART_LABELS[part],
        height=13,
        color=vector(0.12, 0.12, 0.12),
        box=False,
    )

for i, slot in enumerate(SLOTS):
    pos = SLOT_POSITIONS[i]
    gate = box(
        pos=vector(pos.x, 0.64, -1.35 if i < 3 else 1.35),
        size=vector(0.20, 1.08, 0.44),
        color=PART_COLORS[slot["part"]],
        opacity=0.55,
    )
    gate_objects.append(gate)

# Curved guide rails from tracks to central sentence slots.
for i, slot in enumerate(SLOTS):
    slot_pos = SLOT_POSITIONS[i]
    source_z = TRACKS[slot["part"]]["z"]
    points = []
    for t in range(28):
        u = t / 27
        x = slot_pos.x
        y = 0.18 + 0.35 * math.sin(math.pi * u)
        z = source_z * (1 - u) + slot_pos.z * u
        points.append(vector(x, y, z))
    curve(pos=points, radius=0.025, color=PART_COLORS[slot["part"]], opacity=0.45)

# ----------------------------- Utility Classes -----------------------------

class Token:
    def __init__(self, part, word=None, pos=None):
        self.part = part
        self.word = word if word is not None else random.choice(WORD_BANK[part])
        info = TRACKS[part]
        self.track_z = info["z"]
        self.base_speed = info["speed"] * (1 if info["x1"] > info["x0"] else -1)
        self.vel = vector(self.base_speed, 0, 0)
        self.target_slot = None
        self.attached = False
        self.marked = False
        self.age = 0
        self.bob_phase = random.uniform(0, 2 * math.pi)
        self.spin = random.uniform(-1.6, 1.6)
        self.radius = 0.34
        if pos is None:
            start_x = info["x0"] + random.uniform(-0.4, 0.4)
            pos = vector(start_x, 0.52 + random.uniform(-0.02, 0.02), self.track_z + random.uniform(-0.1, 0.1))
        self.body = box(
            pos=pos,
            size=vector(1.18, 0.58, 0.58),
            color=PART_COLORS[part],
            opacity=0.95,
            shininess=0.45,
        )
        self.face = box(
            pos=pos + vector(0, 0.301, 0),
            size=vector(1.07, 0.024, 0.50),
            color=vector(1, 1, 1),
            opacity=0.74,
        )
        self.label = label(
            pos=pos + vector(0, 0.52, 0),
            text=self.word,
            height=12,
            color=vector(0.05, 0.06, 0.08),
            box=False,
        )
        self.part_label = label(
            pos=pos + vector(0, -0.38, 0),
            text=self.part,
            height=9,
            color=vector(0.2, 0.2, 0.2),
            box=False,
            opacity=0.55,
        )
        self.trail = curve(radius=0.018, color=PART_COLORS[part], opacity=0.45)
        self.last_pos_for_trail = vector(pos.x, pos.y, pos.z)

    @property
    def pos(self):
        return self.body.pos

    @pos.setter
    def pos(self, value):
        delta = value - self.body.pos
        self.body.pos += delta
        self.face.pos += delta
        self.label.pos += delta
        self.part_label.pos += delta

    def set_opacity(self, opacity):
        self.body.opacity = opacity
        self.face.opacity = min(0.9, opacity)

    def move_toward(self, target, dt, speed=2.1):
        direction = target - self.pos
        dist = mag(direction)
        if dist > 0.01:
            self.pos = self.pos + norm(direction) * min(dist, speed * dt)
        return dist

    def update_labels(self):
        self.label.text = self.word
        self.label.pos = self.body.pos + vector(0, 0.52, 0)
        self.part_label.pos = self.body.pos + vector(0, -0.38, 0)
        self.face.pos = self.body.pos + vector(0, 0.301, 0)

    def update(self, dt):
        self.age += dt
        if self.attached:
            if self.target_slot is not None:
                desired = SLOT_POSITIONS[self.target_slot] + vector(0, 0.23, 0)
                self.move_toward(desired, dt, speed=4.8)
                self.body.rotate(angle=0.25 * dt, axis=vector(0, 1, 0))
            self.update_labels()
            return

        if self.target_slot is not None:
            target = SLOT_POSITIONS[self.target_slot] + vector(0, 0.46, 0)
            dist = self.move_toward(target, dt, speed=2.35 + 0.25 * math.sin(self.age))
            self.body.rotate(angle=self.spin * dt * 0.35, axis=vector(0, 1, 0))
            if dist < 0.19:
                attach_token_to_slot(self, self.target_slot)
        else:
            self.pos = self.pos + self.vel * dt
            self.pos = vector(self.pos.x, 0.53 + 0.06 * math.sin(self.age * 3 + self.bob_phase), self.pos.z)
            self.body.rotate(angle=self.spin * dt, axis=vector(0, 1, 0))
            info = TRACKS[self.part]
            if self.pos.x > max(info["x0"], info["x1"]) + 0.45:
                self.pos = vector(min(info["x0"], info["x1"]) - 0.25, self.pos.y, self.track_z + random.uniform(-0.1, 0.1))
            if self.pos.x < min(info["x0"], info["x1"]) - 0.45:
                self.pos = vector(max(info["x0"], info["x1"]) + 0.25, self.pos.y, self.track_z + random.uniform(-0.1, 0.1))

        if mag(self.pos - self.last_pos_for_trail) > 0.16:
            self.trail.append(pos=self.pos)
            self.last_pos_for_trail = vector(self.pos.x, self.pos.y, self.pos.z)
            if self.trail.npoints > 38:
                self.trail.pop(0)

        self.update_labels()

    def destroy(self):
        self.body.visible = False
        self.face.visible = False
        self.label.visible = False
        self.part_label.visible = False
        self.trail.visible = False


class Particle:
    def __init__(self, pos, color_value, text=None, life=1.4):
        self.life = life
        self.max_life = life
        self.vel = vector(random.uniform(-0.55, 0.55), random.uniform(0.45, 1.2), random.uniform(-0.55, 0.55))
        self.obj = sphere(pos=pos, radius=random.uniform(0.035, 0.085), color=color_value, opacity=0.72)
        self.label = None
        if text:
            self.label = label(pos=pos + vector(0, 0.25, 0), text=text, height=8, box=False, color=color_value)

    def update(self, dt):
        self.life -= dt
        self.vel += vector(0, -0.18, 0) * dt
        self.obj.pos += self.vel * dt
        self.obj.opacity = max(0, 0.72 * self.life / self.max_life)
        if self.label:
            self.label.pos = self.obj.pos + vector(0, 0.25, 0)
            self.label.opacity = max(0, self.life / self.max_life)
        return self.life > 0

    def destroy(self):
        self.obj.visible = False
        if self.label:
            self.label.visible = False


# ----------------------------- Core Mechanics -----------------------------

def spawn_particles(pos, color_value, count=8, text=None):
    for _ in range(count):
        particles.append(Particle(pos + vector(random.uniform(-0.25, 0.25), 0, random.uniform(-0.25, 0.25)), color_value, text=text if random.random() < 0.18 else None))


def spawn_marker(pos, color_value, text="target", life=2.0):
    ring_obj = ring(pos=pos, axis=vector(0, 1, 0), radius=0.65, thickness=0.025, color=color_value, opacity=0.76)
    label_obj = label(pos=pos + vector(0, 0.72, 0), text=text, height=9, color=color_value, box=False)
    markers.append({"ring": ring_obj, "label": label_obj, "life": life, "max_life": life})


def clear_markers():
    for marker in markers:
        marker["ring"].visible = False
        marker["label"].visible = False
    markers.clear()


def spawn_token(part=None, pos=None, word=None):
    if part is None:
        part = random.choice(list(WORD_BANK.keys()))
    token = Token(part, word=word, pos=pos)
    tokens.append(token)
    return token


def initial_spawn():
    for part in ["ADJ", "NOUN", "VERB", "PREP"]:
        for _ in range(3):
            spawn_token(part)


def find_first_open_slot_for_part(part):
    for idx, slot in enumerate(SLOTS):
        if slot["part"] == part and slot_tokens[idx] is None:
            return idx
    return None


def find_best_slot_for_token(token):
    # Prefer the earliest open slot that keeps the sentence readable.
    part = token.part
    if part == "NOUN":
        if slot_tokens[1] is None:
            return 1
        if slot_tokens[5] is None and slot_tokens[3] is not None:
            return 5
    if part == "ADJ":
        if slot_tokens[0] is None and slot_tokens[1] is None:
            return 0
        if slot_tokens[4] is None and slot_tokens[3] is not None:
            return 4
    if part == "VERB" and slot_tokens[2] is None:
        return 2
    if part == "PREP" and slot_tokens[3] is None and slot_tokens[2] is not None:
        return 3
    return find_first_open_slot_for_part(part)


def attach_token_to_slot(token, slot_index):
    global selected_token
    if slot_index is None:
        return False
    if slot_index < 0 or slot_index >= len(SLOTS):
        return False
    if slot_tokens[slot_index] is not None and slot_tokens[slot_index] is not token:
        return False
    if SLOTS[slot_index]["part"] != token.part:
        return False

    slot_tokens[slot_index] = token
    token.attached = True
    token.target_slot = slot_index
    token.vel = vector(0, 0, 0)
    token.set_opacity(1.0)
    token.pos = SLOT_POSITIONS[slot_index] + vector(0, 0.23, 0)
    spawn_particles(token.pos + vector(0, 0.25, 0), PART_COLORS[token.part], count=10, text="snap")
    update_sentence_display()
    selected_token = token
    return True


def detach_token(token, push=True):
    if token is None:
        return
    for idx, existing in enumerate(slot_tokens):
        if existing is token:
            slot_tokens[idx] = None
    token.attached = False
    token.target_slot = None
    token.vel = vector(
        random.choice([-1, 1]) * (0.7 + random.random() * 0.9),
        0,
        random.uniform(-0.4, 0.4),
    )
    if push:
        token.pos = token.pos + vector(random.uniform(-0.4, 0.4), 0.25, random.uniform(-0.9, 0.9))
    spawn_particles(token.pos, PART_COLORS[token.part], count=7, text="detach")
    update_sentence_display()


def detach_last_attached():
    for token in reversed(slot_tokens):
        if token is not None:
            detach_token(token)
            return


def spill_words(count=9):
    for _ in range(count):
        part = random.choice(["ADJ", "NOUN", "VERB", "PREP"])
        pos = vector(random.uniform(-7.5, 7.5), 0.65, random.uniform(-4.8, 4.8))
        token = spawn_token(part, pos=pos)
        token.vel = vector(random.uniform(-1.5, 1.5), 0, random.uniform(-0.55, 0.55))
        spawn_particles(pos, PART_COLORS[part], count=3)


def route_token_to_slot(token, slot_index=None):
    if token is None:
        return False
    if token.attached:
        return True
    if slot_index is None:
        slot_index = find_best_slot_for_token(token)
    if slot_index is None:
        return False
    token.target_slot = slot_index
    spawn_marker(SLOT_POSITIONS[slot_index] + vector(0, 0.12, 0), PART_COLORS[token.part], text=f"{token.word} → {slot_index+1}", life=1.5)
    return True


def grammar_score():
    score = 0
    if slot_tokens[1] is not None:
        score += 1
    if slot_tokens[2] is not None:
        score += 1
    if slot_tokens[3] is not None:
        score += 0.5
    if slot_tokens[5] is not None:
        score += 0.5
    if slot_tokens[0] is not None and slot_tokens[1] is not None:
        score += 0.35
    if slot_tokens[4] is not None and slot_tokens[5] is not None:
        score += 0.35
    return score


def is_sentence_complete():
    return slot_tokens[1] is not None and slot_tokens[2] is not None and (
        slot_tokens[3] is None or slot_tokens[5] is not None
    )


def sentence_words():
    words = []
    for idx, token in enumerate(slot_tokens):
        if token is not None:
            # Omit floating object adjective if object noun is absent.
            if idx == 4 and slot_tokens[5] is None:
                continue
            words.append(token.word)
    return words


def current_sentence():
    words = sentence_words()
    if not words:
        return "—"
    sentence = " ".join(words)
    return sentence[0].upper() + sentence[1:] + "."


def update_sentence_display():
    sentence = current_sentence()
    sentence_display.text = f"sentence: {sentence}"
    if is_sentence_complete():
        sentence_display.background = vector(0.90, 1.0, 0.88)
    else:
        sentence_display.background = vector(1, 1, 1)


def remove_excess_tokens(max_tokens=32):
    loose = [t for t in tokens if not t.attached]
    while len(tokens) > max_tokens and loose:
        token = loose.pop(0)
        if token in tokens:
            token.destroy()
            tokens.remove(token)


def reset_simulation(seed_sentence=False):
    global selected_token
    clear_markers()
    for token in list(tokens):
        token.destroy()
    tokens.clear()
    for p in list(particles):
        p.destroy()
    particles.clear()
    for i in range(len(slot_tokens)):
        slot_tokens[i] = None
    selected_token = None
    initial_spawn()
    if seed_sentence:
        # Place a minimal readable sentence quickly, then allow AI to elaborate.
        for required_part in ["NOUN", "VERB"]:
            candidates = [t for t in tokens if t.part == required_part and not t.attached]
            if candidates:
                route_token_to_slot(candidates[0])
    update_sentence_display()
    spawn_particles(vector(0, 0.7, 0), vector(1, 0.86, 0.35), count=22, text="new round")


# ----------------------------- AI Controller -----------------------------

class GrammarAI:
    def __init__(self):
        self.enabled = True
        self.mode = AI_MODE
        self.mode_timer = 0
        self.action_timer = 0
        self.round_timer = 0
        self.complete_timer = 0
        self.stagnation_timer = 0
        self.last_signature = ""
        self.last_score = -1
        self.loop_count = 0
        self.preferred_sentence_shape = random.choice(["simple", "rich", "prepositional", "minimal"])
        self.ritual_step = 0

    def read_state(self):
        loose_tokens = [t for t in tokens if not t.attached]
        attached_tokens = [t for t in tokens if t.attached]
        open_slots = [i for i, tok in enumerate(slot_tokens) if tok is None]
        counts = {part: len([t for t in tokens if t.part == part and not t.attached]) for part in WORD_BANK.keys()}
        score = grammar_score()
        signature = "|".join([tok.word if tok else "_" for tok in slot_tokens]) + f":{len(tokens)}:{round(score, 2)}"
        complete = is_sentence_complete()
        return {
            "loose_tokens": loose_tokens,
            "attached_tokens": attached_tokens,
            "open_slots": open_slots,
            "counts": counts,
            "score": score,
            "signature": signature,
            "complete": complete,
            "sentence": current_sentence(),
        }

    def choose_mode(self, state, dt):
        self.mode_timer += dt
        self.round_timer += dt

        changed = state["signature"] != self.last_signature
        score_changed = abs(state["score"] - self.last_score) > 0.01

        if changed or score_changed:
            self.stagnation_timer = 0
            self.last_signature = state["signature"]
            self.last_score = state["score"]
        else:
            self.stagnation_timer += dt

        if state["complete"]:
            self.complete_timer += dt
        else:
            self.complete_timer = 0

        if len(tokens) < 6:
            self.mode = "constructive"
            self.mode_timer = 0
            return

        if self.stagnation_timer > 7.0:
            self.mode = random.choice(["chaotic", "curious", "destructive", "playful"])
            self.mode_timer = 0
            self.stagnation_timer = 0
            return

        if self.complete_timer > 8.5:
            self.mode = "ritual"
            self.mode_timer = 0
            return

        if self.mode_timer > random.uniform(5.0, 9.0):
            if state["score"] < 2:
                choices = ["constructive", "careful", "curious"]
            elif state["complete"]:
                choices = ["artistic", "playful", "ritual", "destructive"]
            else:
                choices = ["constructive", "careful", "playful", "artistic", "chaotic"]
            self.mode = random.choice(choices)
            self.preferred_sentence_shape = random.choice(["simple", "rich", "prepositional", "minimal"])
            self.mode_timer = 0

    def update(self, dt):
        if not self.enabled or PAUSED:
            return
        state = self.read_state()
        self.choose_mode(state, dt)

        self.action_timer -= dt
        if self.action_timer > 0:
            return

        if self.mode == "constructive":
            self.constructive_action(state)
            self.action_timer = 0.55
        elif self.mode == "careful":
            self.careful_action(state)
            self.action_timer = 0.85
        elif self.mode == "playful":
            self.playful_action(state)
            self.action_timer = 0.55
        elif self.mode == "curious":
            self.curious_action(state)
            self.action_timer = 0.70
        elif self.mode == "artistic":
            self.artistic_action(state)
            self.action_timer = 0.38
        elif self.mode == "chaotic":
            self.chaotic_action(state)
            self.action_timer = 0.32
        elif self.mode == "ritual":
            self.ritual_action(state)
            self.action_timer = 0.75
        elif self.mode == "destructive":
            self.destructive_action(state)
            self.action_timer = 0.65

        remove_excess_tokens(36)

    def ensure_part_exists(self, part, amount=1):
        loose = [t for t in tokens if t.part == part and not t.attached]
        for _ in range(max(0, amount - len(loose))):
            spawn_token(part)

    def constructive_action(self, state):
        # Build a valid sentence from left to right.
        if slot_tokens[1] is None:
            self.ensure_part_exists("NOUN")
            self.route_nearest_part_to_slot("NOUN", 1)
            return
        if slot_tokens[2] is None:
            self.ensure_part_exists("VERB")
            self.route_nearest_part_to_slot("VERB", 2)
            return
        if self.preferred_sentence_shape in ["rich", "prepositional"] and slot_tokens[3] is None:
            self.ensure_part_exists("PREP")
            self.route_nearest_part_to_slot("PREP", 3)
            return
        if slot_tokens[3] is not None and slot_tokens[5] is None:
            self.ensure_part_exists("NOUN")
            self.route_nearest_part_to_slot("NOUN", 5)
            return
        if self.preferred_sentence_shape == "rich" and slot_tokens[0] is None:
            self.ensure_part_exists("ADJ")
            self.route_nearest_part_to_slot("ADJ", 0)
            return
        if self.preferred_sentence_shape == "rich" and slot_tokens[4] is None and slot_tokens[5] is None:
            self.ensure_part_exists("ADJ")
            self.route_nearest_part_to_slot("ADJ", 4)
            return
        self.mode = random.choice(["artistic", "playful", "ritual"])

    def careful_action(self, state):
        # Repair grammar conflicts and route only tokens that fit the next sensible slot.
        if slot_tokens[4] is not None and slot_tokens[5] is None and slot_tokens[3] is None:
            detach_token(slot_tokens[4])
            return
        if slot_tokens[3] is not None and slot_tokens[5] is None:
            self.ensure_part_exists("NOUN")
            self.route_nearest_part_to_slot("NOUN", 5)
            return
        if not is_sentence_complete():
            self.constructive_action(state)
            return
        # Highlight completed syntax order.
        idxs = [i for i, t in enumerate(slot_tokens) if t is not None]
        if idxs:
            i = random.choice(idxs)
            spawn_marker(SLOT_POSITIONS[i] + vector(0, 0.12, 0), PART_COLORS[SLOTS[i]["part"]], text=SLOTS[i]["name"], life=1.4)

    def playful_action(self, state):
        # Swap an optional adjective, toss a loose word, or decorate a complete sentence.
        action = random.choice(["bounce", "adjective", "mark", "spill"])
        if action == "bounce" and state["loose_tokens"]:
            token = random.choice(state["loose_tokens"])
            token.vel += vector(random.uniform(-1.2, 1.2), 0, random.uniform(-0.8, 0.8))
            spawn_particles(token.pos, PART_COLORS[token.part], count=6, text="bounce")
        elif action == "adjective":
            if random.random() < 0.5 and slot_tokens[0] is None:
                self.ensure_part_exists("ADJ")
                self.route_nearest_part_to_slot("ADJ", 0)
            elif slot_tokens[4] is None and slot_tokens[3] is not None:
                self.ensure_part_exists("ADJ")
                self.route_nearest_part_to_slot("ADJ", 4)
        elif action == "mark":
            open_or_filled = random.randrange(len(SLOTS))
            spawn_marker(SLOT_POSITIONS[open_or_filled] + vector(0, 0.14, 0), PART_COLORS[SLOTS[open_or_filled]["part"]], text="spark", life=1.2)
        else:
            if len(tokens) < 30:
                spill_words(count=random.randint(2, 4))

    def curious_action(self, state):
        # Try unusual but grammatical extensions.
        missing_parts = [part for part, count in state["counts"].items() if count == 0]
        if missing_parts:
            spawn_token(random.choice(missing_parts))
            return
        if slot_tokens[3] is None and slot_tokens[2] is not None:
            self.route_nearest_part_to_slot("PREP", 3)
            return
        if slot_tokens[5] is None and slot_tokens[3] is not None:
            self.route_nearest_part_to_slot("NOUN", 5)
            return
        if random.random() < 0.35:
            spawn_token(random.choice(["ADJ", "PREP"]))
        else:
            self.playful_action(state)

    def artistic_action(self, state):
        # Create visible grammar trails and colored rings.
        used = [t for t in slot_tokens if t is not None]
        if used:
            token = random.choice(used)
            spawn_particles(token.pos + vector(0, 0.25, 0), PART_COLORS[token.part], count=5, text=random.choice(["syntax", "rhythm", "shape"]))
        if random.random() < 0.4:
            idx = random.randrange(len(SLOTS))
            spawn_marker(SLOT_POSITIONS[idx] + vector(0, 0.12, 0), PART_COLORS[SLOTS[idx]["part"]], text=random.choice(["line", "phrase", "order"]), life=1.7)

    def chaotic_action(self, state):
        # Disrupt loose tokens, occasionally detach optional words, then return to constructive behavior.
        if random.random() < 0.33 and len(tokens) < 34:
            spill_words(count=random.randint(3, 6))
        for token in random.sample(tokens, min(len(tokens), random.randint(1, 4))):
            if not token.attached:
                token.vel += vector(random.uniform(-2.2, 2.2), 0, random.uniform(-1.0, 1.0))
                spawn_particles(token.pos, PART_COLORS[token.part], count=3)
        if random.random() < 0.18:
            optional_idxs = [0, 3, 4, 5]
            filled = [i for i in optional_idxs if slot_tokens[i] is not None]
            if filled:
                detach_token(slot_tokens[random.choice(filled)])
        if self.mode_timer > 3.5:
            self.mode = "constructive"
            self.mode_timer = 0

    def ritual_action(self, state):
        # Celebrate a complete sentence, record it, then loop a new round.
        if state["complete"]:
            if state["sentence"] not in sentence_history and state["sentence"] != "—":
                sentence_history.append(state["sentence"])
                print("Completed sentence:", state["sentence"])
            center_pos = vector(0, 0.85, 0)
            spawn_particles(center_pos, vector(1.0, 0.82, 0.28), count=16, text="complete")
            self.ritual_step += 1
            if self.ritual_step >= 5:
                self.loop_count += 1
                self.ritual_step = 0
                reset_simulation(seed_sentence=False)
                self.mode = random.choice(["constructive", "curious", "playful"])
                self.complete_timer = 0
        else:
            self.constructive_action(state)

    def destructive_action(self, state):
        # Break the current phrase, but not forever.
        filled = [t for t in slot_tokens if t is not None]
        if filled:
            detach_token(random.choice(filled))
        else:
            self.chaotic_action(state)
        if self.mode_timer > 2.8:
            self.mode = "constructive"
            self.mode_timer = 0

    def route_nearest_part_to_slot(self, part, slot_index):
        candidates = [t for t in tokens if t.part == part and not t.attached and t.target_slot is None]
        if not candidates:
            self.ensure_part_exists(part)
            candidates = [t for t in tokens if t.part == part and not t.attached and t.target_slot is None]
        if not candidates:
            return False
        target = SLOT_POSITIONS[slot_index]
        candidates.sort(key=lambda t: mag(t.pos - target))
        return route_token_to_slot(candidates[0], slot_index)


ai = GrammarAI()

# ----------------------------- Human Controls -----------------------------

def print_controls():
    print(__doc__)


def nearest_loose_token():
    loose = [t for t in tokens if not t.attached]
    if not loose:
        return None
    return min(loose, key=lambda t: mag(t.pos - vector(0, 0.5, 0)))


def manual_route_slot(slot_index):
    global selected_token
    if selected_token is None or selected_token.attached:
        selected_token = nearest_loose_token()
    if selected_token:
        route_token_to_slot(selected_token, slot_index)


def on_keydown(evt):
    global PAUSED, AI_ENABLED, AI_MODE_INDEX, AI_MODE, SIM_SPEED, selected_token

    key = evt.key.lower()

    if key == "a":
        AI_ENABLED = not AI_ENABLED
        ai.enabled = AI_ENABLED
        print("AI enabled:", AI_ENABLED)
    elif key == "p":
        PAUSED = not PAUSED
        print("Paused:", PAUSED)
    elif key == "r":
        reset_simulation(seed_sentence=False)
    elif key == "m":
        AI_MODE_INDEX = (AI_MODE_INDEX + 1) % len(AI_MODES)
        AI_MODE = AI_MODES[AI_MODE_INDEX]
        ai.mode = AI_MODE
        ai.mode_timer = 0
        print("AI mode:", ai.mode)
    elif key == "n":
        selected_token = spawn_token("NOUN")
    elif key == "v":
        selected_token = spawn_token("VERB")
    elif key == "j":
        selected_token = spawn_token("ADJ")
    elif key == "o":
        selected_token = spawn_token("PREP")
    elif key == "d":
        detach_last_attached()
    elif key == "c":
        clear_markers()
    elif key == "s":
        spill_words(count=10)
    elif key in ["+", "="]:
        SIM_SPEED = min(3.0, SIM_SPEED + 0.15)
    elif key in ["-", "_"]:
        SIM_SPEED = max(0.25, SIM_SPEED - 0.15)
    elif key == "h":
        print_controls()
    elif key in ["1", "2", "3", "4"]:
        # Fast routes to central grammar positions:
        # 1 subject noun, 2 verb, 3 preposition, 4 object noun
        mapping = {"1": 1, "2": 2, "3": 3, "4": 5}
        slot_idx = mapping[key]
        candidates = [t for t in tokens if t.part == SLOTS[slot_idx]["part"] and not t.attached]
        if candidates:
            selected_token = min(candidates, key=lambda t: mag(t.pos - SLOT_POSITIONS[slot_idx]))
            manual_route_slot(slot_idx)

scene.bind("keydown", on_keydown)

# ----------------------------- Collision / Interaction -----------------------------

def handle_token_collisions(dt):
    # Gentle collisions between loose tokens.
    loose = [t for t in tokens if not t.attached]
    for i in range(len(loose)):
        for j in range(i + 1, len(loose)):
            a = loose[i]
            b = loose[j]
            delta = b.pos - a.pos
            dist = mag(delta)
            if 0.01 < dist < 0.76:
                push = norm(delta) * (0.76 - dist) * 0.5
                a.pos = a.pos - push
                b.pos = b.pos + push
                a.vel = a.vel - push * 1.7
                b.vel = b.vel + push * 1.7
                if random.random() < 0.035:
                    spawn_particles((a.pos + b.pos) * 0.5, vector(1, 1, 1), count=2, text="tap")

    # Grammar gate collision: correct parts get routed, incorrect parts bounce.
    for token in loose:
        if token.target_slot is not None:
            continue
        for i, slot in enumerate(SLOTS):
            gate = gate_objects[i]
            if mag(token.pos - gate.pos) < 0.78:
                if token.part == slot["part"] and slot_tokens[i] is None:
                    if random.random() < 0.55:
                        route_token_to_slot(token, i)
                else:
                    token.vel.x *= -1
                    token.vel.z += random.uniform(-0.7, 0.7)
                    spawn_particles(token.pos, vector(1, 0.35, 0.35), count=3, text="wrong gate")


def update_markers(dt):
    for marker in list(markers):
        marker["life"] -= dt
        marker["ring"].rotate(angle=1.7 * dt, axis=vector(0, 1, 0))
        alpha = max(0, marker["life"] / marker["max_life"])
        marker["ring"].opacity = 0.76 * alpha
        marker["label"].opacity = alpha
        if marker["life"] <= 0:
            marker["ring"].visible = False
            marker["label"].visible = False
            markers.remove(marker)


def update_particles(dt):
    for p in list(particles):
        if not p.update(dt):
            p.destroy()
            particles.remove(p)


def update_status():
    filled = len([t for t in slot_tokens if t is not None])
    loose = len([t for t in tokens if not t.attached])
    status_display.text = (
        f"AI: {'ON' if AI_ENABLED else 'OFF'} | mode: {ai.mode}\n"
        f"speed: {SIM_SPEED:.2f} | paused: {PAUSED}\n"
        f"slots filled: {filled}/{len(SLOTS)} | loose words: {loose}\n"
        f"grammar score: {grammar_score():.2f} | loops: {ai.loop_count}\n"
        f"history: {len(sentence_history)} sentence(s)"
    )


# ----------------------------- Main Loop -----------------------------

reset_simulation(seed_sentence=False)
print_controls()

last_time = time.time()
while True:
    rate(60)
    now = time.time()
    raw_dt = min(0.05, now - last_time)
    last_time = now
    dt = raw_dt * SIM_SPEED

    if PAUSED:
        update_status()
        continue

    ai.enabled = AI_ENABLED
    ai.update(dt)

    for token in list(tokens):
        token.update(dt)

    handle_token_collisions(dt)
    update_particles(dt)
    update_markers(dt)
    update_sentence_display()
    update_status()
