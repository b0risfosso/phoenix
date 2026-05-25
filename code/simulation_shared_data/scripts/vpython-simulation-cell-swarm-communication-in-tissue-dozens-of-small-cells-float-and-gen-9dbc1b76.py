from vpython import *
import random
import math
from collections import deque

# ============================================================
# 3D VPython Simulation:
# Cell Swarm Communication in Tissue + Expressive AI Controller
# ============================================================

scene.title = "Cell Swarm Communication in Tissue"
scene.width = 1200
scene.height = 760
scene.background = vector(0.93, 0.97, 1.0)
scene.forward = vector(-0.75, -0.35, -1.0)
scene.up = vector(0, 1, 0)
scene.range = 4.4
scene.caption = (
    "\nControls: A toggle AI | SPACE pause | R reset | M next AI mode | "
    "WASD / arrows move guide | Q/E up/down | B signal burst | T attach/detach guide | "
    "O orbit particles | C calm | X chaos\n"
)

# -----------------------------
# Utility functions
# -----------------------------

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-8:
        return fallback
    return norm(v)

def randf(a, b):
    return random.uniform(a, b)

def random_unit_vector():
    z = randf(-1, 1)
    t = randf(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(t), z, r * math.sin(t))

def random_in_box(half):
    return vector(randf(-half.x, half.x), randf(-half.y, half.y), randf(-half.z, half.z))

def blend(a, b, t):
    t = clamp(t)
    return a * (1 - t) + b * t

def limit_vector(v, max_mag):
    m = mag(v)
    if m > max_mag and m > 1e-8:
        return v * (max_mag / m)
    return v

def hsv_color(h, s=0.75, v=1.0):
    try:
        return color.hsv_to_rgb(vector(h % 1.0, s, v))
    except Exception:
        return vector(v, v * (1 - s * 0.5), v * (1 - s))

def hide_object(obj):
    if obj is None:
        return
    try:
        obj.visible = False
    except Exception:
        pass
    try:
        obj.clear_trail()
    except Exception:
        pass

# -----------------------------
# Visual constants
# -----------------------------

BOX_HALF = vector(3.25, 2.05, 2.05)
CELL_COUNT = 46
MAX_PARTICLES = 420

PASTEL_CELL_COLORS = [
    vector(0.42, 0.78, 1.00),
    vector(0.62, 0.88, 0.68),
    vector(0.82, 0.72, 1.00),
    vector(1.00, 0.76, 0.78),
    vector(0.78, 0.91, 0.92),
    vector(1.00, 0.88, 0.55),
]

SIGNAL_COLORS = [
    vector(1.00, 0.32, 0.50),  # warm cytokine pink
    vector(0.18, 0.75, 1.00),  # calcium/cyan
    vector(1.00, 0.77, 0.20),  # growth amber
    vector(0.62, 0.46, 1.00),  # violet messenger
    vector(0.34, 0.95, 0.72),  # green mediator
]

MODE_COLORS = {
    "seed_wave": vector(1.00, 0.48, 0.62),
    "shepherd": vector(0.28, 0.70, 1.00),
    "orbit_dance": vector(0.72, 0.50, 1.00),
    "organize": vector(0.35, 0.95, 0.76),
    "sprinkle": vector(1.00, 0.82, 0.28),
    "artist": vector(1.00, 0.42, 0.92),
    "chaos": vector(1.00, 0.43, 0.20),
    "calm": vector(0.70, 0.86, 1.00),
}


# -----------------------------
# Cell object
# -----------------------------

class Cell:
    def __init__(self, sim, index, pos):
        self.sim = sim
        self.index = index
        self.radius = randf(0.125, 0.185)
        self.pos = vector(pos)
        self.vel = random_unit_vector() * randf(0.03, 0.18)
        self.base_color = random.choice(PASTEL_CELL_COLORS)
        self.signal_color = random.choice(SIGNAL_COLORS)

        self.activation = 0.0
        self.signal_input = 0.0
        self.refractory = randf(0.0, 0.8)
        self.pulse_cooldown = randf(0.1, 1.2)
        self.marked = 0.0
        self.memory = 0.0
        self.phase = randf(0, 2 * math.pi)

        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=self.base_color,
            opacity=0.58,
            shininess=0.9
        )
        self.nucleus = sphere(
            pos=self.pos,
            radius=self.radius * 0.38,
            color=blend(self.base_color, vector(1, 1, 1), 0.45),
            opacity=0.35,
            shininess=0.6
        )
        self.halo = sphere(
            pos=self.pos,
            radius=self.radius * 1.55,
            color=self.signal_color,
            opacity=0.035,
            shininess=0.0
        )
        self.mark_ring = ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=self.radius * 1.48,
            thickness=0.012,
            color=vector(1.0, 0.92, 0.25),
            opacity=0.75,
            visible=False
        )

    def destroy(self):
        hide_object(self.body)
        hide_object(self.nucleus)
        hide_object(self.halo)
        hide_object(self.mark_ring)

    def add_signal(self, amount, signal_color=None):
        self.signal_input += amount
        if signal_color is not None:
            self.signal_color = blend(self.signal_color, signal_color, 0.12)

    def ignite(self, amount=1.0, signal_color=None):
        self.activation = clamp(max(self.activation, amount), 0, 1.7)
        self.memory = clamp(self.memory + amount * 0.25, 0, 1)
        self.refractory = min(self.refractory, 0.05)
        self.marked = max(self.marked, 0.45)
        if signal_color is not None:
            self.signal_color = blend(self.signal_color, signal_color, 0.35)

    def mark(self, strength=1.0):
        self.marked = clamp(max(self.marked, strength), 0, 1)

    def update_physics(self, dt):
        brownian = random_unit_vector() * randf(0.0, 0.028)
        pulse_jitter = random_unit_vector() * (0.012 * self.activation)
        self.vel += (brownian + pulse_jitter) * dt * 10.0

        # Gentle upward/downward drift, making cells float instead of fall.
        self.vel += vector(0, math.sin(self.phase + self.sim.time * 0.7) * 0.006, 0) * dt

        self.vel *= 0.996
        self.vel = limit_vector(self.vel, 0.55)

        self.pos += self.vel * dt

        # Bounce against transparent tissue box walls.
        for axis_name in ("x", "y", "z"):
            half_value = getattr(BOX_HALF, axis_name)
            p = getattr(self.pos, axis_name)
            v = getattr(self.vel, axis_name)
            if p > half_value - self.radius:
                setattr(self.pos, axis_name, half_value - self.radius)
                setattr(self.vel, axis_name, -abs(v) * 0.82)
            elif p < -half_value + self.radius:
                setattr(self.pos, axis_name, -half_value + self.radius)
                setattr(self.vel, axis_name, abs(v) * 0.82)

    def update_biology(self, dt):
        self.refractory = max(0, self.refractory - dt)
        self.pulse_cooldown = max(0, self.pulse_cooldown - dt)
        self.marked = max(0, self.marked - dt * 0.18)
        self.memory = max(0, self.memory - dt * 0.018)

        threshold = 0.22 + 0.10 * self.refractory
        if self.signal_input > threshold:
            self.activation = clamp(self.activation + self.signal_input * 1.75, 0, 1.65)
            self.memory = clamp(self.memory + self.signal_input * 0.36, 0, 1)
            self.refractory = 0.24
            self.marked = max(self.marked, 0.35)

        # Activated cells trigger nearby neighbors, creating a wave front.
        if self.activation > 0.72 and self.pulse_cooldown <= 0:
            self.sim.emit_from_cell_to_neighbors(self, count=random.randint(4, 8))
            if random.random() < 0.45:
                self.sim.spawn_orbiting_signal(self, count=random.randint(1, 3))
            self.pulse_cooldown = randf(0.32, 0.74)

        # Signal fades, but memory leaves subtle traces.
        self.activation *= math.exp(-dt * 0.72)
        if self.activation < 0.005:
            self.activation = 0.0

    def update_visuals(self):
        glow = clamp(self.activation)
        remembered = clamp(self.memory)
        c = blend(self.base_color, self.signal_color, glow * 0.82)
        c = blend(c, vector(1, 1, 1), 0.08 * glow)

        self.body.pos = self.pos
        self.nucleus.pos = self.pos
        self.halo.pos = self.pos
        self.mark_ring.pos = self.pos

        self.body.color = c
        self.body.opacity = 0.52 + 0.20 * glow
        self.body.radius = self.radius * (1.0 + 0.11 * glow)

        self.nucleus.color = blend(c, vector(1, 1, 1), 0.55)
        self.nucleus.opacity = 0.27 + 0.33 * glow
        self.nucleus.radius = self.radius * (0.34 + 0.10 * glow)

        self.halo.color = blend(self.signal_color, vector(1, 1, 1), 0.18)
        self.halo.radius = self.radius * (1.55 + 2.15 * glow + 0.55 * remembered)
        self.halo.opacity = 0.028 + 0.25 * glow + 0.045 * remembered

        self.mark_ring.visible = self.marked > 0.03
        self.mark_ring.opacity = 0.20 + 0.65 * self.marked
        self.mark_ring.radius = self.radius * (1.42 + 0.22 * math.sin(self.sim.time * 6 + self.phase))
        axis = self.vel if mag(self.vel) > 0.02 else vector(0, 1, 0)
        self.mark_ring.axis = safe_norm(axis)


# -----------------------------
# Signal particle object
# -----------------------------

class SignalParticle:
    def __init__(
        self,
        sim,
        pos,
        vel,
        signal_color,
        intensity=0.12,
        source=None,
        target=None,
        mode="free",
        orbit_cell=None
    ):
        self.sim = sim
        self.pos = vector(pos)
        self.vel = vector(vel)
        self.signal_color = vector(signal_color)
        self.intensity = intensity
        self.source = source
        self.target = target
        self.mode = mode
        self.orbit_cell = orbit_cell
        self.attached_cell = None
        self.attach_timer = 0.0
        self.life = randf(4.5, 8.5)
        self.age = 0.0
        self.phase = randf(0, 2 * math.pi)
        self.orbit_axis = random_unit_vector()
        self.orbit_offset = random_unit_vector() * randf(0.18, 0.32)
        self.radius = randf(0.022, 0.038)

        self.shape = sphere(
            pos=self.pos,
            radius=self.radius,
            color=self.signal_color,
            opacity=0.82,
            emissive=True,
            make_trail=True,
            retain=18,
            trail_radius=self.radius * 0.28,
            trail_color=blend(self.signal_color, vector(1, 1, 1), 0.25)
        )

    def destroy(self):
        hide_object(self.shape)

    def attach_to(self, cell):
        self.mode = "attached"
        self.attached_cell = cell
        outward = safe_norm(self.pos - cell.pos, random_unit_vector())
        self.orbit_offset = outward * cell.radius * randf(1.03, 1.38)
        self.attach_timer = randf(0.11, 0.38)
        self.vel = vector(0, 0, 0)
        cell.mark(0.4)

    def transfer_into_cell(self):
        if self.attached_cell is not None:
            self.attached_cell.add_signal(self.intensity, self.signal_color)
            self.attached_cell.mark(0.58)
        self.life = -1

    def update(self, dt):
        self.age += dt
        self.life -= dt

        if self.life <= 0:
            return False

        if self.mode == "orbit":
            if self.orbit_cell is None or self.orbit_cell not in self.sim.cells:
                self.mode = "free"
            else:
                self.phase += dt * randf(3.5, 5.5)
                self.orbit_offset = self.orbit_offset.rotate(angle=dt * 3.2, axis=self.orbit_axis)
                r = self.orbit_cell.radius * (1.45 + 0.42 * math.sin(self.phase))
                self.pos = self.orbit_cell.pos + safe_norm(self.orbit_offset) * r
                self.vel = self.orbit_offset.cross(self.orbit_axis) * 1.6
                if self.age > 0.55 and random.random() < dt * 0.58:
                    self.mode = "free"
                    self.target = self.sim.choose_neighbor(self.orbit_cell)
                    if self.target is not None:
                        self.vel = safe_norm(self.target.pos - self.pos) * randf(0.75, 1.25)
                    else:
                        self.vel = random_unit_vector() * randf(0.45, 0.9)

        elif self.mode == "attached":
            if self.attached_cell is None:
                self.mode = "free"
            else:
                self.attach_timer -= dt
                self.orbit_offset = self.orbit_offset.rotate(angle=dt * 7.0, axis=safe_norm(self.attached_cell.vel, vector(0, 1, 0)))
                self.pos = self.attached_cell.pos + self.orbit_offset
                if self.attach_timer <= 0:
                    self.transfer_into_cell()

        else:
            # Free signal particles drift, bounce, mix, and home toward targets.
            if self.target is not None and self.target in self.sim.cells:
                desired = safe_norm(self.target.pos - self.pos) * 0.86
                self.vel = blend(self.vel, desired, 0.035)
            self.vel += random_unit_vector() * dt * 0.18
            self.vel = limit_vector(self.vel, 1.55)
            self.pos += self.vel * dt

            # Bounce off box.
            for axis_name in ("x", "y", "z"):
                half_value = getattr(BOX_HALF, axis_name)
                p = getattr(self.pos, axis_name)
                v = getattr(self.vel, axis_name)
                if p > half_value:
                    setattr(self.pos, axis_name, half_value)
                    setattr(self.vel, axis_name, -abs(v) * 0.78)
                elif p < -half_value:
                    setattr(self.pos, axis_name, -half_value)
                    setattr(self.vel, axis_name, abs(v) * 0.78)

            # Absorb on collision with cell membrane.
            for cell in self.sim.cells:
                if cell is self.source and self.age < 0.28:
                    continue
                d = mag(self.pos - cell.pos)
                if d < cell.radius * 1.22 + self.radius:
                    self.attach_to(cell)
                    break

        self.shape.pos = self.pos
        self.shape.color = self.signal_color
        self.shape.opacity = clamp(self.life / 2.0, 0.15, 0.86)
        return self.life > 0


# -----------------------------
# Expressive AI Controller
# -----------------------------

class AIController:
    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.modes = [
            "seed_wave",
            "shepherd",
            "orbit_dance",
            "organize",
            "sprinkle",
            "artist",
            "chaos",
            "calm",
        ]
        self.mode = "seed_wave"
        self.mode_timer = 8.0
        self.action_cooldown = 0.0
        self.target_cell = None
        self.target_pos = vector(0, 0, 0)
        self.human_override_timer = 0.0
        self.history = deque(maxlen=16)
        self.sample_timer = 0.0
        self.stagnant_time = 0.0
        self.complete_time = 0.0
        self.reset_countdown = None
        self.round_delay = 0.0
        self.last_mode = None

    def read_state(self):
        cells = self.sim.cells
        if not cells:
            return {
                "active_count": 0,
                "avg_activation": 0,
                "max_activation": 0,
                "particle_count": len(self.sim.particles),
                "avg_speed": 0,
                "marked_count": 0,
                "brightest": None,
                "quietest": None,
                "front_cells": [],
            }

        activations = [c.activation for c in cells]
        speeds = [mag(c.vel) for c in cells]
        active_cells = [c for c in cells if c.activation > 0.35]
        front_cells = [c for c in cells if 0.16 < c.activation < 0.95]
        brightest = max(cells, key=lambda c: c.activation)
        quietest = min(cells, key=lambda c: c.activation + c.memory * 0.25)
        return {
            "active_count": len(active_cells),
            "avg_activation": sum(activations) / len(activations),
            "max_activation": max(activations),
            "particle_count": len(self.sim.particles),
            "avg_speed": sum(speeds) / len(speeds),
            "marked_count": len([c for c in cells if c.marked > 0.2]),
            "brightest": brightest,
            "quietest": quietest,
            "front_cells": front_cells,
        }

    def note_human_override(self, seconds=2.2):
        self.human_override_timer = max(self.human_override_timer, seconds)

    def next_mode(self):
        choices = [m for m in self.modes if m != self.mode]
        if self.mode in ("chaos", "sprinkle"):
            choices += ["calm", "organize"]
        if self.mode == "calm":
            choices += ["seed_wave", "artist"]
        self.last_mode = self.mode
        self.mode = random.choice(choices)
        self.mode_timer = randf(6.5, 12.5)
        self.action_cooldown = 0.05
        self.target_cell = None
        self.sim.flash_status("AI mode: " + self.mode)

    def set_mode(self, mode):
        if mode in self.modes:
            self.last_mode = self.mode
            self.mode = mode
            self.mode_timer = randf(6.0, 12.0)
            self.action_cooldown = 0.0
            self.target_cell = None
            self.sim.flash_status("AI mode: " + self.mode)

    def detect_stagnation_or_completion(self, state, dt):
        self.sample_timer -= dt
        if self.sample_timer <= 0:
            self.sample_timer = 1.0
            self.history.append((
                state["active_count"],
                round(state["avg_activation"], 3),
                state["particle_count"],
                round(state["avg_speed"], 3),
            ))

        active_ratio = state["active_count"] / max(1, len(self.sim.cells))

        if active_ratio > 0.82 or state["avg_activation"] > 0.82:
            self.complete_time += dt
        else:
            self.complete_time = max(0, self.complete_time - dt * 0.65)

        if len(self.history) >= 9:
            active_vals = [h[0] for h in self.history]
            avg_vals = [h[1] for h in self.history]
            particle_vals = [h[2] for h in self.history]
            speed_vals = [h[3] for h in self.history]

            quiet_empty = (
                state["active_count"] == 0 and
                state["particle_count"] < 8 and
                state["avg_activation"] < 0.035
            )
            almost_unchanged = (
                max(active_vals) - min(active_vals) <= 2 and
                max(avg_vals) - min(avg_vals) < 0.025 and
                max(particle_vals) - min(particle_vals) <= 8 and
                max(speed_vals) - min(speed_vals) < 0.018
            )

            if quiet_empty or almost_unchanged:
                self.stagnant_time += dt
            else:
                self.stagnant_time = max(0, self.stagnant_time - dt * 0.8)

        if self.complete_time > 4.2:
            self.schedule_reset("wave complete")
        elif self.stagnant_time > 7.5:
            # Try a dramatic mode before resetting, then reset if it remains stalled.
            if self.mode not in ("seed_wave", "chaos", "sprinkle"):
                self.set_mode(random.choice(["seed_wave", "sprinkle", "chaos"]))
                self.stagnant_time = 3.0
            else:
                self.schedule_reset("state stagnant")

    def schedule_reset(self, reason="loop"):
        if self.reset_countdown is None:
            self.reset_countdown = 2.4
            self.sim.flash_status("AI loop reset soon: " + reason)

    def move_guide_toward(self, target, dt, speed=0.9):
        if self.sim.guide_attached_cell is not None:
            self.sim.detach_guide()
        delta = target - self.sim.guide.pos
        d = mag(delta)
        if d > 1e-6:
            self.sim.guide.pos += safe_norm(delta) * min(d, speed * dt)
        self.sim.constrain_guide()

    def stimulate_near_guide(self, radius=0.72, amount=0.012):
        gpos = self.sim.guide.pos
        guide_color = self.sim.guide.color
        for cell in self.sim.cells:
            d = mag(cell.pos - gpos)
            if d < radius:
                falloff = 1 - d / radius
                cell.add_signal(amount * falloff, guide_color)
                cell.mark(0.22 + 0.35 * falloff)

    def update(self, dt):
        if not self.enabled:
            return

        state = self.read_state()
        self.detect_stagnation_or_completion(state, dt)

        if self.reset_countdown is not None:
            self.reset_countdown -= dt
            self.sim.guide.color = vector(1.0, 0.72, 0.28)
            self.sim.guide.opacity = 0.72
            if self.reset_countdown <= 0:
                self.reset_countdown = None
                self.complete_time = 0
                self.stagnant_time = 0
                self.history.clear()
                self.sim.reset_round(looped=True)
                self.set_mode("seed_wave")
            return

        self.human_override_timer = max(0, self.human_override_timer - dt)
        if self.human_override_timer > 0:
            self.sim.guide.color = blend(self.sim.guide.color, vector(1, 1, 1), 0.12)
            return

        self.mode_timer -= dt
        self.action_cooldown = max(0, self.action_cooldown - dt)
        if self.mode_timer <= 0:
            self.next_mode()

        self.sim.guide.color = blend(self.sim.guide.color, MODE_COLORS.get(self.mode, vector(1, 0.7, 0.2)), 0.08)
        self.sim.guide.opacity = 0.55 + 0.18 * math.sin(self.sim.time * 4.0) ** 2

        if self.mode == "seed_wave":
            self.behavior_seed_wave(state, dt)
        elif self.mode == "shepherd":
            self.behavior_shepherd(state, dt)
        elif self.mode == "orbit_dance":
            self.behavior_orbit_dance(state, dt)
        elif self.mode == "organize":
            self.behavior_organize(state, dt)
        elif self.mode == "sprinkle":
            self.behavior_sprinkle(state, dt)
        elif self.mode == "artist":
            self.behavior_artist(state, dt)
        elif self.mode == "chaos":
            self.behavior_chaos(state, dt)
        elif self.mode == "calm":
            self.behavior_calm(state, dt)

    def behavior_seed_wave(self, state, dt):
        if self.target_cell is None or self.target_cell not in self.sim.cells or self.target_cell.activation > 0.55:
            quiet_cells = sorted(self.sim.cells, key=lambda c: c.activation + c.memory * 0.3)
            self.target_cell = random.choice(quiet_cells[:max(3, len(quiet_cells) // 4)])

        target = self.target_cell.pos + random_unit_vector() * 0.18
        self.move_guide_toward(target, dt, speed=1.05)

        if mag(self.sim.guide.pos - self.target_cell.pos) < 0.38 and self.action_cooldown <= 0:
            c = self.target_cell
            c.ignite(1.15, self.sim.guide.color)
            c.mark(1.0)
            self.sim.emit_from_cell_to_neighbors(c, count=12)
            self.sim.spawn_burst(self.sim.guide.pos, count=16, signal_color=self.sim.guide.color)
            self.action_cooldown = randf(1.0, 1.8)

    def behavior_shepherd(self, state, dt):
        front = state["front_cells"]
        if front:
            centroid = vector(0, 0, 0)
            for c in front:
                centroid += c.pos
            centroid /= len(front)
            self.target_pos = centroid
        elif state["brightest"] is not None:
            self.target_pos = state["brightest"].pos
        else:
            self.target_pos = vector(0, 0, 0)

        self.move_guide_toward(self.target_pos, dt, speed=0.82)
        self.stimulate_near_guide(radius=0.86, amount=0.018)

        if self.action_cooldown <= 0:
            near = self.sim.cells_near(self.sim.guide.pos, radius=1.1)
            for c in near[:5]:
                c.vel += safe_norm(c.pos - self.sim.guide.pos, random_unit_vector()) * 0.035
                if c.activation > 0.25:
                    self.sim.emit_from_cell_to_neighbors(c, count=2)
            self.action_cooldown = randf(0.35, 0.65)

    def behavior_orbit_dance(self, state, dt):
        center = state["brightest"]
        if center is None or center.activation < 0.15:
            center = random.choice(self.sim.cells)

        angle = self.sim.time * 1.15
        radius = 0.72 + 0.16 * math.sin(self.sim.time * 1.9)
        target = center.pos + vector(math.cos(angle) * radius, 0.32 * math.sin(angle * 0.7), math.sin(angle) * radius)
        self.move_guide_toward(target, dt, speed=1.18)

        center.mark(0.8)
        self.stimulate_near_guide(radius=0.54, amount=0.012)

        if self.action_cooldown <= 0:
            self.sim.spawn_orbiting_signal(center, count=random.randint(4, 7), signal_color=self.sim.guide.color)
            if random.random() < 0.65:
                self.sim.emit_from_cell_to_neighbors(center, count=random.randint(3, 6))
            self.action_cooldown = randf(0.42, 0.78)

    def behavior_organize(self, state, dt):
        # Gently arrange cells into a living ring/shell without freezing them.
        n = max(1, len(self.sim.cells))
        ring_radius = 1.45 + 0.18 * math.sin(self.sim.time * 0.45)
        for i, cell in enumerate(self.sim.cells):
            a = 2 * math.pi * i / n + self.sim.time * 0.11
            y = 0.62 * math.sin(2 * a + self.sim.round_index * 0.3)
            desired = vector(ring_radius * math.cos(a), y, ring_radius * math.sin(a))
            cell.vel += (desired - cell.pos) * dt * 0.18
            if i % 5 == self.sim.round_index % 5:
                cell.mark(0.22)

        self.target_pos = vector(
            math.cos(self.sim.time * 0.45) * 1.25,
            math.sin(self.sim.time * 0.7) * 0.35,
            math.sin(self.sim.time * 0.45) * 1.25
        )
        self.move_guide_toward(self.target_pos, dt, speed=0.75)

        if self.action_cooldown <= 0:
            ordered = sorted(self.sim.cells, key=lambda c: mag(c.pos - self.sim.guide.pos))
            for c in ordered[:3]:
                c.add_signal(0.23, self.sim.guide.color)
                self.sim.emit_from_cell_to_neighbors(c, count=3)
            self.action_cooldown = randf(0.8, 1.3)

    def behavior_sprinkle(self, state, dt):
        t = self.sim.time
        self.target_pos = vector(
            2.35 * math.sin(t * 0.58),
            1.55 * math.sin(t * 0.91),
            1.75 * math.cos(t * 0.44)
        )
        self.move_guide_toward(self.target_pos, dt, speed=1.25)

        if self.action_cooldown <= 0:
            col = hsv_color((t * 0.08 + random.random() * 0.12) % 1.0, 0.65, 1.0)
            self.sim.spawn_burst(self.sim.guide.pos, count=random.randint(8, 14), signal_color=col, spill=True)
            self.action_cooldown = randf(0.16, 0.32)

    def behavior_artist(self, state, dt):
        t = self.sim.time
        spiral_r = 0.45 + 1.75 * ((math.sin(t * 0.19) + 1) * 0.5)
        self.target_pos = vector(
            spiral_r * math.cos(t * 0.95),
            0.85 * math.sin(t * 0.47),
            spiral_r * math.sin(t * 0.95)
        )
        self.move_guide_toward(self.target_pos, dt, speed=0.98)

        art_color = hsv_color(t * 0.055, 0.72, 1.0)
        self.sim.guide.color = blend(self.sim.guide.color, art_color, 0.18)

        near = self.sim.cells_near(self.sim.guide.pos, radius=0.74)
        for c in near:
            c.mark(0.55)
            c.signal_color = blend(c.signal_color, art_color, 0.025)
            c.add_signal(0.007, art_color)

        if self.action_cooldown <= 0:
            if near:
                c = random.choice(near)
                c.ignite(max(c.activation, 0.42), art_color)
                self.sim.spawn_burst(c.pos, count=6, signal_color=art_color)
            else:
                self.sim.spawn_burst(self.sim.guide.pos, count=5, signal_color=art_color)
            self.action_cooldown = randf(0.42, 0.9)

    def behavior_chaos(self, state, dt):
        if self.action_cooldown <= 0 or mag(self.sim.guide.pos - self.target_pos) < 0.18:
            self.target_pos = random_in_box(BOX_HALF * 0.82)
        self.move_guide_toward(self.target_pos, dt, speed=1.75)

        # Swirl, collide, and spill.
        for c in self.sim.cells_near(self.sim.guide.pos, radius=1.05):
            radial = safe_norm(c.pos - self.sim.guide.pos, random_unit_vector())
            twist = vector(-radial.z, radial.y * 0.2, radial.x)
            c.vel += (radial * 0.18 + twist * 0.16) * dt * 5.0
            c.add_signal(0.01, self.sim.guide.color)

        if self.action_cooldown <= 0:
            self.sim.spawn_burst(self.sim.guide.pos, count=random.randint(18, 30), signal_color=random.choice(SIGNAL_COLORS), spill=True)
            if random.random() < 0.55:
                c = random.choice(self.sim.cells)
                c.ignite(1.0, self.sim.guide.color)
            self.action_cooldown = randf(0.25, 0.55)

    def behavior_calm(self, state, dt):
        center = vector(0, 0, 0)
        self.move_guide_toward(center, dt, speed=0.55)

        for c in self.sim.cells:
            c.vel *= 0.986
            c.activation *= 0.994
            if mag(c.pos) > 2.0:
                c.vel += safe_norm(-c.pos) * dt * 0.08

        # Let a few soft signals continue so the scene remains alive.
        if self.action_cooldown <= 0 and random.random() < 0.65:
            c = random.choice(self.sim.cells)
            c.add_signal(0.14, vector(0.68, 0.88, 1.0))
            c.mark(0.25)
            self.action_cooldown = randf(1.0, 1.8)


# -----------------------------
# Simulation object
# -----------------------------

class CellSwarmSimulation:
    def __init__(self):
        self.time = 0.0
        self.round_index = 0
        self.paused = False
        self.cells = []
        self.particles = []
        self.keys = set()
        self.status_message = ""
        self.status_timer = 0.0

        self.create_box()

        self.guide = sphere(
            pos=vector(0, 0, 0),
            radius=0.115,
            color=vector(1.0, 0.56, 0.22),
            opacity=0.58,
            emissive=True,
            make_trail=True,
            retain=32,
            trail_radius=0.012,
            trail_color=vector(1.0, 0.68, 0.26)
        )
        self.guide_ring = ring(
            pos=self.guide.pos,
            axis=vector(0, 1, 0),
            radius=0.24,
            thickness=0.014,
            color=vector(1.0, 0.72, 0.22),
            opacity=0.65
        )
        self.guide_attached_cell = None
        self.guide_attach_offset = vector(0.36, 0.18, 0)

        self.status_label = label(
            pos=vector(-3.1, 2.58, 0),
            text="",
            height=13,
            color=vector(0.22, 0.28, 0.34),
            box=False,
            line=False,
            opacity=0
        )

        self.ai = AIController(self)

        scene.bind("keydown", self.on_keydown)
        scene.bind("keyup", self.on_keyup)

        self.reset_round(looped=False)

    def create_box(self):
        wall_color = vector(0.76, 0.91, 1.0)
        edge_color = vector(0.52, 0.66, 0.76)
        hx, hy, hz = BOX_HALF.x, BOX_HALF.y, BOX_HALF.z
        thickness = 0.018

        # Transparent stationary walls.
        box(pos=vector(0, hy, 0), size=vector(2 * hx, thickness, 2 * hz), color=wall_color, opacity=0.08)
        box(pos=vector(0, -hy, 0), size=vector(2 * hx, thickness, 2 * hz), color=wall_color, opacity=0.08)
        box(pos=vector(hx, 0, 0), size=vector(thickness, 2 * hy, 2 * hz), color=wall_color, opacity=0.07)
        box(pos=vector(-hx, 0, 0), size=vector(thickness, 2 * hy, 2 * hz), color=wall_color, opacity=0.07)
        box(pos=vector(0, 0, hz), size=vector(2 * hx, 2 * hy, thickness), color=wall_color, opacity=0.05)
        box(pos=vector(0, 0, -hz), size=vector(2 * hx, 2 * hy, thickness), color=wall_color, opacity=0.05)

        corners = [
            vector(x, y, z)
            for x in (-hx, hx)
            for y in (-hy, hy)
            for z in (-hz, hz)
        ]

        def edge(a, b):
            curve(pos=[a, b], color=edge_color, radius=0.008, opacity=0.55)

        for y in (-hy, hy):
            for z in (-hz, hz):
                edge(vector(-hx, y, z), vector(hx, y, z))
        for x in (-hx, hx):
            for z in (-hz, hz):
                edge(vector(x, -hy, z), vector(x, hy, z))
        for x in (-hx, hx):
            for y in (-hy, hy):
                edge(vector(x, y, -hz), vector(x, y, hz))

        label(
            pos=vector(0, -hy - 0.34, hz + 0.02),
            text="transparent tissue chamber: stationary boundary, bouncing cells and signals",
            height=10,
            color=vector(0.42, 0.52, 0.60),
            box=False,
            line=False,
            opacity=0
        )

    def reset_round(self, looped=False):
        for p in self.particles:
            p.destroy()
        self.particles = []

        for c in self.cells:
            c.destroy()
        self.cells = []

        self.round_index += 1

        attempts = 0
        while len(self.cells) < CELL_COUNT and attempts < 5000:
            attempts += 1
            pos = random_in_box(BOX_HALF * 0.82)
            ok = True
            for c in self.cells:
                if mag(pos - c.pos) < c.radius + 0.24:
                    ok = False
                    break
            if ok:
                self.cells.append(Cell(self, len(self.cells), pos))

        self.guide.pos = vector(0, 0, 0)
        self.detach_guide()
        try:
            self.guide.clear_trail()
        except Exception:
            pass

        # Start each round with a small asymmetrical seed so AI/human control has material.
        seed = random.choice(self.cells)
        seed.ignite(0.82, random.choice(SIGNAL_COLORS))
        self.emit_from_cell_to_neighbors(seed, count=10)

        self.flash_status("new tissue round " + str(self.round_index) + (" (AI loop)" if looped else ""))

    def flash_status(self, text, duration=2.5):
        self.status_message = text
        self.status_timer = duration

    def on_keydown(self, evt):
        k = evt.key.lower()
        self.keys.add(k)

        if k == " ":
            self.paused = not self.paused
            self.flash_status("paused" if self.paused else "resumed")
        elif k == "a":
            self.ai.enabled = not self.ai.enabled
            self.flash_status("AI enabled" if self.ai.enabled else "AI disabled")
        elif k == "r":
            self.reset_round(looped=False)
            self.ai.history.clear()
            self.ai.stagnant_time = 0
            self.ai.complete_time = 0
        elif k == "m":
            self.ai.next_mode()
        elif k == "b":
            self.ai.note_human_override()
            self.spawn_burst(self.guide.pos, count=28, signal_color=self.guide.color, spill=True)
            for c in self.cells_near(self.guide.pos, radius=0.82):
                c.add_signal(0.25, self.guide.color)
                c.mark(0.7)
        elif k == "t":
            self.ai.note_human_override()
            if self.guide_attached_cell is None:
                c = self.closest_cell(self.guide.pos)
                if c is not None:
                    self.attach_guide(c)
            else:
                self.detach_guide()
        elif k == "o":
            self.ai.note_human_override()
            c = self.closest_cell(self.guide.pos)
            if c is not None:
                c.ignite(0.85, self.guide.color)
                self.spawn_orbiting_signal(c, count=12, signal_color=self.guide.color)
        elif k == "c":
            self.ai.set_mode("calm")
        elif k == "x":
            self.ai.set_mode("chaos")

    def on_keyup(self, evt):
        k = evt.key.lower()
        if k in self.keys:
            self.keys.remove(k)

    def attach_guide(self, cell):
        self.guide_attached_cell = cell
        self.guide_attach_offset = safe_norm(self.guide.pos - cell.pos, random_unit_vector()) * (cell.radius + 0.32)
        cell.mark(1.0)
        self.flash_status("guide attached to cell " + str(cell.index))

    def detach_guide(self):
        if self.guide_attached_cell is not None:
            self.flash_status("guide detached")
        self.guide_attached_cell = None

    def constrain_guide(self):
        margin = self.guide.radius
        self.guide.pos.x = clamp(self.guide.pos.x, -BOX_HALF.x + margin, BOX_HALF.x - margin)
        self.guide.pos.y = clamp(self.guide.pos.y, -BOX_HALF.y + margin, BOX_HALF.y - margin)
        self.guide.pos.z = clamp(self.guide.pos.z, -BOX_HALF.z + margin, BOX_HALF.z - margin)

    def handle_human_controls(self, dt):
        move = vector(0, 0, 0)
        if "w" in self.keys or "up" in self.keys:
            move.z -= 1
        if "s" in self.keys or "down" in self.keys:
            move.z += 1
        if "a" in self.keys or "left" in self.keys:
            move.x -= 1
        if "d" in self.keys or "right" in self.keys:
            move.x += 1
        if "q" in self.keys:
            move.y -= 1
        if "e" in self.keys:
            move.y += 1

        if mag(move) > 0:
            self.ai.note_human_override()
            if self.guide_attached_cell is not None:
                self.detach_guide()
            self.guide.pos += safe_norm(move) * dt * 1.75
            self.constrain_guide()

            for c in self.cells_near(self.guide.pos, radius=0.48):
                c.mark(0.42)
                c.vel += safe_norm(c.pos - self.guide.pos, random_unit_vector()) * dt * 0.20

    def update_guide_visual(self):
        if self.guide_attached_cell is not None and self.guide_attached_cell in self.cells:
            self.guide_attach_offset = self.guide_attach_offset.rotate(angle=0.035, axis=vector(0, 1, 0))
            self.guide.pos = self.guide_attached_cell.pos + self.guide_attach_offset
            self.guide_attached_cell.mark(0.75)
            self.guide_attached_cell.add_signal(0.006, self.guide.color)
        elif self.guide_attached_cell is not None:
            self.detach_guide()

        self.guide_ring.pos = self.guide.pos
        self.guide_ring.axis = vector(
            math.sin(self.time * 0.7),
            1.0,
            math.cos(self.time * 0.7)
        )
        self.guide_ring.radius = 0.23 + 0.035 * math.sin(self.time * 5.0)
        self.guide_ring.color = blend(self.guide.color, vector(1, 1, 1), 0.25)

    def closest_cell(self, pos):
        if not self.cells:
            return None
        return min(self.cells, key=lambda c: mag(c.pos - pos))

    def cells_near(self, pos, radius):
        nearby = [c for c in self.cells if mag(c.pos - pos) < radius]
        nearby.sort(key=lambda c: mag(c.pos - pos))
        return nearby

    def choose_neighbor(self, source_cell):
        if source_cell is None or not self.cells:
            return None
        candidates = [c for c in self.cells if c is not source_cell]
        candidates.sort(key=lambda c: mag(c.pos - source_cell.pos) + c.activation * 0.7)
        if not candidates:
            return None
        local = [c for c in candidates if mag(c.pos - source_cell.pos) < 1.35]
        if local and random.random() < 0.82:
            return random.choice(local[:min(6, len(local))])
        return random.choice(candidates[:min(10, len(candidates))])

    def spawn_particle(self, pos, vel, signal_color, intensity=0.12, source=None, target=None, mode="free", orbit_cell=None):
        if len(self.particles) >= MAX_PARTICLES:
            old = self.particles.pop(0)
            old.destroy()

        p = SignalParticle(
            self,
            pos=pos,
            vel=vel,
            signal_color=signal_color,
            intensity=intensity,
            source=source,
            target=target,
            mode=mode,
            orbit_cell=orbit_cell
        )
        self.particles.append(p)
        return p

    def spawn_burst(self, pos, count=12, signal_color=None, spill=False):
        if signal_color is None:
            signal_color = random.choice(SIGNAL_COLORS)

        for _ in range(count):
            direction = random_unit_vector()
            if spill:
                direction = safe_norm(direction + vector(0, randf(-0.45, 0.45), 0))
            target = None
            if self.cells and random.random() < 0.55:
                target = random.choice(self.cells)
                direction = safe_norm(target.pos - pos + random_unit_vector() * 0.35)
            speed = randf(0.38, 1.18)
            self.spawn_particle(
                pos=pos + direction * randf(0.03, 0.14),
                vel=direction * speed,
                signal_color=blend(signal_color, random.choice(SIGNAL_COLORS), randf(0.0, 0.25)),
                intensity=randf(0.06, 0.15),
                target=target
            )

    def spawn_orbiting_signal(self, cell, count=3, signal_color=None):
        if signal_color is None:
            signal_color = cell.signal_color
        for _ in range(count):
            offset = random_unit_vector() * cell.radius * randf(1.4, 2.1)
            self.spawn_particle(
                pos=cell.pos + offset,
                vel=random_unit_vector() * 0.25,
                signal_color=blend(signal_color, cell.signal_color, 0.35),
                intensity=randf(0.06, 0.14),
                source=cell,
                mode="orbit",
                orbit_cell=cell
            )

    def emit_from_cell_to_neighbors(self, cell, count=5):
        if cell is None:
            return
        for _ in range(count):
            target = self.choose_neighbor(cell)
            if target is not None:
                direction = safe_norm(target.pos - cell.pos + random_unit_vector() * 0.18)
                col = blend(cell.signal_color, target.signal_color, 0.18)
            else:
                direction = random_unit_vector()
                col = cell.signal_color
            pos = cell.pos + direction * (cell.radius * 1.18)
            vel = direction * randf(0.48, 1.12) + random_unit_vector() * 0.07
            self.spawn_particle(
                pos=pos,
                vel=vel,
                signal_color=col,
                intensity=randf(0.075, 0.155),
                source=cell,
                target=target
            )

    def resolve_cell_collisions(self):
        n = len(self.cells)
        for i in range(n):
            a = self.cells[i]
            for j in range(i + 1, n):
                b = self.cells[j]
                delta = b.pos - a.pos
                d = mag(delta)
                min_d = a.radius + b.radius + 0.018
                if d < min_d and d > 1e-7:
                    normal = delta / d
                    overlap = min_d - d
                    a.pos -= normal * overlap * 0.5
                    b.pos += normal * overlap * 0.5

                    rel = b.vel - a.vel
                    vn = dot(rel, normal)
                    if vn < 0:
                        impulse = normal * (-vn * 0.48)
                        a.vel -= impulse
                        b.vel += impulse

                    # Contact can transfer faint signal memory.
                    if a.activation > 0.35 or b.activation > 0.35:
                        mix_col = blend(a.signal_color, b.signal_color, 0.5)
                        transfer = 0.014 * max(a.activation, b.activation)
                        a.add_signal(transfer, mix_col)
                        b.add_signal(transfer, mix_col)
                        a.mark(0.18)
                        b.mark(0.18)

    def update_status_label(self, dt):
        self.status_timer = max(0, self.status_timer - dt)

        active = len([c for c in self.cells if c.activation > 0.35])
        avg_act = sum([c.activation for c in self.cells]) / max(1, len(self.cells))
        ai_text = "ON" if self.ai.enabled else "OFF"
        pause_text = "PAUSED" if self.paused else "running"

        msg = self.status_message if self.status_timer > 0 else ""
        if self.ai.reset_countdown is not None:
            msg = "loop reset in " + str(round(self.ai.reset_countdown, 1))

        self.status_label.text = (
            "Round: {r}   State: {p}   AI: {ai}   Mode: {m}\n"
            "Active cells: {a}/{n}   Avg glow: {g:.2f}   Signals: {s}\n"
            "{msg}"
        ).format(
            r=self.round_index,
            p=pause_text,
            ai=ai_text,
            m=self.ai.mode,
            a=active,
            n=len(self.cells),
            g=avg_act,
            s=len(self.particles),
            msg=msg
        )

    def step(self, dt):
        self.time += dt

        for c in self.cells:
            c.signal_input = 0.0

        self.handle_human_controls(dt)
        self.ai.update(dt)
        self.update_guide_visual()

        if self.paused:
            for c in self.cells:
                c.update_visuals()
            self.update_status_label(dt)
            return

        alive = []
        for p in self.particles:
            if p.update(dt):
                alive.append(p)
            else:
                p.destroy()
        self.particles = alive

        for c in self.cells:
            c.update_physics(dt)

        self.resolve_cell_collisions()

        for c in self.cells:
            c.update_biology(dt)
            c.update_visuals()

        self.update_status_label(dt)


# -----------------------------
# Main loop
# -----------------------------

sim = CellSwarmSimulation()

while True:
    rate(60)
    sim.step(1.0 / 60.0)
