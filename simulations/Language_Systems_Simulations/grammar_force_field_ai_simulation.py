"""
Grammar as a Force Field — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python grammar_force_field_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset simulation
    M       cycle AI behavior mode
    N       spawn a new sentence cloud
    G       force grammar organization pulse
    X       scatter / disrupt all words
    T       toggle trails
    C       clear temporary markers and field lines
    + / =   increase simulation speed
    - / _   decrease simulation speed
    H       print controls

Scene concept:
    Words are particles inside a grammar field. Each word has grammatical properties
    such as part of speech, number, tense, and role. Compatible words attract,
    incompatible words repel, and stable sentence chains glow when grammar rules are
    satisfied. The AI controller reads the sentence state, chooses behavior modes,
    moves and marks words, attaches compatible grammar links, detaches bad links,
    spills new words, wraps stable sentences with halos, and resets the field when
    the scene becomes complete or stagnant.

Notes:
    This is a visual/educational grammar metaphor, not a full natural-language parser.
    The rules are intentionally simple and visible.
"""

from vpython import *
import random
import math

# -----------------------------------------------------------------------------
# Scene setup
# -----------------------------------------------------------------------------
scene = canvas(
    title="Grammar as a Force Field — AI Controlled VPython Simulation",
    width=1180,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.45, -0.35, -1.0)
scene.range = 14

WORLD_RADIUS = 10.0
DT_BASE = 0.016
SIM_SPEED = 1.0
PAUSED = False
AI_ENABLED = True
TRAILS_ENABLED = True
MAX_MARKERS = 120
MAX_FIELD_LINES = 80
ROUND_INDEX = 1

random.seed()

# -----------------------------------------------------------------------------
# Visual palette and grammar data
# -----------------------------------------------------------------------------
POS_COLORS = {
    "det": vector(0.35, 0.68, 1.00),
    "adj": vector(0.62, 0.82, 0.40),
    "noun": vector(1.00, 0.64, 0.28),
    "verb": vector(1.00, 0.38, 0.38),
    "adv": vector(0.72, 0.50, 1.00),
    "prep": vector(0.45, 0.78, 0.78),
    "conj": vector(0.86, 0.78, 0.30),
    "punct": vector(0.45, 0.45, 0.50),
}

WORD_LIBRARY = [
    {"text": "the", "pos": "det", "number": "any", "tense": "none", "role": "modifier"},
    {"text": "a", "pos": "det", "number": "singular", "tense": "none", "role": "modifier"},
    {"text": "bright", "pos": "adj", "number": "any", "tense": "none", "role": "modifier"},
    {"text": "small", "pos": "adj", "number": "any", "tense": "none", "role": "modifier"},
    {"text": "curious", "pos": "adj", "number": "any", "tense": "none", "role": "modifier"},
    {"text": "student", "pos": "noun", "number": "singular", "tense": "none", "role": "subject"},
    {"text": "students", "pos": "noun", "number": "plural", "tense": "none", "role": "subject"},
    {"text": "robot", "pos": "noun", "number": "singular", "tense": "none", "role": "subject"},
    {"text": "robots", "pos": "noun", "number": "plural", "tense": "none", "role": "subject"},
    {"text": "idea", "pos": "noun", "number": "singular", "tense": "none", "role": "object"},
    {"text": "ideas", "pos": "noun", "number": "plural", "tense": "none", "role": "object"},
    {"text": "builds", "pos": "verb", "number": "singular", "tense": "present", "role": "predicate"},
    {"text": "build", "pos": "verb", "number": "plural", "tense": "present", "role": "predicate"},
    {"text": "sees", "pos": "verb", "number": "singular", "tense": "present", "role": "predicate"},
    {"text": "see", "pos": "verb", "number": "plural", "tense": "present", "role": "predicate"},
    {"text": "follows", "pos": "verb", "number": "singular", "tense": "present", "role": "predicate"},
    {"text": "follow", "pos": "verb", "number": "plural", "tense": "present", "role": "predicate"},
    {"text": "quickly", "pos": "adv", "number": "any", "tense": "none", "role": "modifier"},
    {"text": "carefully", "pos": "adv", "number": "any", "tense": "none", "role": "modifier"},
    {"text": "near", "pos": "prep", "number": "any", "tense": "none", "role": "connector"},
    {"text": "inside", "pos": "prep", "number": "any", "tense": "none", "role": "connector"},
    {"text": "and", "pos": "conj", "number": "any", "tense": "none", "role": "connector"},
    {"text": ".", "pos": "punct", "number": "any", "tense": "none", "role": "terminal"},
]

# Desired sentence grammar path. Multiple words can satisfy each slot.
GRAMMAR_PATH = ["det", "adj", "noun", "verb", "det", "adj", "noun", "adv", "punct"]
SLOT_X_SPACING = 2.2
SLOT_START_X = -SLOT_X_SPACING * (len(GRAMMAR_PATH) - 1) / 2

# Pairwise grammar compatibility. Direction matters for sentence order.
COMPATIBLE_NEXT = {
    "det": {"adj", "noun"},
    "adj": {"adj", "noun"},
    "noun": {"verb", "prep", "conj", "punct"},
    "verb": {"det", "adj", "noun", "adv"},
    "adv": {"prep", "conj", "punct"},
    "prep": {"det", "adj", "noun"},
    "conj": {"det", "adj", "noun"},
    "punct": set(),
}

# -----------------------------------------------------------------------------
# Simulation containers
# -----------------------------------------------------------------------------
words = []
links = []
markers = []
field_lines = []
stable_halos = []
completion_flash = []

status_label = label(
    pos=vector(-12.5, 9.6, 0),
    text="",
    xoffset=0,
    yoffset=0,
    height=12,
    box=False,
    opacity=0,
    color=vector(0.12, 0.16, 0.20),
    align="left",
)

help_label = label(
    pos=vector(0, -10.7, 0),
    text="A AI | P pause | R reset | M mode | G grammar pulse | X scatter | N new words | T trails | H controls",
    height=11,
    box=False,
    opacity=0,
    color=vector(0.18, 0.22, 0.28),
)

# Visual grammar slots / sentence rail
slot_markers = []
for i, slot in enumerate(GRAMMAR_PATH):
    x = SLOT_START_X + i * SLOT_X_SPACING
    base = cylinder(
        pos=vector(x, -3.25, 0),
        axis=vector(0, 0.05, 0),
        radius=0.42,
        color=POS_COLORS[slot],
        opacity=0.25,
    )
    txt = label(
        pos=vector(x, -4.0, 0),
        text=slot.upper(),
        height=9,
        box=False,
        opacity=0,
        color=vector(0.22, 0.24, 0.28),
    )
    slot_markers.append((base, txt))

sentence_rail = curve(color=vector(0.62, 0.68, 0.76), radius=0.025)
for i in range(len(GRAMMAR_PATH)):
    sentence_rail.append(vector(SLOT_START_X + i * SLOT_X_SPACING, -3.25, 0))

boundary = sphere(pos=vector(0, 0, 0), radius=WORLD_RADIUS, color=vector(0.75, 0.86, 1.0), opacity=0.06)
center_core = sphere(pos=vector(0, -3.25, 0), radius=0.18, color=vector(1.0, 0.88, 0.28), emissive=True)

# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------
def clamp_mag(v, max_mag):
    m = mag(v)
    if m > max_mag and m > 0:
        return norm(v) * max_mag
    return v


def random_vec(scale=1.0):
    return vector(
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
    )


def grammar_slot_position(index):
    return vector(SLOT_START_X + index * SLOT_X_SPACING, -3.25, 0)


def destroy_visual(obj):
    try:
        obj.visible = False
    except Exception:
        pass


def cleanup_list(items):
    for item in items:
        destroy_visual(item)
    items.clear()


def text_color_for_pos(pos_name):
    if pos_name in ("noun", "verb", "conj"):
        return vector(0.12, 0.12, 0.14)
    return vector(0.05, 0.08, 0.12)


def print_controls():
    print(__doc__)

# -----------------------------------------------------------------------------
# Word particle and link classes
# -----------------------------------------------------------------------------
class WordParticle:
    def __init__(self, spec, position=None, velocity=None):
        self.text = spec["text"]
        self.pos_type = spec["pos"]
        self.number = spec["number"]
        self.tense = spec["tense"]
        self.role = spec["role"]
        self.mass = 1.0 + 0.16 * len(self.text)
        self.radius = 0.42 if self.pos_type != "punct" else 0.30
        self.pos = position if position is not None else random_vec(7.0)
        self.vel = velocity if velocity is not None else random_vec(1.2)
        self.force = vector(0, 0, 0)
        self.slot_index = None
        self.selected = False
        self.stability = 0.0
        self.age = 0.0
        self.last_mark_time = -99
        base_color = POS_COLORS.get(self.pos_type, vector(0.8, 0.8, 0.8))
        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=base_color,
            opacity=0.86,
            shininess=0.55,
            make_trail=TRAILS_ENABLED,
            trail_radius=0.025,
            retain=32,
        )
        self.label = label(
            pos=self.pos + vector(0, 0.68, 0),
            text=self.text,
            height=12,
            box=True,
            border=5,
            opacity=0.38,
            color=text_color_for_pos(self.pos_type),
            background=vector(1, 1, 1),
        )
        self.property_label = label(
            pos=self.pos + vector(0, -0.72, 0),
            text=f"{self.pos_type}/{self.number}",
            height=8,
            box=False,
            opacity=0,
            color=vector(0.25, 0.29, 0.34),
        )

    def clear_trail(self):
        try:
            self.body.clear_trail()
        except Exception:
            pass

    def update_visual(self):
        self.body.pos = self.pos
        self.label.pos = self.pos + vector(0, 0.68, 0)
        self.property_label.pos = self.pos + vector(0, -0.72, 0)
        glow = min(1.0, self.stability)
        base = POS_COLORS.get(self.pos_type, vector(0.8, 0.8, 0.8))
        self.body.color = base * (1.0 - 0.20 * glow) + vector(1.0, 0.94, 0.38) * (0.20 * glow)
        self.body.opacity = 0.82 + 0.15 * glow
        self.body.radius = self.radius * (1.0 + 0.09 * math.sin(self.age * 4.0) * glow)
        self.body.make_trail = TRAILS_ENABLED

    def remove(self):
        destroy_visual(self.body)
        destroy_visual(self.label)
        destroy_visual(self.property_label)


class GrammarLink:
    def __init__(self, a, b, kind="compatible"):
        self.a = a
        self.b = b
        self.kind = kind
        self.age = 0.0
        self.strength = 0.0
        self.visual = curve(radius=0.04)
        self.update_visual()

    def update_visual(self):
        self.visual.clear()
        self.visual.append(self.a.pos)
        mid = (self.a.pos + self.b.pos) * 0.5 + vector(0, 0.18 * math.sin(self.age * 4.0), 0)
        self.visual.append(mid)
        self.visual.append(self.b.pos)
        if self.kind == "compatible":
            self.visual.color = vector(0.18, 0.62, 0.36) * (0.6 + 0.4 * self.strength)
        else:
            self.visual.color = vector(1.0, 0.25, 0.20)
        self.visual.radius = 0.025 + 0.04 * self.strength

    def remove(self):
        destroy_visual(self.visual)

# -----------------------------------------------------------------------------
# Grammar rule functions
# -----------------------------------------------------------------------------
def next_compatible(a, b):
    if b.pos_type in COMPATIBLE_NEXT.get(a.pos_type, set()):
        if a.pos_type == "noun" and b.pos_type == "verb":
            return a.number == b.number or b.number == "any" or a.number == "any"
        return True
    return False


def pair_compatibility(a, b):
    score = 0.0
    if next_compatible(a, b):
        score += 1.0
    if next_compatible(b, a):
        score += 0.75
    if a.pos_type == b.pos_type and a.pos_type not in ("adj", "noun"):
        score -= 0.55
    if a.pos_type == "punct" and b.pos_type != "punct":
        score -= 0.20
    return score


def sentence_score(sorted_words=None):
    if sorted_words is None:
        sorted_words = sorted(words, key=lambda w: w.pos.x)
    if len(sorted_words) < 3:
        return 0.0
    compatible_count = 0
    possible = max(1, len(sorted_words) - 1)
    subject_verb_ok = False
    has_noun = False
    has_verb = False
    has_terminal = False
    for i in range(len(sorted_words) - 1):
        if next_compatible(sorted_words[i], sorted_words[i + 1]):
            compatible_count += 1
    for i, w in enumerate(sorted_words):
        if w.pos_type == "noun":
            has_noun = True
            for j in range(i + 1, min(i + 4, len(sorted_words))):
                v = sorted_words[j]
                if v.pos_type == "verb" and (w.number == v.number or v.number == "any"):
                    subject_verb_ok = True
        if w.pos_type == "verb":
            has_verb = True
        if w.pos_type == "punct":
            has_terminal = True
    structure_bonus = sum([has_noun, has_verb, has_terminal, subject_verb_ok]) / 4.0
    return 0.68 * (compatible_count / possible) + 0.32 * structure_bonus


def find_best_sentence_chain():
    # Greedy chain matching the visual grammar path.
    unused = list(words)
    chain = []
    for i, slot in enumerate(GRAMMAR_PATH):
        target = grammar_slot_position(i)
        candidates = [w for w in unused if w.pos_type == slot]
        if not candidates and slot == "adj":
            candidates = [w for w in unused if w.pos_type in ("adj", "noun")]
        if candidates:
            best = min(candidates, key=lambda w: mag(w.pos - target))
            chain.append(best)
            unused.remove(best)
    return chain


def current_stability_snapshot():
    chain = find_best_sentence_chain()
    chain_score = 0
    if len(chain) > 1:
        for i in range(len(chain) - 1):
            chain_score += 1 if next_compatible(chain[i], chain[i + 1]) else 0
        chain_score /= max(1, len(chain) - 1)
    global_score = sentence_score()
    avg_speed = sum(mag(w.vel) for w in words) / max(1, len(words))
    return {
        "word_count": len(words),
        "chain_length": len(chain),
        "chain_score": chain_score,
        "global_score": global_score,
        "avg_speed": avg_speed,
        "complete": len(chain) >= len(GRAMMAR_PATH) and chain_score > 0.83 and global_score > 0.72,
    }

# -----------------------------------------------------------------------------
# Creation and reset functions
# -----------------------------------------------------------------------------
def add_marker(position, color_value=vector(1, 0.9, 0.2), radius=0.12, ttl=2.0):
    obj = sphere(pos=position, radius=radius, color=color_value, opacity=0.65, emissive=True)
    markers.append({"obj": obj, "ttl": ttl, "max_ttl": ttl})
    while len(markers) > MAX_MARKERS:
        old = markers.pop(0)
        destroy_visual(old["obj"])


def add_field_line(a, b, color_value=vector(0.34, 0.58, 1.0), ttl=1.6):
    c = curve(radius=0.018, color=color_value)
    c.append(a)
    c.append((a + b) * 0.5 + random_vec(0.2))
    c.append(b)
    field_lines.append({"obj": c, "ttl": ttl, "max_ttl": ttl})
    while len(field_lines) > MAX_FIELD_LINES:
        old = field_lines.pop(0)
        destroy_visual(old["obj"])


def spawn_word(spec=None, position=None, velocity=None):
    spec = spec if spec is not None else random.choice(WORD_LIBRARY)
    if position is None:
        position = random_vec(7.2) + vector(0, random.uniform(0.8, 4.5), 0)
    if velocity is None:
        velocity = random_vec(1.6)
    w = WordParticle(spec, position, velocity)
    words.append(w)
    add_marker(position, POS_COLORS.get(w.pos_type, vector(1, 1, 1)), 0.08, 1.0)
    return w


def spawn_sentence_cloud():
    # Ensure enough tokens exist to form a sentence, then add some decoys.
    templates = [
        ["the", "curious", "student", "builds", "a", "bright", "idea", "carefully", "."],
        ["the", "small", "robots", "follow", "the", "bright", "ideas", "quickly", "."],
        ["a", "bright", "robot", "sees", "the", "small", "idea", "carefully", "."],
    ]
    template = random.choice(templates)
    text_to_spec = {s["text"]: s for s in WORD_LIBRARY}
    for i, word_text in enumerate(template):
        pos = vector(random.uniform(-7.2, 7.2), random.uniform(-1.5, 6.8), random.uniform(-4.2, 4.2))
        spawn_word(text_to_spec[word_text], pos, random_vec(0.9))
    for _ in range(random.randint(4, 7)):
        spawn_word()


def clear_all():
    global words, links, stable_halos, completion_flash
    for w in words:
        w.remove()
    words.clear()
    for link in links:
        link.remove()
    links.clear()
    cleanup_list(stable_halos)
    cleanup_list(completion_flash)
    for item in markers:
        destroy_visual(item["obj"])
    markers.clear()
    for item in field_lines:
        destroy_visual(item["obj"])
    field_lines.clear()


def reset_simulation(reason="manual reset"):
    global ROUND_INDEX
    ROUND_INDEX += 1
    clear_all()
    spawn_sentence_cloud()
    for w in words:
        w.clear_trail()
    center_core.color = vector(1.0, 0.88, 0.28)
    print(f"Grammar field reset: {reason}; round {ROUND_INDEX}")


def grammar_organization_pulse():
    chain = find_best_sentence_chain()
    for i, w in enumerate(chain):
        target = grammar_slot_position(i)
        direction = target - w.pos
        w.vel += clamp_mag(direction, 5.0) * 0.18
        add_field_line(w.pos, target, POS_COLORS[w.pos_type], 1.2)
        add_marker(target, vector(1.0, 0.90, 0.25), 0.10, 0.8)


def scatter_words(force=5.0):
    for w in words:
        w.vel += norm(w.pos + random_vec(2.0)) * random.uniform(1.0, force)
        w.stability *= 0.25
    add_marker(vector(0, 0, 0), vector(1.0, 0.30, 0.25), 0.35, 1.3)

# -----------------------------------------------------------------------------
# Force field update
# -----------------------------------------------------------------------------
def remove_existing_link(a, b):
    for link in list(links):
        if (link.a is a and link.b is b) or (link.a is b and link.b is a):
            link.remove()
            links.remove(link)


def has_link(a, b):
    for link in links:
        if (link.a is a and link.b is b) or (link.a is b and link.b is a):
            return True
    return False


def maybe_attach_links():
    sorted_words = sorted(words, key=lambda w: w.pos.x)
    for i in range(len(sorted_words) - 1):
        a = sorted_words[i]
        b = sorted_words[i + 1]
        d = mag(a.pos - b.pos)
        if d < 1.75 and next_compatible(a, b) and not has_link(a, b):
            links.append(GrammarLink(a, b, "compatible"))
            a.stability = min(1.0, a.stability + 0.25)
            b.stability = min(1.0, b.stability + 0.25)
            add_marker((a.pos + b.pos) * 0.5, vector(0.22, 0.78, 0.35), 0.09, 1.0)
        elif d < 1.05 and not next_compatible(a, b):
            add_field_line(a.pos, b.pos, vector(1.0, 0.25, 0.2), 0.5)
            a.vel += norm(a.pos - b.pos + random_vec(0.05)) * 0.35
            b.vel += norm(b.pos - a.pos + random_vec(0.05)) * 0.35


def update_links(dt):
    for link in list(links):
        link.age += dt
        d = mag(link.a.pos - link.b.pos)
        valid = next_compatible(link.a, link.b) or next_compatible(link.b, link.a)
        if d > 3.8 or not valid:
            link.remove()
            links.remove(link)
            continue
        link.strength = max(0, min(1, 1.0 - abs(d - 1.55) / 2.6))
        # elastic attachment
        desired = 1.38
        direction = link.b.pos - link.a.pos
        if mag(direction) > 0.001:
            pull = norm(direction) * (d - desired) * 0.35
            link.a.vel += pull * dt
            link.b.vel -= pull * dt
        link.update_visual()


def update_forces(dt):
    for w in words:
        w.force = vector(0, 0, 0)
        w.age += dt
        w.stability *= (1.0 - 0.12 * dt)

    # Slot attraction toward sentence rail.
    chain = find_best_sentence_chain()
    for i, w in enumerate(chain):
        target = grammar_slot_position(i)
        w.slot_index = i
        w.force += (target - w.pos) * (0.42 + 0.08 * i)
        w.force += vector(0, -0.18, 0)
    for w in words:
        if w not in chain:
            w.slot_index = None
            # Drift non-chain words around the field so decoys keep moving.
            w.force += -w.pos * 0.015 + random_vec(0.015)

    # Pairwise compatibility attraction / repulsion.
    for i in range(len(words)):
        for j in range(i + 1, len(words)):
            a = words[i]
            b = words[j]
            delta = b.pos - a.pos
            d = mag(delta) + 0.001
            direction = delta / d
            comp_ab = pair_compatibility(a, b)
            comp_ba = pair_compatibility(b, a)
            comp = max(comp_ab, comp_ba)
            # Stronger attraction for grammatical neighbors; repulsion otherwise.
            if comp > 0.5:
                target_distance = 1.45
                strength = 0.28 * comp
                force = direction * (d - target_distance) * strength
                a.force += force
                b.force -= force
            else:
                repel = direction * (0.20 / max(0.22, d * d))
                a.force -= repel
                b.force += repel

            # Collision bounce.
            min_dist = a.radius + b.radius + 0.12
            if d < min_dist:
                impulse = direction * (min_dist - d) * 1.8
                a.force -= impulse
                b.force += impulse

    # Boundary force.
    for w in words:
        distance = mag(w.pos)
        if distance > WORLD_RADIUS - 0.6:
            w.force += -norm(w.pos) * (distance - (WORLD_RADIUS - 0.6)) * 4.0
            w.vel *= 0.92

    # Integrate.
    for w in words:
        acc = w.force / w.mass
        w.vel += acc * dt
        w.vel *= 0.988
        w.vel = clamp_mag(w.vel, 6.0)
        w.pos += w.vel * dt
        w.update_visual()

    maybe_attach_links()
    update_links(dt)

# -----------------------------------------------------------------------------
# Visual effects
# -----------------------------------------------------------------------------
def update_temporary_visuals(dt):
    for item in list(markers):
        item["ttl"] -= dt
        obj = item["obj"]
        obj.opacity = max(0, 0.65 * item["ttl"] / item["max_ttl"])
        obj.radius *= 1.0 + 0.8 * dt
        if item["ttl"] <= 0:
            destroy_visual(obj)
            markers.remove(item)

    for item in list(field_lines):
        item["ttl"] -= dt
        obj = item["obj"]
        obj.radius = max(0.002, obj.radius * (1.0 - 0.8 * dt))
        if item["ttl"] <= 0:
            destroy_visual(obj)
            field_lines.remove(item)

    for halo in list(stable_halos):
        halo.rotate(angle=0.015, axis=vector(0, 1, 0), origin=halo.pos)

    for flash in list(completion_flash):
        flash.opacity *= (1.0 - 1.8 * dt)
        flash.radius *= (1.0 + 1.2 * dt)
        if flash.opacity < 0.02:
            destroy_visual(flash)
            completion_flash.remove(flash)


def wrap_stable_sentence():
    chain = find_best_sentence_chain()
    if len(chain) < 3:
        return
    cleanup_list(stable_halos)
    for w in chain:
        halo = ring(
            pos=w.pos,
            axis=vector(0, 1, 0),
            radius=w.radius * 1.55,
            thickness=0.035,
            color=vector(1.0, 0.88, 0.25),
            opacity=0.42,
        )
        stable_halos.append(halo)


def completion_burst():
    center_core.color = vector(0.2, 1.0, 0.45)
    for r in [1.0, 2.0, 3.0, 4.0]:
        completion_flash.append(
            sphere(pos=vector(0, -3.25, 0), radius=r, color=vector(0.2, 0.9, 0.45), opacity=0.12)
        )
    wrap_stable_sentence()


def update_status(ai):
    snap = current_stability_snapshot()
    mode_text = ai.mode if ai else "none"
    status_label.text = (
        f"Round {ROUND_INDEX} | AI {'ON' if AI_ENABLED else 'OFF'} | Mode: {mode_text}\n"
        f"Words: {snap['word_count']} | Links: {len(links)} | Score: {snap['global_score']:.2f} | "
        f"Chain: {snap['chain_length']}/{len(GRAMMAR_PATH)} | Speed: {snap['avg_speed']:.2f}\n"
        f"Grammar field: compatible words attract, incompatible words repel, stable sentences glow"
    )

# -----------------------------------------------------------------------------
# Expressive AI behavior system
# -----------------------------------------------------------------------------
class GrammarAIController:
    def __init__(self):
        self.modes = [
            "careful_editor",
            "sentence_builder",
            "curious_orbiter",
            "chaotic_shuffle",
            "ritual_alignment",
            "constructive_spiller",
            "destructive_pruner",
            "artistic_weaver",
        ]
        self.mode_index = 0
        self.mode = self.modes[self.mode_index]
        self.mode_timer = 0.0
        self.action_timer = 0.0
        self.last_score = 0.0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.loop_timer = 0.0
        self.round_cooldown = 0.0
        self.override_timer = 0.0
        self.last_positions_signature = None
        self.position_still_timer = 0.0

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        self.mode = self.modes[self.mode_index]
        self.mode_timer = 0.0
        self.action_timer = 0.0
        add_marker(vector(0, 5.5, 0), vector(1.0, 0.88, 0.20), 0.24, 1.0)
        print(f"AI mode: {self.mode}")

    def choose_mode_from_state(self, snap):
        if snap["word_count"] < 8:
            return "constructive_spiller"
        if snap["complete"]:
            return "artistic_weaver"
        if snap["global_score"] < 0.30:
            return "sentence_builder"
        if self.stagnation_timer > 4.0:
            return random.choice(["chaotic_shuffle", "constructive_spiller", "ritual_alignment"])
        if len(links) > 14:
            return "destructive_pruner"
        if snap["avg_speed"] < 0.08 and snap["global_score"] < 0.72:
            return "curious_orbiter"
        return random.choice(["careful_editor", "sentence_builder", "ritual_alignment", "artistic_weaver"])

    def set_mode(self, new_mode):
        if new_mode in self.modes and new_mode != self.mode:
            self.mode = new_mode
            self.mode_index = self.modes.index(new_mode)
            self.mode_timer = 0.0
            self.action_timer = 0.0
            add_marker(vector(0, 6.4, 0), vector(0.95, 0.78, 0.22), 0.18, 0.9)

    def detect_stagnation_and_completion(self, snap, dt):
        score_delta = abs(snap["global_score"] - self.last_score)
        if score_delta < 0.012 and snap["avg_speed"] < 0.16:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0, self.stagnation_timer - dt * 1.2)

        # Position signature adds another stuck detector.
        if words:
            signature = sum(round(w.pos.x, 1) + 0.3 * round(w.pos.y, 1) + 0.2 * round(w.pos.z, 1) for w in words)
            if self.last_positions_signature is not None and abs(signature - self.last_positions_signature) < 0.18:
                self.position_still_timer += dt
            else:
                self.position_still_timer = max(0, self.position_still_timer - dt)
            self.last_positions_signature = signature

        if snap["complete"]:
            self.completion_timer += dt
            if self.completion_timer < dt * 2.0:
                completion_burst()
        else:
            self.completion_timer = max(0, self.completion_timer - dt * 2.0)

        self.last_score = snap["global_score"]
        return self.stagnation_timer > 8.0 or self.position_still_timer > 10.0, self.completion_timer > 5.2

    def update(self, dt):
        if self.override_timer > 0:
            self.override_timer -= dt
            return

        snap = current_stability_snapshot()
        stagnant, complete = self.detect_stagnation_and_completion(snap, dt)
        self.mode_timer += dt
        self.action_timer -= dt
        self.round_cooldown = max(0, self.round_cooldown - dt)

        # Loop system: if complete, empty, or stuck, start a new grammar round.
        if (complete or stagnant or snap["word_count"] == 0) and self.round_cooldown <= 0:
            if complete:
                self.loop_timer += dt
                self.set_mode("artistic_weaver")
                if self.loop_timer > 2.5:
                    reset_simulation("AI completed a stable sentence")
                    self.loop_timer = 0
                    self.round_cooldown = 3.0
                    self.stagnation_timer = 0
                    self.completion_timer = 0
                    return
            else:
                reset_simulation("AI detected stagnation or empty field")
                self.round_cooldown = 3.0
                self.stagnation_timer = 0
                self.position_still_timer = 0
                return
        else:
            self.loop_timer = max(0, self.loop_timer - dt)

        # Behavior switching over time and state.
        if self.mode_timer > random.uniform(5.5, 9.5):
            self.set_mode(self.choose_mode_from_state(snap))

        if self.action_timer <= 0:
            self.perform_mode_action(snap)
            self.action_timer = random.uniform(0.45, 1.15)

        self.apply_continuous_behavior(dt, snap)

    def perform_mode_action(self, snap):
        if self.mode == "careful_editor":
            self.action_careful_editor()
        elif self.mode == "sentence_builder":
            grammar_organization_pulse()
        elif self.mode == "curious_orbiter":
            self.action_curious_orbiter()
        elif self.mode == "chaotic_shuffle":
            if random.random() < 0.55:
                scatter_words(random.uniform(1.4, 3.4))
            else:
                self.action_swap_two_words()
        elif self.mode == "ritual_alignment":
            self.action_ritual_alignment()
        elif self.mode == "constructive_spiller":
            self.action_constructive_spiller()
        elif self.mode == "destructive_pruner":
            self.action_destructive_pruner()
        elif self.mode == "artistic_weaver":
            self.action_artistic_weaver()

    def apply_continuous_behavior(self, dt, snap):
        chain = find_best_sentence_chain()
        t = self.mode_timer
        if self.mode == "curious_orbiter":
            for i, w in enumerate(words):
                if w not in chain:
                    tangent = vector(-w.pos.z, 0, w.pos.x)
                    if mag(tangent) > 0.01:
                        w.vel += norm(tangent) * 0.09 * dt * (1 + 0.5 * math.sin(t + i))
        elif self.mode == "ritual_alignment":
            for i, w in enumerate(chain):
                target = grammar_slot_position(i) + vector(0, 0.16 * math.sin(t * 2 + i), 0)
                w.vel += clamp_mag(target - w.pos, 2.0) * 0.06
        elif self.mode == "artistic_weaver":
            for i in range(len(chain) - 1):
                if random.random() < 0.02:
                    add_field_line(chain[i].pos, chain[i + 1].pos, vector(1.0, 0.82, 0.30), 0.9)
        elif self.mode == "careful_editor":
            for w in words:
                if w.pos_type == "punct":
                    w.vel += (grammar_slot_position(len(GRAMMAR_PATH) - 1) - w.pos) * 0.018

    def action_careful_editor(self):
        sorted_words = sorted(words, key=lambda w: w.pos.x)
        for i in range(len(sorted_words) - 1):
            a, b = sorted_words[i], sorted_words[i + 1]
            if not next_compatible(a, b):
                # Detach or separate the local grammar conflict.
                remove_existing_link(a, b)
                push = norm(a.pos - b.pos + random_vec(0.1)) * 0.65
                a.vel += push
                b.vel -= push
                add_field_line(a.pos, b.pos, vector(1.0, 0.20, 0.20), 1.0)
                add_marker((a.pos + b.pos) * 0.5, vector(1.0, 0.25, 0.25), 0.13, 1.0)
                return
        grammar_organization_pulse()

    def action_curious_orbiter(self):
        if not words:
            return
        target = random.choice(words)
        for w in words:
            if w is not target:
                tangent = cross(norm(w.pos - target.pos + random_vec(0.05)), vector(0, 1, 0))
                if mag(tangent) > 0.001:
                    w.vel += norm(tangent) * random.uniform(0.25, 0.75)
        add_marker(target.pos, vector(0.45, 0.65, 1.0), 0.20, 1.3)

    def action_swap_two_words(self):
        if len(words) < 2:
            return
        a, b = random.sample(words, 2)
        a.vel += (b.pos - a.pos) * 0.16
        b.vel += (a.pos - b.pos) * 0.16
        add_field_line(a.pos, b.pos, vector(0.85, 0.35, 1.0), 1.0)

    def action_ritual_alignment(self):
        chain = find_best_sentence_chain()
        for i, w in enumerate(chain):
            target = grammar_slot_position(i)
            w.vel += clamp_mag(target - w.pos, 4.0) * 0.16
            add_marker(target + vector(0, 0.35, 0), POS_COLORS[w.pos_type], 0.08, 1.2)
        if random.random() < 0.35:
            wrap_stable_sentence()

    def action_constructive_spiller(self):
        # Add a useful missing slot word, not just random particles.
        chain = find_best_sentence_chain()
        existing_slots = [w.pos_type for w in chain]
        missing_slots = [slot for slot in GRAMMAR_PATH if existing_slots.count(slot) < GRAMMAR_PATH[: len(existing_slots) + 1].count(slot)]
        if missing_slots:
            wanted = missing_slots[0]
            candidates = [spec for spec in WORD_LIBRARY if spec["pos"] == wanted]
        else:
            candidates = WORD_LIBRARY
        spec = random.choice(candidates)
        spawn_pos = vector(random.uniform(-5, 5), random.uniform(4.5, 7.5), random.uniform(-2.5, 2.5))
        spawn_word(spec, spawn_pos, vector(random.uniform(-0.6, 0.6), -1.0, random.uniform(-0.3, 0.3)))

    def action_destructive_pruner(self):
        # Remove weakest or most conflicting decoys when the field is overcrowded.
        if len(words) <= len(GRAMMAR_PATH):
            self.set_mode("sentence_builder")
            return
        chain = find_best_sentence_chain()
        non_chain = [w for w in words if w not in chain]
        target = random.choice(non_chain if non_chain else words)
        add_marker(target.pos, vector(1.0, 0.20, 0.20), 0.18, 0.7)
        target.remove()
        words.remove(target)
        for link in list(links):
            if link.a is target or link.b is target:
                link.remove()
                links.remove(link)

    def action_artistic_weaver(self):
        chain = find_best_sentence_chain()
        if len(chain) >= 2:
            for i in range(len(chain) - 1):
                add_field_line(chain[i].pos, chain[i + 1].pos, vector(1.0, 0.82, 0.25), 1.5)
                chain[i].stability = min(1.0, chain[i].stability + 0.12)
                chain[i + 1].stability = min(1.0, chain[i + 1].stability + 0.12)
            wrap_stable_sentence()
        else:
            grammar_organization_pulse()

ai = GrammarAIController()

# -----------------------------------------------------------------------------
# Keyboard controls and user interaction
# -----------------------------------------------------------------------------
def on_keydown(evt):
    global PAUSED, AI_ENABLED, SIM_SPEED, TRAILS_ENABLED
    key = evt.key.lower()
    if key == "a":
        AI_ENABLED = not AI_ENABLED
        print(f"AI {'enabled' if AI_ENABLED else 'disabled'}")
    elif key == "p":
        PAUSED = not PAUSED
        print(f"Simulation {'paused' if PAUSED else 'resumed'}")
    elif key == "r":
        reset_simulation("manual key reset")
    elif key == "m":
        ai.cycle_mode()
    elif key == "n":
        spawn_sentence_cloud()
    elif key == "g":
        grammar_organization_pulse()
        ai.override_timer = 0.8
    elif key == "x":
        scatter_words(5.0)
        ai.override_timer = 1.2
    elif key == "t":
        TRAILS_ENABLED = not TRAILS_ENABLED
        for w in words:
            w.body.make_trail = TRAILS_ENABLED
            if not TRAILS_ENABLED:
                w.clear_trail()
    elif key == "c":
        for item in markers:
            destroy_visual(item["obj"])
        markers.clear()
        for item in field_lines:
            destroy_visual(item["obj"])
        field_lines.clear()
        cleanup_list(stable_halos)
    elif key in ["+", "="]:
        SIM_SPEED = min(4.0, SIM_SPEED + 0.15)
    elif key in ["-", "_"]:
        SIM_SPEED = max(0.15, SIM_SPEED - 0.15)
    elif key == "h":
        print_controls()

scene.bind("keydown", on_keydown)

# Camera pan/rotate helpers with arrow keys and I/J/K/L.
camera_pan = vector(0, 0, 0)

def update_camera_keyboard():
    # VPython does not give continuous key state here, so this function is reserved
    # for extension. Mouse drag and scroll remain available by default.
    pass

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
reset_simulation("initial setup")
print_controls()

while True:
    rate(60)
    if PAUSED:
        update_status(ai)
        continue

    dt = DT_BASE * SIM_SPEED
    update_forces(dt)

    if AI_ENABLED:
        ai.update(dt)

    update_temporary_visuals(dt)
    update_status(ai)
