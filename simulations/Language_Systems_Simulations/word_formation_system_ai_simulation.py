"""
Word Formation System — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python word_formation_system_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset simulation
    M       cycle AI behavior mode
    L       spill new loose letters
    S       force nearest loose letters into a syllable
    W       force nearby syllables into a word
    D       detach / disturb one word or syllable
    C       clear temporary marks and particles
    B       toggle boundary bounce
    + / =   increase simulation speed
    - / _   decrease simulation speed
    H       print controls

Scene concept:
    Individual letters float through a pale 3D language space. Letters collide and attach
    into syllables. Syllables attach into words. Finished words gain labels for sound,
    meaning, and grammatical category. The AI controller can organize, orbit, spill,
    mark, detach, rebuild, decorate, and reset the system when the scene becomes stable.
"""

from vpython import *
import random
import math
import time

# -----------------------------
# Basic VPython scene
# -----------------------------
scene = canvas(
    title="Word Formation System — Letters → Syllables → Words",
    width=1180,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.9, -0.42, -1.0)
scene.range = 18

WORLD_RADIUS = 13.5
SIM_SPEED = 1.0
PAUSED = False
AI_ENABLED = True
BOUNCE_WALLS = True
NEXT_ID = 0
ROUND_NUMBER = 1
LAST_PRINT = 0

VOWELS = list("AEIOU")
CONSONANTS = list("BCDFGHJKLMNPRSTVWL")
SYLLABLE_PATTERNS = ["CV", "VC", "CVC", "CVV", "CCV", "V", "CV"]
WORD_TARGETS = [
    {"word": "SUN", "sound": "/sʌn/", "meaning": "star-light", "category": "noun"},
    {"word": "MOON", "sound": "/muːn/", "meaning": "night-orb", "category": "noun"},
    {"word": "RIVER", "sound": "/ˈrɪvər/", "meaning": "flowing water", "category": "noun"},
    {"word": "BLOOM", "sound": "/bluːm/", "meaning": "open flower", "category": "verb"},
    {"word": "LIGHT", "sound": "/laɪt/", "meaning": "visible energy", "category": "noun"},
    {"word": "DREAM", "sound": "/driːm/", "meaning": "inner image", "category": "noun"},
    {"word": "WAVE", "sound": "/weɪv/", "meaning": "moving crest", "category": "noun"},
    {"word": "GROW", "sound": "/ɡroʊ/", "meaning": "increase", "category": "verb"},
    {"word": "FORM", "sound": "/fɔːrm/", "meaning": "take shape", "category": "verb"},
    {"word": "SOUND", "sound": "/saʊnd/", "meaning": "heard vibration", "category": "noun"},
]
CATEGORIES = {
    "noun": vector(0.25, 0.45, 0.95),
    "verb": vector(0.15, 0.66, 0.34),
    "adjective": vector(0.88, 0.48, 0.18),
    "unknown": vector(0.55, 0.55, 0.62),
}

# -----------------------------
# Visual helpers
# -----------------------------
axis_x = cylinder(pos=vector(-WORLD_RADIUS, -7, 0), axis=vector(2 * WORLD_RADIUS, 0, 0), radius=0.025, color=vector(0.75, 0.78, 0.84), opacity=0.35)
axis_y = cylinder(pos=vector(0, -7, -WORLD_RADIUS), axis=vector(0, 0, 2 * WORLD_RADIUS), radius=0.025, color=vector(0.75, 0.78, 0.84), opacity=0.35)
world_boundary = sphere(pos=vector(0, 0, 0), radius=WORLD_RADIUS, color=vector(0.72, 0.84, 1.0), opacity=0.055)
center_core = sphere(pos=vector(0, 0, 0), radius=0.35, color=vector(1, 0.85, 0.25), opacity=0.45)

status = label(
    pos=vector(0, WORLD_RADIUS + 1.4, 0),
    text="",
    height=14,
    color=vector(0.10, 0.12, 0.20),
    box=False,
    opacity=0,
    line=False,
)

mode_label = label(
    pos=vector(-WORLD_RADIUS + 1.8, WORLD_RADIUS + 0.2, 0),
    text="",
    height=11,
    color=vector(0.12, 0.18, 0.28),
    box=False,
    opacity=0,
    line=False,
)

legend = label(
    pos=vector(0, -WORLD_RADIUS - 1.2, 0),
    text="A AI | P pause | R reset | M mode | L letters | S syllable | W word | D detach | C clear | B bounce | H help",
    height=10,
    color=vector(0.18, 0.20, 0.25),
    box=False,
    opacity=0,
    line=False,
)

# -----------------------------
# Containers
# -----------------------------
letters = []
syllables = []
words = []
particles = []
marks = []
links = []

# -----------------------------
# Utility functions
# -----------------------------
def new_id(prefix):
    global NEXT_ID
    NEXT_ID += 1
    return f"{prefix}{NEXT_ID}"


def rand_vec(scale=1.0):
    return vector(random.uniform(-scale, scale), random.uniform(-scale, scale), random.uniform(-scale, scale))


def rand_inside(radius=WORLD_RADIUS * 0.78):
    while True:
        p = rand_vec(radius)
        if mag(p) <= radius:
            return p


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-6:
        return fallback
    return norm(v)


def clamp_to_world(pos, radius=0.6):
    m = mag(pos)
    limit = WORLD_RADIUS - radius
    if m > limit:
        return safe_norm(pos) * limit
    return pos


def soft_color(base, jitter=0.08):
    return vector(
        min(1, max(0, base.x + random.uniform(-jitter, jitter))),
        min(1, max(0, base.y + random.uniform(-jitter, jitter))),
        min(1, max(0, base.z + random.uniform(-jitter, jitter))),
    )


def letter_color(ch):
    if ch in VOWELS:
        return soft_color(vector(0.95, 0.55, 0.36), 0.06)
    return soft_color(vector(0.34, 0.57, 0.95), 0.07)


def make_trail_dot(pos, col, life=2.0, radius=0.055):
    dot = sphere(pos=pos, radius=radius, color=col, opacity=0.42)
    particles.append({"obj": dot, "life": life, "max_life": life, "shrink": True})
    return dot


def make_pulse(pos, col, text=""):
    shell = sphere(pos=pos, radius=0.25, color=col, opacity=0.22)
    particles.append({"obj": shell, "life": 1.05, "max_life": 1.05, "grow": 0.12})
    if text:
        lab = label(pos=pos + vector(0, 0.55, 0), text=text, height=9, color=col, box=False, opacity=0, line=False)
        particles.append({"obj": lab, "life": 1.0, "max_life": 1.0, "float": vector(0, 0.015, 0)})


def remove_visual(obj):
    try:
        obj.visible = False
    except Exception:
        pass


def clear_temp():
    for p in particles:
        remove_visual(p.get("obj"))
    particles.clear()
    for m in marks:
        remove_visual(m)
    marks.clear()
    for link in links:
        remove_visual(link)
    links.clear()

# -----------------------------
# Entity classes
# -----------------------------
class LetterToken:
    def __init__(self, ch, pos=None, vel=None):
        self.id = new_id("L")
        self.ch = ch
        self.kind = "letter"
        self.pos = pos if pos is not None else rand_inside()
        self.vel = vel if vel is not None else rand_vec(0.045)
        self.spin = rand_vec(0.025)
        self.radius = 0.42
        self.attached = False
        self.parent = None
        self.age = 0.0
        self.color = letter_color(ch)
        self.body = sphere(pos=self.pos, radius=self.radius, color=self.color, opacity=0.86)
        self.glyph = label(pos=self.pos + vector(0, 0.06, 0), text=ch, height=18, color=vector(0.04, 0.05, 0.08), box=False, opacity=0, line=False)
        self.glow = sphere(pos=self.pos, radius=self.radius * 1.35, color=self.color, opacity=0.12)

    def set_pos(self, p):
        self.pos = p
        self.body.pos = p
        self.glyph.pos = p + vector(0, 0.06, 0)
        self.glow.pos = p

    def update_free(self, dt):
        if self.attached:
            return
        self.age += dt
        self.vel += rand_vec(0.012) * dt
        self.vel += -0.012 * self.pos * dt
        if mag(self.vel) > 0.085:
            self.vel = norm(self.vel) * 0.085
        self.set_pos(self.pos + self.vel * dt * 60)
        if BOUNCE_WALLS and mag(self.pos) > WORLD_RADIUS - self.radius:
            n = safe_norm(self.pos)
            self.set_pos(n * (WORLD_RADIUS - self.radius))
            self.vel = self.vel - 2 * dot(self.vel, n) * n
            make_pulse(self.pos, vector(0.55, 0.72, 1.0), "bounce")
        if random.random() < 0.025:
            make_trail_dot(self.pos, self.color, life=1.2, radius=0.035)

    def hide(self):
        remove_visual(self.body)
        remove_visual(self.glyph)
        remove_visual(self.glow)


class SyllableCluster:
    def __init__(self, letter_tokens, pos=None):
        self.id = new_id("SY")
        self.kind = "syllable"
        self.letters = letter_tokens[:]
        self.text = "".join([lt.ch for lt in self.letters])
        self.pos = pos if pos is not None else sum([lt.pos for lt in self.letters], vector(0, 0, 0)) / max(1, len(self.letters))
        self.vel = rand_vec(0.035)
        self.radius = 0.55 + 0.18 * len(self.letters)
        self.attached = False
        self.parent = None
        self.age = 0.0
        self.orbit_angle = random.random() * 2 * math.pi
        self.orbit_radius = 0.65 + 0.15 * len(self.letters)
        self.color = vector(0.98, 0.78, 0.30)
        self.body = sphere(pos=self.pos, radius=self.radius, color=self.color, opacity=0.50)
        self.text_label = label(pos=self.pos + vector(0, 0.12, 0), text=self.text, height=16, color=vector(0.11, 0.07, 0.02), box=False, opacity=0, line=False)
        self.halo = ring(pos=self.pos, axis=vector(0, 1, 0), radius=self.radius * 1.18, thickness=0.035, color=vector(1, 0.70, 0.16), opacity=0.35)
        for i, lt in enumerate(self.letters):
            lt.attached = True
            lt.parent = self
            lt.vel = vector(0, 0, 0)
            angle = i * 2 * math.pi / max(1, len(self.letters))
            offset = vector(math.cos(angle), 0.25 * math.sin(angle * 1.7), math.sin(angle)) * (self.radius * 0.72)
            lt.set_pos(self.pos + offset)
        make_pulse(self.pos, self.color, "syllable")

    def set_pos(self, p):
        delta = p - self.pos
        self.pos = p
        self.body.pos = p
        self.text_label.pos = p + vector(0, 0.12, 0)
        self.halo.pos = p
        for lt in self.letters:
            lt.set_pos(lt.pos + delta)

    def update_free(self, dt):
        self.age += dt
        if self.attached:
            return
        self.vel += -0.010 * self.pos * dt + rand_vec(0.006) * dt
        if mag(self.vel) > 0.065:
            self.vel = norm(self.vel) * 0.065
        self.set_pos(self.pos + self.vel * dt * 60)
        self.halo.axis = rotate(self.halo.axis, angle=0.012 * dt * 60, axis=vector(0, 1, 0))
        if BOUNCE_WALLS and mag(self.pos) > WORLD_RADIUS - self.radius:
            n = safe_norm(self.pos)
            self.set_pos(n * (WORLD_RADIUS - self.radius))
            self.vel = self.vel - 2 * dot(self.vel, n) * n
            make_pulse(self.pos, vector(1.0, 0.74, 0.22), "bounce")

    def hide(self):
        remove_visual(self.body)
        remove_visual(self.text_label)
        remove_visual(self.halo)


class WordCluster:
    def __init__(self, syllable_tokens, target=None, pos=None):
        self.id = new_id("WD")
        self.kind = "word"
        self.syllables = syllable_tokens[:]
        raw = "".join([sy.text for sy in self.syllables])
        self.target = target if target is not None else interpret_word(raw)
        self.text = self.target["word"]
        self.sound = self.target["sound"]
        self.meaning = self.target["meaning"]
        self.category = self.target["category"]
        self.pos = pos if pos is not None else sum([sy.pos for sy in self.syllables], vector(0, 0, 0)) / max(1, len(self.syllables))
        self.vel = rand_vec(0.025)
        self.radius = 1.0 + 0.25 * len(self.syllables)
        self.age = 0.0
        self.score = 0
        self.category_color = CATEGORIES.get(self.category, CATEGORIES["unknown"])
        self.body = sphere(pos=self.pos, radius=self.radius, color=self.category_color, opacity=0.36)
        self.label_word = label(pos=self.pos + vector(0, self.radius + 0.20, 0), text=self.text, height=22, color=vector(0.02, 0.04, 0.08), box=True, opacity=0.18, line=False)
        self.label_info = label(
            pos=self.pos + vector(0, -self.radius - 0.32, 0),
            text=f"sound {self.sound}\nmeaning {self.meaning}\ncategory {self.category}",
            height=9,
            color=vector(0.08, 0.10, 0.14),
            box=False,
            opacity=0,
            line=False,
        )
        self.halo_outer = ring(pos=self.pos, axis=vector(0, 1, 0), radius=self.radius * 1.55, thickness=0.045, color=self.category_color, opacity=0.35)
        self.halo_inner = ring(pos=self.pos, axis=vector(1, 0, 0), radius=self.radius * 1.22, thickness=0.025, color=vector(1, 1, 1), opacity=0.55)
        for i, sy in enumerate(self.syllables):
            sy.attached = True
            sy.parent = self
            sy.vel = vector(0, 0, 0)
            angle = i * 2 * math.pi / max(1, len(self.syllables))
            offset = vector(math.cos(angle), 0.25 * math.sin(angle), math.sin(angle)) * (self.radius * 1.0)
            sy.set_pos(self.pos + offset)
        make_pulse(self.pos, self.category_color, "word")

    def set_pos(self, p):
        delta = p - self.pos
        self.pos = p
        self.body.pos = p
        self.label_word.pos = p + vector(0, self.radius + 0.20, 0)
        self.label_info.pos = p + vector(0, -self.radius - 0.32, 0)
        self.halo_outer.pos = p
        self.halo_inner.pos = p
        for sy in self.syllables:
            sy.set_pos(sy.pos + delta)

    def update(self, dt):
        self.age += dt
        self.vel += -0.006 * self.pos * dt + rand_vec(0.004) * dt
        if mag(self.vel) > 0.045:
            self.vel = norm(self.vel) * 0.045
        self.set_pos(self.pos + self.vel * dt * 60)
        self.halo_outer.axis = rotate(self.halo_outer.axis, angle=0.006 * dt * 60, axis=vector(0, 1, 0))
        self.halo_inner.axis = rotate(self.halo_inner.axis, angle=-0.008 * dt * 60, axis=vector(1, 0.2, 0))
        # orbit syllables around the word center without destroying their internal letter layout
        for i, sy in enumerate(self.syllables):
            angle = self.age * 0.8 + i * 2 * math.pi / max(1, len(self.syllables))
            target = self.pos + vector(math.cos(angle), 0.22 * math.sin(angle * 1.4), math.sin(angle)) * (self.radius * 0.92)
            sy.set_pos(sy.pos + (target - sy.pos) * 0.06 * dt * 60)
        if BOUNCE_WALLS and mag(self.pos) > WORLD_RADIUS - self.radius:
            n = safe_norm(self.pos)
            self.set_pos(n * (WORLD_RADIUS - self.radius))
            self.vel = self.vel - 2 * dot(self.vel, n) * n

    def hide(self):
        remove_visual(self.body)
        remove_visual(self.label_word)
        remove_visual(self.label_info)
        remove_visual(self.halo_outer)
        remove_visual(self.halo_inner)

# -----------------------------
# Word interpretation and construction
# -----------------------------
def interpret_word(raw):
    clean = "".join([c for c in raw.upper() if c.isalpha()])
    if not clean:
        clean = random.choice(["FORM", "SOUND", "SIGN"])
    for target in WORD_TARGETS:
        if clean == target["word"]:
            return target
    # If the raw cluster does not match a known word, give it a pronounceable poetic label.
    category = random.choice(["noun", "verb", "adjective"])
    if len(clean) > 7:
        clean = clean[:7]
    meaning_roots = ["new sign", "made pattern", "spoken shape", "small idea", "sound-form", "living mark"]
    sound = "/" + clean.lower() + "/"
    return {"word": clean, "sound": sound, "meaning": random.choice(meaning_roots), "category": category}


def choose_letter_for_pattern(symbol):
    if symbol == "V":
        return random.choice(VOWELS)
    return random.choice(CONSONANTS)


def spawn_letter(ch=None, pos=None, burst=False):
    if ch is None:
        ch = random.choice(VOWELS if random.random() < 0.38 else CONSONANTS)
    vel = rand_vec(0.13 if burst else 0.055)
    token = LetterToken(ch, pos=pos if pos is not None else rand_inside(), vel=vel)
    letters.append(token)
    return token


def spill_letters(count=18, center=None, word_hint=None):
    center = center if center is not None else rand_inside(WORLD_RADIUS * 0.55)
    chars = []
    if word_hint:
        chars = list(word_hint.upper())
    for i in range(count):
        ch = chars[i % len(chars)] if chars else None
        spawn_letter(ch, pos=center + rand_vec(1.4), burst=True)
    make_pulse(center, vector(0.45, 0.65, 1.0), "letter spill")


def nearest_free_letters(pos, count=2, require_pattern=None):
    free = [lt for lt in letters if not lt.attached]
    if require_pattern:
        chosen = []
        available = free[:]
        for symbol in require_pattern:
            pool = [lt for lt in available if (lt.ch in VOWELS) == (symbol == "V")]
            if not pool:
                return []
            lt = min(pool, key=lambda x: mag(x.pos - pos))
            chosen.append(lt)
            available.remove(lt)
        return chosen
    free.sort(key=lambda x: mag(x.pos - pos))
    return free[:count]


def build_syllable_from_letters(chosen=None, pattern=None, pos=None):
    if chosen is None:
        pattern = pattern if pattern else random.choice(SYLLABLE_PATTERNS)
        chosen = nearest_free_letters(pos if pos is not None else vector(0, 0, 0), len(pattern), pattern)
    if len(chosen) < 1:
        return None
    sy = SyllableCluster(chosen)
    syllables.append(sy)
    return sy


def build_target_word(target=None, center=None):
    target = target if target is not None else random.choice(WORD_TARGETS)
    center = center if center is not None else rand_inside(WORLD_RADIUS * 0.45)
    text = target["word"]
    # Split into 1-3 visual syllable chunks.
    chunks = []
    if len(text) <= 4:
        cut = max(1, len(text) // 2)
        chunks = [text[:cut], text[cut:]] if text[cut:] else [text]
    else:
        cut1 = max(2, len(text) // 3)
        cut2 = max(cut1 + 1, 2 * len(text) // 3)
        chunks = [text[:cut1], text[cut1:cut2], text[cut2:]]
    made_syllables = []
    for ci, chunk in enumerate(chunks):
        local_letters = []
        angle = ci * 2 * math.pi / max(1, len(chunks))
        chunk_center = center + vector(math.cos(angle), 0.1 * ci, math.sin(angle)) * 1.2
        for j, ch in enumerate(chunk):
            lt = spawn_letter(ch, pos=chunk_center + rand_vec(0.42), burst=False)
            local_letters.append(lt)
        sy = build_syllable_from_letters(local_letters)
        if sy:
            made_syllables.append(sy)
    if made_syllables:
        return build_word_from_syllables(made_syllables, target=target)
    return None


def free_syllables_near(pos, count=2):
    free = [sy for sy in syllables if not sy.attached]
    free.sort(key=lambda x: mag(x.pos - pos))
    return free[:count]


def build_word_from_syllables(chosen=None, target=None):
    if chosen is None:
        chosen = free_syllables_near(vector(0, 0, 0), count=random.choice([2, 3]))
    if len(chosen) < 1:
        return None
    wd = WordCluster(chosen, target=target)
    words.append(wd)
    return wd


def detach_cluster():
    if words:
        wd = random.choice(words)
        words.remove(wd)
        pos = wd.pos
        for sy in wd.syllables:
            sy.attached = False
            sy.parent = None
            sy.vel = rand_vec(0.12)
            make_pulse(sy.pos, vector(1.0, 0.55, 0.28), "detach")
        wd.hide()
        make_pulse(pos, vector(1.0, 0.45, 0.20), "word broken")
        return
    free_sy = [sy for sy in syllables if not sy.attached]
    if free_sy:
        sy = random.choice(free_sy)
        syllables.remove(sy)
        for lt in sy.letters:
            lt.attached = False
            lt.parent = None
            lt.vel = rand_vec(0.12)
            make_pulse(lt.pos, vector(0.35, 0.6, 1.0), "letter freed")
        sy.hide()

# -----------------------------
# AI controller
# -----------------------------
class ExpressiveAIController:
    def __init__(self):
        self.modes = [
            "seed_letters",
            "gather_vowels",
            "build_syllables",
            "compose_words",
            "orbit_showcase",
            "semantic_sort",
            "ritual_spiral",
            "chaos_detach",
            "artistic_marking",
            "reset_round",
        ]
        self.mode_index = 0
        self.mode = self.modes[self.mode_index]
        self.timer = 0.0
        self.mode_duration = 5.0
        self.action_cooldown = 0.0
        self.last_signature = None
        self.stable_time = 0.0
        self.complete_time = 0.0
        self.loop_delay = 3.0
        self.playfulness = 0.45
        self.curiosity = 0.60
        self.constructive_bias = 0.72
        self.target_word = random.choice(WORD_TARGETS)
        self.focus_pos = rand_inside(WORLD_RADIUS * 0.35)

    def state(self):
        free_letters = len([lt for lt in letters if not lt.attached])
        free_syllables = len([sy for sy in syllables if not sy.attached])
        attached_letters = len([lt for lt in letters if lt.attached])
        signature = (
            free_letters,
            free_syllables,
            len(words),
            attached_letters,
            tuple(sorted([wd.text for wd in words])[:5]),
        )
        return {
            "free_letters": free_letters,
            "free_syllables": free_syllables,
            "words": len(words),
            "attached_letters": attached_letters,
            "signature": signature,
            "empty": free_letters + free_syllables + len(words) == 0,
            "complete": len(words) >= 4 or (len(words) >= 2 and free_letters < 3 and free_syllables < 1),
        }

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        self.mode = self.modes[self.mode_index]
        self.timer = 0.0
        self.action_cooldown = 0.0
        self.mode_duration = random.uniform(4.0, 8.0)
        self.focus_pos = rand_inside(WORLD_RADIUS * 0.45)
        if random.random() < 0.7:
            self.target_word = random.choice(WORD_TARGETS)
        make_pulse(self.focus_pos, vector(0.78, 0.42, 1.0), self.mode.replace("_", " "))

    def choose_mode_from_state(self, st):
        if st["empty"]:
            return "seed_letters"
        if st["complete"]:
            return "orbit_showcase"
        if st["free_letters"] < 6 and st["free_syllables"] < 2:
            return "seed_letters"
        if st["free_letters"] >= 6 and st["free_syllables"] < 4:
            return "build_syllables"
        if st["free_syllables"] >= 2:
            return "compose_words"
        return random.choice(["gather_vowels", "artistic_marking", "ritual_spiral"])

    def detect_stagnation(self, st, dt):
        if self.last_signature == st["signature"]:
            self.stable_time += dt
        else:
            self.stable_time = 0.0
            self.last_signature = st["signature"]
        if st["complete"]:
            self.complete_time += dt
        else:
            self.complete_time = 0.0
        return self.stable_time > 9.0 or self.complete_time > 7.0

    def update(self, dt):
        self.timer += dt
        self.action_cooldown -= dt
        st = self.state()
        stagnant = self.detect_stagnation(st, dt)
        if stagnant:
            self.mode = "reset_round"
            self.timer = 0.0
            self.action_cooldown = 0.0
        elif self.timer > self.mode_duration:
            next_mode = self.choose_mode_from_state(st)
            if next_mode == self.mode and random.random() < 0.6:
                self.cycle_mode()
            else:
                self.mode = next_mode
                self.timer = 0.0
                self.mode_duration = random.uniform(4.0, 8.0)
        if self.action_cooldown <= 0:
            self.perform_action(st)
            self.action_cooldown = random.uniform(0.45, 1.15)

    def perform_action(self, st):
        if self.mode == "seed_letters":
            if random.random() < 0.45:
                target = random.choice(WORD_TARGETS)
                spill_letters(count=len(target["word"]) + random.randint(3, 8), center=self.focus_pos, word_hint=target["word"])
            else:
                spill_letters(count=random.randint(8, 16), center=self.focus_pos)
        elif self.mode == "gather_vowels":
            self.pull_letters_by_type(vowels=True)
            if random.random() < 0.35:
                self.mark_focus("vowel well", vector(1.0, 0.55, 0.28))
        elif self.mode == "build_syllables":
            for _ in range(random.randint(1, 3)):
                pattern = random.choice(SYLLABLE_PATTERNS)
                build_syllable_from_letters(pattern=pattern, pos=self.focus_pos)
        elif self.mode == "compose_words":
            if random.random() < 0.35:
                build_target_word(random.choice(WORD_TARGETS), center=self.focus_pos + rand_vec(1.2))
            else:
                build_word_from_syllables()
        elif self.mode == "orbit_showcase":
            self.arrange_words_orbit()
            if random.random() < 0.3:
                self.mark_words()
        elif self.mode == "semantic_sort":
            self.semantic_sort_words()
        elif self.mode == "ritual_spiral":
            self.spiral_letters_and_syllables()
            if random.random() < 0.28 and st["free_letters"] > 3:
                build_syllable_from_letters(pattern=random.choice(SYLLABLE_PATTERNS), pos=vector(0, 0, 0))
        elif self.mode == "chaos_detach":
            if random.random() < 0.55:
                detach_cluster()
            else:
                self.scatter_all()
        elif self.mode == "artistic_marking":
            self.draw_constellation_links()
            self.mark_words()
        elif self.mode == "reset_round":
            if self.timer > self.loop_delay:
                reset_simulation(new_round=True)

    def pull_letters_by_type(self, vowels=True):
        target = self.focus_pos
        for lt in letters:
            if lt.attached:
                continue
            selected = (lt.ch in VOWELS) if vowels else (lt.ch not in VOWELS)
            if selected:
                direction = target - lt.pos
                lt.vel += safe_norm(direction) * 0.045
            else:
                lt.vel += safe_norm(lt.pos - target, rand_vec(1)) * 0.015

    def arrange_words_orbit(self):
        if not words:
            return
        n = len(words)
        for i, wd in enumerate(words):
            angle = 2 * math.pi * i / n + time.time() * 0.15
            target = vector(math.cos(angle) * 6.0, 1.5 * math.sin(angle * 2.0), math.sin(angle) * 6.0)
            wd.vel += (target - wd.pos) * 0.0018

    def semantic_sort_words(self):
        anchors = {
            "noun": vector(-5.8, 1.2, -4.5),
            "verb": vector(5.8, 1.2, -4.5),
            "adjective": vector(0, 1.2, 5.5),
            "unknown": vector(0, -1.5, 0),
        }
        for cat, pos in anchors.items():
            if random.random() < 0.04:
                lab = label(pos=pos + vector(0, 1.1, 0), text=cat, height=10, color=CATEGORIES.get(cat, CATEGORIES["unknown"]), box=False, opacity=0, line=False)
                particles.append({"obj": lab, "life": 1.5, "max_life": 1.5})
        for wd in words:
            target = anchors.get(wd.category, anchors["unknown"])
            wd.vel += (target - wd.pos) * 0.0025
            if random.random() < 0.12:
                make_trail_dot(wd.pos, wd.category_color, life=1.5, radius=0.05)

    def spiral_letters_and_syllables(self):
        t = time.time()
        for i, lt in enumerate([x for x in letters if not x.attached]):
            tangent = vector(-lt.pos.z, 0.4 * math.sin(t + i), lt.pos.x)
            lt.vel += safe_norm(tangent, rand_vec(1)) * 0.030
            lt.vel += safe_norm(vector(0, 0, 0) - lt.pos) * 0.010
        for i, sy in enumerate([x for x in syllables if not x.attached]):
            tangent = vector(-sy.pos.z, 0.25 * math.cos(t + i), sy.pos.x)
            sy.vel += safe_norm(tangent, rand_vec(1)) * 0.020

    def scatter_all(self):
        for lt in letters:
            if not lt.attached:
                lt.vel += rand_vec(0.11)
        for sy in syllables:
            if not sy.attached:
                sy.vel += rand_vec(0.08)
        for wd in words:
            wd.vel += rand_vec(0.05)
        make_pulse(vector(0, 0, 0), vector(1.0, 0.45, 0.20), "scatter")

    def mark_focus(self, text, col):
        marker = ring(pos=self.focus_pos, axis=vector(0, 1, 0), radius=1.25, thickness=0.035, color=col, opacity=0.45)
        marks.append(marker)
        lab = label(pos=self.focus_pos + vector(0, 1.45, 0), text=text, height=9, color=col, box=False, opacity=0, line=False)
        marks.append(lab)

    def mark_words(self):
        for wd in words:
            if random.random() < 0.35:
                make_pulse(wd.pos, wd.category_color, wd.category)

    def draw_constellation_links(self):
        all_nodes = [lt for lt in letters if not lt.attached] + [sy for sy in syllables if not sy.attached] + words
        if len(all_nodes) < 2:
            return
        a = random.choice(all_nodes)
        b = min([x for x in all_nodes if x is not a], key=lambda x: mag(x.pos - a.pos))
        link = cylinder(pos=a.pos, axis=b.pos - a.pos, radius=0.018, color=vector(0.55, 0.45, 0.85), opacity=0.28)
        links.append(link)
        particles.append({"obj": link, "life": 2.4, "max_life": 2.4})

AI = ExpressiveAIController()

# -----------------------------
# Simulation update functions
# -----------------------------
def auto_attach_collisions():
    # Letters attach into syllables when compatible free letters cluster.
    free_letters = [lt for lt in letters if not lt.attached]
    random.shuffle(free_letters)
    used = set()
    for lt in free_letters:
        if lt in used:
            continue
        close = [other for other in free_letters if other not in used and other is not lt and mag(other.pos - lt.pos) < 1.0]
        if close and random.random() < 0.018:
            group = [lt] + close[: random.choice([1, 2])]
            # Prefer at least one vowel in a syllable.
            if any(x.ch in VOWELS for x in group):
                for x in group:
                    used.add(x)
                build_syllable_from_letters(group)
    # Syllables attach into words when close together.
    free_sy = [sy for sy in syllables if not sy.attached]
    random.shuffle(free_sy)
    used_sy = set()
    for sy in free_sy:
        if sy in used_sy:
            continue
        close = [other for other in free_sy if other not in used_sy and other is not sy and mag(other.pos - sy.pos) < 2.1]
        if close and random.random() < 0.012:
            group = [sy] + close[: random.choice([1, 2])]
            for x in group:
                used_sy.add(x)
            build_word_from_syllables(group)


def update_particles(dt):
    expired = []
    for p in particles:
        obj = p.get("obj")
        p["life"] -= dt
        if obj is None:
            expired.append(p)
            continue
        if p.get("float") is not None and hasattr(obj, "pos"):
            obj.pos = obj.pos + p["float"] * dt * 60
        if p.get("grow") is not None and hasattr(obj, "radius"):
            obj.radius += p["grow"] * dt * 60
        if p.get("shrink") and hasattr(obj, "radius"):
            obj.radius = max(0.005, obj.radius * (1 - 0.025 * dt * 60))
        if hasattr(obj, "opacity"):
            obj.opacity = max(0, min(1, obj.opacity * 0.985))
        if p["life"] <= 0:
            remove_visual(obj)
            expired.append(p)
    for p in expired:
        if p in particles:
            particles.remove(p)


def update_links_positions():
    # Temporary cylinder links are allowed to fade without following nodes.
    pass


def update_all(dt):
    for lt in letters:
        lt.update_free(dt)
    for sy in syllables:
        sy.update_free(dt)
    for wd in words:
        wd.update(dt)
    auto_attach_collisions()
    update_particles(dt)
    update_status()


def update_status():
    free_letters = len([lt for lt in letters if not lt.attached])
    free_syllables = len([sy for sy in syllables if not sy.attached])
    status.text = (
        f"Round {ROUND_NUMBER} | Letters {free_letters}/{len(letters)} | "
        f"Syllables {free_syllables}/{len(syllables)} | Words {len(words)} | "
        f"AI {'ON' if AI_ENABLED else 'OFF'} | {'PAUSED' if PAUSED else 'running'} | speed {SIM_SPEED:.1f}x"
    )
    mode_label.text = f"AI mode: {AI.mode}\ntarget: {AI.target_word['word']}\nbounce: {'on' if BOUNCE_WALLS else 'off'}"


def print_controls():
    print(__doc__)


def wipe_entities():
    for lt in letters:
        lt.hide()
    for sy in syllables:
        sy.hide()
    for wd in words:
        wd.hide()
    letters.clear()
    syllables.clear()
    words.clear()
    clear_temp()


def reset_simulation(new_round=False):
    global ROUND_NUMBER, NEXT_ID
    if new_round:
        ROUND_NUMBER += 1
    wipe_entities()
    AI.stable_time = 0
    AI.complete_time = 0
    AI.timer = 0
    AI.action_cooldown = 0
    AI.mode = "seed_letters"
    AI.mode_index = AI.modes.index("seed_letters")
    AI.target_word = random.choice(WORD_TARGETS)
    AI.focus_pos = rand_inside(WORLD_RADIUS * 0.35)
    # Start each round with a mix of random letters and one hidden target word supply.
    spill_letters(count=22, center=vector(-2, 0.5, 0))
    spill_letters(count=len(AI.target_word["word"]) + 4, center=vector(2.5, 0.5, 0), word_hint=AI.target_word["word"])
    make_pulse(vector(0, 0, 0), vector(0.55, 0.72, 1.0), "new round")

# -----------------------------
# Keyboard controls
# -----------------------------
def keydown(evt):
    global PAUSED, AI_ENABLED, SIM_SPEED, BOUNCE_WALLS
    k = evt.key.lower()
    if k == "a":
        AI_ENABLED = not AI_ENABLED
        make_pulse(vector(0, 2.4, 0), vector(0.6, 0.45, 1.0), "AI on" if AI_ENABLED else "AI off")
    elif k == "p":
        PAUSED = not PAUSED
    elif k == "r":
        reset_simulation(new_round=True)
    elif k == "m":
        AI.cycle_mode()
    elif k == "l":
        spill_letters(count=18, center=rand_inside(WORLD_RADIUS * 0.5))
    elif k == "s":
        build_syllable_from_letters(pattern=random.choice(SYLLABLE_PATTERNS), pos=vector(0, 0, 0))
    elif k == "w":
        if len([sy for sy in syllables if not sy.attached]) >= 1:
            build_word_from_syllables()
        else:
            build_target_word(random.choice(WORD_TARGETS), center=rand_inside(WORLD_RADIUS * 0.4))
    elif k == "d":
        detach_cluster()
    elif k == "c":
        clear_temp()
    elif k == "b":
        BOUNCE_WALLS = not BOUNCE_WALLS
    elif k in ["+", "="]:
        SIM_SPEED = min(4.0, SIM_SPEED + 0.2)
    elif k in ["-", "_"]:
        SIM_SPEED = max(0.2, SIM_SPEED - 0.2)
    elif k == "h":
        print_controls()

scene.bind("keydown", keydown)

# -----------------------------
# Initialize and run
# -----------------------------
reset_simulation(new_round=False)
print_controls()

last_time = time.time()
while True:
    rate(60)
    now = time.time()
    raw_dt = max(0.001, min(0.05, now - last_time))
    last_time = now
    if PAUSED:
        update_status()
        continue
    dt = raw_dt * SIM_SPEED
    if AI_ENABLED:
        AI.update(dt)
    update_all(dt)
