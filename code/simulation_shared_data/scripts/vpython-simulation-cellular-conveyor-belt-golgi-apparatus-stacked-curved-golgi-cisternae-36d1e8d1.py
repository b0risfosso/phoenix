from vpython import *
import random
import math
import time

# ============================================================
# Cellular Conveyor Belt: Golgi Apparatus
# VPython 3D simulation with expressive AI controller
# ============================================================

scene = canvas(
    title="Cellular Conveyor Belt: Golgi Apparatus",
    width=1280,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0.2, 0),
)
scene.forward = vector(-7.5, -3.0, -6.5)
scene.up = vector(0, 1, 0)
scene.range = 7.3
scene.ambient = color.gray(0.72)

local_light(pos=vector(-4, 6, 4), color=vector(0.75, 0.75, 0.75))
local_light(pos=vector(4, 5, -3), color=vector(0.45, 0.55, 0.65))

scene.append_to_caption(
    "\nControls: SPACE pause/resume | A toggle AI | E human override | M next AI mode | "
    "R reset | S spawn | B burst | N select vesicle | D force detach selected | "
    "Arrow keys / IJKL nudge selected | C orbit camera\n\n"
)

# ----------------------------
# Global simulation constants
# ----------------------------

NUM_CISTERNAE = 6
MEMBRANE_X = 5.55
VESICLE_LIMIT = 42
ROUND_GOAL = 22

vesicles = []
particles = []
membrane_marks = []
cisternae = []

paused = False
orbit_camera = False
sim_time = 0.0
round_number = 1
delivered_round = 0
total_delivered = 0
manual_selected_index = 0
flow_speed = 1.0
human_override = False

last_status_update = 0
last_spawn_time = 0

# ----------------------------
# Utility functions
# ----------------------------

def clamp(x, a, b):
    return max(a, min(b, x))

def mag2(v):
    return v.x * v.x + v.y * v.y + v.z * v.z

def safe_norm(v):
    if mag(v) < 1e-8:
        return vector(0, 0, 0)
    return norm(v)

def lerp(a, b, t):
    return a * (1 - t) + b * t

def color_lerp(c1, c2, t):
    return vector(
        c1.x * (1 - t) + c2.x * t,
        c1.y * (1 - t) + c2.y * t,
        c1.z * (1 - t) + c2.z * t,
    )

def random_unit_vector():
    theta = random.uniform(0, 2 * math.pi)
    z = random.uniform(-0.7, 0.7)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(theta), z, r * math.sin(theta))

def mature_color(progress):
    palette = [
        vector(0.25, 0.65, 1.00),  # cis: blue
        vector(0.20, 0.92, 0.75),  # turquoise
        vector(0.40, 0.92, 0.35),  # green
        vector(1.00, 0.84, 0.25),  # yellow
        vector(1.00, 0.50, 0.20),  # orange
        vector(1.00, 0.28, 0.55),  # trans: magenta
        vector(0.72, 0.38, 1.00),  # secretory purple
    ]
    progress = clamp(progress, 0, 1)
    scaled = progress * (len(palette) - 1)
    i = int(math.floor(scaled))
    if i >= len(palette) - 1:
        return palette[-1]
    return color_lerp(palette[i], palette[i + 1], scaled - i)

def hue_color(h):
    return color.hsv_to_rgb(vector(h % 1.0, 0.72, 1.0))

# ----------------------------
# Stationary scene objects
# ----------------------------

floor = box(
    pos=vector(0, -3.55, 0),
    size=vector(12.5, 0.035, 7.6),
    color=vector(0.88, 0.93, 0.96),
    opacity=0.38,
)

membrane = box(
    pos=vector(MEMBRANE_X, 0, 0),
    size=vector(0.12, 7.2, 5.4),
    color=vector(0.52, 0.78, 1.0),
    opacity=0.20,
)

membrane_label = label(
    pos=vector(MEMBRANE_X + 0.13, 3.75, 0),
    text="Cell membrane / delivery zone",
    height=14,
    box=False,
    color=vector(0.22, 0.36, 0.45),
)

cis_label = label(
    pos=vector(-3.65, -2.95, 0.25),
    text="cis face: vesicles attach",
    height=13,
    box=False,
    color=vector(0.15, 0.35, 0.55),
)

trans_label = label(
    pos=vector(3.25, 2.95, 0.25),
    text="trans face: mature vesicles detach",
    height=13,
    box=False,
    color=vector(0.55, 0.2, 0.38),
)

status_label = label(
    pos=vector(0, 4.05, 0),
    text="",
    height=14,
    box=True,
    border=7,
    color=vector(0.12, 0.18, 0.22),
    background=vector(0.96, 0.99, 1.0),
    opacity=0.72,
)

selector_ring = ring(
    pos=vector(0, -20, 0),
    axis=vector(0, 1, 0),
    radius=0.34,
    thickness=0.018,
    color=vector(0.1, 0.2, 0.3),
    opacity=0.85,
)

# Membrane receptors
receptors = []
for i in range(18):
    y = random.uniform(-2.8, 2.8)
    z = random.uniform(-2.15, 2.15)
    rec = ring(
        pos=vector(MEMBRANE_X - 0.09, y, z),
        axis=vector(1, 0, 0),
        radius=random.uniform(0.11, 0.18),
        thickness=0.015,
        color=vector(0.25, 0.58, 0.9),
        opacity=0.50,
    )
    receptors.append(rec)

# ----------------------------
# Golgi cisternae
# ----------------------------

class Cisterna:
    def __init__(self, index, y, base_color):
        self.index = index
        self.y = y
        self.base_color = base_color
        self.objects = []
        self.width = 0.95 + 0.08 * math.sin(index)
        self.thickness = 0.065
        self.a = 2.75 - 0.08 * index
        self.b = 0.72 + 0.035 * index
        self.xoff = -0.18 + 0.06 * math.sin(index * 0.8)
        self.zoff = 0.04 * math.cos(index)
        self.glow_phase = random.uniform(0, 2 * math.pi)

        segments = 36
        for j in range(segments):
            s = (j + 0.5) / segments
            p = self.path(s)
            tangent = self.tangent(s)
            seg_len = 0.26
            plate = box(
                pos=p,
                axis=tangent,
                size=vector(seg_len, self.thickness, self.width),
                color=base_color,
                opacity=0.28,
            )
            self.objects.append(plate)

        # Soft rim curves to emphasize the curved cisternal plate.
        for side in [-1, 1]:
            pts = []
            for j in range(60):
                s = j / 59
                tangent = self.tangent(s)
                normal_xz = safe_norm(cross(vector(0, 1, 0), tangent))
                pts.append(self.path(s) + normal_xz * side * self.width * 0.53)
            rim = curve(
                pos=pts,
                radius=0.018,
                color=color_lerp(base_color, vector(1, 1, 1), 0.22),
                opacity=0.52,
            )
            self.objects.append(rim)

        # Docking beads at cis and trans ends.
        self.cis_port = sphere(
            pos=self.surface_point(0.0) + vector(-0.13, 0.0, 0),
            radius=0.085,
            color=vector(0.34, 0.68, 1.0),
            opacity=0.75,
        )
        self.trans_port = sphere(
            pos=self.surface_point(1.0) + vector(0.13, 0.0, 0),
            radius=0.085,
            color=vector(1.0, 0.45, 0.62),
            opacity=0.75,
        )
        self.objects.append(self.cis_port)
        self.objects.append(self.trans_port)

    def path(self, s):
        s = clamp(s, 0, 1)
        theta = math.pi * (1 - s)
        x = self.xoff + self.a * math.cos(theta)
        z = self.zoff + self.b * math.sin(theta) + 0.10 * math.sin(2 * theta + self.index * 0.35)
        return vector(x, self.y, z)

    def tangent(self, s):
        s = clamp(s, 0, 1)
        theta = math.pi * (1 - s)
        dx = self.a * math.pi * math.sin(theta)
        dz = -self.b * math.pi * math.cos(theta) - 0.20 * math.pi * math.cos(2 * theta + self.index * 0.35)
        return safe_norm(vector(dx, 0, dz))

    def surface_point(self, s, lift=0.22, side_wobble=0.0):
        tangent = self.tangent(s)
        normal_xz = safe_norm(cross(vector(0, 1, 0), tangent))
        return self.path(s) + vector(0, lift, 0) + normal_xz * side_wobble

    def pulse(self, amount):
        for obj in self.objects:
            if hasattr(obj, "opacity"):
                obj.opacity = clamp(0.22 + amount, 0.15, 0.55)

    def restore_opacity(self):
        for obj in self.objects:
            if hasattr(obj, "opacity"):
                if isinstance(obj, box):
                    obj.opacity = 0.28
                else:
                    obj.opacity = 0.52

cisterna_colors = [
    vector(0.62, 0.85, 1.0),
    vector(0.57, 0.92, 0.92),
    vector(0.66, 0.95, 0.72),
    vector(1.00, 0.92, 0.58),
    vector(1.00, 0.74, 0.55),
    vector(1.00, 0.62, 0.78),
]

for i in range(NUM_CISTERNAE):
    y = -2.35 + i * 0.88
    cisternae.append(Cisterna(i, y, cisterna_colors[i]))

# ----------------------------
# Particles, marks, vesicles
# ----------------------------

class Particle:
    def __init__(self, pos, vel, col, radius=0.035, life=1.2, opacity=0.75):
        self.life = life
        self.max_life = life
        self.vel = vel
        self.obj = sphere(
            pos=pos,
            radius=radius,
            color=col,
            opacity=opacity,
            emissive=False,
        )

    def update(self, dt):
        self.life -= dt
        self.vel *= 0.985
        self.obj.pos += self.vel * dt
        self.obj.opacity = clamp(0.75 * self.life / self.max_life, 0, 0.75)
        self.obj.radius *= 0.997
        if self.life <= 0:
            self.obj.visible = False
            return False
        return True

def spill_particles(pos, col, count=10, speed=0.8, life=1.1):
    for _ in range(count):
        if len(particles) > 280:
            break
        v = random_unit_vector() * random.uniform(0.15, speed)
        particles.append(Particle(pos, v, col, radius=random.uniform(0.018, 0.045), life=random.uniform(0.55, life)))

def create_membrane_mark(pos, col):
    if len(membrane_marks) > 90:
        old = membrane_marks.pop(0)
        old.visible = False
    mark = ring(
        pos=vector(MEMBRANE_X - 0.13, pos.y, pos.z),
        axis=vector(1, 0, 0),
        radius=random.uniform(0.12, 0.25),
        thickness=0.018,
        color=col,
        opacity=0.72,
    )
    membrane_marks.append(mark)

class Vesicle:
    next_id = 0

    def __init__(self, pos=None, artistic_hue=None):
        self.id = Vesicle.next_id
        Vesicle.next_id += 1

        if pos is None:
            pos = vector(
                -5.2 + random.uniform(-0.35, 0.15),
                cisternae[0].y + random.uniform(-0.24, 0.24),
                random.uniform(-0.75, 0.75),
            )

        self.radius = random.uniform(0.115, 0.165)
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vector(random.uniform(0.15, 0.45), random.uniform(-0.05, 0.05), random.uniform(-0.08, 0.08))
        self.state = "incoming"
        self.cis_index = 0
        self.s = 0.0
        self.orbit_phase = random.uniform(0, 2 * math.pi)
        self.age = 0.0
        self.stall_time = 0.0
        self.artistic_hue = artistic_hue
        self.target = cisternae[0].surface_point(0.0, lift=0.26) + vector(-0.25, random.uniform(-0.08, 0.12), random.uniform(-0.18, 0.18))
        self.mem_target = None
        self.just_changed = True

        col = mature_color(0)
        if artistic_hue is not None:
            col = hue_color(artistic_hue)

        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=col,
            opacity=0.88,
            shininess=0.7,
            make_trail=True,
            retain=85,
            trail_radius=0.014,
            trail_color=col,
        )

        self.cargo = sphere(
            pos=self.pos + vector(self.radius * 0.38, self.radius * 0.20, 0),
            radius=self.radius * 0.28,
            color=color_lerp(col, vector(1, 1, 1), 0.50),
            opacity=0.92,
        )

        self.halo = ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=self.radius * 1.45,
            thickness=0.012,
            color=vector(1.0, 1.0, 1.0),
            opacity=0.0,
            visible=True,
        )

        self.marker = sphere(
            pos=self.pos,
            radius=self.radius * 0.18,
            color=vector(1, 1, 1),
            opacity=0.0,
        )

    def progress(self):
        if self.state == "delivered":
            return NUM_CISTERNAE + 1
        if self.state == "outgoing":
            return NUM_CISTERNAE + 0.5
        return self.cis_index + clamp(self.s, 0, 1)

    def set_state(self, state):
        if self.state != state:
            self.just_changed = True
            self.stall_time = 0
            self.state = state

    def current_color(self):
        p = clamp((self.cis_index + self.s) / max(1, NUM_CISTERNAE - 1), 0, 1)
        col = mature_color(p)
        if self.artistic_hue is not None:
            tint = hue_color(self.artistic_hue + 0.23 * p)
            col = color_lerp(col, tint, 0.42)
        return col

    def attach_to_current(self):
        self.set_state("attached")
        self.s = 0.0
        self.vel = vector(0, 0, 0)
        self.halo.opacity = 0.62
        self.halo.color = color_lerp(self.current_color(), vector(1, 1, 1), 0.45)
        spill_particles(self.pos, self.current_color(), count=5, speed=0.25, life=0.65)

    def force_detach(self, strength=1.0):
        if self.state == "attached":
            self.set_state("transfer")
            self.halo.opacity = 0.0
            self.vel = (cisternae[self.cis_index].tangent(self.s) + random_unit_vector() * 0.45) * strength
        elif self.state in ["incoming", "transfer"]:
            self.vel += random_unit_vector() * strength
        elif self.state == "outgoing":
            self.vel += vector(1, 0, 0) * strength + random_unit_vector() * strength * 0.35
        spill_particles(self.pos, vector(1, 0.6, 0.3), count=6, speed=0.5, life=0.8)

    def choose_membrane_target(self):
        rec = random.choice(receptors)
        self.mem_target = rec.pos + vector(-0.05, random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08))

    def update_visuals(self):
        col = self.current_color()
        self.body.color = col
        self.cargo.color = color_lerp(col, vector(1, 1, 1), 0.52)
        self.cargo.pos = self.body.pos + vector(
            self.radius * 0.34 * math.cos(self.age * 3.0),
            self.radius * 0.28 * math.sin(self.age * 2.3),
            self.radius * 0.31 * math.sin(self.age * 2.0),
        )
        self.halo.pos = self.body.pos
        self.halo.axis = vector(0.2 * math.sin(self.age * 1.7), 1, 0.2 * math.cos(self.age * 1.5))
        self.marker.pos = self.body.pos + vector(0, self.radius * 1.2, 0)

    def seek(self, target, speed, dt, agility=4.0):
        to_target = target - self.pos
        dist = mag(to_target)
        if dist > 1e-5:
            desired = norm(to_target) * speed
            self.vel = lerp(self.vel, desired, clamp(agility * dt, 0, 1))
        self.pos += self.vel * dt
        return dist

    def update(self, dt):
        self.age += dt
        old_progress = self.progress()
        self.orbit_phase += dt * (4.5 + self.cis_index * 0.5)

        if self.state == "incoming":
            self.halo.opacity = 0.0
            d = self.seek(self.target, speed=1.10 * flow_speed, dt=dt, agility=3.2)
            self.pos += vector(0, math.sin(self.age * 4.0 + self.id) * 0.004, math.cos(self.age * 3.2) * 0.004)
            if d < 0.18:
                self.attach_to_current()

        elif self.state == "attached":
            c = cisternae[self.cis_index]
            local_speed = (0.135 + 0.025 * self.cis_index) * flow_speed
            self.s += dt * local_speed

            dip = -0.055 * max(0, math.sin(self.s * math.pi * 2.0 + self.orbit_phase * 0.35))
            wobble = 0.16 * math.sin(self.orbit_phase)
            lift = 0.25 + 0.055 * math.cos(self.orbit_phase * 1.2) + dip
            self.pos = c.surface_point(self.s, lift=lift, side_wobble=wobble)

            self.halo.opacity = 0.60 + 0.18 * math.sin(self.age * 8.0)
            self.halo.radius = self.radius * (1.45 + 0.12 * math.sin(self.age * 7.0))

            if random.random() < 0.012 * flow_speed:
                spill_particles(self.pos, self.current_color(), count=1, speed=0.18, life=0.55)

            if self.s >= 1.0:
                self.halo.opacity = 0.0
                if self.cis_index < NUM_CISTERNAE - 1:
                    self.cis_index += 1
                    self.s = 0.0
                    self.target = cisternae[self.cis_index].surface_point(0.0, lift=0.27) + vector(-0.20, random.uniform(-0.05, 0.08), random.uniform(-0.16, 0.16))
                    self.vel = vector(0.50, 0.30, random.uniform(-0.10, 0.10))
                    self.set_state("transfer")
                    spill_particles(self.pos, self.current_color(), count=7, speed=0.35, life=0.75)
                else:
                    self.choose_membrane_target()
                    self.vel = vector(1.8, random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15))
                    self.set_state("outgoing")
                    spill_particles(self.pos, self.current_color(), count=9, speed=0.50, life=0.85)

        elif self.state == "transfer":
            self.halo.opacity = 0.0
            d = self.seek(self.target, speed=1.28 * flow_speed, dt=dt, agility=3.6)
            self.pos += random_unit_vector() * 0.006
            if d < 0.18:
                self.attach_to_current()

        elif self.state == "outgoing":
            self.halo.opacity = 0.0
            if self.mem_target is None:
                self.choose_membrane_target()
            d = self.seek(self.mem_target, speed=2.15 * flow_speed, dt=dt, agility=4.8)
            if random.random() < 0.020:
                spill_particles(self.pos, self.current_color(), count=1, speed=0.22, life=0.45)
            if self.pos.x >= MEMBRANE_X - 0.22 or d < 0.16:
                self.deliver()
                return False

        self.body.pos = self.pos
        self.update_visuals()

        if abs(self.progress() - old_progress) < 0.0003:
            self.stall_time += dt
        else:
            self.stall_time = 0

        return True

    def deliver(self):
        global delivered_round, total_delivered
        self.set_state("delivered")
        delivered_round += 1
        total_delivered += 1
        col = self.current_color()
        create_membrane_mark(self.pos, col)
        spill_particles(self.pos, col, count=18, speed=0.95, life=1.35)
        self.visible_off()

    def visible_off(self):
        self.body.visible = False
        self.cargo.visible = False
        self.halo.visible = False
        self.marker.visible = False
        try:
            self.body.clear_trail()
        except Exception:
            pass

# ----------------------------
# Spawning and reset
# ----------------------------

def spawn_vesicle(pos=None, artistic_hue=None):
    global last_spawn_time
    if len(vesicles) >= VESICLE_LIMIT:
        return None
    v = Vesicle(pos=pos, artistic_hue=artistic_hue)
    vesicles.append(v)
    last_spawn_time = sim_time
    return v

def spawn_burst(count=5, artistic=False):
    for i in range(count):
        hue = None
        if artistic:
            hue = (sim_time * 0.055 + i / max(1, count)) % 1.0
        pos = vector(
            -5.4 + random.uniform(-0.28, 0.18),
            cisternae[0].y + random.uniform(-0.38, 0.38),
            random.uniform(-1.0, 1.0),
        )
        spawn_vesicle(pos=pos, artistic_hue=hue)

def clear_dynamic_objects():
    global vesicles, particles, membrane_marks
    for v in vesicles:
        v.visible_off()
    vesicles = []

    for p in particles:
        p.obj.visible = False
    particles = []

    for m in membrane_marks:
        m.visible = False
    membrane_marks = []

def reset_simulation(spawn_initial=True, new_round=True):
    global delivered_round, round_number, flow_speed, manual_selected_index
    clear_dynamic_objects()
    delivered_round = 0
    manual_selected_index = 0
    flow_speed = 1.0
    if new_round:
        round_number += 1
    for c in cisternae:
        c.restore_opacity()
    if spawn_initial:
        spawn_burst(5, artistic=False)

# ----------------------------
# AI controller
# ----------------------------

class AIController:
    def __init__(self):
        self.enabled = True
        self.mode_names = [
            "careful",
            "constructive",
            "organize",
            "curious",
            "ritual",
            "artistic",
            "chaotic",
            "destructive",
        ]
        self.mode = "constructive"
        self.previous_mode = None
        self.mode_started = 0.0
        self.next_switch = 10.0
        self.last_metric = 0.0
        self.last_change_time = 0.0
        self.completion_time = None
        self.stagnation_time = 0.0
        self.pulse_timer = 0.0
        self.action_timer = 0.0
        self.override_until = 0.0
        self.loop_delay = 2.5
        self.rounds_started_by_ai = 0

        self.drone = sphere(
            pos=vector(-4.6, 3.35, 0),
            radius=0.15,
            color=vector(0.84, 0.38, 1.0),
            emissive=True,
            make_trail=True,
            retain=140,
            trail_radius=0.012,
            trail_color=vector(0.7, 0.4, 1.0),
        )
        self.drone_ring = ring(
            pos=self.drone.pos,
            axis=vector(0, 1, 0),
            radius=0.27,
            thickness=0.015,
            color=vector(0.84, 0.38, 1.0),
            opacity=0.75,
        )
        self.mode_label = label(
            pos=self.drone.pos + vector(0, 0.45, 0),
            text="AI: constructive",
            height=12,
            box=False,
            color=vector(0.35, 0.18, 0.45),
        )

    def read_state(self):
        active = [v for v in vesicles if v.state != "delivered"]
        attached = [v for v in active if v.state == "attached"]
        free = [v for v in active if v.state in ["incoming", "transfer", "outgoing"]]
        outgoing = [v for v in active if v.state == "outgoing"]
        stalled = [v for v in active if v.stall_time > 5.0]
        progress_metric = sum(v.progress() for v in active) + delivered_round * (NUM_CISTERNAE + 2)
        avg_progress = sum(v.progress() for v in active) / max(1, len(active))
        return {
            "active": active,
            "attached": attached,
            "free": free,
            "outgoing": outgoing,
            "stalled": stalled,
            "count": len(active),
            "attached_count": len(attached),
            "free_count": len(free),
            "outgoing_count": len(outgoing),
            "delivered_round": delivered_round,
            "progress_metric": progress_metric,
            "avg_progress": avg_progress,
        }

    def detect_stagnation_or_completion(self, state, dt):
        metric = state["progress_metric"]
        if abs(metric - self.last_metric) > 0.03 or state["count"] != 0:
            if abs(metric - self.last_metric) > 0.03:
                self.last_change_time = sim_time
            self.last_metric = metric

        no_active = state["count"] == 0
        complete = delivered_round >= ROUND_GOAL and no_active
        empty = no_active and sim_time - last_spawn_time > 2.5

        if complete:
            if self.completion_time is None:
                self.completion_time = sim_time
            return "complete"

        if empty:
            if self.completion_time is None:
                self.completion_time = sim_time
            return "empty"

        self.completion_time = None

        if sim_time - self.last_change_time > 13.0 and sim_time > 5.0:
            self.stagnation_time += dt
            if self.stagnation_time > 2.0:
                return "stagnant"
        else:
            self.stagnation_time = 0.0

        return "moving"

    def choose_new_mode(self, reason="timer"):
        candidates = self.mode_names[:]
        if self.mode in candidates and len(candidates) > 1:
            candidates.remove(self.mode)

        if reason == "empty":
            preferred = ["constructive", "ritual", "artistic"]
        elif reason == "stagnant":
            preferred = ["chaotic", "curious", "destructive", "constructive"]
        elif delivered_round > ROUND_GOAL * 0.65:
            preferred = ["artistic", "ritual", "organize"]
        else:
            preferred = candidates

        choices = [m for m in preferred if m != self.mode]
        if not choices:
            choices = candidates

        self.previous_mode = self.mode
        self.mode = random.choice(choices)
        self.mode_started = sim_time
        self.next_switch = random.uniform(8.0, 18.0)
        self.pulse_timer = 0
        self.action_timer = 0
        self.mode_label.text = "AI: " + self.mode

    def next_mode_manual(self):
        idx = self.mode_names.index(self.mode)
        self.previous_mode = self.mode
        self.mode = self.mode_names[(idx + 1) % len(self.mode_names)]
        self.mode_started = sim_time
        self.next_switch = random.uniform(9.0, 16.0)
        self.mode_label.text = "AI: " + self.mode

    def update_drone(self, dt, state):
        if not self.enabled:
            target = vector(-5.0, 3.35, -1.7)
            self.drone.color = vector(0.55, 0.55, 0.60)
            self.drone_ring.color = self.drone.color
            self.mode_label.text = "AI: off"
        elif human_override or sim_time < self.override_until:
            target = vector(-4.5, 3.35, 1.8)
            self.drone.color = vector(1.0, 0.76, 0.20)
            self.drone_ring.color = self.drone.color
            self.mode_label.text = "AI: human override"
        else:
            self.drone.color = {
                "careful": vector(0.28, 0.65, 1.0),
                "constructive": vector(0.25, 0.95, 0.55),
                "organize": vector(0.45, 0.72, 1.0),
                "curious": vector(0.80, 0.45, 1.0),
                "ritual": vector(0.65, 0.42, 1.0),
                "artistic": vector(1.0, 0.32, 0.72),
                "chaotic": vector(1.0, 0.58, 0.15),
                "destructive": vector(1.0, 0.25, 0.18),
            }.get(self.mode, vector(0.8, 0.4, 1.0))
            self.drone_ring.color = self.drone.color
            self.mode_label.text = "AI: " + self.mode

            if self.mode == "curious" and state["active"]:
                target_v = min(state["active"], key=lambda v: v.progress())
                target = target_v.pos + vector(0, 0.55, 0)
            elif self.mode == "organize" and state["active"]:
                avg = vector(0, 0, 0)
                for v in state["active"]:
                    avg += v.pos
                avg /= len(state["active"])
                target = avg + vector(0, 0.85, 0)
            elif self.mode == "ritual":
                angle = sim_time * 0.9
                target = vector(0, 0.1, 0) + vector(3.7 * math.cos(angle), 3.1, 2.1 * math.sin(angle))
            elif self.mode == "artistic":
                angle = sim_time * 1.25
                target = vector(-0.4 + 3.9 * math.cos(angle), 2.7 + 0.45 * math.sin(angle * 0.7), 2.2 * math.sin(angle))
            elif self.mode == "chaotic":
                target = vector(random.uniform(-4.2, 4.8), random.uniform(-2.2, 3.4), random.uniform(-2.2, 2.2))
            elif self.mode == "destructive" and state["active"]:
                target = random.choice(state["active"]).pos + vector(0, 0.35, 0)
            else:
                angle = sim_time * 0.45
                target = vector(-2.6 + 1.0 * math.cos(angle), 3.25 + 0.15 * math.sin(angle), 1.5 * math.sin(angle))

        self.drone.pos = lerp(self.drone.pos, target, clamp(dt * 2.4, 0, 1))
        self.drone_ring.pos = self.drone.pos
        self.drone_ring.axis = vector(math.sin(sim_time * 2.2), 1, math.cos(sim_time * 2.0))
        self.mode_label.pos = self.drone.pos + vector(0, 0.42, 0)

    def organize_spacing(self, state, dt):
        active = state["active"]
        for v in active:
            if v.state == "attached":
                desired_z = 0.14 * math.sin(v.cis_index * 1.3 + v.id)
                v.pos.z = lerp(v.pos.z, desired_z, dt * 0.5)
            elif v.state in ["incoming", "transfer"]:
                lane_z = ((v.id % 5) - 2) * 0.22
                v.vel.z += (lane_z - v.pos.z) * dt * 0.8

    def nudge_stalled(self, state, strength=0.65):
        targets = state["stalled"] if state["stalled"] else state["active"]
        if not targets:
            return
        v = random.choice(targets)
        v.force_detach(strength)
        spill_particles(v.pos, self.drone.color, count=7, speed=0.55, life=0.9)

    def force_marking(self, state):
        if not state["active"]:
            return
        v = random.choice(state["active"])
        v.marker.opacity = 0.75
        v.marker.color = self.drone.color
        spill_particles(v.pos + vector(0, 0.25, 0), self.drone.color, count=4, speed=0.24, life=0.8)

    def actions_for_mode(self, state, dt):
        global flow_speed

        self.action_timer += dt
        self.pulse_timer += dt

        if self.mode == "careful":
            flow_speed = lerp(flow_speed, 0.75, dt * 0.8)
            if state["count"] < 5 and self.action_timer > 1.8:
                spawn_vesicle()
                self.action_timer = 0
            self.organize_spacing(state, dt)
            if state["stalled"] and self.action_timer > 1.0:
                self.nudge_stalled(state, 0.35)
                self.action_timer = 0

        elif self.mode == "constructive":
            flow_speed = lerp(flow_speed, 1.15, dt * 0.9)
            if state["count"] < 14 and self.action_timer > random.uniform(0.45, 1.05):
                spawn_vesicle()
                self.action_timer = 0
            if state["count"] < 4 and self.action_timer > 0.2:
                spawn_burst(3)

        elif self.mode == "organize":
            flow_speed = lerp(flow_speed, 0.95, dt * 1.0)
            self.organize_spacing(state, dt)
            if self.action_timer > 2.4:
                self.force_marking(state)
                self.action_timer = 0
            if state["count"] < 7:
                spawn_vesicle()

        elif self.mode == "curious":
            flow_speed = lerp(flow_speed, 1.05, dt * 0.8)
            if self.action_timer > 1.7:
                self.nudge_stalled(state, 0.45)
                self.force_marking(state)
                self.action_timer = 0
            if state["count"] < 8 and random.random() < 0.025:
                spawn_vesicle()

        elif self.mode == "ritual":
            flow_speed = lerp(flow_speed, 0.92 + 0.25 * math.sin(sim_time * 1.1), dt * 1.2)
            pulse = 0.10 + 0.09 * math.sin(sim_time * 3.0)
            for i, c in enumerate(cisternae):
                c.pulse(max(0.02, pulse * (0.5 + 0.5 * math.sin(sim_time * 1.7 + i))))
            if self.pulse_timer > 4.0:
                spawn_burst(4, artistic=False)
                spill_particles(vector(-4.8, cisternae[0].y + 0.3, 0), self.drone.color, count=15, speed=0.55, life=1.2)
                self.pulse_timer = 0
            self.organize_spacing(state, dt)

        elif self.mode == "artistic":
            flow_speed = lerp(flow_speed, 1.22, dt * 0.8)
            if self.action_timer > 0.95 and state["count"] < 20:
                hue = (sim_time * 0.072 + random.random() * 0.14) % 1.0
                spawn_vesicle(artistic_hue=hue)
                self.action_timer = 0
            if random.random() < 0.018:
                pos = self.drone.pos + random_unit_vector() * 0.22
                spill_particles(pos, hue_color(sim_time * 0.08), count=2, speed=0.25, life=0.9)

        elif self.mode == "chaotic":
            flow_speed = lerp(flow_speed, 1.78, dt * 1.8)
            for c in cisternae:
                c.pulse(random.uniform(0.02, 0.16))
            if self.action_timer > random.uniform(0.55, 1.3):
                if random.random() < 0.58:
                    spawn_burst(random.randint(2, 5), artistic=random.random() < 0.45)
                self.nudge_stalled(state, random.uniform(0.7, 1.4))
                for v in random.sample(state["active"], min(len(state["active"]), random.randint(1, 4))):
                    v.vel += random_unit_vector() * random.uniform(0.35, 1.0)
                self.action_timer = 0

        elif self.mode == "destructive":
            flow_speed = lerp(flow_speed, 1.55, dt * 1.3)
            if self.action_timer > 1.25:
                targets = state["attached"] if state["attached"] else state["active"]
                if targets:
                    for v in random.sample(targets, min(len(targets), 3)):
                        v.force_detach(random.uniform(0.8, 1.5))
                else:
                    spawn_burst(3, artistic=True)
                self.action_timer = 0
            if sim_time - self.mode_started > 7.5:
                self.choose_new_mode("timer")

    def update(self, dt):
        state = self.read_state()
        self.update_drone(dt, state)

        if not self.enabled or human_override or sim_time < self.override_until:
            return

        detector = self.detect_stagnation_or_completion(state, dt)

        if detector in ["complete", "empty"]:
            if self.completion_time is not None and sim_time - self.completion_time > self.loop_delay:
                self.rounds_started_by_ai += 1
                reset_simulation(spawn_initial=True, new_round=True)
                self.completion_time = None
                self.last_change_time = sim_time
                self.choose_new_mode(detector)
                return

        if detector == "stagnant":
            self.choose_new_mode("stagnant")
            if state["count"] == 0:
                spawn_burst(5, artistic=True)
            else:
                self.nudge_stalled(state, 1.2)
            self.last_change_time = sim_time

        if sim_time - self.mode_started > self.next_switch:
            self.choose_new_mode("timer")

        if state["count"] == 0 and delivered_round < ROUND_GOAL:
            self.choose_new_mode("empty")
            spawn_burst(4, artistic=self.mode in ["artistic", "chaotic"])

        self.actions_for_mode(state, dt)

ai = AIController()

# ----------------------------
# Collisions
# ----------------------------

def handle_collisions(dt):
    active = [v for v in vesicles if v.state not in ["delivered", "attached"]]
    n = len(active)
    for i in range(n):
        a = active[i]
        for j in range(i + 1, n):
            b = active[j]
            delta = b.pos - a.pos
            d = mag(delta)
            min_d = a.radius + b.radius
            if 1e-5 < d < min_d:
                push = norm(delta) * (min_d - d) * 0.52
                a.pos -= push
                b.pos += push
                rel = b.vel - a.vel
                normal = norm(delta)
                impulse = dot(rel, normal)
                if impulse < 0.4:
                    a.vel += normal * impulse * 0.35 - normal * 0.10
                    b.vel -= normal * impulse * 0.35 + normal * 0.10
                col = color_lerp(a.body.color, b.body.color, 0.5)
                if random.random() < 0.40:
                    spill_particles((a.pos + b.pos) * 0.5, col, count=2, speed=0.32, life=0.55)

# ----------------------------
# Human controls
# ----------------------------

def selected_vesicle():
    active = [v for v in vesicles if v.state != "delivered"]
    if not active:
        return None
    global manual_selected_index
    manual_selected_index %= len(active)
    return active[manual_selected_index]

def nudge_selected(vec):
    global human_override
    v = selected_vesicle()
    if v is not None:
        v.vel += vec
        v.pos += vec * 0.05
        spill_particles(v.pos, vector(0.15, 0.25, 0.35), count=4, speed=0.3, life=0.6)
        ai.override_until = sim_time + 4.0

def keydown(evt):
    global paused, orbit_camera, manual_selected_index, human_override

    k = evt.key

    if k == " ":
        paused = not paused
    elif k in ["a", "A"]:
        ai.enabled = not ai.enabled
        ai.mode_label.text = "AI: " + ("on" if ai.enabled else "off")
    elif k in ["e", "E"]:
        human_override = not human_override
    elif k in ["m", "M"]:
        ai.next_mode_manual()
    elif k in ["r", "R"]:
        reset_simulation(spawn_initial=True, new_round=True)
        ai.last_change_time = sim_time
    elif k in ["s", "S"]:
        spawn_vesicle()
        ai.override_until = sim_time + 2.5
    elif k in ["b", "B"]:
        spawn_burst(7, artistic=False)
        ai.override_until = sim_time + 2.5
    elif k in ["n", "N"]:
        manual_selected_index += 1
    elif k in ["d", "D"]:
        v = selected_vesicle()
        if v is not None:
            v.force_detach(1.4)
            ai.override_until = sim_time + 4.0
    elif k in ["c", "C"]:
        orbit_camera = not orbit_camera
    elif k == "up" or k in ["i", "I"]:
        nudge_selected(vector(0, 0.55, 0))
    elif k == "down" or k in ["k", "K"]:
        nudge_selected(vector(0, -0.55, 0))
    elif k == "left" or k in ["j", "J"]:
        nudge_selected(vector(-0.55, 0, 0))
    elif k == "right" or k in ["l", "L"]:
        nudge_selected(vector(0.55, 0, 0))
    elif k in ["u", "U"]:
        nudge_selected(vector(0, 0, -0.55))
    elif k in ["o", "O"]:
        nudge_selected(vector(0, 0, 0.55))

scene.bind("keydown", keydown)

# ----------------------------
# Initial round
# ----------------------------

spawn_burst(6, artistic=False)
ai.last_change_time = 0.0

# ----------------------------
# Status display
# ----------------------------

def update_selector():
    v = selected_vesicle()
    if v is None:
        selector_ring.visible = False
        return
    selector_ring.visible = True
    selector_ring.pos = v.pos
    selector_ring.radius = v.radius * 1.95
    selector_ring.axis = vector(0, 1, 0)
    selector_ring.color = vector(0.12, 0.16, 0.22)

def update_status():
    active = [v for v in vesicles if v.state != "delivered"]
    state_counts = {}
    for v in active:
        state_counts[v.state] = state_counts.get(v.state, 0) + 1

    status_label.text = (
        f"Round {round_number} | delivered {delivered_round}/{ROUND_GOAL} "
        f"| total {total_delivered} | active {len(active)} | "
        f"AI {'ON' if ai.enabled else 'OFF'}:{ai.mode} "
        f"{'| HUMAN OVERRIDE' if human_override else ''} "
        f"{'| PAUSED' if paused else ''}\n"
        f"incoming {state_counts.get('incoming', 0)}  attached {state_counts.get('attached', 0)}  "
        f"transfer {state_counts.get('transfer', 0)}  outgoing {state_counts.get('outgoing', 0)}  "
        f"flow {flow_speed:.2f}"
    )

# ----------------------------
# Main loop
# ----------------------------

last_real = time.time()

while True:
    rate(60)

    now = time.time()
    dt = min(0.035, max(0.001, now - last_real))
    last_real = now

    if paused:
        ai.update_drone(dt, ai.read_state())
        update_selector()
        update_status()
        continue

    sim_time += dt

    # Camera orbit is optional and gentle so manual interaction remains usable.
    if orbit_camera:
        angle = sim_time * 0.13
        scene.forward = vector(-7.5 * math.cos(angle), -3.0, -6.5 * math.sin(angle) - 0.25)

    # Update AI first so it can spawn, organize, mark, detach, or reset.
    ai.update(dt)

    # Update dynamic Golgi traffic.
    survivors = []
    for v in vesicles:
        alive = v.update(dt)
        if alive and v.state != "delivered":
            survivors.append(v)
    vesicles = survivors

    handle_collisions(dt)

    # Update particles.
    particle_survivors = []
    for p in particles:
        if p.update(dt):
            particle_survivors.append(p)
    particles = particle_survivors

    # Fade temporary vesicle markers.
    for v in vesicles:
        if v.marker.opacity > 0:
            v.marker.opacity = max(0, v.marker.opacity - dt * 0.35)

    # Subtle membrane receptor pulsing.
    for i, rec in enumerate(receptors):
        rec.opacity = 0.42 + 0.18 * (0.5 + 0.5 * math.sin(sim_time * 1.4 + i * 0.7))
        rec.radius = 0.145 + 0.025 * math.sin(sim_time * 1.1 + i)

    # Restore cisternae opacity unless an AI behavior is intentionally pulsing them.
    if ai.mode not in ["ritual", "chaotic"] or not ai.enabled or human_override:
        for c in cisternae:
            c.restore_opacity()

    update_selector()

    if sim_time - last_status_update > 0.15:
        update_status()
        last_status_update = sim_time
