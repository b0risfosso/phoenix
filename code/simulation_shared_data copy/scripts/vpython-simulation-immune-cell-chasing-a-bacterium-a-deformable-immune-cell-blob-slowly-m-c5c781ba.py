from vpython import *
import random
import math
import time

# Immune Cell Chasing a Bacterium
# VPython self-contained simulation with automatic expressive AI controller.
# Controls:
#   A / D / W / S : move immune cell on the floor plane
#   Q / E         : dip immune cell down / up
#   Arrow keys    : move bacterium
#   J / L         : rotate bacterium
#   Space         : pause / resume
#   Z             : toggle AI
#   X             : detach bacterium if attached
#   R             : reset round
#   M             : cycle AI behavior mode
#   F             : force engulfment
#   H             : show / hide help text

scene = canvas(
    title="Immune Cell Chasing a Bacterium - Deformable 3D VPython Simulation",
    width=1200,
    height=760,
    background=vector(0.93, 0.97, 1.0),
    center=vector(0, 1.2, 0),
)
scene.forward = vector(-0.65, -0.34, -0.68)
scene.range = 10.5
scene.autoscale = False

random.seed()

# ----------------------------- helpers -----------------------------

def clamp(x, a, b):
    return max(a, min(b, x))

def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)

def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-7:
        return fallback
    return norm(v)

def lerp_vec(a, b, f):
    return a * (1.0 - f) + b * f

def rand_range(a, b):
    return a + random.random() * (b - a)

def random_unit_xz():
    a = random.random() * 2.0 * math.pi
    return vector(math.cos(a), 0, math.sin(a))

def random_unit_3d():
    z = rand_range(-1, 1)
    a = random.random() * 2.0 * math.pi
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(a), z, r * math.sin(a))

def limit_vec(v, max_mag):
    m = mag(v)
    if m > max_mag and m > 1e-7:
        return v * (max_mag / m)
    return v

def fibonacci_sphere_points(n):
    pts = []
    phi = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        y = 1.0 - (i / float(n - 1)) * 2.0
        radius = math.sqrt(max(0, 1.0 - y * y))
        theta = phi * i
        x = math.cos(theta) * radius
        z = math.sin(theta) * radius
        pts.append(vector(x, y, z))
    return pts

# ----------------------------- environment -----------------------------

floor = box(
    pos=vector(0, -0.08, 0),
    size=vector(20, 0.04, 20),
    color=vector(0.90, 0.96, 0.95),
    opacity=0.55,
)

grid_lines = []
for x in range(-10, 11):
    grid_lines.append(curve(
        pos=[vector(x, -0.055, -10), vector(x, -0.055, 10)],
        color=vector(0.78, 0.88, 0.88),
        radius=0.008,
    ))
for z in range(-10, 11):
    grid_lines.append(curve(
        pos=[vector(-10, -0.054, z), vector(10, -0.054, z)],
        color=vector(0.78, 0.88, 0.88),
        radius=0.008,
    ))

arena_ring = ring(
    pos=vector(0, -0.02, 0),
    axis=vector(0, 1, 0),
    radius=9.2,
    thickness=0.035,
    color=vector(0.55, 0.73, 0.78),
    opacity=0.45,
)

scene.append_to_caption(
    "\nControls: WASD/QE move immune cell | Arrow keys move bacterium | Space pause | Z AI | X detach | R reset | M mode | F force engulf | H help\n"
)

# ----------------------------- keyboard -----------------------------

keys_down = set()
show_help = True

def keydown(evt):
    global show_help
    k = evt.key.lower()
    keys_down.add(k)

def keyup(evt):
    k = evt.key.lower()
    if k in keys_down:
        keys_down.remove(k)

scene.bind("keydown", keydown)
scene.bind("keyup", keyup)

# ----------------------------- bacterium capsule -----------------------------

class Bacterium:
    def __init__(self, pos):
        self.length = 1.45
        self.radius = 0.34
        self.pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.orientation = safe_norm(random_unit_xz())
        self.spin_angle = 0.0
        self.opacity = 1.0
        self.alive = True
        self.captured = False
        self.fade = 0.0
        self.wobble_phase = random.random() * 10.0

        self.body = cylinder(
            pos=self.pos - self.orientation * self.length * 0.5,
            axis=self.orientation * self.length,
            radius=self.radius,
            color=vector(0.22, 0.72, 0.63),
            opacity=self.opacity,
        )
        self.cap_a = sphere(
            pos=self.pos - self.orientation * self.length * 0.5,
            radius=self.radius,
            color=vector(0.18, 0.64, 0.58),
            opacity=self.opacity,
        )
        self.cap_b = sphere(
            pos=self.pos + self.orientation * self.length * 0.5,
            radius=self.radius,
            color=vector(0.30, 0.82, 0.70),
            opacity=self.opacity,
        )
        self.rings = []
        for s in [-0.35, 0.0, 0.35]:
            self.rings.append(ring(
                pos=self.pos + self.orientation * self.length * s,
                axis=self.orientation,
                radius=self.radius * 1.04,
                thickness=0.028,
                color=vector(0.96, 0.82, 0.42),
                opacity=0.85,
            ))

        self.hairs = []
        for i in range(10):
            side = random_unit_3d()
            side.y *= 0.35
            side = safe_norm(side)
            along = rand_range(-0.45, 0.45)
            self.hairs.append({
                "side": side,
                "along": along,
                "obj": cylinder(
                    pos=self.pos,
                    axis=side * 0.36,
                    radius=0.018,
                    color=vector(0.26, 0.58, 0.50),
                    opacity=0.55,
                )
            })

        self.label = label(
            pos=self.pos + vector(0, 0.9, 0),
            text="bacterium capsule",
            box=False,
            opacity=0,
            color=vector(0.12, 0.36, 0.32),
            height=13,
        )

    def set_visible(self, visible):
        self.body.visible = visible
        self.cap_a.visible = visible
        self.cap_b.visible = visible
        for r in self.rings:
            r.visible = visible
        for h in self.hairs:
            h["obj"].visible = visible
        self.label.visible = visible

    def set_opacity(self, op):
        self.opacity = clamp(op, 0.0, 1.0)
        for obj in [self.body, self.cap_a, self.cap_b]:
            obj.opacity = self.opacity
        for r in self.rings:
            r.opacity = self.opacity * 0.85
        for h in self.hairs:
            h["obj"].opacity = self.opacity * 0.55

    def reset(self, pos):
        self.pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.orientation = safe_norm(random_unit_xz())
        self.spin_angle = 0
        self.alive = True
        self.captured = False
        self.fade = 0.0
        self.set_opacity(1.0)
        self.set_visible(True)
        self.update_geometry(0)

    def update_free_motion(self, dt, move_velocity, rotate_cmd=0.0):
        self.vel = self.vel * 0.82 + move_velocity * 0.18
        self.pos += self.vel * dt

        self.spin_angle += rotate_cmd * dt * 2.5
        if mag(self.vel) > 0.05:
            desired = safe_norm(vector(self.vel.x, self.vel.y * 0.15, self.vel.z), self.orientation)
            self.orientation = safe_norm(lerp_vec(self.orientation, desired, 0.055), self.orientation)

        if abs(rotate_cmd) > 0.001:
            a = rotate_cmd * dt * 1.4
            c = math.cos(a)
            s = math.sin(a)
            o = self.orientation
            self.orientation = safe_norm(vector(o.x * c - o.z * s, o.y, o.x * s + o.z * c), self.orientation)

    def update_geometry(self, t):
        wobble = 0.08 * math.sin(t * 2.4 + self.wobble_phase)
        tilted = safe_norm(self.orientation + vector(0, wobble, 0), self.orientation)

        self.body.pos = self.pos - tilted * self.length * 0.5
        self.body.axis = tilted * self.length
        self.body.radius = self.radius
        self.cap_a.pos = self.pos - tilted * self.length * 0.5
        self.cap_b.pos = self.pos + tilted * self.length * 0.5
        self.cap_a.radius = self.radius
        self.cap_b.radius = self.radius

        for idx, s in enumerate([-0.35, 0.0, 0.35]):
            self.rings[idx].pos = self.pos + tilted * self.length * s
            self.rings[idx].axis = tilted
            self.rings[idx].radius = self.radius * 1.04

        for h in self.hairs:
            base = self.pos + tilted * self.length * h["along"] + h["side"] * self.radius * 0.82
            wave = safe_norm(h["side"] + vector(0, 0.25 * math.sin(t * 4 + h["along"] * 8), 0), h["side"])
            h["obj"].pos = base
            h["obj"].axis = wave * (0.25 + 0.06 * math.sin(t * 5 + h["along"] * 13))
        self.label.pos = self.pos + vector(0, 0.9, 0)

# ----------------------------- immune cell -----------------------------

class Pseudopod:
    def __init__(self, base_dir, phase, color):
        self.base_dir = safe_norm(base_dir)
        self.dir = self.base_dir
        self.phase = phase
        self.length = 0.8
        self.color = color
        self.shaft = cylinder(
            pos=vector(0, 0, 0),
            axis=vector(1, 0, 0),
            radius=0.11,
            color=color,
            opacity=0.42,
        )
        self.tip = sphere(
            pos=vector(0, 0, 0),
            radius=0.18,
            color=color,
            opacity=0.55,
        )

    def update(self, center, radius, target_dir, t, wrap_factor, chase_factor, ritual_factor):
        front = max(0.0, dot(self.base_dir, target_dir))
        side_swirl = cross(target_dir, vector(0, 1, 0))
        if mag(side_swirl) < 0.01:
            side_swirl = vector(1, 0, 0)
        side_swirl = safe_norm(side_swirl)

        ring_dir = safe_norm(target_dir * 0.55 + side_swirl * math.sin(self.phase * 2.7) * 0.65 + vector(0, math.cos(self.phase * 1.9) * 0.25, 0))
        desired = safe_norm(
            self.base_dir * (1.0 - 0.45 * front * chase_factor) +
            target_dir * (0.85 * front * chase_factor) +
            ring_dir * (wrap_factor * 1.6),
            self.dir
        )
        self.dir = safe_norm(lerp_vec(self.dir, desired, 0.08 + 0.05 * wrap_factor), self.dir)

        pulse = 0.35 + 0.32 * math.sin(t * 2.3 + self.phase) + 0.16 * math.sin(t * 4.9 + self.phase * 1.7)
        target_extension = (front ** 2.2) * chase_factor * 1.05
        ritual_extension = ritual_factor * (0.25 + 0.3 * math.sin(t * 3.0 + self.phase))
        wrap_extension = wrap_factor * (1.35 + 0.4 * math.sin(t * 4.0 + self.phase))
        self.length = radius * (0.25 + pulse + target_extension + ritual_extension + wrap_extension)
        self.length = clamp(self.length, radius * 0.25, radius * 2.35)

        self.shaft.pos = center + self.dir * radius * 0.58
        self.shaft.axis = self.dir * self.length
        self.shaft.radius = 0.09 + 0.035 * wrap_factor + 0.02 * max(0, math.sin(t * 5 + self.phase))
        self.tip.pos = self.shaft.pos + self.shaft.axis
        self.tip.radius = 0.15 + 0.08 * wrap_factor + 0.02 * math.sin(t * 4 + self.phase)
        self.shaft.opacity = 0.32 + 0.20 * wrap_factor
        self.tip.opacity = 0.48 + 0.22 * wrap_factor

    def tip_position(self):
        return self.tip.pos

class ImmuneCell:
    def __init__(self, pos):
        self.pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.radius = 1.35
        self.wrap_factor = 0.0
        self.digest_pulse = 0.0
        self.chase_factor = 1.0
        self.ritual_factor = 0.0
        self.target_dir = vector(1, 0, 0)

        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=vector(1.0, 0.62, 0.78),
            opacity=0.36,
            shininess=0.35,
        )
        self.core = sphere(
            pos=self.pos,
            radius=self.radius * 0.46,
            color=vector(0.82, 0.37, 0.70),
            opacity=0.22,
        )

        self.membrane_normals = fibonacci_sphere_points(58)
        self.membrane_phases = [random.random() * 10.0 for _ in self.membrane_normals]
        self.membrane = []
        for i, n in enumerate(self.membrane_normals):
            self.membrane.append(sphere(
                pos=self.pos + n * self.radius,
                radius=0.095,
                color=vector(1.0, 0.44 + random.random() * 0.1, 0.70 + random.random() * 0.12),
                opacity=0.50,
                shininess=0.15,
            ))

        self.pseudopods = []
        dirs = fibonacci_sphere_points(13)
        for i, d in enumerate(dirs):
            if d.y < -0.7:
                d.y *= 0.3
                d = safe_norm(d)
            self.pseudopods.append(Pseudopod(
                d,
                random.random() * 10.0,
                vector(1.0, 0.55 + random.random() * 0.12, 0.74 + random.random() * 0.08)
            ))

        self.engulf_lobes = []
        for i in range(7):
            self.engulf_lobes.append(sphere(
                pos=self.pos,
                radius=0.35,
                color=vector(1.0, 0.58, 0.76),
                opacity=0.0,
                visible=True,
            ))

        self.phagosome = sphere(
            pos=self.pos,
            radius=0.2,
            color=vector(1.0, 0.92, 0.45),
            opacity=0.0,
            visible=True,
        )

        self.path = curve(color=vector(0.98, 0.50, 0.70), radius=0.018, opacity=0.42)
        self.path.append(self.pos)
        self.path_timer = 0.0

        self.label = label(
            pos=self.pos + vector(0, 1.95, 0),
            text="immune cell blob",
            box=False,
            opacity=0,
            color=vector(0.52, 0.13, 0.36),
            height=14,
        )

    def reset(self, pos):
        self.pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.wrap_factor = 0
        self.digest_pulse = 0
        self.chase_factor = 1
        self.ritual_factor = 0
        self.target_dir = vector(1, 0, 0)
        self.path.clear()
        self.path.append(self.pos)
        for l in self.engulf_lobes:
            l.opacity = 0
        self.phagosome.opacity = 0

    def move(self, velocity, dt):
        self.vel = self.vel * 0.82 + velocity * 0.18
        self.pos += self.vel * dt

    def update(self, dt, t, target_pos, phase, ai_mode="CHASE"):
        to_target = target_pos - self.pos
        if mag(to_target) > 1e-5:
            self.target_dir = safe_norm(to_target, self.target_dir)

        if phase == "seek":
            desired_wrap = 0.0
            desired_digest = 0.0
            self.chase_factor = 1.0
        elif phase == "attach":
            desired_wrap = 0.25
            desired_digest = 0.0
            self.chase_factor = 1.25
        elif phase == "engulf":
            desired_wrap = 1.0
            desired_digest = 0.15
            self.chase_factor = 1.15
        elif phase == "digest":
            desired_wrap = 0.45
            desired_digest = 1.0
            self.chase_factor = 0.35
        else:
            desired_wrap = 0.12
            desired_digest = 0.25
            self.chase_factor = 0.25

        self.ritual_factor = 1.0 if ai_mode in ["RITUAL_WRAP", "ARTISTIC_MARK", "ORBIT"] else 0.25 if ai_mode == "POKE" else 0.0
        self.wrap_factor += (desired_wrap - self.wrap_factor) * clamp(dt * 2.1, 0, 1)
        self.digest_pulse += (desired_digest - self.digest_pulse) * clamp(dt * 2.0, 0, 1)

        breathing = 1.0 + 0.035 * math.sin(t * 2.0) + 0.03 * self.digest_pulse * math.sin(t * 8.0)
        self.body.pos = self.pos
        self.body.radius = self.radius * breathing * (1.0 + 0.06 * self.wrap_factor)
        self.core.pos = self.pos + vector(0.08 * math.sin(t * 1.4), 0.06 * math.sin(t * 1.7), 0.08 * math.cos(t * 1.3))
        self.core.radius = self.radius * (0.43 + 0.04 * self.digest_pulse * math.sin(t * 5))

        for i, n in enumerate(self.membrane_normals):
            phase_i = self.membrane_phases[i]
            front = max(0.0, dot(n, self.target_dir))
            wave = 0.065 * math.sin(t * 2.2 + phase_i) + 0.035 * math.sin(t * 4.9 + phase_i * 1.3)
            chase_bulge = 0.52 * (front ** 3.8) * self.chase_factor
            wrap_bulge = self.wrap_factor * 0.48 * (front ** 1.9)
            digest_wobble = self.digest_pulse * 0.09 * math.sin(t * 10 + phase_i)
            downward_flatten = -0.08 if n.y < -0.55 else 0.0
            local_radius = self.radius * (1.0 + wave + chase_bulge + wrap_bulge + digest_wobble + downward_flatten)

            p = self.pos + n * local_radius
            if front > 0.72 and self.wrap_factor > 0.2:
                p += self.target_dir * self.radius * self.wrap_factor * 0.35
            self.membrane[i].pos = p
            self.membrane[i].radius = 0.08 + 0.035 * front + 0.025 * self.wrap_factor
            self.membrane[i].opacity = 0.42 + 0.18 * front + 0.08 * self.wrap_factor

        for p in self.pseudopods:
            p.update(self.pos, self.radius, self.target_dir, t, self.wrap_factor, self.chase_factor, self.ritual_factor)

        for i, lobe in enumerate(self.engulf_lobes):
            angle = i * 2.0 * math.pi / len(self.engulf_lobes) + t * 0.7
            side = cross(self.target_dir, vector(0, 1, 0))
            if mag(side) < 0.01:
                side = vector(1, 0, 0)
            side = safe_norm(side)
            up = safe_norm(cross(side, self.target_dir), vector(0, 1, 0))
            ring_offset = side * math.cos(angle) * self.radius * 0.62 + up * math.sin(angle) * self.radius * 0.62
            lobe.pos = self.pos + self.target_dir * self.radius * (0.55 + 0.28 * self.wrap_factor) + ring_offset * (0.5 + 0.4 * self.wrap_factor)
            lobe.radius = self.radius * (0.18 + 0.20 * self.wrap_factor + 0.03 * math.sin(t * 4 + i))
            lobe.opacity = 0.02 + 0.30 * self.wrap_factor

        self.phagosome.pos = lerp_vec(self.phagosome.pos, target_pos, clamp(dt * 4.0, 0, 1))
        self.phagosome.radius = self.radius * (0.16 + 0.43 * self.wrap_factor + 0.05 * self.digest_pulse * math.sin(t * 5))
        self.phagosome.opacity = 0.02 + 0.20 * self.wrap_factor + 0.12 * self.digest_pulse

        self.path_timer += dt
        if self.path_timer > 0.18:
            self.path_timer = 0.0
            self.path.append(self.pos)
            if len(self.path.point(0)["pos"] if False else []) > 900:
                pass

        self.label.pos = self.pos + vector(0, 1.95, 0)

    def pseudopod_tip_positions(self):
        return [p.tip_position() for p in self.pseudopods]

# ----------------------------- digestion particles -----------------------------

class DigestionParticle:
    def __init__(self):
        self.phase = random.random() * math.tau
        self.phase2 = random.random() * math.tau
        self.radius = rand_range(0.18, 1.05)
        self.speed = rand_range(0.9, 2.2)
        self.obj = sphere(
            pos=vector(0, 0, 0),
            radius=rand_range(0.035, 0.075),
            color=random.choice([
                vector(1.0, 0.92, 0.25),
                vector(0.74, 1.0, 0.32),
                vector(1.0, 0.67, 0.28),
                vector(0.45, 0.95, 0.85),
            ]),
            opacity=0.0,
            emissive=True,
            make_trail=False,
        )

    def update(self, center, t, active, intensity=1.0):
        if not active:
            self.obj.opacity += (0.0 - self.obj.opacity) * 0.12
            return

        a = self.phase + t * self.speed * intensity
        b = self.phase2 + t * self.speed * 0.63 * intensity
        r = self.radius * (0.65 + 0.25 * math.sin(t * 1.5 + self.phase2))
        pos = center + vector(
            math.cos(a) * r,
            math.sin(b) * r * 0.55,
            math.sin(a) * r
        )
        pos += vector(
            0.16 * math.sin(t * 3.2 + self.phase),
            0.12 * math.cos(t * 2.4 + self.phase2),
            0.16 * math.cos(t * 2.8 + self.phase)
        )
        self.obj.pos = pos
        self.obj.opacity += (0.78 - self.obj.opacity) * 0.08
        self.obj.radius = 0.04 + 0.025 * (0.5 + 0.5 * math.sin(t * 6 + self.phase))

# ----------------------------- expressive AI controller -----------------------------

class ExpressiveAIController:
    def __init__(self):
        self.enabled = True
        self.modes = [
            "CHASE",
            "ORBIT",
            "POKE",
            "CAREFUL",
            "CURIOUS",
            "CHAOTIC",
            "ARTISTIC_MARK",
            "RITUAL_WRAP",
            "DIGESTION_DANCE",
        ]
        self.mode = "CHASE"
        self.previous_modes = []
        self.mode_timer = 0.0
        self.mode_duration = rand_range(5.0, 9.0)
        self.stagnation_timer = 0.0
        self.last_signature = None
        self.completion_timer = 0.0
        self.reset_requested = False
        self.ai_clock = 0.0

    def cycle_mode(self):
        idx = self.modes.index(self.mode) if self.mode in self.modes else 0
        self.mode = self.modes[(idx + 1) % len(self.modes)]
        self.mode_timer = 0.0
        self.mode_duration = rand_range(5.0, 10.0)

    def choose_new_mode(self, sim):
        phase = sim.phase
        if phase == "seek":
            candidates = ["CHASE", "ORBIT", "POKE", "CAREFUL", "CURIOUS", "CHAOTIC", "ARTISTIC_MARK"]
        elif phase == "attach":
            candidates = ["POKE", "RITUAL_WRAP", "CAREFUL", "ORBIT"]
        elif phase == "engulf":
            candidates = ["RITUAL_WRAP", "ARTISTIC_MARK", "DIGESTION_DANCE"]
        elif phase == "digest":
            candidates = ["DIGESTION_DANCE", "ARTISTIC_MARK", "RITUAL_WRAP"]
        else:
            candidates = ["ARTISTIC_MARK", "CURIOUS", "CHASE"]

        candidates = [m for m in candidates if m not in self.previous_modes[-2:]] or candidates
        self.mode = random.choice(candidates)
        self.previous_modes.append(self.mode)
        if len(self.previous_modes) > 6:
            self.previous_modes = self.previous_modes[-6:]
        self.mode_timer = 0.0
        self.mode_duration = rand_range(4.5, 10.0)

    def detect_stagnation_or_completion(self, sim, dt):
        d = mag(sim.bacterium.pos - sim.immune.pos)
        progress = sim.phase_progress()
        signature = (d, progress, sim.round_id)

        if self.last_signature is not None:
            dd = abs(signature[0] - self.last_signature[0])
            dp = abs(signature[1] - self.last_signature[1])
            if dd < 0.006 and dp < 0.002 and sim.phase in ["seek", "attach", "engulf"]:
                self.stagnation_timer += dt
            else:
                self.stagnation_timer = max(0, self.stagnation_timer - dt * 1.5)

        self.last_signature = signature

        if sim.phase == "complete":
            self.completion_timer += dt
            if self.completion_timer > 4.2:
                self.reset_requested = True
        else:
            self.completion_timer = 0.0

        if self.stagnation_timer > 18.0:
            self.reset_requested = True

    def update(self, sim, dt):
        self.ai_clock += dt
        action = {
            "immune_velocity": vector(0, 0, 0),
            "bacterium_velocity": vector(0, 0, 0),
            "bacterium_rotate": 0.0,
            "mark": False,
            "spill": False,
            "detach": False,
            "particle_intensity": 1.0,
        }

        if not self.enabled:
            return action

        self.detect_stagnation_or_completion(sim, dt)

        if self.reset_requested and not sim.paused:
            sim.reset_round()
            self.reset_requested = False
            self.stagnation_timer = 0.0
            self.completion_timer = 0.0
            self.choose_new_mode(sim)
            return action

        self.mode_timer += dt
        if self.mode_timer > self.mode_duration:
            self.choose_new_mode(sim)

        immune = sim.immune
        bac = sim.bacterium
        to_bac = bac.pos - immune.pos
        dist = mag(to_bac)
        dir_to_bac = safe_norm(to_bac, vector(1, 0, 0))
        tangent = safe_norm(cross(vector(0, 1, 0), dir_to_bac), vector(0, 0, 1))
        if math.sin(self.ai_clock * 0.35) < 0:
            tangent *= -1

        flee_dir = safe_norm(bac.pos - immune.pos, random_unit_xz())
        playful_wave = vector(
            math.sin(self.ai_clock * 1.7),
            0.25 * math.sin(self.ai_clock * 2.3),
            math.cos(self.ai_clock * 1.3),
        )

        if sim.phase in ["engulf", "digest", "complete"]:
            if self.mode not in ["RITUAL_WRAP", "DIGESTION_DANCE", "ARTISTIC_MARK"]:
                self.mode = "DIGESTION_DANCE"
                self.mode_timer = 0.0

        if self.mode == "CHASE":
            action["immune_velocity"] = dir_to_bac * 1.35
            action["bacterium_velocity"] = flee_dir * 0.22 + playful_wave * 0.08
            action["bacterium_rotate"] = 0.5 * math.sin(self.ai_clock)
        elif self.mode == "ORBIT":
            action["immune_velocity"] = tangent * 0.95 + dir_to_bac * clamp((dist - 1.8) * 0.35, -0.2, 0.8)
            action["bacterium_velocity"] = -tangent * 0.25 + flee_dir * 0.05
            action["bacterium_rotate"] = 1.1
            action["mark"] = True
        elif self.mode == "POKE":
            pulse = 0.4 + 0.9 * max(0, math.sin(self.ai_clock * 2.6))
            action["immune_velocity"] = dir_to_bac * pulse + tangent * 0.18 * math.sin(self.ai_clock * 5.0)
            action["bacterium_velocity"] = flee_dir * 0.18 * max(0, math.sin(self.ai_clock * 2.6 - 0.7))
            if dist < 2.3 and random.random() < 0.015:
                action["spill"] = True
        elif self.mode == "CAREFUL":
            ideal = 2.3
            approach = clamp((dist - ideal) * 0.45, -0.45, 0.65)
            action["immune_velocity"] = dir_to_bac * approach + tangent * 0.18
            action["bacterium_velocity"] = playful_wave * 0.05
        elif self.mode == "CURIOUS":
            action["immune_velocity"] = (dir_to_bac * 0.55 + playful_wave * 0.45)
            action["bacterium_velocity"] = (-playful_wave * 0.18 + tangent * 0.12)
            if random.random() < 0.01:
                action["mark"] = True
        elif self.mode == "CHAOTIC":
            jitter = safe_norm(playful_wave + random_unit_3d() * 0.7)
            action["immune_velocity"] = dir_to_bac * 0.75 + jitter * 0.65
            action["bacterium_velocity"] = flee_dir * 0.45 + random_unit_xz() * 0.35
            action["bacterium_rotate"] = rand_range(-2.5, 2.5)
            action["spill"] = random.random() < 0.025
        elif self.mode == "ARTISTIC_MARK":
            action["immune_velocity"] = tangent * 0.55 + dir_to_bac * 0.25 + vector(0, 0.14 * math.sin(self.ai_clock * 2.2), 0)
            action["bacterium_velocity"] = -tangent * 0.15
            action["mark"] = True
            action["particle_intensity"] = 1.4
        elif self.mode == "RITUAL_WRAP":
            action["immune_velocity"] = dir_to_bac * clamp((dist - 0.45) * 0.22, 0, 0.42) + tangent * 0.22 * math.sin(self.ai_clock * 1.8)
            action["bacterium_velocity"] = vector(0, 0, 0)
            action["bacterium_rotate"] = 0.35 * math.sin(self.ai_clock * 2.0)
            action["mark"] = random.random() < 0.04
            action["particle_intensity"] = 1.7
        elif self.mode == "DIGESTION_DANCE":
            action["immune_velocity"] = vector(0.18 * math.sin(self.ai_clock * 1.4), 0.08 * math.sin(self.ai_clock * 2.1), 0.18 * math.cos(self.ai_clock * 1.2))
            action["bacterium_velocity"] = vector(0, 0, 0)
            action["particle_intensity"] = 2.4
            action["spill"] = random.random() < 0.035

        return action

# ----------------------------- simulation -----------------------------

class Simulation:
    def __init__(self):
        self.t = 0.0
        self.round_id = 0
        self.paused = False
        self.help_visible = True
        self.arena_radius = 8.9

        self.immune = ImmuneCell(vector(-4.8, 1.25, -2.2))
        self.bacterium = Bacterium(vector(4.6, 0.7, 2.2))
        self.ai = ExpressiveAIController()

        self.phase = "seek"
        self.phase_timer = 0.0
        self.attach_dir = vector(1, 0, 0)
        self.engulf_start_pos = vector(0, 0, 0)
        self.digest_center = vector(0, 0, 0)

        self.particles = [DigestionParticle() for _ in range(80)]
        self.markers = []
        self.marker_timer = 0.0
        self.spill_timer = 0.0
        self.manual_override_timer = 0.0

        self.status_label = label(
            pos=vector(-8.9, 5.4, -7.9),
            text="",
            box=True,
            border=8,
            opacity=0.18,
            color=vector(0.1, 0.22, 0.28),
            background=vector(1, 1, 1),
            height=13,
        )
        self.help_label = label(
            pos=vector(0, 6.4, 0),
            text="",
            box=True,
            border=8,
            opacity=0.20,
            color=vector(0.12, 0.20, 0.28),
            background=vector(1, 1, 1),
            height=12,
        )

        self.reset_round()

    def phase_progress(self):
        if self.phase == "seek":
            d = mag(self.bacterium.pos - self.immune.pos)
            return clamp(1.0 - d / 11.0, 0, 1)
        if self.phase == "attach":
            return clamp(self.phase_timer / 1.6, 0, 1)
        if self.phase == "engulf":
            return clamp(self.phase_timer / 4.0, 0, 1)
        if self.phase == "digest":
            return clamp(self.phase_timer / 7.0, 0, 1)
        return 1.0

    def reset_round(self):
        self.round_id += 1
        self.phase = "seek"
        self.phase_timer = 0.0
        self.attach_dir = random_unit_xz()
        self.engulf_start_pos = vector(0, 0, 0)
        self.digest_center = vector(0, 0, 0)

        immune_pos = random_unit_xz() * rand_range(4.0, 6.5) + vector(0, 1.25, 0)
        bac_pos = -safe_norm(vector(immune_pos.x, 0, immune_pos.z), random_unit_xz()) * rand_range(4.0, 6.8) + vector(0, 0.7, 0)
        bac_pos += random_unit_xz() * rand_range(0.0, 1.0)

        self.immune.reset(immune_pos)
        self.bacterium.reset(bac_pos)

        for p in self.particles:
            p.obj.opacity = 0.0

        for m in self.markers:
            m["obj"].visible = False
        self.markers = []

        self.ai.stagnation_timer = 0.0
        self.ai.completion_timer = 0.0
        self.ai.last_signature = None
        self.ai.choose_new_mode(self)

    def detach(self):
        if self.phase in ["attach", "engulf"] and self.phase_timer < 1.8:
            away = safe_norm(self.bacterium.pos - self.immune.pos, random_unit_xz())
            self.bacterium.captured = False
            self.bacterium.alive = True
            self.bacterium.set_opacity(1.0)
            self.bacterium.pos = self.immune.pos + away * 2.8 + vector(0, 0.1, 0)
            self.bacterium.vel = away * 1.4
            self.phase = "seek"
            self.phase_timer = 0.0

    def force_engulf(self):
        self.attach_dir = safe_norm(self.bacterium.pos - self.immune.pos, vector(1, 0, 0))
        self.bacterium.captured = True
        self.phase = "engulf"
        self.phase_timer = 0.0
        self.engulf_start_pos = self.bacterium.pos

    def add_marker(self, pos, color_value=None, size=0.08, life=7.5):
        if color_value is None:
            color_value = random.choice([
                vector(1.0, 0.66, 0.82),
                vector(0.96, 0.82, 0.35),
                vector(0.48, 0.90, 0.86),
                vector(0.72, 0.70, 1.0),
            ])
        m = sphere(
            pos=pos,
            radius=size,
            color=color_value,
            opacity=0.45,
            emissive=False,
        )
        self.markers.append({"obj": m, "age": 0.0, "life": life})
        if len(self.markers) > 180:
            old = self.markers.pop(0)
            old["obj"].visible = False

    def spill_particles(self, origin, count=8):
        for i in range(count):
            self.add_marker(
                origin + random_unit_3d() * rand_range(0.05, 0.55),
                random.choice([vector(1, 0.88, 0.25), vector(0.7, 1, 0.35), vector(0.38, 0.88, 0.82)]),
                rand_range(0.035, 0.085),
                rand_range(3.0, 6.5),
            )

    def update_markers(self, dt):
        alive = []
        for m in self.markers:
            m["age"] += dt
            f = 1.0 - m["age"] / m["life"]
            if f <= 0:
                m["obj"].visible = False
            else:
                m["obj"].opacity = 0.45 * f
                m["obj"].radius *= 1.0 + 0.05 * dt
                alive.append(m)
        self.markers = alive

    def constrain_to_arena(self, obj, min_y=0.28, max_y=3.2):
        flat = vector(obj.pos.x, 0, obj.pos.z)
        r = mag(flat)
        if r > self.arena_radius:
            n = safe_norm(flat, random_unit_xz())
            obj.pos.x = n.x * self.arena_radius
            obj.pos.z = n.z * self.arena_radius
            if hasattr(obj, "vel"):
                obj.vel -= 1.8 * dot(obj.vel, n) * n
                obj.vel *= 0.65
        obj.pos.y = clamp(obj.pos.y, min_y, max_y)

    def read_human_input(self, dt):
        global show_help

        immune_cmd = vector(0, 0, 0)
        bac_cmd = vector(0, 0, 0)
        bac_rot = 0.0
        instant = {
            "toggle_pause": False,
            "toggle_ai": False,
            "reset": False,
            "detach": False,
            "cycle_mode": False,
            "force_engulf": False,
            "toggle_help": False,
        }

        if "w" in keys_down:
            immune_cmd.z -= 1
        if "s" in keys_down:
            immune_cmd.z += 1
        if "a" in keys_down:
            immune_cmd.x -= 1
        if "d" in keys_down:
            immune_cmd.x += 1
        if "q" in keys_down:
            immune_cmd.y -= 0.8
        if "e" in keys_down:
            immune_cmd.y += 0.8

        if "up" in keys_down:
            bac_cmd.z -= 1
        if "down" in keys_down:
            bac_cmd.z += 1
        if "left" in keys_down:
            bac_cmd.x -= 1
        if "right" in keys_down:
            bac_cmd.x += 1
        if "u" in keys_down:
            bac_cmd.y += 0.7
        if "o" in keys_down:
            bac_cmd.y -= 0.7
        if "j" in keys_down:
            bac_rot -= 1
        if "l" in keys_down:
            bac_rot += 1

        pressed_once_keys = {
            " ": "toggle_pause",
            "z": "toggle_ai",
            "r": "reset",
            "x": "detach",
            "m": "cycle_mode",
            "f": "force_engulf",
            "h": "toggle_help",
        }

        if not hasattr(self, "_last_keys"):
            self._last_keys = set()
        for key_name, action_name in pressed_once_keys.items():
            if key_name in keys_down and key_name not in self._last_keys:
                instant[action_name] = True
        self._last_keys = set(keys_down)

        if mag(immune_cmd) > 0 or mag(bac_cmd) > 0 or abs(bac_rot) > 0:
            self.manual_override_timer = 1.2

        return safe_norm(immune_cmd) * 1.85 if mag(immune_cmd) > 0 else vector(0, 0, 0), \
            safe_norm(bac_cmd) * 1.45 if mag(bac_cmd) > 0 else vector(0, 0, 0), \
            bac_rot, instant

    def update_phase_logic(self, dt):
        self.phase_timer += dt
        immune = self.immune
        bac = self.bacterium
        dist = mag(bac.pos - immune.pos)

        if self.phase == "seek":
            collided = dist < immune.radius * 1.05 + bac.radius * 0.85
            pseudopod_contact = False
            for tip in immune.pseudopod_tip_positions():
                if mag(tip - bac.pos) < bac.radius + 0.35:
                    pseudopod_contact = True
                    break

            if collided or pseudopod_contact:
                self.phase = "attach"
                self.phase_timer = 0.0
                self.attach_dir = safe_norm(bac.pos - immune.pos, vector(1, 0, 0))
                bac.captured = True
                bac.vel = vector(0, 0, 0)
                self.spill_particles(bac.pos, 10)

        elif self.phase == "attach":
            p = smoothstep(self.phase_timer / 1.6)
            contact_pos = immune.pos + self.attach_dir * immune.radius * 0.92 + vector(0, 0.06 * math.sin(self.t * 8), 0)
            bac.pos = lerp_vec(bac.pos, contact_pos, 0.10 + 0.12 * p)
            bac.orientation = safe_norm(lerp_vec(bac.orientation, -self.attach_dir, 0.04), bac.orientation)
            if self.phase_timer > 1.6:
                self.phase = "engulf"
                self.phase_timer = 0.0
                self.engulf_start_pos = bac.pos
                self.spill_particles(bac.pos, 14)

        elif self.phase == "engulf":
            p = smoothstep(self.phase_timer / 4.0)
            inside_target = immune.pos + self.attach_dir * immune.radius * (0.75 * (1.0 - p)) + vector(0, 0.05 * math.sin(self.t * 6), 0)
            bac.pos = lerp_vec(self.engulf_start_pos, inside_target, p)
            bac.orientation = safe_norm(lerp_vec(bac.orientation, self.attach_dir, 0.02), bac.orientation)
            bac.set_opacity(1.0 - 0.25 * p)
            self.digest_center = bac.pos
            if self.phase_timer > 4.0:
                self.phase = "digest"
                self.phase_timer = 0.0
                self.digest_center = immune.pos
                self.spill_particles(immune.pos, 22)

        elif self.phase == "digest":
            p = smoothstep(self.phase_timer / 7.0)
            swirl = vector(
                math.cos(self.t * 2.2) * 0.36 * (1 - p),
                math.sin(self.t * 3.1) * 0.22 * (1 - p),
                math.sin(self.t * 2.2) * 0.36 * (1 - p),
            )
            bac.pos = immune.pos + swirl
            bac.set_opacity((1.0 - p) * 0.68)
            self.digest_center = bac.pos
            if self.phase_timer > 7.0:
                self.phase = "complete"
                self.phase_timer = 0.0
                bac.set_opacity(0.0)
                bac.set_visible(False)
                self.spill_particles(immune.pos, 32)

        elif self.phase == "complete":
            pass

    def update_labels(self):
        ai_status = "ON" if self.ai.enabled else "OFF"
        manual = "manual override" if self.manual_override_timer > 0 else "auto"
        self.status_label.text = (
            f"Round {self.round_id} | Phase: {self.phase.upper()} | AI: {ai_status} | Mode: {self.ai.mode}\n"
            f"Progress: {self.phase_progress():.2f} | Control: {manual} | Stagnation: {self.ai.stagnation_timer:.1f}s\n"
            f"Immune can move, dip, wrap, collide, mark, orbit, and engulf. Bacterium can flee, rotate, attach, detach, and fade."
        )

        self.immune.label.visible = self.help_visible
        self.bacterium.label.visible = self.help_visible

        if self.help_visible:
            self.help_label.visible = True
            self.help_label.text = (
                "AI behavior modes: CHASE, ORBIT, POKE, CAREFUL, CURIOUS, CHAOTIC, ARTISTIC_MARK, RITUAL_WRAP, DIGESTION_DANCE\n"
                "The AI reads distance, phase, timers, positions, velocity, collision state, and completion/stagnation.\n"
                "It chooses velocities, rotations, wrapping style, marking, spilling particles, detaching, and resetting new rounds.\n"
                "Human keys still work while AI runs; press Z to pause AI, Space to pause simulation, X to detach, R to reset."
            )
        else:
            self.help_label.visible = False

    def update(self, dt):
        if self.paused:
            self.update_labels()
            return

        self.t += dt
        self.manual_override_timer = max(0, self.manual_override_timer - dt)

        human_immune_vel, human_bac_vel, human_bac_rot, instant = self.read_human_input(dt)

        if instant["toggle_pause"]:
            self.paused = not self.paused
        if instant["toggle_ai"]:
            self.ai.enabled = not self.ai.enabled
        if instant["reset"]:
            self.reset_round()
        if instant["detach"]:
            self.detach()
        if instant["cycle_mode"]:
            self.ai.cycle_mode()
        if instant["force_engulf"]:
            self.force_engulf()
        if instant["toggle_help"]:
            self.help_visible = not self.help_visible

        ai_action = self.ai.update(self, dt)

        ai_scale = 0.35 if self.manual_override_timer > 0 else 1.0
        immune_vel = ai_action["immune_velocity"] * ai_scale + human_immune_vel
        bac_vel = ai_action["bacterium_velocity"] * ai_scale + human_bac_vel
        bac_rot = ai_action["bacterium_rotate"] * ai_scale + human_bac_rot

        if self.phase in ["seek", "attach"]:
            self.immune.move(immune_vel, dt)
        elif self.phase in ["engulf", "digest", "complete"]:
            self.immune.move(immune_vel * 0.45, dt)

        self.constrain_to_arena(self.immune, min_y=0.55, max_y=3.2)

        if self.phase == "seek" and not self.bacterium.captured:
            self.bacterium.update_free_motion(dt, bac_vel, bac_rot)
            self.constrain_to_arena(self.bacterium, min_y=0.34, max_y=2.4)

        self.update_phase_logic(dt)

        target_pos = self.bacterium.pos if self.bacterium.body.visible else self.immune.pos + self.immune.target_dir
        self.immune.update(dt, self.t, target_pos, self.phase, self.ai.mode)
        self.bacterium.update_geometry(self.t)

        digestion_active = self.phase in ["digest", "complete", "engulf"]
        intensity = ai_action["particle_intensity"]
        particle_center = self.bacterium.pos if self.phase == "engulf" else self.immune.pos
        for p in self.particles:
            p.update(particle_center, self.t, digestion_active, intensity)

        self.marker_timer += dt
        self.spill_timer += dt
        if ai_action["mark"] and self.marker_timer > 0.12:
            self.marker_timer = 0.0
            mark_pos = self.immune.pos + random_unit_3d() * rand_range(0.8, 1.5)
            self.add_marker(mark_pos, size=rand_range(0.035, 0.075), life=rand_range(5, 10))

        if ai_action["spill"] and self.spill_timer > 0.35:
            self.spill_timer = 0.0
            origin = self.bacterium.pos if self.phase in ["seek", "attach"] else self.immune.pos
            self.spill_particles(origin, random.randint(3, 9))

        self.update_markers(dt)

        if self.phase == "complete" and self.phase_timer > 1.0:
            self.immune.move(vector(0, 0.04 * math.sin(self.t * 2), 0), dt)

        self.update_labels()

# ----------------------------- main loop -----------------------------

sim = Simulation()
last_time = time.time()

while True:
    rate(60)
    now = time.time()
    dt = clamp(now - last_time, 0.001, 0.05)
    last_time = now

    # Allow pause key to unpause even when paused.
    if sim.paused:
        human_immune_vel, human_bac_vel, human_bac_rot, instant = sim.read_human_input(dt)
        if instant["toggle_pause"]:
            sim.paused = False
        if instant["toggle_ai"]:
            sim.ai.enabled = not sim.ai.enabled
        if instant["reset"]:
            sim.reset_round()
            sim.paused = False
        if instant["toggle_help"]:
            sim.help_visible = not sim.help_visible
        sim.update_labels()
    else:
        sim.update(dt)
