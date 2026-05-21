"""
Genome-to-Trait Expression System
3D VPython simulation with an expressive rule-based AI controller.

Run:
    pip install vpython
    python genome_to_trait_expression_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset simulation
    M       cycle AI behavior mode
    E       pulse eye-color gene region
    H       pulse height gene region
    B       pulse blood-type gene region
    G       add gene expression burst
    T       add trait marker pulse
    C       clear temporary particles/signals
    + / =   increase simulation speed
    - / _   decrease simulation speed
    ?       print controls

Scene:
    A transparent nucleus contains a stylized chromosome/DNA genome. Gene regions
    brighten or dim, release RNA signals, send protein particles outward, and influence
    visible trait panels for eye color, height, and blood type. An expressive AI controller
    reads the state and switches between careful, curious, chaotic, constructive, artistic,
    ritual-like, and reset modes to create changing rounds of gene-to-trait expression.

Notes:
    This is an educational symbolic simulation, not a biological model of inheritance
    or phenotype prediction. Real traits are often polygenic and environmentally influenced.
"""

from vpython import *
import random
import math
from dataclasses import dataclass, field

# ----------------------------- Scene setup -----------------------------

scene = canvas(
    title="Genome-to-Trait Expression System — VPython AI Simulation",
    width=1250,
    height=760,
    background=vector(0.96, 0.98, 1.0),
    center=vector(0, 0, 0),
    range=13,
)
scene.forward = vector(-0.35, -0.25, -1)
scene.up = vector(0, 1, 0)
scene.userzoom = True
scene.userspin = True

WORLD_RADIUS = 10.5
NUCLEUS_RADIUS = 3.2
DT_BASE = 0.012

soft_blue = vector(0.42, 0.67, 1.0)
soft_purple = vector(0.65, 0.48, 0.95)
soft_green = vector(0.35, 0.80, 0.48)
soft_red = vector(1.0, 0.38, 0.34)
soft_gold = vector(1.0, 0.78, 0.28)
soft_teal = vector(0.15, 0.75, 0.78)
soft_brown = vector(0.48, 0.26, 0.12)
soft_gray = vector(0.55, 0.58, 0.63)
soft_pink = vector(1.0, 0.48, 0.75)


# ----------------------------- Helpers -----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def rand_vec(scale=1.0):
    return vector(
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
    )


def safe_norm(v):
    magv = mag(v)
    if magv < 1e-8:
        return vector(0, 0, 0)
    return v / magv


def mix_color(a, b, t):
    t = clamp(t, 0, 1)
    return a * (1 - t) + b * t


def spiral_point(i, n, radius=2.1, height=5.0, twist=5.6):
    f = i / max(1, n - 1)
    ang = twist * math.pi * f
    r = radius * (0.72 + 0.18 * math.sin(ang * 2.0))
    return vector(r * math.cos(ang), height * (f - 0.5), r * math.sin(ang))


def remove_obj(obj):
    try:
        obj.visible = False
        obj.delete()
    except Exception:
        try:
            obj.visible = False
        except Exception:
            pass


def print_controls():
    print(__doc__)


# ----------------------------- Data models -----------------------------

@dataclass
class GeneRegion:
    name: str
    trait: str
    index: int
    color_dim: vector
    color_active: vector
    expression: float = 0.20
    target_expression: float = 0.20
    cooldown: float = 0.0
    body: object = None
    aura: object = None
    label_obj: object = None
    history: list = field(default_factory=list)


@dataclass
class Signal:
    kind: str
    trait: str
    body: object
    vel: vector
    age: float = 0.0
    life: float = 5.0
    target: vector = field(default_factory=lambda: vector(0, 0, 0))
    attached: bool = False
    trail: object = None


@dataclass
class TraitPanel:
    name: str
    position: vector
    base_color: vector
    current_value: float = 0.25
    target_value: float = 0.25
    panel: object = None
    marker: object = None
    label_obj: object = None
    extra: list = field(default_factory=list)


# ----------------------------- Global state -----------------------------

objects_to_clear = []
chromosome_segments = []
gene_regions = []
signals = []
trait_panels = {}
trait_link_lines = []
temporary_marks = []

running = True
ai_enabled = True
sim_speed = 1.0
time_elapsed = 0.0
round_number = 1
last_summary_value = 0.0
stable_timer = 0.0
completion_timer = 0.0
selected_trait = "eye"


class ExpressiveAI:
    def __init__(self):
        self.modes = [
            "curious_scan",
            "construct_eye_trait",
            "grow_height_trait",
            "balance_blood_trait",
            "chaotic_mutation",
            "ritual_sequence",
            "artistic_trails",
            "careful_repair",
            "completion_reset",
        ]
        self.mode_index = 0
        self.mode = self.modes[self.mode_index]
        self.mode_timer = 0.0
        self.action_timer = 0.0
        self.repetition_guard = {}
        self.last_state_score = 0.0
        self.stagnation_timer = 0.0
        self.complete_timer = 0.0
        self.round_pause = 0.0
        self.focus_trait = "eye"
        self.orbit_angle = 0.0
        self.ritual_step = 0
        self.message = ""

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        self.mode = self.modes[self.mode_index]
        self.mode_timer = 0.0
        self.action_timer = 0.0
        self.message = "AI mode: " + self.mode

    def choose_mode_from_state(self, state):
        if state["complete"]:
            self.mode = "completion_reset"
            return
        if state["stagnant"]:
            self.mode = random.choice(["chaotic_mutation", "ritual_sequence", "artistic_trails"])
            return
        if state["signal_count"] < 5:
            self.mode = random.choice(["curious_scan", "construct_eye_trait", "grow_height_trait"])
            return
        if state["average_expression"] > 0.78:
            self.mode = random.choice(["careful_repair", "artistic_trails", "balance_blood_trait"])
            return
        if self.mode_timer > random.uniform(5.5, 9.5):
            self.mode = random.choice(self.modes[:-1])
            self.mode_timer = 0.0
            self.action_timer = 0.0

    def read_state(self):
        avg_expr = sum(g.expression for g in gene_regions) / max(1, len(gene_regions))
        trait_avg = sum(p.current_value for p in trait_panels.values()) / max(1, len(trait_panels))
        active_genes = sum(1 for g in gene_regions if g.expression > 0.55)
        signal_count = len(signals)
        score = avg_expr * 1.4 + trait_avg + active_genes * 0.05 + signal_count * 0.01
        changed = abs(score - self.last_state_score)
        if changed < 0.015:
            self.stagnation_timer += DT_BASE * sim_speed
        else:
            self.stagnation_timer = max(0, self.stagnation_timer - 0.05)
        self.last_state_score = score
        complete = trait_avg > 0.82 and avg_expr > 0.62
        if complete:
            self.complete_timer += DT_BASE * sim_speed
        else:
            self.complete_timer = 0.0
        return {
            "average_expression": avg_expr,
            "trait_average": trait_avg,
            "active_genes": active_genes,
            "signal_count": signal_count,
            "score": score,
            "stagnant": self.stagnation_timer > 4.0,
            "complete": self.complete_timer > 2.7,
        }

    def act(self, dt):
        self.mode_timer += dt
        self.action_timer += dt
        state = self.read_state()
        self.choose_mode_from_state(state)

        if self.mode == "curious_scan":
            self.curious_scan(dt, state)
        elif self.mode == "construct_eye_trait":
            self.construct_trait(dt, "eye", state)
        elif self.mode == "grow_height_trait":
            self.construct_trait(dt, "height", state)
        elif self.mode == "balance_blood_trait":
            self.construct_trait(dt, "blood", state)
        elif self.mode == "chaotic_mutation":
            self.chaotic_mutation(dt, state)
        elif self.mode == "ritual_sequence":
            self.ritual_sequence(dt, state)
        elif self.mode == "artistic_trails":
            self.artistic_trails(dt, state)
        elif self.mode == "careful_repair":
            self.careful_repair(dt, state)
        elif self.mode == "completion_reset":
            self.completion_reset(dt, state)

    def curious_scan(self, dt, state):
        self.orbit_angle += dt * 1.2
        focus = min(gene_regions, key=lambda g: g.expression)
        self.focus_trait = focus.trait
        pulse_gene(focus, amount=0.018)
        if self.action_timer > 1.15:
            spawn_mark(focus.body.pos, focus.color_active, "scan")
            launch_signal(focus, "rna")
            self.action_timer = 0.0
        self.message = "AI curious scan: waking dim gene regions"

    def construct_trait(self, dt, trait, state):
        candidates = [g for g in gene_regions if g.trait == trait]
        for g in candidates:
            pulse_gene(g, amount=0.018 + random.random() * 0.009)
        if self.action_timer > 0.8:
            g = random.choice(candidates)
            launch_signal(g, random.choice(["rna", "protein"]))
            spawn_mark(g.body.pos, g.color_active, trait)
            self.action_timer = 0.0
        self.focus_trait = trait
        self.message = "AI constructive mode: building " + trait + " trait signal"

    def chaotic_mutation(self, dt, state):
        if self.action_timer > 0.33:
            g = random.choice(gene_regions)
            delta = random.uniform(-0.22, 0.34)
            g.target_expression = clamp(g.target_expression + delta, 0.03, 1.0)
            spawn_mark(g.body.pos + rand_vec(0.35), vector(1, 0.55, 0.2), "spark")
            if random.random() < 0.7:
                launch_signal(g, random.choice(["rna", "protein", "repair"]))
            self.action_timer = 0.0
        jitter_chromosome(0.018)
        self.message = "AI chaotic mutation: pulsing random expression changes"

    def ritual_sequence(self, dt, state):
        if self.action_timer > 0.7:
            sequence = ["eye", "height", "blood", "height", "eye", "blood"]
            trait = sequence[self.ritual_step % len(sequence)]
            candidates = [g for g in gene_regions if g.trait == trait]
            g = candidates[self.ritual_step % len(candidates)]
            pulse_gene(g, amount=0.16)
            launch_signal(g, "rna")
            spawn_orbit_ring(g.body.pos, g.color_active)
            self.ritual_step += 1
            self.action_timer = 0.0
        self.message = "AI ritual sequence: repeating a gene activation pattern"

    def artistic_trails(self, dt, state):
        if self.action_timer > 0.45:
            g = random.choice(gene_regions)
            pulse_gene(g, amount=0.08)
            sig = launch_signal(g, random.choice(["rna", "protein"]))
            if sig:
                sig.body.make_trail = True
                sig.body.trail_radius = 0.025
                sig.body.retain = 65
            self.action_timer = 0.0
        for panel in trait_panels.values():
            panel.marker.rotate(angle=dt * 0.6, axis=vector(0, 1, 0))
        self.message = "AI artistic trails: drawing expression paths"

    def careful_repair(self, dt, state):
        high_genes = [g for g in gene_regions if g.expression > 0.78]
        for g in high_genes:
            g.target_expression = max(0.48, g.target_expression - 0.012)
            if random.random() < 0.05:
                launch_signal(g, "repair")
        if self.action_timer > 1.4:
            low = min(gene_regions, key=lambda g: g.expression)
            low.target_expression = min(0.58, low.target_expression + 0.12)
            spawn_mark(low.body.pos, vector(0.35, 0.85, 1.0), "repair")
            self.action_timer = 0.0
        self.message = "AI careful repair: balancing overactive genes"

    def completion_reset(self, dt, state):
        self.message = "AI completion: starting a new expression round"
        if self.action_timer > 1.2:
            reset_simulation(new_round=True)
            self.mode = "curious_scan"
            self.mode_timer = 0.0
            self.action_timer = 0.0


ai = ExpressiveAI()


# ----------------------------- Build scene -----------------------------

def make_static_scene():
    global nucleus, cell_boundary, status_label, ai_label, legend_label

    cell_boundary = sphere(
        pos=vector(0, 0, 0),
        radius=WORLD_RADIUS,
        color=vector(0.72, 0.88, 1.0),
        opacity=0.075,
        shininess=0.2,
    )

    nucleus = sphere(
        pos=vector(0, 0, 0),
        radius=NUCLEUS_RADIUS,
        color=vector(0.68, 0.78, 1.0),
        opacity=0.16,
        shininess=0.4,
    )

    # Nucleus rim rings using VPython ring.
    for axis, col in [
        (vector(1, 0, 0), vector(0.56, 0.72, 1.0)),
        (vector(0, 1, 0), vector(0.56, 0.72, 1.0)),
        (vector(0, 0, 1), vector(0.56, 0.72, 1.0)),
    ]:
        objects_to_clear.append(
            ring(pos=vector(0, 0, 0), axis=axis, radius=NUCLEUS_RADIUS, thickness=0.018, color=col, opacity=0.35)
        )

    label(pos=vector(0, NUCLEUS_RADIUS + 0.7, 0), text="transparent nucleus", height=13, box=False, color=vector(0.20, 0.28, 0.45))

    status_label = label(
        pos=vector(-8.8, 8.9, 0),
        text="starting simulation",
        height=13,
        box=True,
        border=8,
        color=vector(0.1, 0.15, 0.25),
        background=vector(0.93, 0.96, 1.0),
        opacity=0.55,
    )

    ai_label = label(
        pos=vector(5.1, 8.9, 0),
        text="AI enabled",
        height=13,
        box=True,
        border=8,
        color=vector(0.1, 0.15, 0.25),
        background=vector(0.95, 1.0, 0.93),
        opacity=0.55,
    )

    legend_label = label(
        pos=vector(0, -8.9, 0),
        text="A AI | P pause | R reset | M mode | E/H/B pulse traits | G burst | T trait pulse | C clear | ? controls",
        height=12,
        box=False,
        color=vector(0.18, 0.23, 0.33),
    )


def build_chromosome():
    global chromosome_curve
    chromosome_segments.clear()
    gene_regions.clear()

    n = 160
    pts_a = []
    pts_b = []
    for i in range(n):
        p = spiral_point(i, n, radius=1.25, height=5.3, twist=6.2)
        radial = safe_norm(vector(p.x, 0, p.z))
        if mag(radial) < 0.1:
            radial = vector(1, 0, 0)
        pts_a.append(p + radial * 0.13)
        pts_b.append(p - radial * 0.13)

    for pts, col in [(pts_a, soft_purple), (pts_b, soft_blue)]:
        chromosome_segments.append(curve(pos=pts, radius=0.035, color=col, opacity=0.75))

    # ladder rungs
    for i in range(0, n, 5):
        chromosome_segments.append(curve(pos=[pts_a[i], pts_b[i]], radius=0.016, color=vector(0.82, 0.84, 0.92), opacity=0.62))

    gene_specs = [
        ("OCA2/HERC2", "eye", 20, vector(0.25, 0.35, 0.62), vector(0.34, 0.62, 1.0)),
        ("MC1R-like", "eye", 42, vector(0.48, 0.28, 0.18), vector(0.75, 0.38, 0.18)),
        ("IGF1-like", "height", 70, vector(0.32, 0.55, 0.28), vector(0.42, 0.95, 0.48)),
        ("FGFR-like", "height", 94, vector(0.38, 0.48, 0.32), vector(0.72, 1.0, 0.38)),
        ("ABO", "blood", 118, vector(0.55, 0.22, 0.24), vector(1.0, 0.38, 0.36)),
        ("RHD-like", "blood", 140, vector(0.55, 0.37, 0.18), vector(1.0, 0.72, 0.25)),
    ]

    for name, trait, idx, dim, active in gene_specs:
        base = pts_a[idx]
        body = sphere(
            pos=base,
            radius=0.18,
            color=dim,
            emissive=False,
            opacity=0.88,
            shininess=0.6,
        )
        aura = sphere(
            pos=base,
            radius=0.30,
            color=active,
            opacity=0.12,
            shininess=0.1,
        )
        label_obj = label(
            pos=base + vector(0.34, 0.24, 0),
            text=name + "\n" + trait,
            height=9,
            box=False,
            color=vector(0.15, 0.18, 0.25),
        )
        g = GeneRegion(name=name, trait=trait, index=idx, color_dim=dim, color_active=active, body=body, aura=aura, label_obj=label_obj)
        gene_regions.append(g)


def make_trait_panels():
    trait_panels.clear()

    specs = [
        ("eye", vector(-7.8, 2.9, 0), soft_brown, "Eye color\nbrown/blue marker"),
        ("height", vector(-7.8, 0.0, 0), soft_green, "Height marker\ngrowth scale"),
        ("blood", vector(-7.8, -2.9, 0), soft_red, "Blood type\nABO/Rh marker"),
    ]

    for name, pos, color_base, title in specs:
        panel = box(pos=pos, size=vector(1.8, 1.2, 0.12), color=vector(0.90, 0.94, 1.0), opacity=0.68)
        marker = sphere(pos=pos + vector(0, 0, 0.42), radius=0.34, color=color_base, opacity=0.88, shininess=0.45)
        label_obj = label(pos=pos + vector(0, 0.95, 0), text=title, height=11, box=False, color=vector(0.14, 0.17, 0.24))
        tp = TraitPanel(name=name, position=pos, base_color=color_base, panel=panel, marker=marker, label_obj=label_obj)
        trait_panels[name] = tp

    # Height meter
    height_panel = trait_panels["height"]
    for k in range(5):
        y = height_panel.position.y - 0.45 + k * 0.23
        bar = box(pos=height_panel.position + vector(0.68, y - height_panel.position.y, 0.45), size=vector(0.18, 0.04, 0.04), color=soft_green, opacity=0.35)
        height_panel.extra.append(bar)

    # Blood marker plates
    blood_panel = trait_panels["blood"]
    for k, txt in enumerate(["A", "B", "O", "Rh"]):
        x = -0.57 + k * 0.38
        plate = box(pos=blood_panel.position + vector(x, -0.36, 0.42), size=vector(0.24, 0.15, 0.04), color=soft_red, opacity=0.25)
        t = label(pos=plate.pos + vector(0, -0.23, 0), text=txt, height=7, box=False, color=vector(0.25, 0.1, 0.1))
        blood_panel.extra.extend([plate, t])


def make_links():
    trait_link_lines.clear()
    for trait, panel in trait_panels.items():
        for g in gene_regions:
            if g.trait == trait:
                line = curve(pos=[g.body.pos, panel.position], radius=0.008, color=g.color_active, opacity=0.12)
                trait_link_lines.append((line, g, panel))


def reset_simulation(new_round=False):
    global time_elapsed, round_number, stable_timer, completion_timer, selected_trait

    for sig in signals:
        remove_obj(sig.body)
        if sig.trail:
            remove_obj(sig.trail)
    signals.clear()

    for obj in temporary_marks:
        remove_obj(obj)
    temporary_marks.clear()

    for g in gene_regions:
        g.expression = random.uniform(0.12, 0.38)
        g.target_expression = g.expression
        g.cooldown = 0.0
        g.history.clear()

    for p in trait_panels.values():
        p.current_value = random.uniform(0.12, 0.30)
        p.target_value = p.current_value

    time_elapsed = 0.0
    stable_timer = 0.0
    completion_timer = 0.0
    selected_trait = "eye"
    if new_round:
        round_number += 1
    else:
        round_number = 1
    ai.stagnation_timer = 0.0
    ai.complete_timer = 0.0


def build_scene():
    make_static_scene()
    build_chromosome()
    make_trait_panels()
    make_links()
    reset_simulation(new_round=False)


# ----------------------------- Interactions -----------------------------

def pulse_gene(gene_or_trait, amount=0.20):
    if isinstance(gene_or_trait, str):
        targets = [g for g in gene_regions if g.trait == gene_or_trait]
    else:
        targets = [gene_or_trait]
    for g in targets:
        g.target_expression = clamp(g.target_expression + amount, 0.02, 1.0)
        g.cooldown = 0.6


def dim_gene(gene_or_trait, amount=0.15):
    if isinstance(gene_or_trait, str):
        targets = [g for g in gene_regions if g.trait == gene_or_trait]
    else:
        targets = [gene_or_trait]
    for g in targets:
        g.target_expression = clamp(g.target_expression - amount, 0.02, 1.0)


def launch_signal(gene, kind="rna"):
    if len(signals) > 110:
        old = signals.pop(0)
        remove_obj(old.body)

    trait_target = trait_panels[gene.trait].position + vector(0, 0, 0.25)
    start = gene.body.pos + rand_vec(0.12)

    if kind == "rna":
        col = vector(0.28, 0.72, 1.0)
        radius = 0.065
        life = 4.5
    elif kind == "protein":
        col = gene.color_active
        radius = 0.085
        life = 6.2
    else:
        col = vector(0.55, 0.95, 1.0)
        radius = 0.055
        life = 3.5

    b = sphere(pos=start, radius=radius, color=col, opacity=0.92, emissive=True, make_trail=True, retain=35, trail_radius=0.012)
    vel = safe_norm(trait_target - start) * random.uniform(0.55, 0.95) + rand_vec(0.12)
    sig = Signal(kind=kind, trait=gene.trait, body=b, vel=vel, life=life, target=trait_target)
    signals.append(sig)
    return sig


def gene_expression_burst():
    for g in gene_regions:
        if random.random() < 0.65:
            pulse_gene(g, amount=random.uniform(0.10, 0.28))
            launch_signal(g, random.choice(["rna", "protein"]))


def trait_marker_pulse():
    for p in trait_panels.values():
        p.target_value = clamp(p.target_value + random.uniform(0.06, 0.18), 0.0, 1.0)
        spawn_mark(p.position + vector(0, 0, 0.6), p.base_color, p.name)


def clear_temporary():
    for obj in temporary_marks:
        remove_obj(obj)
    temporary_marks.clear()
    while len(signals) > 30:
        old = signals.pop(0)
        remove_obj(old.body)


def spawn_mark(pos, col, text=""):
    s = sphere(pos=pos, radius=0.055 + random.random() * 0.08, color=col, opacity=0.65, emissive=True)
    s.velocity = rand_vec(0.35)
    s.age = 0.0
    s.life = random.uniform(1.5, 3.2)
    temporary_marks.append(s)
    if text and random.random() < 0.25:
        lab = label(pos=pos + vector(0, 0.28, 0), text=text, height=7, box=False, color=col)
        lab.age = 0.0
        lab.life = 1.4
        lab.velocity = vector(0, 0.04, 0)
        temporary_marks.append(lab)
    return s


def spawn_orbit_ring(pos, col):
    r = ring(pos=pos, axis=vector(0, 1, 0), radius=0.34, thickness=0.012, color=col, opacity=0.65)
    r.age = 0.0
    r.life = 1.8
    r.velocity = vector(0, 0, 0)
    temporary_marks.append(r)
    return r


def jitter_chromosome(amount):
    for g in gene_regions:
        g.body.pos += rand_vec(amount)
        g.aura.pos = g.body.pos
        g.label_obj.pos = g.body.pos + vector(0.34, 0.24, 0)


def update_genes(dt):
    for g in gene_regions:
        # Natural dimming plus smoothing toward target.
        g.target_expression = clamp(g.target_expression - dt * 0.026, 0.05, 1.0)
        g.expression += (g.target_expression - g.expression) * clamp(dt * 3.2, 0, 1)
        g.cooldown = max(0.0, g.cooldown - dt)

        pulse = 0.06 * math.sin(time_elapsed * 4.0 + g.index * 0.13)
        glow = clamp(g.expression + pulse, 0, 1)
        g.body.color = mix_color(g.color_dim, g.color_active, glow)
        g.body.radius = 0.16 + 0.16 * glow
        g.body.emissive = glow > 0.55
        g.aura.pos = g.body.pos
        g.aura.radius = 0.26 + 0.55 * glow
        g.aura.opacity = 0.05 + 0.26 * glow
        g.label_obj.pos = g.body.pos + vector(0.34, 0.24, 0)
        g.history.append(g.expression)
        if len(g.history) > 40:
            g.history.pop(0)

        # Active regions periodically transcribe RNA.
        if g.expression > 0.62 and random.random() < dt * (0.45 + g.expression):
            launch_signal(g, "rna")
        if g.expression > 0.78 and random.random() < dt * 0.35:
            launch_signal(g, "protein")


def update_signals(dt):
    for sig in signals[:]:
        sig.age += dt
        to_target = sig.target - sig.body.pos
        dist = mag(to_target)

        # Signals leave the nucleus, then home to the trait panel.
        attraction = safe_norm(to_target) * (0.25 + 0.52 * min(1, sig.age / sig.life))
        swirl = vector(
            math.sin(time_elapsed * 2.0 + sig.body.pos.y),
            math.cos(time_elapsed * 1.7 + sig.body.pos.x),
            math.sin(time_elapsed * 2.4 + sig.body.pos.z),
        ) * 0.035

        sig.vel += (attraction + swirl) * dt
        sig.vel *= 0.995
        if mag(sig.vel) > 1.8:
            sig.vel = safe_norm(sig.vel) * 1.8
        sig.body.pos += sig.vel * dt

        # Collide/attach with trait panel marker.
        if dist < 0.62:
            panel = trait_panels[sig.trait]
            if sig.kind == "repair":
                panel.target_value = clamp(panel.target_value - 0.035, 0.0, 1.0)
            elif sig.kind == "rna":
                panel.target_value = clamp(panel.target_value + 0.025, 0.0, 1.0)
            else:
                panel.target_value = clamp(panel.target_value + 0.045, 0.0, 1.0)
            spawn_mark(panel.position + vector(random.uniform(-0.35, 0.35), random.uniform(-0.25, 0.25), 0.55), panel.base_color, "")
            remove_obj(sig.body)
            signals.remove(sig)
            continue

        if sig.age > sig.life:
            remove_obj(sig.body)
            signals.remove(sig)


def update_traits(dt):
    # Gene expression influences each trait target.
    for trait, panel in trait_panels.items():
        related = [g.expression for g in gene_regions if g.trait == trait]
        gene_influence = sum(related) / max(1, len(related))
        panel.target_value = clamp(panel.target_value * 0.996 + gene_influence * 0.004, 0, 1)
        panel.current_value += (panel.target_value - panel.current_value) * clamp(dt * 2.0, 0, 1)

        val = panel.current_value
        panel.marker.radius = 0.23 + 0.42 * val
        panel.marker.opacity = 0.52 + 0.42 * val
        panel.marker.emissive = val > 0.68

        if trait == "eye":
            blue = vector(0.28, 0.50, 1.0)
            brown = vector(0.42, 0.22, 0.10)
            panel.marker.color = mix_color(blue, brown, clamp(val, 0, 1))
            panel.label_obj.text = "Eye color\nsignal: %.2f" % val
        elif trait == "height":
            panel.marker.color = mix_color(vector(0.72, 0.95, 0.62), vector(0.10, 0.72, 0.22), val)
            panel.marker.pos.y = panel.position.y + val * 0.55
            panel.label_obj.text = "Height marker\nsignal: %.2f" % val
            for idx, item in enumerate(panel.extra):
                item.opacity = 0.18 + (0.62 if val > idx / max(1, len(panel.extra)) else 0.04)
        elif trait == "blood":
            panel.marker.color = mix_color(vector(1.0, 0.65, 0.52), vector(0.75, 0.02, 0.08), val)
            panel.label_obj.text = "Blood type\nsignal: %.2f" % val
            for idx, item in enumerate(panel.extra):
                if hasattr(item, "opacity"):
                    item.opacity = 0.12 + 0.52 * clamp(val - idx * 0.14, 0, 1)

        panel.panel.color = mix_color(vector(0.90, 0.94, 1.0), panel.base_color, 0.16 + val * 0.24)
        panel.panel.opacity = 0.50 + val * 0.26


def update_links(dt):
    for line, g, panel in trait_link_lines:
        line.clear()
        line.append(g.body.pos)
        line.append(panel.position)
        line.color = g.color_active
        line.opacity = 0.06 + 0.26 * g.expression


def update_temporary(dt):
    for obj in temporary_marks[:]:
        if not hasattr(obj, "age"):
            continue
        obj.age += dt
        if hasattr(obj, "velocity"):
            obj.pos += obj.velocity * dt
        if isinstance(obj, ring):
            obj.radius += dt * 0.18
            obj.rotate(angle=dt * 1.5, axis=vector(0, 1, 0))
        try:
            obj.opacity = max(0.0, obj.opacity * (1 - dt * 0.55))
        except Exception:
            pass
        if obj.age > obj.life:
            remove_obj(obj)
            temporary_marks.remove(obj)


def detect_global_stability(dt):
    global last_summary_value, stable_timer, completion_timer

    avg_expr = sum(g.expression for g in gene_regions) / len(gene_regions)
    trait_avg = sum(p.current_value for p in trait_panels.values()) / len(trait_panels)
    score = avg_expr + trait_avg + len(signals) * 0.006
    if abs(score - last_summary_value) < 0.01:
        stable_timer += dt
    else:
        stable_timer = max(0.0, stable_timer - dt * 0.5)
    last_summary_value = score

    complete = trait_avg > 0.84 and avg_expr > 0.58
    if complete:
        completion_timer += dt
    else:
        completion_timer = max(0.0, completion_timer - dt)

    if stable_timer > 12.0 or completion_timer > 6.0 or len(signals) == 0 and time_elapsed > 16.0:
        reset_simulation(new_round=True)


def update_labels():
    avg_expr = sum(g.expression for g in gene_regions) / max(1, len(gene_regions))
    trait_avg = sum(p.current_value for p in trait_panels.values()) / max(1, len(trait_panels))
    status_label.text = (
        "round %d | time %.1f | speed %.1fx | paused %s\n"
        "genes %.2f | traits %.2f | signals %d | stable %.1f"
        % (round_number, time_elapsed, sim_speed, str(not running), avg_expr, trait_avg, len(signals), stable_timer)
    )
    ai_label.text = (
        "AI %s | mode: %s\n%s"
        % ("ON" if ai_enabled else "OFF", ai.mode, ai.message)
    )


# ----------------------------- Keyboard controls -----------------------------

def on_keydown(evt):
    global running, ai_enabled, sim_speed, selected_trait
    key = evt.key.lower()

    if key == "a":
        ai_enabled = not ai_enabled
    elif key == "p":
        running = not running
    elif key == "r":
        reset_simulation(new_round=True)
    elif key == "m":
        ai.cycle_mode()
    elif key == "e":
        selected_trait = "eye"
        pulse_gene("eye", 0.35)
        for g in [x for x in gene_regions if x.trait == "eye"]:
            launch_signal(g, "rna")
    elif key == "h":
        selected_trait = "height"
        pulse_gene("height", 0.35)
        for g in [x for x in gene_regions if x.trait == "height"]:
            launch_signal(g, "rna")
    elif key == "b":
        selected_trait = "blood"
        pulse_gene("blood", 0.35)
        for g in [x for x in gene_regions if x.trait == "blood"]:
            launch_signal(g, "rna")
    elif key == "g":
        gene_expression_burst()
    elif key == "t":
        trait_marker_pulse()
    elif key == "c":
        clear_temporary()
    elif key in ["+", "="]:
        sim_speed = clamp(sim_speed + 0.25, 0.25, 4.0)
    elif key in ["-", "_"]:
        sim_speed = clamp(sim_speed - 0.25, 0.25, 4.0)
    elif key == "?":
        print_controls()


scene.bind("keydown", on_keydown)


# ----------------------------- Main loop -----------------------------

build_scene()
print_controls()

while True:
    rate(60)
    dt = DT_BASE * sim_speed

    if not running:
        update_labels()
        continue

    time_elapsed += dt

    if ai_enabled:
        ai.act(dt)

    update_genes(dt)
    update_signals(dt)
    update_traits(dt)
    update_links(dt)
    update_temporary(dt)
    detect_global_stability(dt)
    update_labels()
