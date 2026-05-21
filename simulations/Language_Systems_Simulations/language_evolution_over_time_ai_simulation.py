"""
Language Evolution Over Time — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python language_evolution_over_time_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset simulation
    M       cycle AI behavior mode
    B       force borrowing event
    S       force word split event
    G       force word merge event
    N       spawn new word
    C       clear temporary markers/trails
    + / =   increase simulation speed
    - / _   decrease simulation speed
    H       print controls

Scene concept:
    Words are represented as floating labeled spheres in a semantic-pronunciation space.
    Each word drifts across generations, leaving a historical trail. Close words can merge.
    Unstable words can split into descendants. Border contacts can borrow words from
    neighboring language regions. Pronunciation changes are shown by phoneme beads moving
    around each word. New meanings are shown as translucent halos and attached meaning tags.

AI controller:
    The AI reads the state of the simulation and chooses visible language-evolution actions:
    drift, split, merge, borrow, mark, organize, orbit, spill new meanings, wrap language
    families, and reset the system if it becomes stable, empty, complete, or stagnant.
"""

from vpython import *
import random
import math
import time

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

scene = canvas(
    title="Language Evolution Over Time — VPython Simulation with Expressive AI",
    width=1280,
    height=760,
    background=vector(0.92, 0.96, 1.0),
    center=vector(0, 0, 0),
    range=18
)

scene.forward = vector(-0.65, -0.35, -0.68)
scene.up = vector(0, 1, 0)

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def clamp(value, low, high):
    return max(low, min(high, value))

def mag_safe(v):
    m = mag(v)
    if m < 1e-8:
        return 1e-8
    return m

def norm_safe(v):
    m = mag_safe(v)
    return v / m

def rand_vec(scale=1.0):
    return vector(
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
        random.uniform(-scale, scale)
    )

def random_unit():
    return norm_safe(rand_vec(1.0))

def mix_color(c1, c2, t):
    t = clamp(t, 0, 1)
    return c1 * (1 - t) + c2 * t

def short_word(base):
    suffixes = ["a", "e", "i", "o", "u", "en", "on", "um", "ar", "el", "is", "or", "eth"]
    prefixes = ["", "ka", "lo", "mi", "ta", "su", "no", "re", "an", "vo"]
    if random.random() < 0.45:
        return random.choice(prefixes) + base
    return base + random.choice(suffixes)

def mutate_text(word):
    letters = "aeioubcdfghklmnprstvwxyz"
    if len(word) < 2:
        return word + random.choice(letters)
    mode = random.choice(["substitute", "insert", "delete", "shift", "duplicate"])
    idx = random.randrange(len(word))
    if mode == "substitute":
        return word[:idx] + random.choice(letters) + word[idx + 1:]
    if mode == "insert":
        return word[:idx] + random.choice(letters) + word[idx:]
    if mode == "delete" and len(word) > 3:
        return word[:idx] + word[idx + 1:]
    if mode == "duplicate":
        return word[:idx] + word[idx] + word[idx:]
    if mode == "shift":
        return word[-1] + word[:-1]
    return word

def make_label_text(word):
    return word[:14]

# ---------------------------------------------------------------------------
# Global simulation state
# ---------------------------------------------------------------------------

LANGUAGE_COLORS = [
    vector(0.25, 0.48, 0.95),   # blue
    vector(0.90, 0.36, 0.30),   # red
    vector(0.20, 0.62, 0.42),   # green
    vector(0.84, 0.55, 0.16),   # amber
    vector(0.52, 0.36, 0.78),   # purple
]

LANGUAGE_NAMES = ["North Tongue", "River Tongue", "Coast Tongue", "Hill Tongue", "Market Creole"]

BASE_WORDS = [
    "sun", "water", "stone", "hand", "mother", "fire", "path", "grain", "sky", "song",
    "trade", "house", "fish", "root", "wind", "name", "heart", "moon", "child", "law",
]

MEANINGS = [
    "light", "drink", "memory", "tool", "family", "heat", "journey", "food", "weather",
    "ritual", "exchange", "shelter", "river", "origin", "motion", "identity", "feeling",
    "night", "future", "rule", "power", "home", "danger", "gift", "belief", "market",
]

PHONEME_COLORS = [
    vector(0.95, 0.65, 0.25),
    vector(0.25, 0.75, 0.90),
    vector(0.85, 0.38, 0.85),
    vector(0.40, 0.85, 0.45),
    vector(0.95, 0.45, 0.32),
]

words = []
languages = []
particles = []
temporary_marks = []
family_rings = []
generation = 0
sim_time = 0.0
speed_multiplier = 1.0
paused = False
selected_word = None
manual_impulse = vector(0, 0, 0)

# ---------------------------------------------------------------------------
# Visual environment
# ---------------------------------------------------------------------------

floor = box(
    pos=vector(0, -8.2, 0),
    size=vector(34, 0.12, 34),
    color=vector(0.86, 0.91, 0.93),
    opacity=0.42
)

x_axis = curve(
    pos=[vector(-16, -8.0, 0), vector(16, -8.0, 0)],
    color=vector(0.55, 0.58, 0.62),
    radius=0.025
)
z_axis = curve(
    pos=[vector(0, -8.0, -16), vector(0, -8.0, 16)],
    color=vector(0.55, 0.58, 0.62),
    radius=0.025
)

label(
    pos=vector(13.5, -7.5, 0),
    text="meaning drift →",
    height=12,
    color=vector(0.25, 0.28, 0.32),
    box=False,
    opacity=0
)
label(
    pos=vector(0, -7.5, 13.8),
    text="pronunciation drift →",
    height=12,
    color=vector(0.25, 0.28, 0.32),
    box=False,
    opacity=0
)

status_label = label(
    pos=vector(-16, 10.2, 0),
    text="",
    height=13,
    color=vector(0.05, 0.08, 0.12),
    box=True,
    line=False,
    border=8,
    background=vector(1, 1, 1),
    opacity=0.72
)

legend_label = label(
    pos=vector(11.5, 9.4, 0),
    text="H: controls | A: AI | P: pause | R: reset | M: mode",
    height=11,
    color=vector(0.08, 0.1, 0.14),
    box=False,
    opacity=0
)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class LanguageRegion:
    def __init__(self, index, name, center, color_value):
        self.index = index
        self.name = name
        self.center = center
        self.color = color_value
        self.radius = random.uniform(4.1, 5.5)
        self.body = sphere(
            pos=center,
            radius=self.radius,
            color=color_value,
            opacity=0.08
        )
        self.boundary = ring(
            pos=center,
            axis=vector(0, 1, 0),
            radius=self.radius,
            thickness=0.035,
            color=color_value,
            opacity=0.35
        )
        self.name_label = label(
            pos=center + vector(0, self.radius + 0.6, 0),
            text=name,
            height=12,
            color=color_value * 0.8,
            box=False,
            opacity=0
        )

    def update(self, t):
        self.boundary.rotate(angle=0.002 * math.sin(t * 0.4 + self.index), axis=vector(0, 1, 0), origin=self.center)
        self.body.opacity = 0.055 + 0.025 * (0.5 + 0.5 * math.sin(t * 0.5 + self.index))


class WordNode:
    def __init__(self, word, meaning, lang_index, pos, parent_id=None, generation_created=0):
        self.id = random.randint(100000, 999999)
        self.word = word
        self.meaning = meaning
        self.lang_index = lang_index
        self.parent_id = parent_id
        self.children = []
        self.age = 0.0
        self.generation_created = generation_created
        self.stability = random.uniform(0.25, 0.75)
        self.change_pressure = random.uniform(0.2, 0.9)
        self.borrowed = False
        self.alive = True
        self.meaning_strength = random.uniform(0.45, 1.0)
        self.pronunciation_angle = random.uniform(0, 2 * math.pi)
        self.pronunciation_shift = rand_vec(0.3)
        self.semantic_velocity = rand_vec(0.035)
        self.selected = False
        self.family_phase = random.uniform(0, 2 * math.pi)

        base_color = LANGUAGE_COLORS[lang_index]
        self.color = mix_color(base_color, vector(1, 1, 1), 0.12)

        self.body = sphere(
            pos=pos,
            radius=0.43,
            color=self.color,
            opacity=0.94,
            shininess=0.25,
            make_trail=True,
            retain=115,
            trail_radius=0.025,
            trail_color=self.color
        )

        self.halo = sphere(
            pos=pos,
            radius=0.78,
            color=self.color,
            opacity=0.12
        )

        self.text_label = label(
            pos=pos + vector(0, 0.85, 0),
            text=make_label_text(self.word),
            height=11,
            color=vector(0.04, 0.05, 0.07),
            box=True,
            background=vector(1, 1, 1),
            opacity=0.62,
            border=5
        )

        self.meaning_label = label(
            pos=pos + vector(0, -0.82, 0),
            text=self.meaning,
            height=8,
            color=vector(0.20, 0.23, 0.26),
            box=False,
            opacity=0
        )

        self.phonemes = []
        count = clamp(len(word), 3, 7)
        for i in range(count):
            bead = sphere(
                pos=pos,
                radius=0.095,
                color=PHONEME_COLORS[i % len(PHONEME_COLORS)],
                opacity=0.9
            )
            self.phonemes.append(bead)

        self.links = []

    def pos(self):
        return self.body.pos

    def set_pos(self, p):
        self.body.pos = p
        self.halo.pos = p
        self.text_label.pos = p + vector(0, 0.85, 0)
        self.meaning_label.pos = p + vector(0, -0.82, 0)

    def update_visuals(self, dt, t):
        p = self.body.pos
        self.age += dt

        lang_color = LANGUAGE_COLORS[self.lang_index]
        self.body.color = mix_color(lang_color, vector(1, 1, 1), 0.05 + 0.25 * (1 - self.stability))
        self.halo.color = self.body.color
        self.halo.radius = 0.68 + 0.45 * self.meaning_strength + 0.12 * math.sin(t * 2.2 + self.family_phase)
        self.halo.opacity = 0.08 + 0.08 * (1 - self.stability)

        if self.selected:
            self.body.radius = 0.57
            self.halo.opacity = 0.24
        else:
            self.body.radius = 0.43 + 0.05 * (1 - self.stability)

        self.text_label.text = make_label_text(self.word)
        self.meaning_label.text = self.meaning

        self.pronunciation_angle += dt * (1.5 + 2.2 * self.change_pressure)
        for i, bead in enumerate(self.phonemes):
            a = self.pronunciation_angle + i * 2 * math.pi / len(self.phonemes)
            r = 0.62 + 0.05 * math.sin(t * 2 + i)
            bead.pos = p + vector(math.cos(a) * r, 0.05 * math.sin(a * 2), math.sin(a) * r)
            bead.opacity = 0.65 + 0.25 * math.sin(t * 3 + i)

    def move(self, delta):
        self.set_pos(self.body.pos + delta)

    def hide(self):
        self.alive = False
        self.body.visible = False
        self.halo.visible = False
        self.text_label.visible = False
        self.meaning_label.visible = False
        for bead in self.phonemes:
            bead.visible = False
        for link in self.links:
            link.visible = False

    def delete(self):
        self.hide()
        self.body.clear_trail()


class Particle:
    def __init__(self, pos, vel, color_value, radius=0.07, ttl=2.0, label_text=None):
        self.pos = pos
        self.vel = vel
        self.ttl = ttl
        self.life = ttl
        self.body = sphere(pos=pos, radius=radius, color=color_value, opacity=0.75)
        self.text = None
        if label_text:
            self.text = label(
                pos=pos + vector(0, 0.25, 0),
                text=label_text,
                height=7,
                color=color_value * 0.75,
                box=False,
                opacity=0
            )

    def update(self, dt):
        self.life -= dt
        self.pos += self.vel * dt
        self.vel *= 0.985
        self.body.pos = self.pos
        self.body.opacity = max(0, 0.75 * self.life / self.ttl)
        if self.text:
            self.text.pos = self.pos + vector(0, 0.25, 0)
            self.text.color = self.body.color
        return self.life > 0

    def delete(self):
        self.body.visible = False
        if self.text:
            self.text.visible = False


class AIController:
    def __init__(self):
        self.enabled = True
        self.modes = [
            "careful_drift",
            "split_dialects",
            "merge_cognates",
            "borrow_trade_words",
            "ritual_family_wrap",
            "chaotic_sound_shift",
            "construct_meanings",
            "archive_lineages",
            "market_creole",
            "reset_garden",
        ]
        self.mode_index = 0
        self.mode = self.modes[self.mode_index]
        self.timer = 0.0
        self.mode_duration = 6.0
        self.action_cooldown = 0.0
        self.last_metric = 0.0
        self.stagnation_time = 0.0
        self.completed_time = 0.0
        self.round_number = 1
        self.notice_timer = 0.0

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        self.mode = self.modes[self.mode_index]
        self.timer = 0.0
        flash_notice("AI mode: " + self.mode.replace("_", " "))

    def read_state(self):
        active = [w for w in words if w.alive]
        if not active:
            return {
                "count": 0,
                "avg_stability": 0,
                "avg_pressure": 0,
                "spread": 0,
                "borrowed_count": 0,
                "oldest_age": 0,
                "close_pairs": [],
                "isolated": [],
                "crowded": [],
            }

        center = vector(0, 0, 0)
        for w in active:
            center += w.pos()
        center /= len(active)

        spread = sum(mag(w.pos() - center) for w in active) / len(active)
        avg_stability = sum(w.stability for w in active) / len(active)
        avg_pressure = sum(w.change_pressure for w in active) / len(active)
        borrowed_count = sum(1 for w in active if w.borrowed)
        oldest_age = max(w.age for w in active)

        close_pairs = []
        crowded = []
        isolated = []

        for i, a in enumerate(active):
            near_count = 0
            for b in active[i + 1:]:
                d = mag(a.pos() - b.pos())
                if d < 1.2:
                    close_pairs.append((a, b, d))
                if d < 2.2:
                    near_count += 1
            if near_count == 0:
                isolated.append(a)
            if near_count >= 3:
                crowded.append(a)

        metric = count_lineages() + spread + avg_pressure * 5 + borrowed_count * 0.7
        change = abs(metric - self.last_metric)
        if change < 0.025:
            self.stagnation_time += 1 / 60
        else:
            self.stagnation_time = max(0, self.stagnation_time - 0.35)
        self.last_metric = metric

        if len(active) >= 42 or avg_stability > 0.93 or self.stagnation_time > 9:
            self.completed_time += 1 / 60
        else:
            self.completed_time = 0

        return {
            "count": len(active),
            "avg_stability": avg_stability,
            "avg_pressure": avg_pressure,
            "spread": spread,
            "borrowed_count": borrowed_count,
            "oldest_age": oldest_age,
            "close_pairs": close_pairs,
            "isolated": isolated,
            "crowded": crowded,
            "metric": metric,
        }

    def choose_mode_from_state(self, state):
        if state["count"] < 7:
            return "construct_meanings"
        if state["count"] > 45:
            return "archive_lineages"
        if state["close_pairs"] and random.random() < 0.32:
            return "merge_cognates"
        if state["avg_pressure"] > 0.78:
            return "split_dialects"
        if state["borrowed_count"] < 3 and random.random() < 0.28:
            return "borrow_trade_words"
        if state["spread"] < 5.2:
            return "careful_drift"
        if self.stagnation_time > 6:
            return "chaotic_sound_shift"
        return random.choice(self.modes[:-1])

    def switch_to(self, mode_name):
        if mode_name in self.modes:
            self.mode = mode_name
            self.mode_index = self.modes.index(mode_name)
            self.timer = 0.0
            flash_notice("AI shifted to " + mode_name.replace("_", " "))

    def update(self, dt):
        if not self.enabled:
            return

        self.timer += dt
        self.action_cooldown -= dt
        state = self.read_state()

        if state["count"] == 0:
            reset_simulation(new_round=True)
            return

        if self.completed_time > 3.2:
            self.switch_to("reset_garden")
            reset_simulation(new_round=True)
            self.completed_time = 0
            self.stagnation_time = 0
            return

        if self.timer > self.mode_duration:
            self.switch_to(self.choose_mode_from_state(state))
            self.mode_duration = random.uniform(4.2, 8.5)
            self.timer = 0.0

        if self.action_cooldown > 0:
            return

        if self.mode == "careful_drift":
            self.action_careful_drift(state)
            self.action_cooldown = random.uniform(0.45, 0.9)

        elif self.mode == "split_dialects":
            self.action_split_dialects(state)
            self.action_cooldown = random.uniform(0.9, 1.6)

        elif self.mode == "merge_cognates":
            self.action_merge_cognates(state)
            self.action_cooldown = random.uniform(0.75, 1.3)

        elif self.mode == "borrow_trade_words":
            self.action_borrow_trade_words(state)
            self.action_cooldown = random.uniform(1.0, 1.8)

        elif self.mode == "ritual_family_wrap":
            self.action_family_wrap(state)
            self.action_cooldown = random.uniform(1.2, 2.0)

        elif self.mode == "chaotic_sound_shift":
            self.action_chaotic_sound_shift(state)
            self.action_cooldown = random.uniform(0.45, 0.95)

        elif self.mode == "construct_meanings":
            self.action_construct_meanings(state)
            self.action_cooldown = random.uniform(0.8, 1.3)

        elif self.mode == "archive_lineages":
            self.action_archive_lineages(state)
            self.action_cooldown = random.uniform(0.8, 1.4)

        elif self.mode == "market_creole":
            self.action_market_creole(state)
            self.action_cooldown = random.uniform(0.7, 1.2)

        elif self.mode == "reset_garden":
            reset_simulation(new_round=True)
            self.action_cooldown = 2.0

    def action_careful_drift(self, state):
        active = active_words()
        if not active:
            return
        target = random.choice(active)
        lang = languages[target.lang_index]
        direction = norm_safe(lang.center - target.pos()) * 0.06 + rand_vec(0.04)
        target.semantic_velocity += direction
        target.change_pressure = clamp(target.change_pressure + random.uniform(-0.04, 0.05), 0.05, 1.0)
        mark_word(target, "drift", vector(0.25, 0.48, 0.95))

    def action_split_dialects(self, state):
        active = active_words()
        candidates = [w for w in active if w.change_pressure > 0.46 or w.age > 6]
        if not candidates:
            candidates = active
        target = random.choice(candidates)
        split_word(target, reason="dialect split")

    def action_merge_cognates(self, state):
        if state["close_pairs"]:
            a, b, _ = min(state["close_pairs"], key=lambda item: item[2])
            merge_words(a, b)
        else:
            active = active_words()
            if len(active) >= 2:
                a, b = random.sample(active, 2)
                midpoint = (a.pos() + b.pos()) / 2
                a.semantic_velocity += norm_safe(midpoint - a.pos()) * 0.08
                b.semantic_velocity += norm_safe(midpoint - b.pos()) * 0.08

    def action_borrow_trade_words(self, state):
        active = active_words()
        if not active:
            return
        source = random.choice(active)
        borrow_word(source)

    def action_family_wrap(self, state):
        create_family_ring()
        for w in active_words():
            center = languages[w.lang_index].center
            tangent = cross(vector(0, 1, 0), norm_safe(w.pos() - center))
            w.semantic_velocity += tangent * 0.025
        flash_notice("AI wrapped language families")

    def action_chaotic_sound_shift(self, state):
        active = active_words()
        if not active:
            return
        count = min(len(active), random.randint(2, 6))
        for target in random.sample(active, count):
            target.word = mutate_text(target.word)
            target.change_pressure = clamp(target.change_pressure + 0.14, 0.0, 1.0)
            target.semantic_velocity += rand_vec(0.16)
            emit_particles(target.pos(), 8, vector(0.85, 0.38, 0.85), "sound")
        flash_notice("AI triggered sound shift")

    def action_construct_meanings(self, state):
        spawn_new_word()
        active = active_words()
        if active:
            target = random.choice(active)
            target.meaning = random.choice(MEANINGS)
            target.meaning_strength = clamp(target.meaning_strength + 0.15, 0.2, 1.4)
            mark_word(target, "meaning", vector(0.20, 0.62, 0.42))

    def action_archive_lineages(self, state):
        active = sorted(active_words(), key=lambda w: w.age, reverse=True)
        if len(active) < 10:
            return
        target = random.choice(active[:max(3, len(active) // 3)])
        if random.random() < 0.5:
            target.stability = clamp(target.stability + 0.18, 0, 1)
            target.change_pressure = clamp(target.change_pressure - 0.16, 0, 1)
            mark_word(target, "archived", vector(0.3, 0.3, 0.3))
        else:
            fade_word(target)

    def action_market_creole(self, state):
        active = active_words()
        if len(active) < 2:
            return
        different = [(a, b) for a in active for b in active if a != b and a.lang_index != b.lang_index]
        if not different:
            return
        a, b = random.choice(different)
        midpoint = (a.pos() + b.pos()) / 2 + rand_vec(0.4)
        new_word_text = a.word[:max(1, len(a.word)//2)] + b.word[max(1, len(b.word)//2):]
        new_meaning = random.choice([a.meaning, b.meaning, "trade-" + random.choice(MEANINGS)])
        lang_index = 4 if len(languages) > 4 else random.randrange(len(languages))
        child = create_word(new_word_text, new_meaning, lang_index, midpoint, parent_id=a.id, generation_created=generation)
        child.borrowed = True
        child.change_pressure = 0.78
        child.meaning_strength = 1.15
        a.children.append(child.id)
        b.children.append(child.id)
        create_link(a, child, vector(0.52, 0.36, 0.78), 0.035)
        create_link(b, child, vector(0.52, 0.36, 0.78), 0.035)
        emit_particles(midpoint, 18, vector(0.52, 0.36, 0.78), "creole")
        flash_notice("AI formed a creole blend")


ai = AIController()

# ---------------------------------------------------------------------------
# Core simulation functions
# ---------------------------------------------------------------------------

def active_words():
    return [w for w in words if w.alive]

def count_lineages():
    parent_ids = set(w.parent_id for w in words if w.parent_id is not None and w.alive)
    child_ids = set(w.id for w in words if w.alive and w.children)
    return len(parent_ids | child_ids)

def create_language_regions():
    global languages
    languages = []
    centers = [
        vector(-8.3, 0, -5.5),
        vector(7.8, 0, -5.4),
        vector(-7.5, 0, 6.2),
        vector(7.5, 0, 6.0),
        vector(0.0, 0, 0.0),
    ]
    for i, name in enumerate(LANGUAGE_NAMES):
        languages.append(LanguageRegion(i, name, centers[i], LANGUAGE_COLORS[i]))

def create_word(word, meaning, lang_index, pos, parent_id=None, generation_created=0):
    node = WordNode(word, meaning, lang_index, pos, parent_id, generation_created)
    words.append(node)
    return node

def seed_words():
    for i in range(15):
        lang_index = i % 4
        center = languages[lang_index].center
        word = random.choice(BASE_WORDS)
        meaning = random.choice(MEANINGS)
        p = center + rand_vec(2.3) + vector(0, random.uniform(-0.5, 2.2), 0)
        node = create_word(word, meaning, lang_index, p, generation_created=generation)
        node.semantic_velocity = rand_vec(0.025)

def spawn_new_word(lang_index=None):
    if lang_index is None:
        lang_index = random.randrange(len(languages))
    base = random.choice(BASE_WORDS)
    word = short_word(base)
    meaning = random.choice(MEANINGS)
    p = languages[lang_index].center + rand_vec(random.uniform(1.2, 3.4)) + vector(0, random.uniform(-0.4, 2.8), 0)
    node = create_word(word, meaning, lang_index, p, generation_created=generation)
    node.change_pressure = random.uniform(0.35, 0.82)
    emit_particles(p, 14, LANGUAGE_COLORS[lang_index], "new")
    flash_notice("New word emerged: " + node.word)
    return node

def split_word(parent, reason="split"):
    if not parent.alive or len(active_words()) > 55:
        return None
    child_word = mutate_text(parent.word)
    child_meaning = parent.meaning
    if random.random() < 0.42:
        child_meaning = random.choice(MEANINGS)
    offset = random_unit() * random.uniform(1.0, 1.9)
    child = create_word(
        child_word,
        child_meaning,
        parent.lang_index,
        parent.pos() + offset,
        parent_id=parent.id,
        generation_created=generation,
    )
    parent.children.append(child.id)
    child.semantic_velocity = offset * 0.04 + rand_vec(0.05)
    child.change_pressure = clamp(parent.change_pressure + random.uniform(-0.12, 0.22), 0.05, 1.0)
    parent.change_pressure = clamp(parent.change_pressure - 0.10, 0.05, 1.0)
    create_link(parent, child, LANGUAGE_COLORS[parent.lang_index], 0.03)
    emit_particles(parent.pos(), 18, LANGUAGE_COLORS[parent.lang_index], "split")
    mark_word(parent, "ancestor", LANGUAGE_COLORS[parent.lang_index])
    flash_notice(parent.word + " split into " + child.word)
    return child

def merge_words(a, b):
    if not a.alive or not b.alive or a == b:
        return None

    new_lang = a.lang_index if random.random() < 0.5 else b.lang_index
    left = a.word[:max(1, len(a.word)//2)]
    right = b.word[max(1, len(b.word)//2):]
    merged_word = (left + right)[:16]
    new_meaning = a.meaning if random.random() < 0.5 else b.meaning
    if random.random() < 0.25:
        new_meaning = a.meaning + "+" + b.meaning

    midpoint = (a.pos() + b.pos()) / 2
    child = create_word(merged_word, new_meaning, new_lang, midpoint + rand_vec(0.2), parent_id=a.id, generation_created=generation)
    child.borrowed = a.borrowed or b.borrowed or (a.lang_index != b.lang_index)
    child.stability = clamp((a.stability + b.stability) / 2 + 0.08, 0, 1)
    child.change_pressure = clamp((a.change_pressure + b.change_pressure) / 2 - 0.05, 0.05, 1.0)
    a.children.append(child.id)
    b.children.append(child.id)

    create_link(a, child, vector(0.1, 0.1, 0.1), 0.04)
    create_link(b, child, vector(0.1, 0.1, 0.1), 0.04)

    emit_particles(midpoint, 20, vector(0.12, 0.12, 0.12), "merge")
    fade_word(a)
    fade_word(b)
    flash_notice("Merged words into " + child.word)
    return child

def borrow_word(source):
    if not source.alive:
        return None
    possible = [i for i in range(len(languages)) if i != source.lang_index]
    target_lang = random.choice(possible)
    borrowed_text = mutate_text(source.word)
    p = languages[target_lang].center + rand_vec(2.2) + vector(0, random.uniform(-0.1, 2.5), 0)
    borrowed = create_word(borrowed_text, source.meaning, target_lang, p, parent_id=source.id, generation_created=generation)
    borrowed.borrowed = True
    borrowed.change_pressure = 0.65
    borrowed.meaning_strength = source.meaning_strength + 0.15
    source.children.append(borrowed.id)
    create_link(source, borrowed, vector(0.84, 0.55, 0.16), 0.03)
    emit_particles(source.pos(), 12, vector(0.84, 0.55, 0.16), "borrow")
    emit_particles(p, 12, vector(0.84, 0.55, 0.16), "loan")
    flash_notice(source.word + " was borrowed as " + borrowed.word)
    return borrowed

def fade_word(word_node):
    if len(active_words()) <= 5:
        return
    emit_particles(word_node.pos(), 12, vector(0.45, 0.45, 0.45), "old")
    word_node.hide()

def create_link(a, b, color_value, radius_value):
    link = curve(
        pos=[a.pos(), b.pos()],
        color=color_value,
        radius=radius_value,
        opacity=0.38
    )
    a.links.append(link)
    b.links.append(link)
    temporary_marks.append(link)
    return link

def update_links():
    for w in words:
        if not w.alive:
            continue
        for link in w.links:
            if hasattr(link, "visible") and link.visible:
                # Keep links subtle; static genealogy links intentionally remain
                # anchored to historical positions by not updating every endpoint.
                pass

def emit_particles(pos, count, color_value, label_text=None):
    for _ in range(count):
        vel = rand_vec(random.uniform(0.5, 1.6))
        particles.append(Particle(pos + rand_vec(0.15), vel, color_value, ttl=random.uniform(1.0, 2.5), label_text=label_text if random.random() < 0.15 else None))

def mark_word(word_node, text, color_value):
    marker = ring(
        pos=word_node.pos(),
        axis=vector(0, 1, 0),
        radius=0.82,
        thickness=0.035,
        color=color_value,
        opacity=0.75
    )
    tag = label(
        pos=word_node.pos() + vector(0, 1.25, 0),
        text=text,
        height=8,
        color=color_value * 0.75,
        box=False,
        opacity=0
    )
    temporary_marks.append(marker)
    temporary_marks.append(tag)

def create_family_ring():
    active = active_words()
    if not active:
        return
    for lang in languages:
        family = [w for w in active if w.lang_index == lang.index]
        if len(family) < 2:
            continue
        center = vector(0, 0, 0)
        for w in family:
            center += w.pos()
        center /= len(family)
        radius = max(1.1, sum(mag(w.pos() - center) for w in family) / len(family) + 0.6)
        r = ring(
            pos=center,
            axis=vector(0, 1, 0),
            radius=radius,
            thickness=0.045,
            color=lang.color,
            opacity=0.42
        )
        temporary_marks.append(r)
        family_rings.append(r)

def clear_temporary_marks():
    for item in temporary_marks:
        try:
            item.visible = False
        except Exception:
            pass
    temporary_marks.clear()
    family_rings.clear()
    for p in particles:
        p.delete()
    particles.clear()
    flash_notice("Temporary marks cleared")

def flash_notice(text):
    notice = label(
        pos=vector(0, 10.5, 0),
        text=text,
        height=13,
        color=vector(0.05, 0.08, 0.12),
        box=True,
        background=vector(1.0, 0.98, 0.82),
        opacity=0.75,
        border=8
    )
    temporary_marks.append(notice)

def reset_simulation(new_round=False):
    global words, particles, temporary_marks, family_rings, generation, sim_time, selected_word

    for w in words:
        w.delete()
    words = []

    for p in particles:
        p.delete()
    particles = []

    for item in temporary_marks:
        try:
            item.visible = False
        except Exception:
            pass
    temporary_marks = []
    family_rings = []

    selected_word = None

    if new_round:
        ai.round_number += 1
        generation = 0
        sim_time = 0.0
    else:
        generation = 0
        sim_time = 0.0
        ai.round_number = 1

    seed_words()
    flash_notice("New language-evolution round " + str(ai.round_number))

# ---------------------------------------------------------------------------
# Physics / evolution update
# ---------------------------------------------------------------------------

def update_word_drift(dt):
    active = active_words()

    for w in active:
        lang = languages[w.lang_index]
        home_pull = (lang.center - w.pos()) * 0.0025
        mutation_noise = rand_vec(0.006 * (0.4 + w.change_pressure))
        upward_bias = vector(0, 0.002 * math.sin(sim_time + w.family_phase), 0)

        w.semantic_velocity += home_pull + mutation_noise + upward_bias

        # Borrowed words drift between their language center and the trade center.
        if w.borrowed:
            trade_pull = (languages[-1].center - w.pos()) * 0.003
            w.semantic_velocity += trade_pull

        # Word pressure slowly changes; stability tends to rise with age.
        w.change_pressure = clamp(w.change_pressure + random.uniform(-0.006, 0.007) * dt * 10, 0.03, 1.0)
        w.stability = clamp(w.stability + 0.004 * dt - 0.002 * w.change_pressure * dt, 0.02, 1.0)
        w.meaning_strength = clamp(w.meaning_strength + random.uniform(-0.005, 0.005), 0.25, 1.35)

        # Keep words inside the overall visible field.
        if mag(w.pos()) > 15:
            w.semantic_velocity += norm_safe(-w.pos()) * 0.08

        w.semantic_velocity *= 0.982
        w.move(w.semantic_velocity * dt * 60)

    # Soft repulsion so labels do not collapse too tightly.
    for i, a in enumerate(active):
        for b in active[i + 1:]:
            diff = a.pos() - b.pos()
            d = mag_safe(diff)
            if d < 0.95:
                push = norm_safe(diff) * (0.015 / d)
                a.move(push)
                b.move(-push)
            elif d < 1.3 and random.random() < 0.002 * speed_multiplier:
                if random.random() < 0.5:
                    merge_words(a, b)

def spontaneous_evolution_events(dt):
    global generation

    if random.random() < 0.006 * speed_multiplier and len(active_words()) < 50:
        spawn_new_word()

    active = active_words()
    if not active:
        return

    if random.random() < 0.009 * speed_multiplier:
        candidates = [w for w in active if w.change_pressure > 0.68]
        if candidates:
            split_word(random.choice(candidates), reason="pressure split")

    if random.random() < 0.004 * speed_multiplier:
        borrow_word(random.choice(active))

    if random.random() < 0.003 * speed_multiplier and len(active) > 14:
        elder = sorted(active, key=lambda w: w.age, reverse=True)[0]
        if elder.age > 18 and random.random() < elder.stability:
            fade_word(elder)

    generation += 1 if random.random() < 0.04 * speed_multiplier else 0

def update_particles(dt):
    alive_particles = []
    for p in particles:
        if p.update(dt):
            alive_particles.append(p)
        else:
            p.delete()
    particles[:] = alive_particles

def update_visuals(dt):
    for lang in languages:
        lang.update(sim_time)
    for w in active_words():
        w.update_visuals(dt, sim_time)
    for item in family_rings:
        try:
            item.rotate(angle=0.004 * speed_multiplier, axis=vector(0, 1, 0), origin=item.pos)
            item.opacity *= 0.997
        except Exception:
            pass

def update_status():
    active = active_words()
    borrowed = sum(1 for w in active if w.borrowed)
    avg_pressure = 0 if not active else sum(w.change_pressure for w in active) / len(active)
    avg_stability = 0 if not active else sum(w.stability for w in active) / len(active)
    status_label.text = (
        "Round: {round_no} | Generation: {gen} | Words: {count} | Borrowed: {borrowed}\n"
        "AI: {ai_state} | Mode: {mode} | Speed: {speed:.1f}x | Paused: {paused}\n"
        "Avg pressure: {pressure:.2f} | Avg stability: {stability:.2f} | Stagnation: {stag:.1f}s"
    ).format(
        round_no=ai.round_number,
        gen=generation,
        count=len(active),
        borrowed=borrowed,
        ai_state="on" if ai.enabled else "off",
        mode=ai.mode.replace("_", " "),
        speed=speed_multiplier,
        paused=paused,
        pressure=avg_pressure,
        stability=avg_stability,
        stag=ai.stagnation_time,
    )

# ---------------------------------------------------------------------------
# Keyboard and mouse controls
# ---------------------------------------------------------------------------

def print_controls():
    print("""
Language Evolution Over Time — controls

A       toggle AI controller on/off
P       pause/resume simulation
R       reset simulation
M       cycle AI behavior mode
B       force borrowing event
S       force word split event
G       force word merge event
N       spawn new word
C       clear temporary markers/trails
+ / =   increase simulation speed
- / _   decrease simulation speed
H       print controls

Click a word to select it.
With a word selected:
    W/S     push along pronunciation axis
    A/D     push along meaning axis if AI is off; otherwise A toggles AI
    Space   push up
    X       push down
    Delete  fade selected word
""")

def pick_word_from_mouse():
    global selected_word
    picked = scene.mouse.pick
    if picked is None:
        return
    for w in active_words():
        if picked == w.body or picked == w.halo or picked in w.phonemes:
            if selected_word:
                selected_word.selected = False
            selected_word = w
            selected_word.selected = True
            mark_word(w, "selected", vector(0.05, 0.08, 0.12))
            flash_notice("Selected word: " + w.word)
            return

def handle_key(evt):
    global paused, speed_multiplier, selected_word
    key = evt.key

    if key in ["h", "H"]:
        print_controls()
        flash_notice("Controls printed in terminal")

    elif key in ["p", "P"]:
        paused = not paused
        flash_notice("Paused" if paused else "Resumed")

    elif key in ["r", "R"]:
        reset_simulation(new_round=True)

    elif key in ["m", "M"]:
        ai.cycle_mode()

    elif key in ["b", "B"]:
        active = active_words()
        if active:
            borrow_word(random.choice(active))

    elif key in ["s", "S"]:
        active = active_words()
        if active:
            split_word(random.choice(active), reason="manual split")

    elif key in ["g", "G"]:
        active = active_words()
        if len(active) >= 2:
            a, b = random.sample(active, 2)
            merge_words(a, b)

    elif key in ["n", "N"]:
        spawn_new_word()

    elif key in ["c", "C"]:
        clear_temporary_marks()

    elif key in ["+", "="]:
        speed_multiplier = clamp(speed_multiplier + 0.2, 0.2, 5.0)
        flash_notice("Speed " + str(round(speed_multiplier, 1)) + "x")

    elif key in ["-", "_"]:
        speed_multiplier = clamp(speed_multiplier - 0.2, 0.2, 5.0)
        flash_notice("Speed " + str(round(speed_multiplier, 1)) + "x")

    elif key in ["a", "A"]:
        # A is AI toggle. If AI is off and a word is selected, D/W/S/etc can still move it.
        ai.enabled = not ai.enabled
        flash_notice("AI on" if ai.enabled else "AI off")

    elif selected_word:
        push = vector(0, 0, 0)
        if key in ["w", "W"]:
            push = vector(0, 0, -0.45)
        elif key in ["s", "S"]:
            push = vector(0, 0, 0.45)
        elif key in ["d", "D"]:
            push = vector(0.45, 0, 0)
        elif key == " ":
            push = vector(0, 0.45, 0)
        elif key in ["x", "X"]:
            push = vector(0, -0.45, 0)
        elif key in ["delete", "backspace"]:
            fade_word(selected_word)
            selected_word = None
            return

        if mag(push) > 0:
            selected_word.semantic_velocity += push * 0.08
            selected_word.move(push)
            mark_word(selected_word, "moved", vector(0.25, 0.48, 0.95))

scene.bind("keydown", handle_key)
scene.bind("click", lambda evt: pick_word_from_mouse())

# ---------------------------------------------------------------------------
# Build and run
# ---------------------------------------------------------------------------

create_language_regions()
seed_words()
print_controls()
flash_notice("Language evolution simulation started")

last = time.time()
while True:
    rate(60)
    now = time.time()
    raw_dt = now - last
    last = now

    dt = clamp(raw_dt, 0.001, 0.05) * speed_multiplier

    if not paused:
        sim_time += dt
        update_word_drift(dt)
        spontaneous_evolution_events(dt)
        ai.update(dt)
        update_particles(dt)
        update_visuals(dt)

    update_status()
