from vpython import *
import random
import math
from collections import deque

# ------------------------------------------------------------
# Two-Predator Fish School in a Reef
# VPython self-contained simulation with expressive AI controller
# ------------------------------------------------------------

scene.title = "Two-Predator Fish School in a Reef - Safe-Zone Corridor Simulation"
scene.background = vector(0.86, 0.95, 1.0)
scene.width = 1200
scene.height = 760
scene.center = vector(0, 0, 0)
scene.forward = vector(-0.85, -0.35, -0.9)
scene.range = 18
scene.caption = (
    "\nControls: W/S forward-back, A/D left-right, Q/E up-down primary predator | "
    "I toggle AI | P pause | R reset | B bounce/wrap | M new AI mode | "
    "O toggle human override | C clear marks | +/- predator speed\n"
)

# -----------------------------
# Global simulation parameters
# -----------------------------

NUM_PREY = 46
NUM_PREDATORS = 2
NUM_CORAL = 10
BOX = vector(30, 18, 22)
HALF = BOX * 0.5
FLOOR_Y = -HALF.y
CEILING_Y = HALF.y
PREY_RADIUS = 0.22
PREDATOR_RADIUS = 0.78
# Capture tuning: larger catch zone and stronger pursuit make catches happen more often.
CAPTURE_RADIUS_BONUS = 0.72
PREDATOR_PURSUIT_BOOST = 1.28
PACK_CAPTURE_PRESSURE = 1.18
PREY_ESCAPE_DAMPING = 0.86
DT = 1.0 / 60.0

MAX_PARTICLES = 220
MAX_MARKS = 70

# Safe-zone and hidden-corridor behavior.
# When predators close in, each coral obstacle casts a temporary shelter zone on
# the far side of the obstacle. Fish steer toward those shelters and then along
# narrow corridor segments between nearby coral structures.
SHELTER_TRIGGER_DISTANCE = 8.8
SHELTER_RELEASE_DISTANCE = 10.6
SHELTER_RADIUS = 2.45
SHELTER_FORCE = 5.9
CORRIDOR_FORCE = 4.7
CORRIDOR_MAX_WIDTH = 7.2
CORRIDOR_MIN_WIDTH = 3.1
CORRIDOR_VISUAL_LIMIT = 9

boundary_mode = "bounce"
paused = False
allow_human_override = True
predator_speed_multiplier = 1.0

round_number = 1
caught_this_round = 0
total_caught = 0
sim_time = 0.0

keys_down = set()

# -----------------------------
# Utility functions
# -----------------------------

EPS = 1e-8


def clamp(x, a, b):
    return max(a, min(b, x))


def safe_norm(v, fallback=None):
    m = mag(v)
    if m > EPS:
        return v / m
    if fallback is not None:
        return safe_norm(fallback)
    return random_unit_vector()


def limit(v, max_mag):
    m = mag(v)
    if m > max_mag and m > EPS:
        return v * (max_mag / m)
    return v


def lerp(a, b, t):
    return a * (1 - t) + b * t


def color_lerp(a, b, t):
    t = clamp(t, 0, 1)
    return vector(a.x * (1 - t) + b.x * t, a.y * (1 - t) + b.y * t, a.z * (1 - t) + b.z * t)


def random_unit_vector():
    while True:
        v = vector(random.uniform(-1, 1), random.uniform(-0.7, 0.7), random.uniform(-1, 1))
        if mag(v) > 0.05:
            return norm(v)


def random_swim_pos():
    return vector(
        random.uniform(-HALF.x + 1.5, HALF.x - 1.5),
        random.uniform(FLOOR_Y + 2.0, CEILING_Y - 1.5),
        random.uniform(-HALF.z + 1.5, HALF.z - 1.5),
    )


def xz_distance(a, b):
    return mag(vector(a.x - b.x, 0, a.z - b.z))


def nearest_point_on_segment(p, a, b):
    ab = b - a
    denom = mag2(ab)
    if denom < EPS:
        return a
    t = dot(p - a, ab) / denom
    t = clamp(t, 0, 1)
    return a + ab * t


# -----------------------------
# Stationary reef space
# -----------------------------

floor = box(
    pos=vector(0, FLOOR_Y - 0.04, 0),
    size=vector(BOX.x, 0.08, BOX.z),
    color=vector(0.96, 0.89, 0.70),
)

reef_boundary = box(
    pos=vector(0, 0, 0),
    size=BOX,
    color=vector(0.65, 0.82, 0.96),
    opacity=0.055,
)

surface = box(
    pos=vector(0, CEILING_Y + 0.01, 0),
    size=vector(BOX.x, 0.02, BOX.z),
    color=vector(0.72, 0.95, 1.0),
    opacity=0.20,
)

escape_gates = [
    {"pos": vector(HALF.x, 0.3, -5.8), "axis": vector(1, 0, 0), "radius": 2.0, "name": "E"},
    {"pos": vector(-HALF.x, 1.4, 5.8), "axis": vector(1, 0, 0), "radius": 2.1, "name": "W"},
    {"pos": vector(4.5, 0.8, HALF.z), "axis": vector(0, 0, 1), "radius": 1.8, "name": "N"},
    {"pos": vector(-7.0, -0.2, -HALF.z), "axis": vector(0, 0, 1), "radius": 1.9, "name": "S"},
]

gate_objects = []
for g in escape_gates:
    gate_objects.append(
        ring(
            pos=g["pos"],
            axis=g["axis"],
            radius=g["radius"],
            thickness=0.05,
            color=vector(0.45, 0.95, 0.78),
            opacity=0.45,
        )
    )
    gate_objects.append(
        label(
            pos=g["pos"] + vector(0, g["radius"] + 0.55, 0),
            text="escape",
            height=10,
            color=vector(0.1, 0.45, 0.38),
            box=False,
            opacity=0,
        )
    )


# -----------------------------
# Dynamic visual effects
# -----------------------------

particles = []
danger_marks = []


class Particle:
    def __init__(self, pos, vel, col, radius=0.06, life=1.3):
        self.vel = vel
        self.life = life
        self.max_life = life
        self.obj = sphere(pos=pos, radius=radius, color=col, opacity=0.75, emissive=True)

    def update(self, dt):
        self.life -= dt
        self.obj.pos += self.vel * dt
        self.vel *= 0.975
        self.obj.opacity = max(0, 0.75 * self.life / self.max_life)
        self.obj.radius *= 0.994
        return self.life > 0

    def destroy(self):
        self.obj.visible = False


class DangerMark:
    def __init__(self, pos, intensity=1.0, col=vector(1.0, 0.45, 0.20), life=7.0, label_text=""):
        self.pos = vector(pos.x, pos.y, pos.z)
        self.life = life
        self.max_life = life
        self.intensity = intensity
        self.ring = ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=0.35 + 0.45 * intensity,
            thickness=0.025,
            color=col,
            opacity=0.38,
        )
        self.glow = sphere(
            pos=self.pos,
            radius=0.20 + 0.10 * intensity,
            color=col,
            opacity=0.18,
            emissive=True,
        )
        self.label = None
        if label_text:
            self.label = label(pos=self.pos + vector(0, 0.65, 0), text=label_text, height=8, box=False, opacity=0, color=col)

    def update(self, dt):
        self.life -= dt
        fade = max(0, self.life / self.max_life)
        self.ring.radius += dt * (0.22 + 0.08 * self.intensity)
        self.ring.opacity = 0.38 * fade
        self.glow.opacity = 0.18 * fade
        if self.label:
            self.label.opacity = 0
            self.label.color = self.ring.color
        return self.life > 0

    def destroy(self):
        self.ring.visible = False
        self.glow.visible = False
        if self.label:
            self.label.visible = False


def spawn_particles(pos, col, count=12, speed=2.2):
    global particles
    for _ in range(count):
        if len(particles) >= MAX_PARTICLES:
            old = particles.pop(0)
            old.destroy()
        vel = random_unit_vector() * random.uniform(0.25, speed)
        particles.append(Particle(pos, vel, col, radius=random.uniform(0.035, 0.085), life=random.uniform(0.65, 1.8)))


def add_mark(pos, intensity=1.0, col=vector(1.0, 0.45, 0.20), life=7.0, label_text=""):
    global danger_marks
    if len(danger_marks) >= MAX_MARKS:
        old = danger_marks.pop(0)
        old.destroy()
    danger_marks.append(DangerMark(pos, intensity, col, life, label_text))


def clear_marks():
    global danger_marks, particles
    for m in danger_marks:
        m.destroy()
    for p in particles:
        p.destroy()
    danger_marks = []
    particles = []


# -----------------------------
# Coral obstacles
# -----------------------------

class CoralObstacle:
    def __init__(self, base_pos, radius, height, col):
        self.base = base_pos
        self.radius = radius
        self.height = height
        self.center = base_pos + vector(0, height * 0.52, 0)
        self.parts = []

        stalk = cylinder(
            pos=base_pos,
            axis=vector(0, height, 0),
            radius=radius * 0.25,
            color=col,
            opacity=0.92,
        )
        self.parts.append(stalk)

        bulbs = random.randint(2, 4)
        for i in range(bulbs):
            y = height * random.uniform(0.35, 0.95)
            angle = random.uniform(0, 2 * math.pi)
            side = vector(math.cos(angle), random.uniform(0.15, 0.5), math.sin(angle))
            branch_len = radius * random.uniform(0.9, 1.55)
            branch_axis = safe_norm(side) * branch_len
            branch = cylinder(
                pos=base_pos + vector(0, y, 0),
                axis=branch_axis,
                radius=radius * random.uniform(0.08, 0.16),
                color=color_lerp(col, vector(1.0, 0.72, 0.65), random.uniform(0, 0.35)),
                opacity=0.86,
            )
            tip = sphere(
                pos=branch.pos + branch_axis,
                radius=radius * random.uniform(0.16, 0.29),
                color=branch.color,
                opacity=0.84,
            )
            self.parts.extend([branch, tip])

        crown = sphere(
            pos=base_pos + vector(0, height * random.uniform(0.75, 1.0), 0),
            radius=radius * random.uniform(0.23, 0.42),
            color=color_lerp(col, vector(1.0, 0.88, 0.70), 0.25),
            opacity=0.78,
        )
        self.parts.append(crown)

        self.marker = sphere(pos=self.center, radius=self.radius, color=vector(1, 1, 1), opacity=0.035, visible=True)

    def avoidance(self, pos, avoid_distance):
        d = pos - self.center
        dist = mag(d)
        zone = self.radius + avoid_distance
        if dist < zone:
            return safe_norm(d + vector(0, 0.2, 0)) * ((zone - dist) / zone)
        return vector(0, 0, 0)

    def collides(self, pos, extra=0.0):
        return mag(pos - self.center) < self.radius + extra


obstacles = []
coral_palette = [
    vector(1.0, 0.45, 0.42),
    vector(1.0, 0.62, 0.33),
    vector(0.95, 0.55, 0.82),
    vector(0.70, 0.55, 1.0),
    vector(0.98, 0.78, 0.42),
]

attempts = 0
while len(obstacles) < NUM_CORAL and attempts < 200:
    attempts += 1
    p = vector(
        random.uniform(-HALF.x + 3.0, HALF.x - 3.0),
        FLOOR_Y,
        random.uniform(-HALF.z + 3.0, HALF.z - 3.0),
    )
    if mag(vector(p.x, 0, p.z)) < 3.0:
        continue
    ok = True
    for o in obstacles:
        if xz_distance(p, o.base) < o.radius + 3.3:
            ok = False
            break
    if ok:
        r = random.uniform(1.0, 1.9)
        h = random.uniform(2.3, 5.2)
        obstacles.append(CoralObstacle(p, r, h, random.choice(coral_palette)))


# -----------------------------
# Safe zones and hidden corridors
# -----------------------------

class SafeZoneCorridorSystem:
    """Creates predator-shadow shelters behind coral and routes prey through gaps."""
    def __init__(self, obstacle_list):
        self.obstacles = obstacle_list
        self.safe_zones = []
        self.corridors = []
        self.active = False
        self.safe_count = 0
        self.corridor_count = 0
        self.pulse_timer = 0.0
        self._build_visuals()
        self._build_corridors()

    def _build_visuals(self):
        for o in self.obstacles:
            zone_ring = ring(
                pos=o.center,
                axis=vector(0, 1, 0),
                radius=SHELTER_RADIUS,
                thickness=0.035,
                color=vector(0.22, 0.88, 0.72),
                opacity=0.0,
            )
            zone_glow = sphere(
                pos=o.center,
                radius=SHELTER_RADIUS * 0.55,
                color=vector(0.22, 0.88, 0.72),
                opacity=0.0,
            )
            zone_label = label(
                pos=o.center + vector(0, 0.95, 0),
                text="shelter",
                height=7,
                box=False,
                opacity=0,
                color=vector(0.05, 0.38, 0.30),
            )
            self.safe_zones.append({
                "obstacle": o,
                "pos": o.center,
                "score": 0.0,
                "ring": zone_ring,
                "glow": zone_glow,
                "label": zone_label,
            })

    def _build_corridors(self):
        pairs = []
        for i, a in enumerate(self.obstacles):
            for b in self.obstacles[i + 1:]:
                d = xz_distance(a.center, b.center)
                gap = d - a.radius - b.radius
                if CORRIDOR_MIN_WIDTH <= gap <= CORRIDOR_MAX_WIDTH:
                    mid = (a.center + b.center) * 0.5
                    pairs.append((gap, mid, a, b))
        pairs.sort(key=lambda item: item[0])
        for gap, mid, a, b in pairs[:CORRIDOR_VISUAL_LIMIT]:
            axis = b.center - a.center
            axis.y = 0
            if mag(axis) < EPS:
                continue
            c = cylinder(
                pos=a.center,
                axis=b.center - a.center,
                radius=0.045,
                color=vector(0.30, 0.95, 0.92),
                opacity=0.0,
            )
            mid_marker = sphere(
                pos=mid,
                radius=0.16,
                color=vector(0.30, 0.95, 0.92),
                opacity=0.0,
                emissive=True,
            )
            self.corridors.append({
                "a": a,
                "b": b,
                "mid": mid,
                "gap": gap,
                "obj": c,
                "marker": mid_marker,
            })

    def update(self, dt, prey_list, predator_list):
        active_prey = [f for f in prey_list if not f.caught]
        if active_prey:
            center = vector(0, 0, 0)
            for f in active_prey:
                center += f.pos
            center /= len(active_prey)
            closest_predator = min(predator_list, key=lambda pr: mag(pr.pos - center))
            school_threat_dist = mag(closest_predator.pos - center)
        else:
            center = vector(0, 0, 0)
            closest_predator = predator_list[0]
            school_threat_dist = 9999

        should_activate = school_threat_dist < SHELTER_TRIGGER_DISTANCE
        should_release = school_threat_dist > SHELTER_RELEASE_DISTANCE
        if should_activate and not self.active:
            self.active = True
            add_mark(center, 0.7, vector(0.22, 0.88, 0.72), 4.0, "safe zones")
            spawn_particles(center, vector(0.22, 0.88, 0.72), count=12, speed=1.8)
        elif should_release and self.active:
            self.active = False
            add_mark(center, 0.45, vector(0.68, 0.96, 1.0), 3.0, "reform")

        self.pulse_timer += dt
        pulse = 0.5 + 0.5 * math.sin(self.pulse_timer * 3.2)
        threat = closest_predator.pos
        self.safe_count = 0

        for zone in self.safe_zones:
            o = zone["obstacle"]
            away = safe_norm(o.center - threat, vector(1, 0, 0))
            shelter_pos = o.center + away * (o.radius + SHELTER_RADIUS * 0.62)
            shelter_pos.y = clamp(o.center.y + 0.18, FLOOR_Y + 1.2, CEILING_Y - 1.0)
            zone["pos"] = shelter_pos

            # A shelter is strongest when the obstacle lies between the predator and the shelter,
            # and when the school is close enough to plausibly weave through it.
            shadow_quality = max(0.0, dot(safe_norm(shelter_pos - threat), away))
            school_relevance = clamp(1.0 - mag(center - shelter_pos) / 17.0, 0, 1)
            zone["score"] = shadow_quality * (0.45 + 0.55 * school_relevance)
            if self.active and zone["score"] > 0.18:
                self.safe_count += 1

            visual_strength = zone["score"] if self.active else 0.0
            zone["ring"].pos = shelter_pos
            zone["ring"].radius = SHELTER_RADIUS * (0.86 + 0.10 * pulse)
            zone["ring"].opacity = 0.10 + 0.28 * visual_strength
            zone["glow"].pos = shelter_pos
            zone["glow"].opacity = 0.04 + 0.11 * visual_strength
            zone["label"].pos = shelter_pos + vector(0, 0.85, 0)
            zone["label"].color = vector(0.05, 0.38 + 0.25 * visual_strength, 0.30)

        self.corridor_count = 0
        for corridor in self.corridors:
            a_score = self._zone_score_for_obstacle(corridor["a"])
            b_score = self._zone_score_for_obstacle(corridor["b"])
            corridor_strength = max(a_score, b_score)
            visible = self.active and corridor_strength > 0.18
            if visible:
                self.corridor_count += 1
            corridor["obj"].opacity = (0.12 + 0.18 * pulse) * corridor_strength if visible else 0.0
            corridor["marker"].opacity = 0.18 * corridor_strength if visible else 0.0
            corridor["marker"].radius = 0.14 + 0.09 * pulse

    def _zone_score_for_obstacle(self, obstacle):
        for zone in self.safe_zones:
            if zone["obstacle"] is obstacle:
                return zone["score"]
        return 0.0

    def best_zone_for(self, fish_pos, threat_pos):
        best_zone = None
        best_score = -99999
        away_from_threat = safe_norm(fish_pos - threat_pos, vector(1, 0, 0))
        for zone in self.safe_zones:
            if not self.active or zone["score"] <= 0.12:
                continue
            to_zone = zone["pos"] - fish_pos
            d = mag(to_zone)
            if d < EPS:
                continue
            directional = dot(safe_norm(to_zone), away_from_threat)
            score = zone["score"] * 5.0 + directional * 2.6 - d * 0.12
            if score > best_score:
                best_score = score
                best_zone = zone
        return best_zone

    def corridor_pull_for(self, fish_pos, threat_pos):
        if not self.active or not self.corridors:
            return vector(0, 0, 0)
        best = None
        best_score = -99999
        away = safe_norm(fish_pos - threat_pos, vector(1, 0, 0))
        for corridor in self.corridors:
            strength = max(self._zone_score_for_obstacle(corridor["a"]), self._zone_score_for_obstacle(corridor["b"]))
            if strength <= 0.15:
                continue
            mid = corridor["mid"]
            d = mag(mid - fish_pos)
            direction_score = dot(safe_norm(mid - fish_pos, away), away)
            score = strength * 3.0 + direction_score * 1.9 - d * 0.10
            if score > best_score:
                best_score = score
                best = corridor
        if best is None:
            return vector(0, 0, 0)
        mid_pull = safe_norm(best["mid"] - fish_pos, vector(0, 0, 0))
        # Tangential component encourages weaving through the gap rather than stopping at it.
        gap_axis = safe_norm(best["b"].center - best["a"].center, vector(1, 0, 0))
        weave = safe_norm(cross(vector(0, 1, 0), gap_axis), vector(1, 0, 0))
        if dot(weave, away) < 0:
            weave *= -1
        return mid_pull * 0.72 + weave * 0.55

    def steering_for(self, fish_pos, fish_vel, threat_pos, fear):
        if not self.active:
            return vector(0, 0, 0)
        zone = self.best_zone_for(fish_pos, threat_pos)
        acc = vector(0, 0, 0)
        if zone:
            to_zone = zone["pos"] - fish_pos
            zone_dist = mag(to_zone)
            if zone_dist > EPS:
                desired = safe_norm(to_zone) * (SHELTER_FORCE * (0.55 + 0.75 * fear) * zone["score"])
                acc += desired
                if zone_dist < SHELTER_RADIUS * 0.9:
                    # Once inside shelter, sidestep along the obstacle shadow to create a visible weaving path.
                    around = safe_norm(cross(vector(0, 1, 0), zone["pos"] - threat_pos), vector(1, 0, 0))
                    if (int(sim_time * 1.5 + zone_dist) % 2) == 0:
                        around *= -1
                    acc += around * (1.7 + 2.2 * fear)
        acc += self.corridor_pull_for(fish_pos, threat_pos) * (CORRIDOR_FORCE * (0.5 + fear))
        return acc


shelter_system = SafeZoneCorridorSystem(obstacles)


# -----------------------------
# Moving objects
# -----------------------------

class Predator:
    def __init__(self, idx=0):
        self.idx = idx
        start_angle = (2 * math.pi * idx) / max(NUM_PREDATORS, 1)
        self.pos = vector(math.cos(start_angle) * (1.0 + idx * 0.9), 1.3 + 0.35 * idx, math.sin(start_angle) * (1.0 + idx * 0.9))
        self.vel = safe_norm(vector(math.cos(start_angle + 0.8), 0.1, math.sin(start_angle + 0.8))) * random.uniform(1.6, 2.4)
        self.forward = safe_norm(self.vel)
        self.max_speed = 6.4
        self.max_force = 12.2
        self.restlessness = 0.0
        self.base_color = color_lerp(vector(0.18, 0.34, 0.78), vector(0.78, 0.20, 0.62), idx / max(NUM_PREDATORS - 1, 1))
        self.nose_color = color_lerp(vector(0.12, 0.24, 0.62), vector(0.58, 0.12, 0.48), idx / max(NUM_PREDATORS - 1, 1))
        self.tail_color = color_lerp(vector(0.23, 0.42, 0.86), vector(0.88, 0.30, 0.68), idx / max(NUM_PREDATORS - 1, 1))

        self.body = sphere(
            pos=self.pos,
            radius=PREDATOR_RADIUS,
            color=self.base_color,
            opacity=0.96,
        )
        self.body.size = vector(PREDATOR_RADIUS * 2.15, PREDATOR_RADIUS * 1.18, PREDATOR_RADIUS * 1.1)

        self.nose = cone(
            pos=self.pos + self.forward * PREDATOR_RADIUS * 0.95,
            axis=self.forward * PREDATOR_RADIUS * 0.85,
            radius=PREDATOR_RADIUS * 0.42,
            color=self.nose_color,
            opacity=0.95,
        )
        self.tail = cone(
            pos=self.pos - self.forward * PREDATOR_RADIUS * 1.05,
            axis=-self.forward * PREDATOR_RADIUS * 0.8,
            radius=PREDATOR_RADIUS * 0.55,
            color=self.tail_color,
            opacity=0.85,
        )
        self.eye_l = sphere(pos=self.pos + vector(0.35, 0.16, 0.23), radius=0.065, color=color.white, emissive=True)
        self.eye_r = sphere(pos=self.pos + vector(0.35, 0.16, -0.23), radius=0.065, color=color.white, emissive=True)

        self.trail = curve(color=color_lerp(self.base_color, color.white, 0.25), radius=0.035, retain=55)

    def reset(self):
        start_angle = (2 * math.pi * self.idx) / max(NUM_PREDATORS, 1) + random.uniform(-0.35, 0.35)
        self.pos = vector(math.cos(start_angle) * random.uniform(1.5, 5.0), random.uniform(-1, 3.5), math.sin(start_angle) * random.uniform(1.5, 5.0))
        self.vel = safe_norm(vector(math.cos(start_angle + 0.7), random.uniform(-0.2, 0.2), math.sin(start_angle + 0.7))) * 2.0
        self.forward = safe_norm(self.vel)
        self.restlessness = 0
        self.trail.clear()
        self.update_visual()

    def apply_accel(self, accel, dt):
        accel = limit(accel, self.max_force * predator_speed_multiplier * PREDATOR_PURSUIT_BOOST)
        self.vel += accel * dt
        self.vel *= 0.997
        self.vel = limit(self.vel, self.max_speed * predator_speed_multiplier * PREDATOR_PURSUIT_BOOST)

    def update(self, dt):
        self.pos += self.vel * dt
        self.handle_boundaries()
        self.handle_obstacles()
        if mag(self.vel) > 0.03:
            self.forward = safe_norm(lerp(self.forward, safe_norm(self.vel), 0.14))
        self.trail.append(pos=self.pos)
        self.update_visual()

    def handle_obstacles(self):
        for o in obstacles:
            if o.collides(self.pos, PREDATOR_RADIUS * 0.75):
                push = safe_norm(self.pos - o.center)
                self.pos = o.center + push * (o.radius + PREDATOR_RADIUS * 0.75)
                self.vel = self.vel - 2 * dot(self.vel, push) * push
                self.vel *= 0.72
                add_mark(self.pos, 0.55, vector(0.2, 0.35, 1.0), 3.0, "")
                spawn_particles(self.pos, vector(0.35, 0.55, 1.0), count=4, speed=1.1)

    def handle_boundaries(self):
        global boundary_mode
        if boundary_mode == "wrap":
            wrapped = False
            if self.pos.x > HALF.x:
                self.pos.x = -HALF.x
                wrapped = True
            elif self.pos.x < -HALF.x:
                self.pos.x = HALF.x
                wrapped = True
            if self.pos.y > CEILING_Y:
                self.pos.y = FLOOR_Y + 1.5
                wrapped = True
            elif self.pos.y < FLOOR_Y + 0.8:
                self.pos.y = CEILING_Y - 0.8
                wrapped = True
            if self.pos.z > HALF.z:
                self.pos.z = -HALF.z
                wrapped = True
            elif self.pos.z < -HALF.z:
                self.pos.z = HALF.z
                wrapped = True
            if wrapped:
                self.trail.clear()
                add_mark(self.pos, 0.8, vector(0.42, 0.55, 1.0), 4.0, "wrap")
        else:
            bounced = False
            if self.pos.x > HALF.x - PREDATOR_RADIUS:
                self.pos.x = HALF.x - PREDATOR_RADIUS
                self.vel.x *= -0.78
                bounced = True
            elif self.pos.x < -HALF.x + PREDATOR_RADIUS:
                self.pos.x = -HALF.x + PREDATOR_RADIUS
                self.vel.x *= -0.78
                bounced = True
            if self.pos.y > CEILING_Y - PREDATOR_RADIUS:
                self.pos.y = CEILING_Y - PREDATOR_RADIUS
                self.vel.y *= -0.78
                bounced = True
            elif self.pos.y < FLOOR_Y + 1.0:
                self.pos.y = FLOOR_Y + 1.0
                self.vel.y *= -0.78
                bounced = True
            if self.pos.z > HALF.z - PREDATOR_RADIUS:
                self.pos.z = HALF.z - PREDATOR_RADIUS
                self.vel.z *= -0.78
                bounced = True
            elif self.pos.z < -HALF.z + PREDATOR_RADIUS:
                self.pos.z = -HALF.z + PREDATOR_RADIUS
                self.vel.z *= -0.78
                bounced = True
            if bounced:
                add_mark(self.pos, 0.45, vector(0.24, 0.48, 1.0), 2.6, "")

    def update_visual(self):
        self.body.pos = self.pos
        self.body.color = color_lerp(self.base_color, vector(0.95, 0.18, 0.92), clamp((predator_speed_multiplier - 1.0) * 0.55, 0, 1))

        f = self.forward
        self.nose.pos = self.pos + f * PREDATOR_RADIUS * 0.78
        self.nose.axis = f * PREDATOR_RADIUS * 0.95

        self.tail.pos = self.pos - f * PREDATOR_RADIUS * 0.98
        self.tail.axis = -f * PREDATOR_RADIUS * 0.78

        side = safe_norm(cross(f, vector(0, 1, 0)), vector(0, 0, 1))
        upish = safe_norm(cross(side, f), vector(0, 1, 0))
        self.eye_l.pos = self.pos + f * 0.48 + upish * 0.22 + side * 0.23
        self.eye_r.pos = self.pos + f * 0.48 + upish * 0.22 - side * 0.23


class PreyFish:
    def __init__(self, idx):
        self.idx = idx
        self.base_col = color_lerp(vector(0.18, 0.78, 0.88), vector(0.60, 0.95, 0.55), random.random())
        self.body = sphere(pos=random_swim_pos(), radius=PREY_RADIUS, color=self.base_col, opacity=0.96)
        self.fin = cone(pos=self.body.pos, axis=vector(-0.2, 0, 0), radius=PREY_RADIUS * 0.55, color=color_lerp(self.base_col, color.white, 0.25), opacity=0.8)
        self.trail = curve(pos=[self.body.pos], color=color_lerp(self.base_col, vector(1, 1, 1), 0.35), radius=0.012, retain=38)
        self.vel = random_unit_vector() * random.uniform(1.4, 2.4)
        self.pos = self.body.pos
        self.caught = False
        self.captor = None
        self.caught_timer = 0.0
        self.orbit_phase = random.uniform(0, 2 * math.pi)
        self.orbit_radius = random.uniform(1.0, 2.2)
        self.max_speed = random.uniform(3.0, 3.9)
        self.mark_cooldown = random.uniform(0, 2.0)
        self.fear = 0.0
        self.sheltered = False
        self.shelter_mark_cooldown = random.uniform(0.0, 2.0)

    def reset(self, pos=None):
        self.caught = False
        self.captor = None
        self.caught_timer = 0.0
        self.orbit_phase = random.uniform(0, 2 * math.pi)
        self.orbit_radius = random.uniform(1.0, 2.2)
        self.pos = pos if pos is not None else safe_random_prey_pos()
        self.vel = random_unit_vector() * random.uniform(1.4, 2.4)
        self.body.opacity = 0.96
        self.fin.opacity = 0.8
        self.body.radius = PREY_RADIUS
        self.body.color = self.base_col
        self.fin.color = color_lerp(self.base_col, color.white, 0.25)
        self.sheltered = False
        self.shelter_mark_cooldown = random.uniform(0.0, 2.0)
        self.trail.clear()
        self.trail.color = color_lerp(self.base_col, vector(1, 1, 1), 0.35)
        self.update_visual()

    def mark_caught(self, predator):
        global caught_this_round, total_caught
        if self.caught:
            return
        self.caught = True
        self.captor = predator
        self.caught_timer = 0.0
        self.orbit_phase = random.uniform(0, 2 * math.pi)
        self.orbit_radius = random.uniform(1.15, 2.45)
        caught_this_round += 1
        total_caught += 1
        self.body.color = vector(1.0, 0.30, 0.20)
        self.fin.color = vector(1.0, 0.65, 0.20)
        self.trail.color = vector(1.0, 0.30, 0.20)
        add_mark(self.pos, 1.25, vector(1.0, 0.28, 0.18), 8.0, "caught")
        spawn_particles(self.pos, vector(1.0, 0.38, 0.18), count=17, speed=2.5)

    def update(self, dt, prey_list, predators):
        if self.caught:
            attached_predator = self.captor if self.captor is not None else nearest_predator_to(self.pos, predators)
            self.update_attached(dt, attached_predator)
            return

        acceleration = vector(0, 0, 0)
        neighbor_count = 0
        align = vector(0, 0, 0)
        cohesion = vector(0, 0, 0)
        separation = vector(0, 0, 0)

        for other in prey_list:
            if other is self or other.caught:
                continue
            offset = other.pos - self.pos
            d = mag(offset)
            if d < 4.3:
                neighbor_count += 1
                align += other.vel
                cohesion += other.pos
                if d < 1.15:
                    separation -= offset / max(d * d, 0.05)

        if neighbor_count > 0:
            align = safe_norm(align / neighbor_count) * self.max_speed - self.vel
            cohesion = ((cohesion / neighbor_count) - self.pos)
            cohesion = safe_norm(cohesion) * self.max_speed - self.vel if mag(cohesion) > 0.05 else vector(0, 0, 0)
            separation = safe_norm(separation) * self.max_speed - self.vel if mag(separation) > 0.05 else vector(0, 0, 0)

            acceleration += align * 0.52
            acceleration += cohesion * 0.34
            acceleration += separation * 1.35

        nearest_threat = nearest_predator_to(self.pos, predators)
        to_predator = self.pos - nearest_threat.pos
        pred_dist = mag(to_predator)
        close_predators = sum(1 for pr in predators if mag(self.pos - pr.pos) < 8.0)
        self.fear = clamp((7.7 - pred_dist) / 7.7, 0, 1)
        pack_fear = clamp(close_predators / max(NUM_PREDATORS, 1), 0, 1)
        if pred_dist < 8.0:
            flee = safe_norm(to_predator) * (8.0 - pred_dist) / 8.0
            acceleration += flee * (7.2 + 4.4 * self.fear + 1.6 * pack_fear)

            gate = nearest_escape_gate(self.pos, nearest_threat.pos)
            gate_pull = safe_norm(gate["pos"] - self.pos)
            acceleration += gate_pull * (0.75 + 1.65 * self.fear)

            shelter_accel = shelter_system.steering_for(self.pos, self.vel, nearest_threat.pos, self.fear)
            if mag(shelter_accel) > 0.01:
                self.sheltered = True
                acceleration += shelter_accel
                self.shelter_mark_cooldown -= dt
                if self.shelter_mark_cooldown <= 0:
                    self.shelter_mark_cooldown = random.uniform(1.6, 3.2)
                    add_mark(self.pos, 0.35 + 0.35 * self.fear, vector(0.22, 0.88, 0.72), 2.7, "hide")
            else:
                self.sheltered = False

            self.mark_cooldown -= dt
            if self.mark_cooldown <= 0:
                self.mark_cooldown = random.uniform(1.3, 3.1)
                add_mark(self.pos, 0.28 + self.fear, vector(0.35, 0.95, 0.75), 3.5, "")
        elif shelter_system.active:
            # Even fish not immediately threatened follow the emerging hidden-corridor route,
            # keeping the whole group weaving behind cover.
            shelter_accel = shelter_system.steering_for(self.pos, self.vel, nearest_threat.pos, max(self.fear, 0.35))
            if mag(shelter_accel) > 0.01:
                self.sheltered = True
                acceleration += shelter_accel * 0.72
            else:
                self.sheltered = False
        else:
            self.sheltered = False

        for o in obstacles:
            avoid_strength = 6.2 if shelter_system.active else 9.0
            acceleration += o.avoidance(self.pos, 2.05) * avoid_strength
            if o.collides(self.pos, PREY_RADIUS):
                push = safe_norm(self.pos - o.center)
                self.pos = o.center + push * (o.radius + PREY_RADIUS + 0.02)
                self.vel += push * 2.5
                add_mark(self.pos, 0.25, vector(1.0, 0.70, 0.34), 2.0, "")

        for mark in danger_marks:
            d = mag(self.pos - mark.pos)
            influence = 2.0 + mark.intensity * 1.2
            if d < influence:
                acceleration += safe_norm(self.pos - mark.pos) * (influence - d) * 0.7

        acceleration += self.boundary_steering() * 4.0
        acceleration += random_unit_vector() * 0.12

        shelter_boost = 1.25 if (shelter_system.active and self.sheltered) else 1.0
        max_force = (7.2 + 3.2 * self.fear) * PREY_ESCAPE_DAMPING * shelter_boost
        acceleration = limit(acceleration, max_force)
        self.vel += acceleration * dt
        self.vel = limit(self.vel, self.max_speed * (1.0 + 0.34 * self.fear + (0.18 if self.sheltered else 0.0)) * PREY_ESCAPE_DAMPING)
        self.pos += self.vel * dt

        self.check_escape_gates()
        self.handle_boundaries()

        capture_radius = PREDATOR_RADIUS + PREY_RADIUS + CAPTURE_RADIUS_BONUS
        for threat in predators:
            if mag(self.pos - threat.pos) < capture_radius:
                self.mark_caught(threat)
                break

        self.update_visual()
        self.trail.append(pos=self.pos)

    def update_attached(self, dt, predator):
        self.caught_timer += dt
        self.orbit_phase += dt * (1.25 + 0.18 * (self.idx % 5))
        f = predator.forward
        side = safe_norm(cross(f, vector(0, 1, 0)), vector(0, 0, 1))
        upish = safe_norm(cross(side, f), vector(0, 1, 0))
        spiral = side * math.cos(self.orbit_phase) + upish * math.sin(self.orbit_phase)
        trail_back = -f * (0.35 + 0.08 * (self.idx % 7))
        self.pos = predator.pos + spiral * self.orbit_radius + trail_back
        self.vel = predator.vel
        fade_t = clamp(self.caught_timer / 8.0, 0, 1)
        self.body.color = color_lerp(vector(1.0, 0.28, 0.18), vector(0.42, 0.34, 0.62), fade_t)
        self.fin.color = color_lerp(vector(1.0, 0.62, 0.16), vector(0.55, 0.45, 0.75), fade_t)
        self.body.opacity = 0.88 - 0.25 * fade_t
        self.fin.opacity = 0.65 - 0.22 * fade_t
        self.update_visual()

    def boundary_steering(self):
        steer = vector(0, 0, 0)
        margin = 2.0
        if self.pos.x > HALF.x - margin:
            steer.x -= (self.pos.x - (HALF.x - margin)) / margin
        elif self.pos.x < -HALF.x + margin:
            steer.x += ((-HALF.x + margin) - self.pos.x) / margin
        if self.pos.y > CEILING_Y - margin:
            steer.y -= (self.pos.y - (CEILING_Y - margin)) / margin
        elif self.pos.y < FLOOR_Y + 1.2 + margin:
            steer.y += ((FLOOR_Y + 1.2 + margin) - self.pos.y) / margin
        if self.pos.z > HALF.z - margin:
            steer.z -= (self.pos.z - (HALF.z - margin)) / margin
        elif self.pos.z < -HALF.z + margin:
            steer.z += ((-HALF.z + margin) - self.pos.z) / margin
        return steer

    def check_escape_gates(self):
        for g in escape_gates:
            gp = g["pos"]
            if g["axis"].x != 0:
                near_wall = abs(abs(self.pos.x) - HALF.x) < 0.38
                within = mag(vector(0, self.pos.y - gp.y, self.pos.z - gp.z)) < g["radius"]
                if near_wall and within:
                    self.pos.x = -self.pos.x * 0.96
                    self.trail.clear()
                    add_mark(gp, 0.7, vector(0.30, 0.95, 0.68), 4.5, "escape")
                    spawn_particles(gp, vector(0.30, 0.95, 0.68), count=5, speed=1.3)
                    return
            else:
                near_wall = abs(abs(self.pos.z) - HALF.z) < 0.38
                within = mag(vector(self.pos.x - gp.x, self.pos.y - gp.y, 0)) < g["radius"]
                if near_wall and within:
                    self.pos.z = -self.pos.z * 0.96
                    self.trail.clear()
                    add_mark(gp, 0.7, vector(0.30, 0.95, 0.68), 4.5, "escape")
                    spawn_particles(gp, vector(0.30, 0.95, 0.68), count=5, speed=1.3)
                    return

    def handle_boundaries(self):
        global boundary_mode
        if boundary_mode == "wrap":
            wrapped = False
            if self.pos.x > HALF.x:
                self.pos.x = -HALF.x + 0.2
                wrapped = True
            elif self.pos.x < -HALF.x:
                self.pos.x = HALF.x - 0.2
                wrapped = True
            if self.pos.y > CEILING_Y:
                self.pos.y = FLOOR_Y + 1.3
                wrapped = True
            elif self.pos.y < FLOOR_Y + 0.8:
                self.pos.y = CEILING_Y - 0.6
                wrapped = True
            if self.pos.z > HALF.z:
                self.pos.z = -HALF.z + 0.2
                wrapped = True
            elif self.pos.z < -HALF.z:
                self.pos.z = HALF.z - 0.2
                wrapped = True
            if wrapped:
                self.trail.clear()
        else:
            if self.pos.x > HALF.x - PREY_RADIUS:
                self.pos.x = HALF.x - PREY_RADIUS
                self.vel.x *= -0.82
            elif self.pos.x < -HALF.x + PREY_RADIUS:
                self.pos.x = -HALF.x + PREY_RADIUS
                self.vel.x *= -0.82
            if self.pos.y > CEILING_Y - PREY_RADIUS:
                self.pos.y = CEILING_Y - PREY_RADIUS
                self.vel.y *= -0.82
            elif self.pos.y < FLOOR_Y + 0.75:
                self.pos.y = FLOOR_Y + 0.75
                self.vel.y *= -0.82
            if self.pos.z > HALF.z - PREY_RADIUS:
                self.pos.z = HALF.z - PREY_RADIUS
                self.vel.z *= -0.82
            elif self.pos.z < -HALF.z + PREY_RADIUS:
                self.pos.z = -HALF.z + PREY_RADIUS
                self.vel.z *= -0.82

    def update_visual(self):
        self.body.pos = self.pos
        if not self.caught:
            fear_col = color_lerp(self.base_col, vector(1.0, 0.92, 0.30), self.fear * 0.85)
            if self.sheltered and shelter_system.active:
                fear_col = color_lerp(fear_col, vector(0.18, 0.95, 0.78), 0.55)
            self.body.color = fear_col
            self.fin.color = color_lerp(fear_col, color.white, 0.30)
            trail_target = vector(0.18, 0.95, 0.78) if self.sheltered and shelter_system.active else vector(1.0, 0.86, 0.22)
            self.trail.color = color_lerp(color_lerp(self.base_col, vector(1, 1, 1), 0.35), trail_target, self.fear if not self.sheltered else 0.8)

        f = safe_norm(self.vel, vector(1, 0, 0))
        self.fin.pos = self.pos - f * PREY_RADIUS * 0.85
        self.fin.axis = -f * PREY_RADIUS * 1.05


def nearest_escape_gate(pos, threat_pos):
    best = escape_gates[0]
    best_score = -99999
    away = safe_norm(pos - threat_pos)
    for g in escape_gates:
        to_gate = safe_norm(g["pos"] - pos)
        dist = mag(g["pos"] - pos)
        score = dot(to_gate, away) * 4.0 - dist * 0.075
        if score > best_score:
            best_score = score
            best = g
    return best


def safe_random_prey_pos():
    for _ in range(500):
        p = random_swim_pos()
        ok = True
        for o in obstacles:
            if o.collides(p, 1.2):
                ok = False
                break
        if ok:
            return p
    return random_swim_pos()


predators = [Predator(i) for i in range(NUM_PREDATORS)]
predator = predators[0]
prey = [PreyFish(i) for i in range(NUM_PREY)]


def nearest_predator_to(pos, predator_list):
    return min(predator_list, key=lambda pr: mag(pos - pr.pos))


def secondary_predator_accel(pr, idx, active_prey):
    """Steer non-primary predators so they flank, herd, and occasionally ambush."""
    if not active_prey:
        target = vector(math.cos(sim_time * 0.35 + idx) * 4.0, 0.8 + math.sin(sim_time * 0.5 + idx), math.sin(sim_time * 0.35 + idx) * 4.0)
    else:
        nearest = min(active_prey, key=lambda f: mag(f.pos - pr.pos))
        school_center = vector(0, 0, 0)
        for f in active_prey:
            school_center += f.pos
        school_center /= len(active_prey)

        flank_angle = sim_time * (0.45 + 0.07 * idx) + idx * 2.1
        flank = vector(math.cos(flank_angle), 0.25 * math.sin(flank_angle * 1.7), math.sin(flank_angle))
        if idx % 3 == 1:
            target = nearest.pos + nearest.vel * 0.95 + flank * 1.25
        elif idx % 3 == 2:
            gate = nearest_escape_gate(school_center, pr.pos)
            target = school_center - safe_norm(gate["pos"] - school_center) * 2.7 + flank * 0.9
        else:
            target = nearest.pos + nearest.vel * 0.65 + flank * (1.8 + 0.4 * math.sin(sim_time + idx))

    desired = target - pr.pos
    if mag(desired) > EPS:
        desired_vel = safe_norm(desired) * pr.max_speed * predator_speed_multiplier * PREDATOR_PURSUIT_BOOST * random.uniform(0.98, 1.22)
        acc = desired_vel - pr.vel
    else:
        acc = vector(0, 0, 0)

    # Keep predators from stacking into one another so the pack stays visible.
    for other in predators:
        if other is pr:
            continue
        offset = pr.pos - other.pos
        d = mag(offset)
        if d < 2.25:
            acc += safe_norm(offset, random_unit_vector()) * (2.25 - d) * 5.0

    for o in obstacles:
        acc += o.avoidance(pr.pos, 2.4) * 7.0

    acc += random_unit_vector() * 0.12
    return limit(acc, pr.max_force * 1.45 * predator_speed_multiplier * PACK_CAPTURE_PRESSURE)


# -----------------------------
# AI controller
# -----------------------------

AI_MODES = [
    "HUNT",
    "HERD",
    "AMBUSH",
    "ORBIT_CORAL",
    "PATROL",
    "SCATTER",
    "CURIOUS_MARKS",
    "REST",
    "RITUAL_RESET",
]


class ReefAIController:
    def __init__(self):
        self.enabled = True
        self.mode = "HUNT"
        self.previous_mode = None
        self.mode_time = 0.0
        self.next_switch = random.uniform(6.0, 11.0)
        self.history = deque(maxlen=22)
        self.sample_timer = 0.0
        self.stagnant = False
        self.completed = False
        self.loop_timer = 0.0
        self.patrol_points = self.make_patrol_points()
        self.patrol_index = 0
        self.orbit_obstacle = random.choice(obstacles) if obstacles else None
        self.ambush_point = vector(0, 0, 0)
        self.ambush_wait = 0.0
        self.ritual_angle = 0.0
        self.mode_color = {
            "HUNT": vector(1.0, 0.32, 0.20),
            "HERD": vector(0.30, 0.74, 1.0),
            "AMBUSH": vector(0.72, 0.44, 1.0),
            "ORBIT_CORAL": vector(1.0, 0.58, 0.28),
            "PATROL": vector(0.28, 0.56, 1.0),
            "SCATTER": vector(1.0, 0.88, 0.12),
            "CURIOUS_MARKS": vector(0.18, 0.90, 0.62),
            "REST": vector(0.60, 0.76, 0.96),
            "RITUAL_RESET": vector(1.0, 0.35, 0.70),
        }

    def make_patrol_points(self):
        return [
            vector(-HALF.x * 0.65, -1.0, -HALF.z * 0.55),
            vector(HALF.x * 0.55, 2.4, -HALF.z * 0.50),
            vector(HALF.x * 0.60, 0.5, HALF.z * 0.55),
            vector(-HALF.x * 0.50, 2.0, HALF.z * 0.45),
            vector(0, 4.2, 0),
        ]

    def read_state(self):
        active = [f for f in prey if not f.caught]
        caught = len(prey) - len(active)

        if active:
            center = vector(0, 0, 0)
            avg_vel = vector(0, 0, 0)
            for f in active:
                center += f.pos
                avg_vel += f.vel
            center /= len(active)
            avg_vel /= len(active)
            nearest = min(active, key=lambda f: mag(f.pos - predator.pos))
            nearest_dist = mag(nearest.pos - predator.pos)
            avg_speed = sum(mag(f.vel) for f in active) / len(active)
            spread = sum(mag(f.pos - center) for f in active) / len(active)
        else:
            center = vector(0, 0, 0)
            avg_vel = vector(0, 0, 0)
            nearest = None
            nearest_dist = 9999
            avg_speed = 0
            spread = 0

        return {
            "active": active,
            "caught": caught,
            "active_count": len(active),
            "school_center": center,
            "school_velocity": avg_vel,
            "nearest": nearest,
            "nearest_dist": nearest_dist,
            "avg_speed": avg_speed,
            "spread": spread,
            "marks_count": len(danger_marks),
            "predator_pos": predator.pos,
            "predator_vel": predator.vel,
        }

    def update_stagnation(self, dt, state):
        self.sample_timer += dt
        if self.sample_timer >= 1.0:
            self.sample_timer = 0.0
            self.history.append(
                (
                    sim_time,
                    state["caught"],
                    state["active_count"],
                    vector(state["school_center"].x, state["school_center"].y, state["school_center"].z),
                    state["avg_speed"],
                )
            )

        self.completed = state["active_count"] <= max(2, int(NUM_PREY * 0.07))

        if len(self.history) >= 12:
            first = self.history[0]
            last = self.history[-1]
            caught_changed = last[1] != first[1]
            active_changed = last[2] != first[2]
            center_motion = mag(last[3] - first[3])
            mean_speed = sum(h[4] for h in self.history) / len(self.history)
            self.stagnant = (not caught_changed) and (not active_changed) and center_motion < 1.4 and mean_speed < 2.1
        else:
            self.stagnant = False

    def force_next_mode(self):
        self.choose_new_mode(self.read_state(), forced=True)

    def choose_new_mode(self, state, forced=False):
        active_count = state["active_count"]
        nearest_dist = state["nearest_dist"]
        spread = state["spread"]

        weighted = []

        def add(mode, weight):
            if mode != self.mode:
                weighted.append((mode, weight))

        if self.completed:
            add("RITUAL_RESET", 10)
        elif self.stagnant:
            add("SCATTER", 5)
            add("RITUAL_RESET", 2)
            add("ORBIT_CORAL", 3)
        else:
            if active_count < NUM_PREY * 0.25:
                add("HUNT", 5)
                add("AMBUSH", 3)
                add("RITUAL_RESET", 1)
            if nearest_dist < 3.0:
                add("HUNT", 6)
                add("SCATTER", 2)
            if spread < 3.5:
                add("SCATTER", 4)
                add("HERD", 4)
            if len(danger_marks) > 8:
                add("CURIOUS_MARKS", 3)
            add("HUNT", 4)
            add("HERD", 3)
            add("AMBUSH", 2)
            add("ORBIT_CORAL", 3)
            add("PATROL", 2)
            add("REST", 1)

        if not weighted:
            weighted = [(m, 1) for m in AI_MODES if m != self.mode]

        total = sum(w for _, w in weighted)
        pick = random.uniform(0, total)
        acc = 0
        new_mode = weighted[-1][0]
        for mode, weight in weighted:
            acc += weight
            if pick <= acc:
                new_mode = mode
                break

        self.previous_mode = self.mode
        self.mode = new_mode
        self.mode_time = 0.0
        self.next_switch = random.uniform(5.0, 13.0)

        if self.mode == "ORBIT_CORAL" and obstacles:
            self.orbit_obstacle = random.choice(obstacles)
        if self.mode == "AMBUSH":
            gate = random.choice(escape_gates)
            inward = -safe_norm(vector(gate["pos"].x, 0, gate["pos"].z), vector(1, 0, 0))
            self.ambush_point = gate["pos"] + inward * random.uniform(2.0, 4.5) + vector(0, random.uniform(-1, 1.5), 0)
            self.ambush_wait = random.uniform(1.0, 3.0)
        if self.mode == "PATROL":
            self.patrol_index = random.randrange(len(self.patrol_points))
        if self.mode == "RITUAL_RESET":
            self.loop_timer = 0.0
            add_mark(predator.pos, 1.2, vector(1.0, 0.36, 0.72), 6.0, "loop")

    def steering_to(self, target, arrive_radius=0.5, speed_scale=1.0):
        desired = target - predator.pos
        d = mag(desired)
        if d < EPS:
            return vector(0, 0, 0)
        desired_speed = predator.max_speed * predator_speed_multiplier * speed_scale
        if d < arrive_radius:
            desired_speed *= d / max(arrive_radius, EPS)
        desired_vel = safe_norm(desired) * desired_speed
        return desired_vel - predator.vel

    def avoid_coral_accel(self):
        acc = vector(0, 0, 0)
        for o in obstacles:
            acc += o.avoidance(predator.pos, 2.4) * 7.0
        return acc

    def choose_action(self, dt, state):
        active = state["active"]
        center = state["school_center"]
        nearest = state["nearest"]

        if self.mode == "HUNT":
            if nearest:
                lead = nearest.pos + nearest.vel * clamp(state["nearest_dist"] / 5.0, 0.2, 1.2)
                acc = self.steering_to(lead, arrive_radius=0.7, speed_scale=1.15)
            else:
                acc = self.steering_to(vector(0, 1.0, 0), 1.0, 0.7)

        elif self.mode == "HERD":
            if active:
                gate = nearest_escape_gate(center, predator.pos)
                herd_dir = safe_norm(gate["pos"] - center)
                behind_school = center - herd_dir * (3.8 + clamp(state["spread"], 1.0, 5.0) * 0.3)
                behind_school += vector(0, math.sin(sim_time * 0.8) * 0.9, 0)
                acc = self.steering_to(behind_school, arrive_radius=1.4, speed_scale=0.95)
                if mag(predator.pos - behind_school) < 1.8:
                    acc += self.steering_to(center + random_unit_vector() * 1.5, 1.0, 0.65)
            else:
                acc = self.steering_to(vector(0, 1.5, 0), 1.0, 0.7)

        elif self.mode == "AMBUSH":
            if self.mode_time < self.ambush_wait:
                acc = self.steering_to(self.ambush_point, arrive_radius=0.8, speed_scale=0.55)
                predator.vel *= 0.993
            else:
                if nearest:
                    acc = self.steering_to(nearest.pos + nearest.vel * 0.45, arrive_radius=0.3, speed_scale=1.35)
                else:
                    acc = self.steering_to(vector(0, 1, 0), 1.0, 0.5)

        elif self.mode == "ORBIT_CORAL":
            if self.orbit_obstacle:
                c = self.orbit_obstacle.center
                radial = predator.pos - c
                radial.y *= 0.35
                if mag(radial) < 0.2:
                    radial = random_unit_vector()
                tangent = safe_norm(cross(vector(0, 1, 0), radial), vector(1, 0, 0))
                orbit_radius = self.orbit_obstacle.radius + 2.0 + 0.6 * math.sin(self.mode_time)
                target = c + safe_norm(radial) * orbit_radius + tangent * 1.5 + vector(0, math.sin(sim_time * 1.3) * 1.2, 0)
                acc = self.steering_to(target, arrive_radius=0.9, speed_scale=0.9)
            else:
                acc = self.steering_to(center, 1.0, 0.8)

        elif self.mode == "PATROL":
            target = self.patrol_points[self.patrol_index]
            if mag(predator.pos - target) < 1.2:
                self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
                add_mark(target, 0.45, vector(0.25, 0.52, 1.0), 3.2, "")
            acc = self.steering_to(target, arrive_radius=1.1, speed_scale=0.95)

        elif self.mode == "SCATTER":
            if active:
                pulse = vector(math.sin(sim_time * 2.7), math.sin(sim_time * 1.9) * 0.45, math.cos(sim_time * 2.2))
                target = center + safe_norm(pulse) * (1.2 + 2.2 * math.sin(self.mode_time * 1.7))
                acc = self.steering_to(target, arrive_radius=0.65, speed_scale=1.28)
                if int(self.mode_time * 2.0) != int((self.mode_time - dt) * 2.0):
                    add_mark(predator.pos, 0.55, vector(1.0, 0.85, 0.15), 3.0, "scatter")
                    spawn_particles(predator.pos, vector(1.0, 0.85, 0.15), count=5, speed=1.4)
            else:
                acc = self.steering_to(vector(0, 0, 0), 1.0, 0.8)

        elif self.mode == "CURIOUS_MARKS":
            if danger_marks:
                freshest = max(danger_marks, key=lambda m: m.life)
                offset = vector(math.sin(sim_time), 0.4 * math.cos(sim_time * 1.7), math.cos(sim_time))
                acc = self.steering_to(freshest.pos + offset * 1.8, arrive_radius=0.8, speed_scale=0.78)
            elif nearest:
                acc = self.steering_to(nearest.pos, 1.3, 0.75)
            else:
                acc = self.steering_to(vector(0, 1.0, 0), 1.0, 0.6)

        elif self.mode == "REST":
            rest_point = vector(0, FLOOR_Y + 2.2, 0)
            if obstacles:
                o = min(obstacles, key=lambda ob: mag(ob.center - predator.pos))
                rest_point = o.center + vector(0, -0.4, 0) + safe_norm(predator.pos - o.center) * (o.radius + 1.5)
            acc = self.steering_to(rest_point, arrive_radius=1.6, speed_scale=0.45)
            predator.vel *= 0.985

        elif self.mode == "RITUAL_RESET":
            self.ritual_angle += dt * 2.1
            radius = max(1.0, 5.5 - self.mode_time * 0.45)
            target = vector(math.cos(self.ritual_angle) * radius, 0.8 + math.sin(self.ritual_angle * 1.5) * 1.2, math.sin(self.ritual_angle) * radius)
            acc = self.steering_to(target, arrive_radius=0.8, speed_scale=0.85)
            if int(self.mode_time * 3) != int((self.mode_time - dt) * 3):
                add_mark(predator.pos, 0.45, vector(1.0, 0.35, 0.70), 2.5, "")
        else:
            acc = vector(0, 0, 0)

        acc += self.avoid_coral_accel()
        acc += random_unit_vector() * 0.08
        return limit(acc, predator.max_force * 1.25 * predator_speed_multiplier)

    def update(self, dt):
        self.mode_time += dt
        state = self.read_state()
        self.update_stagnation(dt, state)

        if self.completed and self.mode != "RITUAL_RESET":
            self.choose_new_mode(state, forced=True)

        if self.mode_time > self.next_switch and not self.completed:
            self.choose_new_mode(state)

        if self.mode == "RITUAL_RESET":
            self.loop_timer += dt
            if self.loop_timer > 5.4 or (self.completed and self.loop_timer > 3.0):
                reset_round(looped=True)
                self.choose_new_mode(self.read_state(), forced=True)
                return vector(0, 0, 0)

        return self.choose_action(dt, state)


ai = ReefAIController()


# -----------------------------
# Simulation state and reset
# -----------------------------

hud = label(
    pos=vector(0, CEILING_Y + 1.25, 0),
    text="",
    height=13,
    color=vector(0.05, 0.20, 0.28),
    box=False,
    opacity=0,
)

mode_label = label(
    pos=vector(-HALF.x + 1.0, CEILING_Y + 0.5, -HALF.z + 1.0),
    text="",
    height=10,
    color=vector(0.15, 0.28, 0.55),
    box=False,
    opacity=0,
)


def reset_round(looped=False):
    global round_number, caught_this_round, sim_time
    if looped:
        round_number += 1
    caught_this_round = 0
    clear_marks()
    shelter_system.active = False
    for pr in predators:
        pr.reset()
    used = []
    for f in prey:
        p = safe_random_prey_pos()
        tries = 0
        while any(mag(p - u) < 0.75 for u in used) and tries < 60:
            p = safe_random_prey_pos()
            tries += 1
        used.append(p)
        f.reset(p)
    ai.history.clear()
    ai.stagnant = False
    ai.completed = False
    ai.loop_timer = 0.0
    ai.mode_time = 0.0
    ai.next_switch = random.uniform(5, 10)
    add_mark(vector(0, 1.0, 0), 1.0, vector(0.35, 0.95, 0.75), 4.0, "new round")
    spawn_particles(vector(0, 1.0, 0), vector(0.35, 0.95, 0.75), count=28, speed=3.0)


# -----------------------------
# Keyboard control
# -----------------------------

def keydown(evt):
    global paused, boundary_mode, allow_human_override, predator_speed_multiplier
    k = evt.key.lower()
    keys_down.add(k)

    if k == "p":
        paused = not paused
    elif k == "i":
        ai.enabled = not ai.enabled
        add_mark(predator.pos, 0.8, vector(0.38, 0.75, 1.0), 3.0, "AI on" if ai.enabled else "AI off")
    elif k == "r":
        reset_round(looped=True)
    elif k == "b":
        boundary_mode = "wrap" if boundary_mode == "bounce" else "bounce"
        add_mark(predator.pos, 0.7, vector(0.35, 0.95, 0.75), 3.5, boundary_mode)
    elif k == "m":
        ai.force_next_mode()
        add_mark(predator.pos, 0.6, ai.mode_color.get(ai.mode, vector(1, 1, 1)), 3.0, ai.mode)
    elif k == "o":
        allow_human_override = not allow_human_override
        add_mark(predator.pos, 0.7, vector(0.95, 0.55, 0.25), 3.0, "override on" if allow_human_override else "override off")
    elif k == "c":
        clear_marks()
    elif k in ["+", "="]:
        predator_speed_multiplier = clamp(predator_speed_multiplier + 0.12, 0.45, 2.3)
    elif k in ["-", "_"]:
        predator_speed_multiplier = clamp(predator_speed_multiplier - 0.12, 0.45, 2.3)


def keyup(evt):
    k = evt.key.lower()
    if k in keys_down:
        keys_down.remove(k)


scene.bind("keydown", keydown)
scene.bind("keyup", keyup)


def manual_control_accel():
    f = predator.forward
    side = safe_norm(cross(f, vector(0, 1, 0)), vector(0, 0, 1))
    up = vector(0, 1, 0)

    acc = vector(0, 0, 0)
    if "w" in keys_down or "up" in keys_down:
        acc += f
    if "s" in keys_down or "down" in keys_down:
        acc -= f
    if "a" in keys_down or "left" in keys_down:
        acc -= side
    if "d" in keys_down or "right" in keys_down:
        acc += side
    if "q" in keys_down:
        acc += up
    if "e" in keys_down:
        acc -= up

    if mag(acc) > 0:
        return safe_norm(acc) * predator.max_force * 1.15 * predator_speed_multiplier
    return vector(0, 0, 0)


manual_override_timer = 0.0


def update_effects(dt):
    global particles, danger_marks
    survivors = []
    for p in particles:
        if p.update(dt):
            survivors.append(p)
        else:
            p.destroy()
    particles = survivors

    mark_survivors = []
    for m in danger_marks:
        if m.update(dt):
            mark_survivors.append(m)
        else:
            m.destroy()
    danger_marks = mark_survivors


def update_gate_animation(t):
    for i, obj in enumerate(gate_objects):
        if isinstance(obj, ring):
            obj.opacity = 0.30 + 0.18 * (0.5 + 0.5 * math.sin(t * 1.8 + i))
            obj.thickness = 0.045 + 0.012 * (0.5 + 0.5 * math.sin(t * 2.4 + i * 0.7))


def update_hud():
    active = sum(1 for f in prey if not f.caught)
    human_active = mag(manual_control_accel()) > 0 and allow_human_override
    sheltered_count = sum(1 for f in prey if (not f.caught) and getattr(f, "sheltered", False))
    shelter_state = "ACTIVE" if shelter_system.active else "quiet"
    hud.text = (
        f"Round {round_number} | Predators: {NUM_PREDATORS} | Active prey: {active}/{NUM_PREY} | "
        f"Caught this round: {caught_this_round} | Total caught: {total_caught} | "
        f"Safe zones: {shelter_state} {shelter_system.safe_count} | "
        f"Corridors: {shelter_system.corridor_count} | Sheltered: {sheltered_count}\n"
        f"AI: {'ON' if ai.enabled else 'OFF'} | Mode: {ai.mode} | "
        f"Boundary: {boundary_mode} | "
        f"{'PAUSED' if paused else 'running'} | "
        f"{'human override' if human_active else 'auto'}"
    )
    mode_label.text = (
        f"AI mode: {ai.mode}\n"
        f"stagnant: {ai.stagnant}\n"
        f"complete: {ai.completed}\n"
        f"safe-zone routing: {shelter_state}"
    )
    mode_label.color = ai.mode_color.get(ai.mode, vector(0.15, 0.28, 0.55))


# -----------------------------
# Main loop
# -----------------------------

reset_round(looped=False)

while True:
    rate(60)

    if paused:
        update_hud()
        continue

    sim_time += DT
    update_gate_animation(sim_time)

    manual_acc = manual_control_accel()
    manual_is_active = mag(manual_acc) > 0.01 and allow_human_override

    if manual_is_active:
        manual_override_timer = 1.15
    else:
        manual_override_timer = max(0, manual_override_timer - DT)

    if ai.enabled and manual_override_timer <= 0:
        accel = ai.update(DT)
    elif ai.enabled:
        ai_state = ai.read_state()
        ai.update_stagnation(DT, ai_state)
        ai.mode_time += DT
        accel = manual_acc
    else:
        accel = manual_acc
        if mag(accel) < 0.01:
            predator.vel *= 0.992

    predator.apply_accel(accel, DT)
    predator.update(DT)

    active_prey_for_pack = [f for f in prey if not f.caught]
    for idx, pr in enumerate(predators[1:], start=1):
        pack_accel = secondary_predator_accel(pr, idx, active_prey_for_pack)
        pr.apply_accel(pack_accel, DT)
        pr.update(DT)

    shelter_system.update(DT, prey, predators)

    for f in prey:
        f.update(DT, prey, predators)

    update_effects(DT)

    if ai.enabled:
        active_count = sum(1 for f in prey if not f.caught)
        if active_count == 0 and ai.mode != "RITUAL_RESET":
            ai.mode = "RITUAL_RESET"
            ai.mode_time = 0
            ai.loop_timer = 0
            add_mark(predator.pos, 1.0, vector(1.0, 0.35, 0.70), 5.0, "complete")

    update_hud()
