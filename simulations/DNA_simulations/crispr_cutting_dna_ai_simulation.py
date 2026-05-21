"""
CRISPR Cutting DNA — VPython 3D Simulation with Expressive AI Controller

Run:
    pip install vpython
    python crispr_cutting_dna_ai_simulation.py

Controls:
    H  show/hide help
    A  toggle AI on/off
    P  pause/resume simulation
    R  reset round
    C  force Cas9 cut if attached
    M  toggle AI mode manually
    1  AI careful_search mode
    2  AI orbit_scan mode
    3  AI attach_cut mode
    4  AI repair_build mode
    5  AI chaotic_edit mode
    6  AI artistic_mark mode
    Arrow keys / WASD move Cas9 manually when AI is off or override is active
    Q/E rotate Cas9 manually
    Space brief human override / nudge guide RNA

Notes:
    This is a visual/educational simulation, not a molecularly accurate physical model.
    It models the stages conceptually:
      1. guide RNA searches DNA
      2. matching target is marked
      3. Cas9 attaches
      4. DNA is cut
      5. repair particles reconnect or modify the cut
      6. AI resets/loops when the round completes or stagnates
"""

from vpython import *
from math import sin, cos, pi, atan2
import random
import time

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="CRISPR Cutting DNA — AI Controlled Simulation",
    width=1280,
    height=760,
    background=vector(0.96, 0.985, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.18, -0.18, -1)
scene.range = 10.5
scene.userspin = True
scene.userzoom = True

# Light visual palette
COL_DNA_A = vector(0.34, 0.55, 0.95)
COL_DNA_B = vector(0.96, 0.50, 0.55)
COL_BACKBONE = vector(0.76, 0.80, 0.86)
COL_TARGET = vector(1.00, 0.82, 0.20)
COL_CAS9 = vector(0.45, 0.92, 0.72)
COL_GRNA = vector(0.40, 0.74, 0.98)
COL_REPAIR = vector(0.93, 0.66, 1.00)
COL_CUT = vector(1.0, 0.23, 0.22)
COL_MARK = vector(1.0, 0.88, 0.25)
COL_TEXT = vector(0.10, 0.16, 0.25)
COL_AI = vector(0.35, 0.35, 0.95)
COL_SHADOW = vector(0.78, 0.84, 0.90)

random.seed(7)

# -----------------------------
# Utility functions
# -----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp_vec(a, b, t):
    return a + (b - a) * clamp(t, 0, 1)


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-9:
        return fallback
    return norm(v)


def make_label(txt, pos, height=12, color_val=COL_TEXT, box=False):
    return label(
        text=txt,
        pos=pos,
        height=height,
        color=color_val,
        box=box,
        opacity=0.0 if not box else 0.15,
        line=False,
        font="sans",
    )


def set_visible(items, visible):
    for it in items:
        try:
            it.visible = visible
        except Exception:
            pass

# -----------------------------
# Labels and UI
# -----------------------------
status_label = make_label("", vector(-9.0, 7.1, 0), height=13)
mode_label = make_label("", vector(-9.0, 6.55, 0), height=12, color_val=COL_AI)
help_label = make_label("", vector(4.6, 6.9, 0), height=10, color_val=vector(0.18, 0.22, 0.30), box=True)
round_label = make_label("", vector(-9.0, -6.9, 0), height=11, color_val=vector(0.25, 0.30, 0.35))

show_help = True
paused = False
human_override_timer = 0.0

help_text = (
    "Controls\n"
    "A AI on/off   P pause   R reset   H help\n"
    "C force cut   M cycle AI mode\n"
    "1 careful  2 orbit  3 cut  4 repair  5 chaotic  6 artistic\n"
    "WASD/Arrows move Cas9, Q/E rotate, Space nudge guide RNA"
)

# -----------------------------
# DNA model
# -----------------------------
BASES = ["A", "T", "C", "G"]
PAIR = {"A": "T", "T": "A", "C": "G", "G": "C"}
BASE_COL = {
    "A": vector(0.22, 0.58, 1.00),
    "T": vector(1.00, 0.45, 0.50),
    "C": vector(0.36, 0.82, 0.55),
    "G": vector(0.98, 0.72, 0.30),
}

class DNABasePair:
    def __init__(self, index, x, angle, base, target=False):
        self.index = index
        self.x = x
        self.angle = angle
        self.base = base
        self.pair_base = PAIR[base]
        self.target = target
        self.cut = False
        self.repaired = False
        self.modified = False
        self.marked = False
        self.wiggle = random.random() * 10
        r = 1.35
        self.p1 = vector(x, r * cos(angle), r * sin(angle))
        self.p2 = vector(x, -r * cos(angle), -r * sin(angle))
        self.mid = (self.p1 + self.p2) * 0.5
        self.axis = self.p2 - self.p1

        self.left_sphere = sphere(pos=self.p1, radius=0.16, color=BASE_COL[base], shininess=0.35)
        self.right_sphere = sphere(pos=self.p2, radius=0.16, color=BASE_COL[self.pair_base], shininess=0.35)
        self.rung = cylinder(pos=self.p1, axis=self.axis, radius=0.035, color=vector(0.74, 0.77, 0.82), opacity=0.82)
        self.base_label = label(text=f"{base}-{self.pair_base}", pos=self.mid + vector(0, 0.32, 0), height=7, color=vector(0.22, 0.26, 0.32), box=False, line=False)

        # Break markers start hidden.
        self.cut_marker_1 = cylinder(pos=self.p1, axis=(self.mid - self.p1) * 0.43, radius=0.055, color=COL_CUT, visible=False)
        self.cut_marker_2 = cylinder(pos=self.p2, axis=(self.mid - self.p2) * 0.43, radius=0.055, color=COL_CUT, visible=False)
        self.spark = sphere(pos=self.mid, radius=0.18, color=COL_CUT, emissive=True, opacity=0.0, visible=False)
        self.halo = sphere(pos=self.mid, radius=0.48, color=COL_TARGET if target else vector(0.7, 0.7, 0.7), opacity=0.0, visible=False)
        self.patch = sphere(pos=self.mid, radius=0.13, color=COL_REPAIR, emissive=True, opacity=0.0, visible=False)

    def update_visual(self, t):
        # Gentle breathing so the helix feels alive.
        breathe = 0.025 * sin(t * 1.6 + self.wiggle)
        if not self.cut:
            self.rung.visible = True
            self.rung.pos = self.p1
            self.rung.axis = self.p2 - self.p1
            self.left_sphere.pos = self.p1 + vector(0, breathe, 0)
            self.right_sphere.pos = self.p2 - vector(0, breathe, 0)
            self.base_label.pos = self.mid + vector(0, 0.32 + breathe, 0)
        else:
            # Separate strand ends after cut.
            sep = 0.42 + 0.10 * sin(t * 5.2 + self.index)
            n = safe_norm(self.axis)
            self.left_sphere.pos = self.p1 - n * sep
            self.right_sphere.pos = self.p2 + n * sep
            self.rung.visible = False
            self.base_label.pos = self.mid + vector(0, 0.55, 0)

        if self.target:
            self.halo.visible = True
            self.halo.pos = self.mid
            self.halo.opacity = 0.08 + 0.06 * sin(t * 2.0) ** 2
            self.halo.radius = 0.45 + 0.08 * sin(t * 2.4 + self.index)
        elif self.marked:
            self.halo.visible = True
            self.halo.pos = self.mid
            self.halo.opacity = 0.05

        if self.cut:
            self.cut_marker_1.visible = True
            self.cut_marker_2.visible = True
            self.cut_marker_1.pos = self.left_sphere.pos
            self.cut_marker_2.pos = self.right_sphere.pos
            self.spark.visible = True
            self.spark.pos = self.mid
            self.spark.opacity = 0.20 + 0.25 * sin(t * 8.0) ** 2
        else:
            self.cut_marker_1.visible = False
            self.cut_marker_2.visible = False
            self.spark.visible = False
            self.spark.opacity = 0.0

        if self.repaired:
            self.patch.visible = True
            self.patch.pos = self.mid + vector(0, 0.07 * sin(t * 4.0), 0)
            self.patch.opacity = 0.60
            self.patch.radius = 0.17 if not self.modified else 0.24
        else:
            self.patch.visible = False
            self.patch.opacity = 0.0

    def mark(self):
        self.marked = True
        self.halo.visible = True
        self.halo.color = COL_MARK
        self.halo.opacity = 0.18

    def cut_pair(self):
        self.cut = True
        self.repaired = False
        self.modified = False

    def repair_pair(self, modify=False):
        self.cut = False
        self.repaired = True
        self.modified = modify
        if modify:
            self.base = random.choice(BASES)
            self.pair_base = PAIR[self.base]
            self.left_sphere.color = BASE_COL[self.base]
            self.right_sphere.color = BASE_COL[self.pair_base]
            self.base_label.text = f"{self.base}-{self.pair_base}*"
        else:
            self.base_label.text = f"{self.base}-{self.pair_base}"

class DNAMolecule:
    def __init__(self, n=34):
        self.n = n
        self.base_pairs = []
        self.target_index = n // 2 + 4
        self.target_window = [self.target_index - 1, self.target_index, self.target_index + 1]
        self.left_backbone = None
        self.right_backbone = None
        self.backbone_points_1 = []
        self.backbone_points_2 = []
        self.build()

    def build(self):
        for bp in getattr(self, "base_pairs", []):
            self.destroy_pair(bp)
        self.base_pairs = []
        if self.left_backbone:
            self.left_backbone.visible = False
        if self.right_backbone:
            self.right_backbone.visible = False

        start_x = -7.0
        spacing = 0.43
        twist = 0.62
        sequence = [random.choice(BASES) for _ in range(self.n)]
        # Give the target a recognizable motif.
        motif = ["G", "G", "A"]
        for k, idx in enumerate(self.target_window):
            sequence[idx] = motif[k]

        for i in range(self.n):
            x = start_x + i * spacing
            angle = i * twist
            bp = DNABasePair(i, x, angle, sequence[i], target=(i in self.target_window))
            self.base_pairs.append(bp)

        self.refresh_backbones()

    def destroy_pair(self, bp):
        for obj in [bp.left_sphere, bp.right_sphere, bp.rung, bp.base_label, bp.cut_marker_1, bp.cut_marker_2, bp.spark, bp.halo, bp.patch]:
            try:
                obj.visible = False
            except Exception:
                pass

    def refresh_backbones(self):
        self.backbone_points_1 = [bp.p1 for bp in self.base_pairs]
        self.backbone_points_2 = [bp.p2 for bp in self.base_pairs]
        if self.left_backbone:
            self.left_backbone.visible = False
        if self.right_backbone:
            self.right_backbone.visible = False
        self.left_backbone = curve(pos=self.backbone_points_1, radius=0.045, color=COL_BACKBONE, opacity=0.70)
        self.right_backbone = curve(pos=self.backbone_points_2, radius=0.045, color=COL_BACKBONE, opacity=0.70)

    def update(self, t):
        for bp in self.base_pairs:
            bp.update_visual(t)

    def get_target_center(self):
        pts = [self.base_pairs[i].mid for i in self.target_window]
        return sum(pts, vector(0, 0, 0)) / len(pts)

    def get_cut_pairs(self):
        return [bp for bp in self.base_pairs if bp.cut]

    def get_unrepaired_cut_pairs(self):
        return [bp for bp in self.base_pairs if bp.cut and not bp.repaired]

    def all_target_cut(self):
        return all(self.base_pairs[i].cut or self.base_pairs[i].repaired for i in self.target_window)

    def all_target_repaired(self):
        return all(self.base_pairs[i].repaired for i in self.target_window)

    def cut_target(self):
        for idx in self.target_window:
            self.base_pairs[idx].cut_pair()

    def mark_target(self):
        for idx in self.target_window:
            self.base_pairs[idx].mark()

    def repair_one_cut(self, modify_chance=0.25):
        cuts = self.get_unrepaired_cut_pairs()
        if not cuts:
            return False
        bp = random.choice(cuts)
        bp.repair_pair(modify=random.random() < modify_chance)
        return True

    def reset(self):
        self.build()

# -----------------------------
# Guide RNA, Cas9, repair particles, effects
# -----------------------------
class GuideRNA:
    def __init__(self):
        self.phase = 0.0
        self.bound = False
        self.target_match = False
        self.scan_index = 0
        self.pos = vector(-8.3, 2.6, 0)
        self.body = curve(radius=0.045, color=COL_GRNA, opacity=0.95)
        self.glow = sphere(pos=self.pos, radius=0.20, color=COL_GRNA, emissive=True, opacity=0.32)
        self.label = make_label("guide RNA", self.pos + vector(0, 0.45, 0), height=9, color_val=vector(0.16, 0.38, 0.62))
        self.trail = curve(radius=0.018, color=COL_GRNA, opacity=0.50)
        self.trail_count = 0
        self.update_shape()

    def update_shape(self):
        pts = []
        for i in range(14):
            x = self.pos.x + (i - 7) * 0.12
            y = self.pos.y + 0.08 * sin(i * 0.9 + self.phase)
            z = self.pos.z + 0.08 * cos(i * 0.9 + self.phase)
            pts.append(vector(x, y, z))
        self.body.clear()
        for p in pts:
            self.body.append(p)
        self.glow.pos = self.pos
        self.label.pos = self.pos + vector(0, 0.45, 0)

    def move_toward(self, target, speed, dt):
        direction = target - self.pos
        if mag(direction) > 0.03:
            self.pos += safe_norm(direction) * speed * dt

    def orbit_around(self, center, radius, angular_speed, dt, vertical=0.0):
        self.phase += angular_speed * dt
        self.pos = center + vector(radius * cos(self.phase), vertical + 0.35 * sin(self.phase * 1.4), radius * sin(self.phase))

    def update(self, dt, t):
        self.phase += dt * 5.0
        self.update_shape()
        self.trail_count += 1
        if self.trail_count % 3 == 0:
            self.trail.append(self.pos)
            if self.trail.npoints > 90:
                self.trail.pop(0)

    def reset(self):
        self.phase = random.random() * 10
        self.bound = False
        self.target_match = False
        self.scan_index = 0
        self.pos = vector(-8.3, 2.6 + random.uniform(-0.5, 0.5), random.uniform(-0.4, 0.4))
        self.trail.clear()

class Cas9Protein:
    def __init__(self):
        self.pos = vector(-8.1, 3.7, 0.2)
        self.vel = vector(0, 0, 0)
        self.attached = False
        self.cut_done = False
        self.angle = 0.0
        self.intent = "idle"
        self.body = ellipsoid(pos=self.pos, length=1.25, height=0.82, width=0.92, color=COL_CAS9, opacity=0.92, shininess=0.50)
        self.inner = sphere(pos=self.pos + vector(0.15, 0.12, 0.0), radius=0.22, color=vector(0.25, 0.72, 0.56), opacity=0.55)
        self.active_site = sphere(pos=self.pos + vector(0.55, 0, 0), radius=0.14, color=COL_CUT, emissive=True, opacity=0.75)
        self.guide_socket = ring(pos=self.pos + vector(-0.28, -0.08, 0), axis=vector(1, 0, 0), radius=0.27, thickness=0.035, color=COL_GRNA, opacity=0.65)
        self.label = make_label("Cas9", self.pos + vector(0, 0.75, 0), height=10, color_val=vector(0.12, 0.38, 0.25))
        self.aura = sphere(pos=self.pos, radius=0.75, color=COL_CAS9, opacity=0.05)

    def update_visual(self, t):
        bob = vector(0, 0.035 * sin(t * 2.7), 0)
        self.body.pos = self.pos + bob
        self.inner.pos = self.pos + vector(0.15 * cos(self.angle), 0.12, 0.15 * sin(self.angle)) + bob
        self.active_site.pos = self.pos + vector(0.55 * cos(self.angle), 0.02, 0.55 * sin(self.angle)) + bob
        self.guide_socket.pos = self.pos + vector(-0.28 * cos(self.angle), -0.08, -0.28 * sin(self.angle)) + bob
        self.guide_socket.axis = vector(cos(self.angle), 0, sin(self.angle))
        self.label.pos = self.pos + vector(0, 0.78, 0)
        self.aura.pos = self.pos
        self.aura.opacity = 0.05 if not self.attached else 0.14 + 0.05 * sin(t * 8) ** 2
        self.active_site.opacity = 0.35 + (0.45 if self.attached else 0.12) * sin(t * 5.3) ** 2

    def move_toward(self, target, speed, dt):
        d = target - self.pos
        if mag(d) > 0.03:
            self.vel = safe_norm(d) * speed
            self.pos += self.vel * dt
            self.angle = atan2(d.z, d.x)
        else:
            self.vel *= 0.3

    def rotate(self, amount):
        self.angle += amount

    def attach_to(self, target):
        self.attached = True
        self.intent = "attached"
        self.pos = lerp_vec(self.pos, target + vector(0, 0.85, 0.22), 0.35)

    def detach(self):
        self.attached = False
        self.cut_done = False
        self.intent = "detached"

    def reset(self):
        self.pos = vector(-8.1, 3.7 + random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4))
        self.vel = vector(0, 0, 0)
        self.attached = False
        self.cut_done = False
        self.intent = "idle"
        self.angle = 0.0

class RepairParticle:
    def __init__(self, i):
        self.i = i
        self.home = vector(random.uniform(4.8, 7.8), random.uniform(-3.5, 3.8), random.uniform(-2.0, 2.0))
        self.pos = self.home + vector(random.uniform(-0.6, 0.6), random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4))
        self.target = self.home
        self.carrying_patch = False
        self.active = False
        self.mode = "idle"
        self.body = sphere(pos=self.pos, radius=random.uniform(0.11, 0.18), color=COL_REPAIR, opacity=0.75, emissive=True)
        self.trail = curve(radius=0.012, color=COL_REPAIR, opacity=0.32)
        self.tick = 0

    def update(self, dt, dna, t):
        self.tick += 1
        if self.active:
            cuts = dna.get_unrepaired_cut_pairs()
            if cuts:
                bp = cuts[self.i % len(cuts)]
                self.target = bp.mid + vector(random.uniform(-0.08, 0.08), random.uniform(0.0, 0.45), random.uniform(-0.08, 0.08))
                self.mode = "repairing"
                if mag(self.pos - self.target) < 0.22:
                    dna.repair_one_cut(modify_chance=0.38)
                    self.active = False
                    self.mode = "return"
                    self.target = self.home
            else:
                self.active = False
                self.mode = "return"
                self.target = self.home
        else:
            self.target = self.home + vector(0.18 * sin(t * 1.2 + self.i), 0.15 * cos(t * 1.5 + self.i), 0.12 * sin(t * 1.7 + self.i))

        d = self.target - self.pos
        if mag(d) > 0.02:
            self.pos += safe_norm(d) * (1.4 if self.active else 0.55) * dt
        self.body.pos = self.pos
        self.body.opacity = 0.95 if self.active else 0.38
        self.body.radius = 0.18 if self.active else 0.12
        if self.tick % 4 == 0:
            self.trail.append(self.pos)
            if self.trail.npoints > 45:
                self.trail.pop(0)

    def activate(self):
        self.active = True
        self.carrying_patch = True

    def reset(self):
        self.pos = self.home + vector(random.uniform(-0.8, 0.8), random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5))
        self.active = False
        self.carrying_patch = False
        self.mode = "idle"
        self.trail.clear()

class MarkerParticle:
    def __init__(self):
        self.pos = vector(0, 0, 0)
        self.vel = vector(0, 0, 0)
        self.life = 0
        self.body = sphere(pos=self.pos, radius=0.045, color=COL_MARK, emissive=True, opacity=0.0, visible=False)

    def spawn(self, pos, color_val=COL_MARK, speed=1.0):
        self.pos = pos
        self.vel = vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)) * speed
        self.life = random.uniform(0.5, 1.6)
        self.body.pos = self.pos
        self.body.color = color_val
        self.body.opacity = 0.85
        self.body.visible = True

    def update(self, dt):
        if self.life <= 0:
            self.body.visible = False
            return
        self.life -= dt
        self.vel *= 0.985
        self.pos += self.vel * dt
        self.body.pos = self.pos
        self.body.opacity = max(0, self.life / 1.6)

# -----------------------------
# AI behavior controller
# -----------------------------
class AIController:
    MODES = [
        "careful_search",
        "orbit_scan",
        "attach_cut",
        "repair_build",
        "chaotic_edit",
        "artistic_mark",
        "ritual_loop",
    ]

    def __init__(self):
        self.enabled = True
        self.mode = "careful_search"
        self.mode_time = 0.0
        self.round = 1
        self.completed_rounds = 0
        self.stagnation_time = 0.0
        self.last_progress_score = -1
        self.loop_delay = 0.0
        self.personality = "careful"
        self.manual_override = False
        self.mode_index = 0
        self.chaos_budget = 0
        self.art_marks = []

    def read_state(self, dna, grna, cas9, repairs):
        target = dna.get_target_center()
        cut_count = len(dna.get_cut_pairs())
        repaired_count = sum(1 for idx in dna.target_window if dna.base_pairs[idx].repaired)
        marked_count = sum(1 for idx in dna.target_window if dna.base_pairs[idx].marked)
        active_repairs = sum(1 for r in repairs if r.active)
        dist_cas9_target = mag(cas9.pos - (target + vector(0, 0.85, 0.22)))
        dist_grna_target = mag(grna.pos - (target + vector(0, 1.0, 0)))
        complete = dna.all_target_repaired()
        progress_score = marked_count * 2 + int(grna.target_match) * 3 + int(cas9.attached) * 5 + cut_count * 7 + repaired_count * 11
        return {
            "target": target,
            "cut_count": cut_count,
            "repaired_count": repaired_count,
            "marked_count": marked_count,
            "active_repairs": active_repairs,
            "dist_cas9_target": dist_cas9_target,
            "dist_grna_target": dist_grna_target,
            "complete": complete,
            "progress_score": progress_score,
        }

    def detect_stagnation(self, state, dt):
        if state["progress_score"] == self.last_progress_score:
            self.stagnation_time += dt
        else:
            self.stagnation_time = 0.0
            self.last_progress_score = state["progress_score"]
        return self.stagnation_time > 8.0

    def set_mode(self, mode):
        if mode in self.MODES:
            self.mode = mode
            self.mode_time = 0.0
            self.mode_index = self.MODES.index(mode)
            self.chaos_budget = random.randint(2, 5)

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.MODES)
        self.set_mode(self.MODES[self.mode_index])

    def choose_action(self, state, dna, grna, cas9, repairs, dt):
        # State machine: reacts to current stage and also changes style over time.
        if self.loop_delay > 0:
            return "wait_loop"
        if state["complete"]:
            return "complete_round"
        if state["cut_count"] > 0 and state["repaired_count"] < 3:
            if self.mode not in ["repair_build", "artistic_mark"]:
                self.set_mode("repair_build")
        elif cas9.attached and not cas9.cut_done:
            self.set_mode("attach_cut")
        elif grna.target_match and not cas9.attached:
            if self.mode not in ["attach_cut", "ritual_loop", "chaotic_edit"]:
                self.set_mode("attach_cut")
        elif state["marked_count"] == 0:
            if self.mode_time > 5.0 or self.mode not in ["careful_search", "orbit_scan", "artistic_mark"]:
                self.set_mode(random.choice(["careful_search", "orbit_scan", "artistic_mark"]))

        # Avoid doing one thing forever.
        if self.mode_time > random.uniform(7.0, 12.0):
            possible = [m for m in self.MODES if m != self.mode]
            # Prefer constructive progression, but sometimes play.
            if state["marked_count"] == 0:
                possible = ["careful_search", "orbit_scan", "artistic_mark"]
            elif state["cut_count"] == 0:
                possible = ["attach_cut", "ritual_loop", "chaotic_edit"]
            elif state["repaired_count"] < 3:
                possible = ["repair_build", "artistic_mark"]
            self.set_mode(random.choice(possible))

        return self.mode

    def act(self, action, dna, grna, cas9, repairs, effects, dt, t):
        target = dna.get_target_center()
        cas9_target = target + vector(0, 0.88, 0.22)
        grna_target = target + vector(0, 1.15, -0.18)

        if action == "careful_search":
            # Guide RNA walks along the DNA and marks target when close.
            idx = int((sin(t * 0.65) * 0.5 + 0.5) * (dna.n - 1))
            scan_bp = dna.base_pairs[idx]
            scan_pos = scan_bp.mid + vector(0, 1.35, 0.15 * sin(t * 2.0))
            grna.move_toward(scan_pos, 1.2, dt)
            cas9.move_toward(grna.pos + vector(-0.65, 0.75, 0.2), 0.9, dt)
            cas9.rotate(0.25 * dt)
            if mag(grna.pos - grna_target) < 0.9 or idx in dna.target_window:
                dna.mark_target()
                grna.target_match = True
                self.set_mode("attach_cut")
                for _ in range(8):
                    random.choice(effects).spawn(target + vector(random.uniform(-0.2, 0.2), random.uniform(0.0, 0.5), random.uniform(-0.2, 0.2)), COL_MARK, speed=1.1)

        elif action == "orbit_scan":
            # Both guide RNA and Cas9 orbit the target before committing.
            grna.orbit_around(target, 1.55, 1.5, dt, vertical=0.85)
            orbit_pos = target + vector(2.25 * cos(t * 0.9), 1.05 + 0.25 * sin(t * 1.6), 2.25 * sin(t * 0.9))
            cas9.move_toward(orbit_pos, 1.6, dt)
            cas9.rotate(1.2 * dt)
            if self.mode_time > 3.2:
                dna.mark_target()
                grna.target_match = True
                self.set_mode("attach_cut")

        elif action == "attach_cut":
            # Cas9 attaches to the marked target and cuts.
            grna.move_toward(grna_target, 1.7, dt)
            cas9.move_toward(cas9_target, 1.65, dt)
            if mag(cas9.pos - cas9_target) < 0.28:
                cas9.attach_to(target)
                if self.mode_time > 0.8 or mag(grna.pos - grna_target) < 0.45:
                    dna.cut_target()
                    cas9.cut_done = True
                    self.set_mode("repair_build")
                    for _ in range(25):
                        random.choice(effects).spawn(target, COL_CUT, speed=2.5)
                    for r in random.sample(repairs, min(7, len(repairs))):
                        r.activate()

        elif action == "repair_build":
            # Repair particles swarm toward cut sites.
            if random.random() < 0.05:
                for r in random.sample(repairs, min(3, len(repairs))):
                    r.activate()
            cas9.move_toward(target + vector(1.5, 1.6, 0.5 * sin(t)), 0.85, dt)
            grna.move_toward(target + vector(-1.0, 1.35, -0.5), 0.65, dt)
            if dna.all_target_repaired():
                self.loop_delay = 2.2

        elif action == "chaotic_edit":
            # A more destructive/curious mode: bumps, detaches, random marks, then still proceeds.
            wobble = vector(random.uniform(-0.8, 0.8), random.uniform(-0.45, 0.45), random.uniform(-0.8, 0.8))
            cas9.move_toward(target + vector(0, 1.0, 0.2) + wobble, 2.2, dt)
            grna.move_toward(target + vector(random.uniform(-0.5, 0.5), 1.15, random.uniform(-0.5, 0.5)), 1.9, dt)
            cas9.rotate(random.uniform(-2.0, 2.0) * dt)
            if random.random() < 0.10:
                idx = random.choice(dna.target_window)
                dna.base_pairs[idx].mark()
                random.choice(effects).spawn(dna.base_pairs[idx].mid, vector(1.0, 0.55, 0.25), speed=1.8)
            if self.mode_time > 2.0:
                dna.mark_target()
                grna.target_match = True
                self.set_mode("attach_cut")

        elif action == "artistic_mark":
            # Paints glowing particles and non-destructive marks around the target.
            phase = t * 1.4
            brush = target + vector(1.4 * cos(phase), 1.0 + 0.35 * sin(phase * 2), 1.4 * sin(phase))
            grna.move_toward(brush, 1.5, dt)
            cas9.move_toward(brush + vector(0.6 * sin(phase), 0.65, 0.6 * cos(phase)), 1.1, dt)
            if random.random() < 0.25:
                random.choice(effects).spawn(brush, random.choice([COL_MARK, COL_GRNA, COL_REPAIR]), speed=0.6)
            if self.mode_time > 4.2:
                dna.mark_target()
                grna.target_match = True
                self.set_mode("attach_cut")

        elif action == "ritual_loop":
            # A ceremonial orbit before cutting.
            grna.orbit_around(target, 1.1 + 0.25 * sin(t), 2.1, dt, vertical=1.0)
            cas9.move_toward(target + vector(1.65 * cos(t * 1.2 + pi), 1.15, 1.65 * sin(t * 1.2 + pi)), 1.4, dt)
            if random.random() < 0.08:
                random.choice(effects).spawn(target + vector(0, 1.1, 0), COL_MARK, speed=1.0)
            if self.mode_time > 4.8:
                dna.mark_target()
                grna.target_match = True
                self.set_mode("attach_cut")

    def update(self, dna, grna, cas9, repairs, effects, dt, t):
        if not self.enabled:
            return
        self.mode_time += dt
        if self.loop_delay > 0:
            self.loop_delay -= dt
            if self.loop_delay <= 0:
                reset_round()
            return
        state = self.read_state(dna, grna, cas9, repairs)
        stagnant = self.detect_stagnation(state, dt)
        if stagnant:
            # Reset if the scene stops changing, unless a cut is waiting for repair.
            if state["cut_count"] > 0 and state["repaired_count"] < 3:
                self.set_mode("repair_build")
                for r in repairs:
                    if random.random() < 0.5:
                        r.activate()
                self.stagnation_time = 0.0
            else:
                self.loop_delay = 0.6
                self.stagnation_time = 0.0
                return
        action = self.choose_action(state, dna, grna, cas9, repairs, dt)
        if action == "complete_round":
            self.loop_delay = 2.4
            self.completed_rounds += 1
            return
        self.act(action, dna, grna, cas9, repairs, effects, dt, t)

    def reset(self):
        self.mode = random.choice(["careful_search", "orbit_scan", "artistic_mark", "ritual_loop"])
        self.mode_index = self.MODES.index(self.mode)
        self.mode_time = 0.0
        self.stagnation_time = 0.0
        self.last_progress_score = -1
        self.loop_delay = 0.0
        self.round += 1

# -----------------------------
# Build simulation objects
# -----------------------------
dna = DNAMolecule(n=34)
grna = GuideRNA()
cas9 = Cas9Protein()
repair_particles = [RepairParticle(i) for i in range(18)]
effects = [MarkerParticle() for _ in range(80)]
ai = AIController()

# Stationary scene objects: soft platform, target bracket, legend.
platform = box(pos=vector(0, -2.15, 0), size=vector(16.5, 0.04, 5.2), color=vector(0.90, 0.94, 0.98), opacity=0.55)
target_bracket = ring(pos=dna.get_target_center(), axis=vector(1, 0, 0), radius=1.8, thickness=0.025, color=COL_TARGET, opacity=0.30)
legend_bg = box(pos=vector(6.4, -5.85, 0), size=vector(5.1, 1.45, 0.04), color=vector(1, 1, 1), opacity=0.35)
legend = make_label(
    "Blue/red/green/gold spheres = DNA bases\nCyan guide RNA searches target\nGreen Cas9 attaches and cuts\nPurple repair particles reconnect/modify DNA",
    vector(6.4, -5.78, 0.05),
    height=9,
    color_val=vector(0.15, 0.18, 0.23),
)

# -----------------------------
# Human controls
# -----------------------------
keys_down = set()

def reset_round():
    global dna, grna, cas9, repair_particles, effects, target_bracket
    dna.reset()
    grna.reset()
    cas9.reset()
    for r in repair_particles:
        r.reset()
    for e in effects:
        e.life = 0
        e.body.visible = False
    target_bracket.pos = dna.get_target_center()
    ai.reset()


def keydown(evt):
    global paused, show_help, human_override_timer
    k = evt.key.lower()
    keys_down.add(k)
    if k == "h":
        show_help = not show_help
    elif k == "a":
        ai.enabled = not ai.enabled
    elif k == "p":
        paused = not paused
    elif k == "r":
        reset_round()
    elif k == "c":
        if cas9.attached or mag(cas9.pos - (dna.get_target_center() + vector(0, 0.88, 0.22))) < 1.2:
            dna.mark_target()
            dna.cut_target()
            cas9.cut_done = True
            for r in random.sample(repair_particles, min(7, len(repair_particles))):
                r.activate()
    elif k == "m":
        ai.cycle_mode()
    elif k in ["1", "2", "3", "4", "5", "6"]:
        mapping = {
            "1": "careful_search",
            "2": "orbit_scan",
            "3": "attach_cut",
            "4": "repair_build",
            "5": "chaotic_edit",
            "6": "artistic_mark",
        }
        ai.set_mode(mapping[k])
    elif k == " ":
        human_override_timer = 2.5
        grna.pos += vector(0.25, 0.2, random.uniform(-0.3, 0.3))


def keyup(evt):
    k = evt.key.lower()
    if k in keys_down:
        keys_down.remove(k)

scene.bind("keydown", keydown)
scene.bind("keyup", keyup)


def apply_human_controls(dt):
    global human_override_timer
    move = vector(0, 0, 0)
    if "w" in keys_down or "up" in keys_down:
        move.y += 1
    if "s" in keys_down or "down" in keys_down:
        move.y -= 1
    if "a" in keys_down or "left" in keys_down:
        move.x -= 1
    if "d" in keys_down or "right" in keys_down:
        move.x += 1
    if "z" in keys_down:
        move.z += 1
    if "x" in keys_down:
        move.z -= 1
    if mag(move) > 0:
        human_override_timer = 2.0
        cas9.pos += safe_norm(move) * 2.2 * dt
        cas9.attached = False
    if "q" in keys_down:
        human_override_timer = 2.0
        cas9.rotate(-2.2 * dt)
    if "e" in keys_down:
        human_override_timer = 2.0
        cas9.rotate(2.2 * dt)
    if human_override_timer > 0:
        human_override_timer -= dt

# -----------------------------
# Main simulation loop
# -----------------------------
last_time = time.time()
t = 0.0

print("CRISPR Cutting DNA AI simulation loaded.")
print("Press H in the VPython window for controls.")

while True:
    rate(60)
    now = time.time()
    dt = clamp(now - last_time, 0.001, 0.04)
    last_time = now
    if paused:
        help_label.visible = show_help
        status_label.text = "PAUSED — press P to resume"
        mode_label.text = f"AI: {'ON' if ai.enabled else 'OFF'} | mode: {ai.mode}"
        continue

    t += dt
    apply_human_controls(dt)

    # AI runs automatically but yields briefly to human keyboard override.
    if human_override_timer <= 0:
        ai.update(dna, grna, cas9, repair_particles, effects, dt, t)

    dna.update(t)
    grna.update(dt, t)
    cas9.update_visual(t)
    for r in repair_particles:
        r.update(dt, dna, t)
    for e in effects:
        e.update(dt)

    target_bracket.pos = dna.get_target_center()
    target_bracket.radius = 1.75 + 0.08 * sin(t * 1.4)
    target_bracket.opacity = 0.18 + 0.10 * sin(t * 2.0) ** 2

    state = ai.read_state(dna, grna, cas9, repair_particles)
    status_label.text = (
        f"CRISPR round {ai.round} | target marked {state['marked_count']}/3 | "
        f"cut pairs {state['cut_count']} | repaired {state['repaired_count']}/3"
    )
    mode_label.text = (
        f"AI: {'ON' if ai.enabled else 'OFF'} | mode: {ai.mode} | "
        f"stagnation {ai.stagnation_time:0.1f}s | override {max(0,human_override_timer):0.1f}s"
    )
    round_label.text = "AI reads: guide distance %.2f, Cas9 distance %.2f, active repair particles %d" % (
        state["dist_grna_target"], state["dist_cas9_target"], state["active_repairs"]
    )
    help_label.visible = show_help
    help_label.text = help_text
