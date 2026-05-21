"""
Single-Cell Survival System — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python single_cell_survival_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset round
    M       cycle AI behavior mode
    O       human override: emergency repair pulse + nutrient attraction
    C       clear temporary marks and particles
    F       spill food particles near the cell
    T       spill toxin particles near the cell
    Space   manual forward pulse
    Arrow keys / WASD  manual steering pulse
    Q / E   manual rotate cell
    H       print controls

Scene concept:
    A living cell moves through a soft nutrient field. It absorbs food, avoids toxins,
    repairs membrane damage, grows, and divides. A built-in AI controller can read
    the simulation state, choose actions, switch behavior modes, detect stagnation,
    and reset/loop the world into new survival rounds.

The file is self-contained and uses VPython primitives only.
"""

from vpython import *
import random
import math
import time

# ------------------------------------------------------------
# Scene setup
# ------------------------------------------------------------

scene = canvas(
    title="Single-Cell Survival System — AI Controlled 3D VPython Simulation",
    width=1200,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
    range=14,
)

scene.caption = """
Single-cell survival system with expressive AI control.

Controls:
A toggle AI | P pause | R reset | M mode | O override pulse | C clear marks
F spill food | T spill toxin | Space pulse | WASD/arrows steer | Q/E rotate | H print controls
"""

# ------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------

WORLD_RADIUS = 11.5
FOOD_COUNT = 70
TOXIN_COUNT = 34
REPAIR_COUNT = 12
MAX_MARKS = 170
MAX_WASTE = 90
DT = 0.022

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def mag_safe(v):
    m = mag(v)
    return m if m > 1e-7 else 1e-7

def norm_safe(v):
    m = mag(v)
    if m < 1e-7:
        return vector(0, 0, 0)
    return v / m

def rand_vec(scale=1.0):
    return vector(
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
    )

def rand_unit():
    v = rand_vec(1)
    if mag(v) < 0.001:
        return vector(1, 0, 0)
    return norm(v)

def random_world_pos(radius=WORLD_RADIUS):
    for _ in range(100):
        p = rand_vec(radius)
        if mag(p) < radius:
            return p
    return rand_unit() * random.uniform(0, radius)

def lerp(a, b, t):
    return a + (b - a) * clamp(t, 0, 1)

def color_lerp(c1, c2, t):
    return vector(
        lerp(c1.x, c2.x, t),
        lerp(c1.y, c2.y, t),
        lerp(c1.z, c2.z, t),
    )

def set_visible(obj, visible):
    try:
        obj.visible = visible
    except Exception:
        pass

# ------------------------------------------------------------
# Colors
# ------------------------------------------------------------

COL_CELL = vector(0.38, 0.82, 0.95)
COL_MEMBRANE = vector(0.45, 0.92, 1.0)
COL_NUCLEUS = vector(0.62, 0.52, 0.95)
COL_FOOD = vector(0.20, 0.78, 0.32)
COL_TOXIN = vector(1.0, 0.36, 0.30)
COL_REPAIR = vector(1.0, 0.88, 0.25)
COL_WASTE = vector(0.70, 0.70, 0.76)
COL_FIELD = vector(0.72, 0.88, 1.0)
COL_MARK = vector(0.10, 0.25, 0.75)

# ------------------------------------------------------------
# Static world visuals
# ------------------------------------------------------------

boundary = sphere(
    pos=vector(0, 0, 0),
    radius=WORLD_RADIUS,
    color=vector(0.76, 0.88, 1.0),
    opacity=0.08,
    shininess=0.0,
)

equator_ring = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 1, 0),
    radius=WORLD_RADIUS,
    thickness=0.018,
    color=vector(0.60, 0.76, 0.95),
    opacity=0.35,
)

vertical_ring = ring(
    pos=vector(0, 0, 0),
    axis=vector(1, 0, 0),
    radius=WORLD_RADIUS,
    thickness=0.018,
    color=vector(0.60, 0.76, 0.95),
    opacity=0.22,
)

floor = box(
    pos=vector(0, -WORLD_RADIUS - 0.18, 0),
    size=vector(WORLD_RADIUS * 2.2, 0.04, WORLD_RADIUS * 2.2),
    color=vector(0.92, 0.96, 0.98),
    opacity=0.55,
)

# Soft nutrient field beads, stationary visual guides
field_nodes = []
for i in range(34):
    p = random_world_pos(WORLD_RADIUS * 0.96)
    node = sphere(
        pos=p,
        radius=random.uniform(0.035, 0.08),
        color=COL_FIELD,
        opacity=random.uniform(0.10, 0.24),
        shininess=0,
    )
    field_nodes.append(node)

# ------------------------------------------------------------
# Particle classes
# ------------------------------------------------------------

class WorldParticle:
    def __init__(self, kind, pos=None, velocity=None):
        self.kind = kind
        self.pos = pos if pos is not None else random_world_pos(WORLD_RADIUS * 0.94)
        self.vel = velocity if velocity is not None else rand_vec(0.04)
        self.age = 0.0
        self.attached = False
        self.attached_time = 0.0
        self.attachment_offset = vector(0, 0, 0)
        self.dead = False
        self.orbit_phase = random.uniform(0, 2 * math.pi)
        self.spin = rand_unit()

        if kind == "food":
            self.radius = random.uniform(0.09, 0.16)
            self.obj = sphere(
                pos=self.pos,
                radius=self.radius,
                color=COL_FOOD,
                opacity=0.85,
                emissive=False,
                shininess=0.45,
            )
            self.halo = sphere(
                pos=self.pos,
                radius=self.radius * 1.65,
                color=COL_FOOD,
                opacity=0.13,
                shininess=0,
            )
        elif kind == "toxin":
            self.radius = random.uniform(0.11, 0.19)
            self.obj = sphere(
                pos=self.pos,
                radius=self.radius,
                color=COL_TOXIN,
                opacity=0.78,
                shininess=0.25,
            )
            self.halo = sphere(
                pos=self.pos,
                radius=self.radius * 1.85,
                color=COL_TOXIN,
                opacity=0.10,
                shininess=0,
            )
        elif kind == "repair":
            self.radius = random.uniform(0.06, 0.10)
            self.obj = sphere(
                pos=self.pos,
                radius=self.radius,
                color=COL_REPAIR,
                opacity=0.9,
                shininess=0.8,
            )
            self.halo = sphere(
                pos=self.pos,
                radius=self.radius * 1.8,
                color=COL_REPAIR,
                opacity=0.16,
                shininess=0,
            )
        else:
            self.radius = 0.06
            self.obj = sphere(pos=self.pos, radius=self.radius, color=color.white)
            self.halo = None

    def update_visual(self):
        self.obj.pos = self.pos
        if self.halo:
            self.halo.pos = self.pos
            self.halo.radius = self.radius * (1.45 + 0.25 * math.sin(self.age * 4 + self.orbit_phase))

    def hide(self):
        set_visible(self.obj, False)
        if self.halo:
            set_visible(self.halo, False)
        self.dead = True

    def update_free_motion(self, dt):
        self.age += dt
        if self.attached:
            return

        noise = rand_vec(0.006)
        self.vel += noise

        if self.kind == "food":
            self.vel *= 0.992
        elif self.kind == "toxin":
            self.vel += 0.008 * vector(
                math.sin(self.age * 1.7 + self.orbit_phase),
                math.cos(self.age * 1.3 + self.orbit_phase) * 0.4,
                math.sin(self.age * 1.1),
            )
            self.vel *= 0.988
        elif self.kind == "repair":
            self.vel *= 0.985

        self.pos += self.vel

        d = mag(self.pos)
        if d > WORLD_RADIUS:
            n = norm_safe(self.pos)
            self.pos = n * WORLD_RADIUS
            self.vel = self.vel - 2 * dot(self.vel, n) * n
            self.vel *= 0.72

        self.update_visual()

class TemporaryMark:
    def __init__(self, pos, kind="spark", life=1.8, radius=0.07, direction=None):
        self.kind = kind
        self.life = life
        self.max_life = life
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = direction if direction is not None else rand_vec(0.04)

        if kind == "food":
            col = COL_FOOD
        elif kind == "toxin":
            col = COL_TOXIN
        elif kind == "repair":
            col = COL_REPAIR
        elif kind == "division":
            col = vector(0.8, 0.45, 1.0)
        elif kind == "scan":
            col = vector(0.2, 0.45, 1.0)
        else:
            col = vector(0.6, 0.72, 1.0)

        self.obj = sphere(
            pos=self.pos,
            radius=radius,
            color=col,
            opacity=0.72,
            shininess=0.4,
        )

    def update(self, dt):
        self.life -= dt
        self.pos += self.vel
        self.vel *= 0.97
        self.obj.pos = self.pos
        self.obj.opacity = max(0.0, 0.72 * self.life / self.max_life)
        self.obj.radius *= 0.992
        if self.life <= 0:
            self.obj.visible = False
            return False
        return True

class DamagePatch:
    def __init__(self, cell, local_dir, severity=0.32):
        self.local_dir = norm_safe(local_dir)
        if mag(self.local_dir) < 0.01:
            self.local_dir = rand_unit()
        self.severity = severity
        self.obj = sphere(
            pos=cell.pos + self.local_dir * (cell.radius + 0.035),
            radius=0.17 + 0.18 * severity,
            color=COL_TOXIN,
            opacity=0.38 + 0.20 * severity,
            shininess=0.0,
        )

    def update(self, cell):
        self.obj.pos = cell.pos + self.local_dir * (cell.radius + 0.04)
        self.obj.radius = (0.15 + 0.22 * self.severity) * cell.radius / 1.0
        self.obj.opacity = clamp(0.15 + self.severity * 0.55, 0, 0.65)

    def repair(self, amount):
        self.severity -= amount
        if self.severity <= 0:
            self.obj.visible = False
            return True
        return False

class Cell:
    def __init__(self, pos=vector(0, 0, 0), name="Cell", primary=True):
        self.name = name
        self.primary = primary
        self.pos = pos
        self.vel = vector(0.03, 0.01, 0.0)
        self.forward = vector(1, 0, 0)
        self.radius = 1.0
        self.energy = 58.0
        self.health = 86.0
        self.growth = 0.0
        self.absorbed_food = 0
        self.damage_patches = []
        self.pulse = 0.0
        self.age = 0.0
        self.divide_cooldown = 0.0
        self.last_meaningful_change = time.time()
        self.completed_divisions = 0

        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=COL_CELL,
            opacity=0.32,
            shininess=0.6,
            make_trail=True,
            trail_type="curve",
            interval=3,
            retain=150,
            trail_radius=0.025,
        )
        self.membrane = sphere(
            pos=self.pos,
            radius=self.radius * 1.04,
            color=COL_MEMBRANE,
            opacity=0.18,
            shininess=0.7,
        )
        self.nucleus = sphere(
            pos=self.pos,
            radius=self.radius * 0.34,
            color=COL_NUCLEUS,
            opacity=0.80,
            shininess=0.6,
        )
        self.sensor_ring = ring(
            pos=self.pos,
            axis=self.forward,
            radius=self.radius * 1.38,
            thickness=0.018,
            color=vector(0.22, 0.55, 1.0),
            opacity=0.22,
        )
        self.repair_ring = ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=self.radius * 1.17,
            thickness=0.014,
            color=COL_REPAIR,
            opacity=0.20,
        )
        self.label = label(
            pos=self.pos + vector(0, 1.55, 0),
            text="survival cell",
            height=12,
            box=False,
            opacity=0.0,
            color=vector(0.15, 0.22, 0.35),
        )

        self.organelles = []
        for i in range(7):
            organelle = sphere(
                pos=self.pos + rand_unit() * random.uniform(0.1, 0.55),
                radius=random.uniform(0.045, 0.075),
                color=vector(0.82, 0.66, 1.0),
                opacity=0.65,
                shininess=0.4,
            )
            self.organelles.append({
                "obj": organelle,
                "phase": random.uniform(0, 2 * math.pi),
                "axis": rand_unit(),
                "dist": random.uniform(0.18, 0.58),
                "speed": random.uniform(0.8, 1.6),
            })

    def apply_force(self, f, max_speed=0.19):
        self.vel += f
        if mag(self.vel) > max_speed:
            self.vel = norm(self.vel) * max_speed

    def rotate_forward(self, angle):
        c = math.cos(angle)
        s = math.sin(angle)
        f = self.forward
        self.forward = norm_safe(vector(f.x * c - f.z * s, f.y, f.x * s + f.z * c))

    def add_damage(self, world_point, severity=0.25):
        local = norm_safe(world_point - self.pos)
        patch = DamagePatch(self, local, severity)
        self.damage_patches.append(patch)
        self.health -= 5 + 10 * severity
        self.health = clamp(self.health, 0, 100)
        self.last_meaningful_change = time.time()

    def repair_damage(self, amount=0.012):
        self.health = clamp(self.health + amount * 24, 0, 100)
        for patch in list(self.damage_patches):
            if patch.repair(amount):
                self.damage_patches.remove(patch)
                self.last_meaningful_change = time.time()

    def absorb_food(self, particle):
        self.energy = clamp(self.energy + 14, 0, 130)
        self.growth += 7.5
        self.absorbed_food += 1
        self.pulse = 1.0
        self.last_meaningful_change = time.time()

    def toxin_hit(self, particle):
        self.energy = clamp(self.energy - 9.0, 0, 130)
        self.add_damage(particle.pos, severity=random.uniform(0.18, 0.44))
        self.vel += norm_safe(self.pos - particle.pos) * 0.10
        self.pulse = 0.7

    def update(self, dt):
        self.age += dt
        self.divide_cooldown = max(0, self.divide_cooldown - dt)
        self.energy = clamp(self.energy - dt * (0.55 + 0.10 * len(self.damage_patches)), 0, 130)

        if self.energy < 18:
            self.health -= dt * 2.4
        elif self.energy > 65 and len(self.damage_patches) == 0:
            self.health += dt * 0.8

        if len(self.damage_patches) > 0:
            self.health -= dt * 0.35 * len(self.damage_patches)

        self.health = clamp(self.health, 0, 100)

        # Natural membrane repair if enough energy exists.
        if self.energy > 35 and len(self.damage_patches) > 0:
            self.energy -= dt * 0.6
            self.repair_damage(0.0025)

        # Growth changes body size.
        target_radius = 1.0 + clamp(self.growth, 0, 100) / 100.0 * 0.55
        self.radius = lerp(self.radius, target_radius, 0.025)

        # Motion damping and boundary.
        self.vel *= 0.985
        self.pos += self.vel

        d = mag(self.pos)
        if d + self.radius > WORLD_RADIUS:
            n = norm_safe(self.pos)
            self.pos = n * (WORLD_RADIUS - self.radius)
            self.vel = self.vel - 2 * dot(self.vel, n) * n
            self.vel *= 0.45

        if mag(self.vel) > 0.01:
            self.forward = norm_safe(lerp(self.forward, norm_safe(self.vel), 0.03))

        self.pulse = max(0.0, self.pulse - dt * 1.8)

        # Visual health/energy state.
        stress = 1.0 - self.health / 100.0
        hungry = 1.0 - clamp(self.energy / 70.0, 0, 1)
        body_col = color_lerp(COL_CELL, vector(1.0, 0.55, 0.44), stress * 0.72)
        body_col = color_lerp(body_col, vector(0.72, 0.72, 0.78), hungry * 0.32)

        self.body.pos = self.pos
        self.body.radius = self.radius * (1.0 + 0.04 * self.pulse * math.sin(self.age * 18))
        self.body.color = body_col

        self.membrane.pos = self.pos
        self.membrane.radius = self.radius * (1.045 + 0.035 * self.pulse)
        self.membrane.color = color_lerp(COL_MEMBRANE, vector(1, 0.62, 0.56), stress * 0.45)

        self.nucleus.pos = self.pos - self.forward * self.radius * 0.10 + vector(0, 0.06 * math.sin(self.age * 1.8), 0)
        self.nucleus.radius = self.radius * 0.34

        self.sensor_ring.pos = self.pos
        self.sensor_ring.axis = self.forward
        self.sensor_ring.radius = self.radius * (1.30 + 0.12 * math.sin(self.age * 2.2))
        self.sensor_ring.opacity = 0.14 + 0.16 * self.pulse

        self.repair_ring.pos = self.pos
        self.repair_ring.axis = vector(math.sin(self.age * 0.8), 1, math.cos(self.age * 0.8))
        self.repair_ring.radius = self.radius * (1.10 + 0.05 * len(self.damage_patches))
        self.repair_ring.opacity = 0.12 + 0.06 * len(self.damage_patches)

        self.label.pos = self.pos + vector(0, self.radius + 0.6, 0)
        self.label.text = (
            f"{self.name}\n"
            f"energy {int(self.energy)} | health {int(self.health)} | growth {int(self.growth)}\n"
            f"food {self.absorbed_food} | damage {len(self.damage_patches)}"
        )

        for patch in self.damage_patches:
            patch.update(self)

        # Orbiting organelles.
        for item in self.organelles:
            phase = item["phase"] + self.age * item["speed"]
            axis = item["axis"]
            local = vector(
                math.cos(phase) * item["dist"],
                math.sin(phase * 0.8) * item["dist"] * 0.42,
                math.sin(phase) * item["dist"],
            )
            drift = cross(axis, local) * 0.14
            item["obj"].pos = self.pos + (local + drift) * self.radius
            item["obj"].radius = 0.052 * self.radius

    def can_divide(self):
        return self.growth >= 92 and self.energy >= 58 and self.health >= 55 and self.divide_cooldown <= 0

    def divide(self):
        self.growth = 28
        self.energy = clamp(self.energy - 30, 0, 130)
        self.divide_cooldown = 8.0
        self.completed_divisions += 1
        self.pulse = 1.2
        offset = rand_unit() * (self.radius * 1.7)
        daughter = Cell(self.pos + offset, name=f"Daughter {self.completed_divisions}", primary=False)
        daughter.radius = 0.72
        daughter.energy = 42
        daughter.health = 76
        daughter.growth = 6
        daughter.vel = offset * 0.035 + rand_vec(0.03)
        daughter.body.opacity = 0.22
        daughter.membrane.opacity = 0.12
        daughter.sensor_ring.opacity = 0.08
        daughter.label.height = 9
        return daughter

    def hide(self):
        for obj in [self.body, self.membrane, self.nucleus, self.sensor_ring, self.repair_ring, self.label]:
            set_visible(obj, False)
        for patch in self.damage_patches:
            patch.obj.visible = False
        for item in self.organelles:
            item["obj"].visible = False

# ------------------------------------------------------------
# AI controller
# ------------------------------------------------------------

class CellAIController:
    """
    Rule-based expressive AI controller.

    It reads:
        cell position, velocity, energy, health, growth, damage count,
        nearest food, nearest toxin, repair availability, particle counts,
        recent movement/progress, division readiness, and elapsed mode time.

    It can:
        steer, rotate, forage, avoid, repair, scan, spill, mark, organize,
        trigger division, pulse movement, reset a round, and cycle modes.

    The controller is deliberately simple but structured like a state machine so
    it can later be replaced by behavior trees, utility AI, reinforcement learning,
    or a learned policy.
    """

    MODES = [
        "forage",
        "avoid_toxins",
        "repair",
        "grow_and_divide",
        "curious_scan",
        "ritual_orbit",
        "chaotic_spill",
        "constructive_garden",
        "careful_rest",
    ]

    def __init__(self):
        self.enabled = True
        self.mode = "forage"
        self.mode_index = 0
        self.mode_timer = 0.0
        self.decision_timer = 0.0
        self.override_timer = 0.0
        self.last_progress_value = 0.0
        self.stagnation_timer = 0.0
        self.round_timer = 0.0
        self.completion_timer = 0.0
        self.target_point = vector(0, 0, 0)
        self.last_scan_time = 0.0
        self.rest_timer = 0.0
        self.ritual_angle = 0.0
        self.chaos_cooldown = 0.0
        self.loop_rounds = True

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.MODES)
        self.mode = self.MODES[self.mode_index]
        self.mode_timer = 0.0
        self.decision_timer = 0.0
        add_log_mark(cell.pos + vector(0, cell.radius + 0.7, 0), "scan", 1.0, 0.08)
        print("AI mode:", self.mode)

    def set_mode(self, mode):
        if mode in self.MODES and mode != self.mode:
            self.mode = mode
            self.mode_index = self.MODES.index(mode)
            self.mode_timer = 0.0
            self.decision_timer = 0.0

    def read_state(self, cell, foods, toxins, repairs, daughters):
        alive_foods = [p for p in foods if not p.dead]
        alive_toxins = [p for p in toxins if not p.dead]
        alive_repairs = [p for p in repairs if not p.dead]

        nearest_food = min(alive_foods, key=lambda p: mag(p.pos - cell.pos), default=None)
        nearest_toxin = min(alive_toxins, key=lambda p: mag(p.pos - cell.pos), default=None)
        nearest_repair = min(alive_repairs, key=lambda p: mag(p.pos - cell.pos), default=None)

        toxin_threats = [p for p in alive_toxins if mag(p.pos - cell.pos) < 2.7 + cell.radius]
        food_near = [p for p in alive_foods if mag(p.pos - cell.pos) < 3.4 + cell.radius]

        progress_value = (
            cell.energy * 0.45
            + cell.health * 0.45
            + cell.growth * 0.75
            + cell.absorbed_food * 4.0
            + cell.completed_divisions * 60.0
            - len(cell.damage_patches) * 10.0
        )

        return {
            "nearest_food": nearest_food,
            "nearest_toxin": nearest_toxin,
            "nearest_repair": nearest_repair,
            "toxin_threats": toxin_threats,
            "food_near": food_near,
            "food_count": len(alive_foods),
            "toxin_count": len(alive_toxins),
            "repair_count": len(alive_repairs),
            "daughter_count": len(daughters),
            "progress_value": progress_value,
            "speed": mag(cell.vel),
            "low_energy": cell.energy < 34,
            "damaged": cell.health < 72 or len(cell.damage_patches) > 0,
            "critical": cell.health < 35 or cell.energy < 15,
            "ready_to_divide": cell.can_divide(),
        }

    def choose_mode(self, state):
        # Priority reactions.
        if state["critical"] or (state["damaged"] and state["repair_count"] > 0):
            self.set_mode("repair")
            return
        if len(state["toxin_threats"]) >= 2:
            self.set_mode("avoid_toxins")
            return
        if state["ready_to_divide"]:
            self.set_mode("grow_and_divide")
            return
        if state["low_energy"] and state["food_count"] > 0:
            self.set_mode("forage")
            return

        # Timed expressive switching avoids doing the same thing forever.
        if self.mode_timer > random.uniform(7.0, 13.0):
            candidates = ["forage", "curious_scan", "ritual_orbit", "constructive_garden", "careful_rest"]
            if state["food_count"] < 15:
                candidates.append("chaotic_spill")
            if state["toxin_count"] > 16:
                candidates.append("avoid_toxins")
            if state["damaged"]:
                candidates.append("repair")
            self.set_mode(random.choice(candidates))

    def detect_stagnation_or_completion(self, dt, state):
        delta = abs(state["progress_value"] - self.last_progress_value)
        if delta < 0.035 and state["speed"] < 0.018:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0.0, self.stagnation_timer - dt * 1.5)

        self.last_progress_value = lerp(self.last_progress_value, state["progress_value"], 0.04)

        completed = (
            state["food_count"] <= 3
            or state["daughter_count"] >= 4
            or (state["food_count"] <= 10 and cell.growth > 80 and cell.energy > 85)
        )

        if completed:
            self.completion_timer += dt
        else:
            self.completion_timer = 0.0

        halted = self.stagnation_timer > 8.0
        empty = state["food_count"] <= 1
        deadish = cell.health <= 3 or cell.energy <= 0

        return halted or empty or deadish or self.completion_timer > 5.0

    def steer_toward(self, cell, target, strength=0.025, max_speed=0.20):
        desired = norm_safe(target - cell.pos)
        if mag(desired) > 0:
            cell.apply_force(desired * strength, max_speed=max_speed)
            cell.forward = norm_safe(lerp(cell.forward, desired, 0.08))

    def steer_away(self, cell, point, strength=0.04):
        away = norm_safe(cell.pos - point)
        if mag(away) > 0:
            cell.apply_force(away * strength, max_speed=0.22)
            cell.forward = norm_safe(lerp(cell.forward, away, 0.06))

    def update(self, dt, cell, foods, toxins, repairs, daughters):
        if not self.enabled:
            return

        self.round_timer += dt
        self.mode_timer += dt
        self.decision_timer -= dt
        self.override_timer = max(0.0, self.override_timer - dt)
        self.chaos_cooldown = max(0.0, self.chaos_cooldown - dt)

        state = self.read_state(cell, foods, toxins, repairs, daughters)

        if self.decision_timer <= 0:
            self.choose_mode(state)
            self.decision_timer = random.uniform(0.35, 0.8)

        should_reset = self.detect_stagnation_or_completion(dt, state)
        if should_reset and self.loop_rounds:
            reset_world(reason="AI loop reset: complete, empty, halted, or unstable")
            return

        # Visual AI state ring.
        if self.mode in ("forage", "constructive_garden"):
            cell.sensor_ring.color = vector(0.25, 0.76, 0.35)
        elif self.mode == "avoid_toxins":
            cell.sensor_ring.color = vector(1.0, 0.40, 0.32)
        elif self.mode == "repair":
            cell.sensor_ring.color = COL_REPAIR
        elif self.mode == "grow_and_divide":
            cell.sensor_ring.color = vector(0.85, 0.48, 1.0)
        else:
            cell.sensor_ring.color = vector(0.25, 0.52, 1.0)

        # Behavior modes.
        if self.mode == "forage":
            target = state["nearest_food"]
            if target:
                self.steer_toward(cell, target.pos, 0.025, 0.20)
                self.attract_food_cloud(cell, foods, strength=0.010, radius=4.0)
                if random.random() < 0.035:
                    add_log_mark(cell.pos + cell.forward * cell.radius * 1.3, "food", 1.0, 0.055)
            else:
                self.wander(cell, dt)

        elif self.mode == "avoid_toxins":
            if state["nearest_toxin"]:
                self.steer_away(cell, state["nearest_toxin"].pos, 0.055)
                self.push_toxins_away(cell, toxins, strength=0.026, radius=3.5)
                if random.random() < 0.05:
                    add_log_mark(cell.pos + rand_unit() * cell.radius * 1.4, "toxin", 1.1, 0.06)
            else:
                self.wander(cell, dt)

        elif self.mode == "repair":
            self.repair_behavior(cell, repairs, state)

        elif self.mode == "grow_and_divide":
            if cell.can_divide():
                perform_division()
            elif state["nearest_food"]:
                self.steer_toward(cell, state["nearest_food"].pos, 0.032, 0.19)
                self.attract_food_cloud(cell, foods, strength=0.012, radius=4.5)
            else:
                self.constructive_garden(cell, foods, toxins)

        elif self.mode == "curious_scan":
            self.curious_scan(cell, foods, toxins, repairs, dt)

        elif self.mode == "ritual_orbit":
            self.ritual_orbit(cell, dt)

        elif self.mode == "chaotic_spill":
            self.chaotic_spill(cell, foods, toxins)

        elif self.mode == "constructive_garden":
            self.constructive_garden(cell, foods, toxins)

        elif self.mode == "careful_rest":
            self.careful_rest(cell, repairs, toxins)

    def wander(self, cell, dt):
        if self.mode_timer < 0.2 or random.random() < 0.014:
            self.target_point = random_world_pos(WORLD_RADIUS * 0.76)
        self.steer_toward(cell, self.target_point, 0.014, 0.15)

    def repair_behavior(self, cell, repairs, state):
        # Pull repair particles into orbit; when they arrive, use them to heal patches.
        if state["nearest_repair"]:
            self.steer_toward(cell, state["nearest_repair"].pos, 0.016, 0.17)

        for p in repairs:
            if p.dead:
                continue
            d = mag(p.pos - cell.pos)
            if d < 4.5:
                tangent = cross(norm_safe(p.pos - cell.pos), vector(0, 1, 0))
                if mag(tangent) < 0.01:
                    tangent = cross(norm_safe(p.pos - cell.pos), vector(1, 0, 0))
                p.vel += norm_safe(cell.pos - p.pos) * 0.010 + norm_safe(tangent) * 0.012

            if d < cell.radius * 1.25 + p.radius:
                cell.repair_damage(0.075)
                cell.energy = clamp(cell.energy - 1.0, 0, 130)
                add_log_mark(p.pos, "repair", 1.3, 0.08)
                p.hide()
                if len(cell.damage_patches) == 0 and cell.health > 84:
                    self.set_mode("forage")
                    break

        if len(cell.damage_patches) == 0 and cell.health > 80:
            self.wander(cell, DT)

    def attract_food_cloud(self, cell, foods, strength=0.007, radius=4.0):
        for p in foods:
            if p.dead or p.attached:
                continue
            d = mag(p.pos - cell.pos)
            if d < radius:
                p.vel += norm_safe(cell.pos - p.pos) * strength

    def push_toxins_away(self, cell, toxins, strength=0.018, radius=3.0):
        for p in toxins:
            if p.dead:
                continue
            d = mag(p.pos - cell.pos)
            if d < radius:
                p.vel += norm_safe(p.pos - cell.pos) * strength
                if random.random() < 0.03:
                    add_log_mark(p.pos, "toxin", 0.7, 0.04)

    def curious_scan(self, cell, foods, toxins, repairs, dt):
        self.ritual_angle += dt * 1.4
        scan_dir = vector(math.cos(self.ritual_angle), 0.25 * math.sin(self.ritual_angle * 0.7), math.sin(self.ritual_angle))
        cell.forward = norm_safe(lerp(cell.forward, scan_dir, 0.06))
        cell.apply_force(scan_dir * 0.006, max_speed=0.13)

        if random.random() < 0.075:
            pos = cell.pos + scan_dir * random.uniform(cell.radius * 1.2, cell.radius * 2.2)
            add_log_mark(pos, "scan", 1.4, 0.045, direction=scan_dir * 0.035)

        # Mark nearest object type.
        all_particles = [p for p in foods + toxins + repairs if not p.dead]
        if all_particles and random.random() < 0.03:
            p = min(all_particles, key=lambda q: mag(q.pos - cell.pos))
            kind = p.kind if p.kind in ("food", "toxin", "repair") else "scan"
            add_log_mark(p.pos, kind, 1.2, 0.075)

    def ritual_orbit(self, cell, dt):
        self.ritual_angle += dt * 0.9
        center = vector(0, 0, 0)
        radial = norm_safe(cell.pos - center)
        if mag(radial) < 0.1:
            radial = vector(1, 0, 0)
        tangent = cross(vector(0, 1, 0), radial)
        if mag(tangent) < 0.01:
            tangent = vector(0, 0, 1)
        desired = norm_safe(tangent + 0.16 * norm_safe(center - cell.pos))
        cell.apply_force(desired * 0.019, max_speed=0.18)
        cell.forward = norm_safe(lerp(cell.forward, desired, 0.07))

        # Orbit nearby food in a ring around the cell before absorbing.
        for p in foods:
            if p.dead or mag(p.pos - cell.pos) > 3.2:
                continue
            local = p.pos - cell.pos
            tangent_food = cross(vector(0, 1, 0), norm_safe(local))
            p.vel += norm_safe(tangent_food) * 0.018 + norm_safe(cell.pos - p.pos) * 0.006

        if random.random() < 0.055:
            add_log_mark(cell.pos + rand_unit() * cell.radius * 1.6, "scan", 1.0, 0.05)

    def chaotic_spill(self, cell, foods, toxins):
        self.wander(cell, DT)
        if self.chaos_cooldown <= 0:
            if len([p for p in foods if not p.dead]) < FOOD_COUNT * 1.3:
                spill_food(cell.pos + rand_unit() * 1.6, count=random.randint(4, 8))
            if random.random() < 0.35 and len([p for p in toxins if not p.dead]) < TOXIN_COUNT * 1.4:
                spill_toxins(cell.pos + rand_unit() * 2.5, count=random.randint(1, 3))
            cell.pulse = 1.0
            self.chaos_cooldown = random.uniform(1.4, 2.8)

    def constructive_garden(self, cell, foods, toxins):
        # Pull food inward and push toxins outward to create a visible "safe garden".
        self.attract_food_cloud(cell, foods, strength=0.012, radius=5.4)
        self.push_toxins_away(cell, toxins, strength=0.018, radius=5.2)

        if random.random() < 0.018:
            spill_food(cell.pos + rand_unit() * random.uniform(2.2, 3.2), count=1)

        # Move slowly around the food cluster.
        live_foods = [p for p in foods if not p.dead]
        if live_foods:
            avg = vector(0, 0, 0)
            near = 0
            for p in live_foods:
                if mag(p.pos - cell.pos) < 6.0:
                    avg += p.pos
                    near += 1
            if near > 0:
                avg /= near
                self.steer_toward(cell, avg, 0.012, 0.12)
            else:
                self.wander(cell, DT)
        else:
            self.wander(cell, DT)

    def careful_rest(self, cell, repairs, toxins):
        # Slow movement, repair, hold distance from toxins.
        cell.vel *= 0.965
        if cell.health < 100 and cell.energy > 20:
            cell.repair_damage(0.006)
            cell.energy -= 0.018

        nearest_toxin = min([p for p in toxins if not p.dead], key=lambda p: mag(p.pos - cell.pos), default=None)
        if nearest_toxin and mag(nearest_toxin.pos - cell.pos) < 3.6:
            self.steer_away(cell, nearest_toxin.pos, 0.025)

        for p in repairs:
            if not p.dead and mag(p.pos - cell.pos) < 4:
                p.vel += norm_safe(cell.pos - p.pos) * 0.006

# ------------------------------------------------------------
# World state
# ------------------------------------------------------------

foods = []
toxins = []
repairs = []
marks = []
waste = []
daughters = []
cell = None
ai = CellAIController()
paused = False
manual_force = vector(0, 0, 0)
round_number = 0

status_label = label(
    pos=vector(-WORLD_RADIUS, WORLD_RADIUS + 0.9, 0),
    text="",
    height=13,
    box=False,
    opacity=0,
    color=vector(0.12, 0.18, 0.28),
)

mode_label = label(
    pos=vector(0, WORLD_RADIUS + 0.9, 0),
    text="",
    height=14,
    box=False,
    opacity=0,
    color=vector(0.10, 0.18, 0.35),
)

def add_log_mark(pos, kind="spark", life=1.4, radius=0.06, direction=None):
    global marks
    mark = TemporaryMark(pos, kind=kind, life=life, radius=radius, direction=direction)
    marks.append(mark)
    if len(marks) > MAX_MARKS:
        old = marks.pop(0)
        old.obj.visible = False

def clear_marks():
    global marks, waste
    for m in marks:
        m.obj.visible = False
    marks = []
    for w in waste:
        w.obj.visible = False
    waste = []

def spill_food(origin, count=8):
    for _ in range(count):
        p = WorldParticle("food", pos=origin + rand_vec(0.6), velocity=rand_vec(0.08))
        foods.append(p)
        add_log_mark(p.pos, "food", 0.9, 0.045)

def spill_toxins(origin, count=5):
    for _ in range(count):
        p = WorldParticle("toxin", pos=origin + rand_vec(0.8), velocity=rand_vec(0.08))
        toxins.append(p)
        add_log_mark(p.pos, "toxin", 1.0, 0.045)

def spill_waste(origin, count=5):
    global waste
    for _ in range(count):
        p = WorldParticle("waste", pos=origin + rand_vec(0.3), velocity=rand_vec(0.08))
        p.obj.color = COL_WASTE
        p.obj.opacity = 0.38
        p.obj.radius = random.uniform(0.035, 0.075)
        p.life = random.uniform(2.0, 4.0)
        waste.append(p)
    while len(waste) > MAX_WASTE:
        old = waste.pop(0)
        old.hide()

def perform_division():
    global daughters
    if cell and cell.can_divide():
        daughter = cell.divide()
        daughters.append(daughter)
        add_log_mark(cell.pos, "division", 2.0, 0.18)
        for _ in range(24):
            add_log_mark(cell.pos + rand_vec(cell.radius * 1.4), "division", 1.6, random.uniform(0.035, 0.08), direction=rand_vec(0.08))
        print("Cell divided. Daughter cells:", len(daughters))

def reset_world(reason="manual reset"):
    global foods, toxins, repairs, marks, waste, daughters, cell, round_number

    round_number += 1
    print(f"Reset round {round_number}: {reason}")

    # Hide old objects.
    for p in foods + toxins + repairs + waste:
        p.hide()
    for m in marks:
        m.obj.visible = False
    for d in daughters:
        d.hide()
    if cell is not None:
        cell.hide()

    foods = []
    toxins = []
    repairs = []
    marks = []
    waste = []
    daughters = []

    cell = Cell(pos=rand_vec(0.5), name=f"Cell R{round_number}", primary=True)

    for _ in range(FOOD_COUNT):
        foods.append(WorldParticle("food"))
    for _ in range(TOXIN_COUNT):
        toxins.append(WorldParticle("toxin"))
    for _ in range(REPAIR_COUNT):
        repairs.append(WorldParticle("repair"))

    # Add a few nutrient-rich and toxin-rich regions so the AI has choices.
    for _ in range(18):
        cluster = vector(random.choice([-1, 1]) * random.uniform(3.0, 7.0), random.uniform(-1.5, 2.2), random.uniform(-7.0, 7.0))
        foods.append(WorldParticle("food", pos=cluster + rand_vec(1.0), velocity=rand_vec(0.035)))

    for _ in range(8):
        cluster = vector(random.uniform(-6.5, 6.5), random.uniform(-2.0, 2.5), random.choice([-1, 1]) * random.uniform(4.0, 8.0))
        toxins.append(WorldParticle("toxin", pos=cluster + rand_vec(0.9), velocity=rand_vec(0.04)))

    ai.mode_timer = 0
    ai.stagnation_timer = 0
    ai.completion_timer = 0
    ai.round_timer = 0
    ai.last_progress_value = 0
    ai.set_mode("forage")

    for _ in range(18):
        add_log_mark(cell.pos + rand_vec(1.2), "scan", 1.4, 0.05)

# ------------------------------------------------------------
# Interaction and physics
# ------------------------------------------------------------

def update_particles(dt):
    for p in foods + toxins + repairs:
        if not p.dead:
            p.update_free_motion(dt)

    for p in list(waste):
        if p.dead:
            continue
        p.age += dt
        p.life -= dt
        p.vel += rand_vec(0.002)
        p.vel *= 0.97
        p.pos += p.vel
        p.obj.pos = p.pos
        p.obj.opacity = max(0, 0.38 * p.life / 4.0)
        if p.life <= 0:
            p.hide()

def update_collisions(dt):
    # Food can attach to membrane briefly, then absorb.
    for p in foods:
        if p.dead:
            continue

        d = mag(p.pos - cell.pos)
        attach_dist = cell.radius + p.radius + 0.08

        if not p.attached and d < attach_dist:
            p.attached = True
            p.attached_time = 0.0
            p.attachment_offset = norm_safe(p.pos - cell.pos) * (cell.radius + p.radius * 0.55)
            p.vel = vector(0, 0, 0)
            add_log_mark(p.pos, "food", 1.0, 0.06)

        if p.attached:
            p.attached_time += dt
            swirl = vector(
                math.sin(p.attached_time * 6 + p.orbit_phase),
                math.cos(p.attached_time * 4 + p.orbit_phase) * 0.4,
                math.cos(p.attached_time * 5 + p.orbit_phase),
            ) * 0.03
            p.pos = cell.pos + p.attachment_offset + swirl
            p.update_visual()

            if p.attached_time > 0.5:
                cell.absorb_food(p)
                spill_waste(cell.pos - cell.forward * cell.radius, count=2)
                add_log_mark(p.pos, "food", 1.2, 0.10)
                p.hide()

    # Toxins collide and damage; AI/human can push them.
    for p in toxins:
        if p.dead:
            continue

        d = mag(p.pos - cell.pos)
        if d < cell.radius + p.radius:
            cell.toxin_hit(p)
            add_log_mark(p.pos, "toxin", 1.5, 0.13)
            p.vel = norm_safe(p.pos - cell.pos) * random.uniform(0.09, 0.16)
            p.pos = cell.pos + norm_safe(p.pos - cell.pos) * (cell.radius + p.radius + 0.08)

    # Repair particles physically attach/detach around membrane.
    for p in repairs:
        if p.dead:
            continue
        d = mag(p.pos - cell.pos)
        if d < cell.radius * 1.15 + p.radius and (cell.health < 98 or len(cell.damage_patches) > 0):
            cell.repair_damage(0.05)
            p.hide()
            add_log_mark(p.pos, "repair", 1.4, 0.09)
        elif d < cell.radius * 1.7 + p.radius:
            tangent = cross(norm_safe(p.pos - cell.pos), vector(0, 1, 0))
            p.vel += norm_safe(tangent) * 0.01 + norm_safe(cell.pos - p.pos) * 0.004

def update_daughters(dt):
    for d in daughters:
        d.update(dt)
        # Daughters are semi-autonomous simple wanderers.
        if random.random() < 0.02:
            d.apply_force(rand_unit() * 0.025, max_speed=0.13)

        # Daughter cells can absorb food too, but do not control main AI.
        for p in foods:
            if p.dead:
                continue
            if mag(p.pos - d.pos) < d.radius + p.radius:
                d.absorb_food(p)
                p.hide()
                add_log_mark(p.pos, "food", 1.0, 0.07)

        for p in toxins:
            if p.dead:
                continue
            if mag(p.pos - d.pos) < d.radius + p.radius:
                d.toxin_hit(p)
                p.vel = norm_safe(p.pos - d.pos) * 0.11

def update_marks(dt):
    global marks
    marks = [m for m in marks if m.update(dt)]

def update_status():
    live_food = len([p for p in foods if not p.dead])
    live_toxin = len([p for p in toxins if not p.dead])
    live_repair = len([p for p in repairs if not p.dead])
    status_label.text = (
        f"Round {round_number} | food {live_food} | toxins {live_toxin} | repair {live_repair} | "
        f"daughters {len(daughters)}"
    )
    mode_label.text = (
        f"AI {'ON' if ai.enabled else 'OFF'} | mode: {ai.mode} | "
        f"{'PAUSED' if paused else 'running'}"
    )

def emergency_override():
    # Human override that works whether AI is on or off.
    ai.override_timer = 2.5
    cell.energy = clamp(cell.energy + 8, 0, 130)
    cell.repair_damage(0.12)
    cell.pulse = 1.2
    for p in foods:
        if not p.dead and mag(p.pos - cell.pos) < 6:
            p.vel += norm_safe(cell.pos - p.pos) * 0.035
    for p in toxins:
        if not p.dead and mag(p.pos - cell.pos) < 5:
            p.vel += norm_safe(p.pos - cell.pos) * 0.045
    for _ in range(22):
        add_log_mark(cell.pos + rand_vec(cell.radius * 1.5), "repair", 1.3, 0.06, direction=rand_vec(0.07))

def print_controls():
    print(__doc__)

# ------------------------------------------------------------
# Keyboard input
# ------------------------------------------------------------

keys_down = set()

def keydown(evt):
    global paused, manual_force
    k = evt.key.lower()
    keys_down.add(k)

    if k == "a":
        ai.enabled = not ai.enabled
        print("AI enabled:", ai.enabled)
    elif k == "p":
        paused = not paused
        print("Paused:", paused)
    elif k == "r":
        reset_world(reason="manual reset")
    elif k == "m":
        ai.cycle_mode()
    elif k == "o":
        emergency_override()
    elif k == "c":
        clear_marks()
    elif k == "f":
        spill_food(cell.pos + cell.forward * 1.5, count=10)
    elif k == "t":
        spill_toxins(cell.pos + cell.forward * 2.0, count=6)
    elif k == "h":
        print_controls()
    elif k == " ":
        cell.apply_force(cell.forward * 0.12, max_speed=0.24)

def keyup(evt):
    k = evt.key.lower()
    if k in keys_down:
        keys_down.remove(k)

scene.bind("keydown", keydown)
scene.bind("keyup", keyup)

def update_manual_control():
    # Manual control runs alongside AI. Human input adds force and can override direction.
    force = vector(0, 0, 0)
    if "w" in keys_down or "up" in keys_down:
        force += vector(0, 0, -1)
    if "s" in keys_down or "down" in keys_down:
        force += vector(0, 0, 1)
    if "a" in keys_down or "left" in keys_down:
        # A is also toggle on keydown; holding it still steers left after the toggle.
        force += vector(-1, 0, 0)
    if "d" in keys_down or "right" in keys_down:
        force += vector(1, 0, 0)
    if "q" in keys_down:
        cell.rotate_forward(-0.045)
    if "e" in keys_down:
        cell.rotate_forward(0.045)

    if mag(force) > 0:
        cell.apply_force(norm(force) * 0.038, max_speed=0.24)
        cell.forward = norm_safe(lerp(cell.forward, norm(force), 0.12))

# ------------------------------------------------------------
# Main loop
# ------------------------------------------------------------

reset_world(reason="initial world")
print_controls()

while True:
    rate(45)

    if paused:
        update_status()
        continue

    update_manual_control()

    ai.update(DT, cell, foods, toxins, repairs, daughters)

    # Cell survival and dynamics.
    cell.update(DT)

    update_particles(DT)
    update_collisions(DT)
    update_daughters(DT)
    update_marks(DT)

    # Automatic division check even if AI is off.
    if cell.can_divide():
        perform_division()

    # If the cell dies while AI is disabled, still make the world loop after a short pause.
    if cell.health <= 0 or cell.energy <= 0:
        for _ in range(8):
            add_log_mark(cell.pos + rand_vec(cell.radius * 1.3), "toxin", 1.2, 0.07)
        reset_world(reason="cell failed survival")

    update_status()
