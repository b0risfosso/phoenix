from vpython import *
import random
import math
import time as pytime
import csv
import os
from datetime import datetime

# ============================================================
# 3D VPython Simulation:
# Endocytosis and Exocytosis at a Cell Membrane
# Includes an automatic AI behavior controller and human controls.
# Updated: replaced torus(...) with ring(...) for VPython installations where torus is unavailable.
# ============================================================

# ----------------------------
# Scene setup: light styling
# ----------------------------
scene.title = "Endocytosis and Exocytosis at the Membrane — AI Controlled 3D Simulation"
scene.width = 1180
scene.height = 760
scene.background = vector(0.93, 0.97, 1.0)
scene.forward = vector(-1.6, -1.05, -1.25)
scene.center = vector(0, 0, 0)
scene.range = 8.2
scene.ambient = color.gray(0.78)

scene.caption = """
Controls:
  SPACE / P : pause / resume
  A         : toggle AI controller
  R         : reset simulation round
  E         : start an endocytic wrapping event
  X         : send an internal vesicle outward for exocytosis
  V         : spawn internal vesicle
  N         : select next vesicle
  I/K/J/L/U/O : nudge selected vesicle
  M         : cycle AI behavior mode
  C         : force chaotic AI mode
  S         : force orbit/swirl AI mode
  H         : temporary human override of AI

AI modes automatically read the simulation state, choose actions, and loop/reset when the system becomes stable or complete.
"""

# ----------------------------
# Constants
# ----------------------------
CELL_R = 3.15
WORLD_R = 7.6
PARTICLE_R = 0.075
VESICLE_R = 0.34
MAX_ACTIVE_PITS = 5
MAX_PARTICLES = 170

# ----------------------------
# Utility functions
# ----------------------------
def clamp(x, a, b):
    return max(a, min(b, x))

def randf(a, b):
    return random.uniform(a, b)

def random_unit():
    while True:
        v = vector(randf(-1, 1), randf(-1, 1), randf(-1, 1))
        m = mag(v)
        if m > 1e-6:
            return v / m

def random_tangent(n):
    a = random_unit()
    t = cross(n, a)
    if mag(t) < 1e-5:
        t = cross(n, vector(0, 1, 0))
    return norm(t)

def tangent_basis(n):
    t1 = random_tangent(n)
    t2 = norm(cross(n, t1))
    return t1, t2

def surface_point(n, radius=CELL_R):
    return norm(n) * radius

def smoothstep(x):
    x = clamp(x, 0, 1)
    return x * x * (3 - 2 * x)

def mix_vec(a, b, f):
    return a * (1 - f) + b * f

def color_mix(a, b, f):
    return vector(a.x * (1 - f) + b.x * f,
                  a.y * (1 - f) + b.y * f,
                  a.z * (1 - f) + b.z * f)

def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-8:
        return fallback
    return norm(v)

# ----------------------------
# Visual palette
# ----------------------------
COL_MEMBRANE = vector(0.80, 0.92, 1.0)
COL_MEMBRANE_EDGE = vector(0.48, 0.74, 1.0)
COL_PARTICLE = vector(0.95, 0.55, 0.72)
COL_CAPTURED = vector(1.0, 0.38, 0.72)
COL_RELEASED = vector(1.0, 0.78, 0.24)
COL_VESICLE = vector(0.38, 0.82, 0.62)
COL_EXO_VESICLE = vector(1.0, 0.68, 0.26)
COL_PIT = vector(0.42, 0.58, 1.0)
COL_FUSION = vector(1.0, 0.75, 0.15)
COL_AI = vector(0.30, 0.38, 0.75)

# ============================================================
# Simulation object classes
# ============================================================

class Particle:
    def __init__(self, sim, pos, vel=None, kind="external", col=None, trail=False):
        self.sim = sim
        self.pos = vector(pos)
        self.prev_pos = vector(pos)
        self.vel = vector(vel) if vel is not None else random_unit() * randf(0.08, 0.25)
        self.kind = kind
        self.alive = True
        self.captured_by = None
        self.marked = False
        self.age = 0.0
        self.diffusion = randf(0.20, 0.55)
        if col is None:
            col = COL_PARTICLE if kind == "external" else COL_RELEASED
        self.obj = sphere(
            pos=self.pos,
            radius=PARTICLE_R,
            color=col,
            shininess=0.45,
            opacity=0.95,
            make_trail=trail,
            retain=70,
            trail_radius=0.012
        )

    def mark(self, col=vector(1, 0.22, 0.65)):
        self.marked = True
        self.obj.color = col
        self.obj.emissive = False

    def unmark(self):
        if self.kind == "released":
            self.obj.color = COL_RELEASED
        else:
            self.obj.color = COL_PARTICLE
        self.marked = False

    def attach_to(self, pit):
        self.captured_by = pit
        self.vel = vector(0, 0, 0)
        self.kind = "captured"
        self.obj.color = COL_CAPTURED
        self.obj.radius = PARTICLE_R * 1.10

    def detach(self, impulse=None):
        self.captured_by = None
        self.kind = "external"
        self.obj.color = COL_PARTICLE
        if impulse is None:
            impulse = random_unit() * 0.25
        self.vel = impulse

    def hide(self):
        self.alive = False
        self.obj.visible = False
        if hasattr(self.obj, "clear_trail"):
            try:
                self.obj.clear_trail()
            except Exception:
                pass

    def update(self, dt):
        if not self.alive:
            return
        self.age += dt
        self.prev_pos = vector(self.pos)

        if self.captured_by is not None:
            self.obj.pos = self.pos
            return

        # Brownian diffusion / slow scattering
        boost = self.sim.diffusion_boost
        self.vel += random_unit() * self.diffusion * (0.70 + boost) * math.sqrt(max(dt, 0.0001))
        self.vel *= (1.0 - 0.40 * dt)

        # Mild global swirl field, used by some AI modes
        if self.sim.swirl_strength > 0.01:
            r = self.pos
            swirl_axis = self.sim.swirl_axis
            tangent = cross(swirl_axis, r)
            if mag(tangent) > 0.001:
                self.vel += norm(tangent) * self.sim.swirl_strength * 0.10 * dt

        self.pos += self.vel * dt

        # Collision / bounce from the membrane: particles stay outside unless captured
        rmag = mag(self.pos)
        if rmag < CELL_R + PARTICLE_R * 1.3:
            n = safe_norm(self.pos)
            self.pos = n * (CELL_R + PARTICLE_R * 1.35)
            radial = dot(self.vel, n)
            if radial < 0:
                self.vel -= 1.65 * radial * n
            self.vel += n * 0.05

        # Soft outer boundary
        if mag(self.pos) > WORLD_R:
            n = safe_norm(self.pos)
            self.pos = n * WORLD_R
            radial = dot(self.vel, n)
            if radial > 0:
                self.vel -= 1.35 * radial * n

        self.obj.pos = self.pos


class EndocyticPit:
    def __init__(self, sim, normal, playful=False):
        self.sim = sim
        self.n = safe_norm(normal)
        self.t1, self.t2 = tangent_basis(self.n)
        self.age = 0.0
        self.duration = randf(6.0, 9.5) if not playful else randf(3.8, 6.0)
        self.progress = 0.0
        self.captured = []
        self.done = False
        self.playful = playful
        self.max_cargo = random.randint(4, 9)
        self.mouth_radius = randf(0.55, 0.78)
        self.max_depth = randf(0.95, 1.25)
        self.phase = randf(0, 2 * math.pi)

        self.rings = []
        for i in range(7):
            frac = (i + 1) / 7.0
            tor = ring(
                pos=self.n * CELL_R,
                axis=self.n,
                radius=self.mouth_radius * (1.0 - 0.05 * i),
                thickness=0.020 + 0.004 * i,
                color=color_mix(COL_PIT, vector(0.72, 0.45, 1.0), frac),
                opacity=0.50
            )
            self.rings.append(tor)

        self.marker = sphere(
            pos=self.n * (CELL_R + 0.035),
            radius=0.12,
            color=vector(0.44, 0.65, 1.0),
            opacity=0.35,
            shininess=0.1
        )

    def hide(self):
        for r in self.rings:
            r.visible = False
        self.marker.visible = False

    def capture_nearby_particles(self):
        site = self.n * CELL_R
        if len(self.captured) >= self.max_cargo:
            return

        for p in self.sim.particles:
            if not p.alive or p.captured_by is not None:
                continue
            if p.kind not in ["external", "released"]:
                continue

            radial_alignment = dot(safe_norm(p.pos), self.n)
            d = mag(p.pos - site)
            capture_radius = self.mouth_radius * (1.55 + 0.45 * self.progress)

            if radial_alignment > 0.58 and d < capture_radius and len(self.captured) < self.max_cargo:
                p.attach_to(self)
                self.captured.append(p)

    def arrange_captured_particles(self, dt):
        site = self.n * CELL_R
        p = self.progress
        for i, part in enumerate(self.captured):
            angle = self.phase + i * 2.39996 + self.age * (0.25 if self.playful else 0.08)
            radial_fraction = 0.28 + 0.62 * ((i % 4) / 3.0)
            cup_radius = self.mouth_radius * (1.0 - 0.72 * smoothstep(p)) * radial_fraction
            cup_depth = self.max_depth * smoothstep(p) * (0.35 + 0.52 * ((i % 3) / 2.0))
            wobble = 0.025 * math.sin(self.age * 5.0 + i)

            tangent_offset = (math.cos(angle) * self.t1 + math.sin(angle) * self.t2) * (cup_radius + wobble)
            target = site - self.n * cup_depth + tangent_offset
            part.pos = mix_vec(part.pos, target, clamp(7.5 * dt, 0, 1))
            part.obj.pos = part.pos

    def update_visual(self):
        p = smoothstep(self.progress)
        site = self.n * CELL_R

        for i, ring in enumerate(self.rings):
            frac = (i + 1) / len(self.rings)
            depth = self.max_depth * p * frac
            necking = smoothstep(max(0, (p - 0.52) / 0.48))
            ring_radius = self.mouth_radius * (1.0 - 0.76 * p * frac) * (1.0 - 0.35 * necking * frac)
            ring_radius = max(0.075, ring_radius)

            small_wave = 0.015 * math.sin(self.age * 4.0 + frac * 10.0)
            ring.pos = site - self.n * depth
            ring.axis = self.n
            ring.radius = ring_radius + small_wave
            ring.thickness = 0.020 + 0.014 * p * frac
            ring.opacity = 0.34 + 0.28 * (1 - frac)
            ring.color = color_mix(COL_PIT, vector(0.72, 0.39, 0.95), p * frac)

        self.marker.pos = site - self.n * (self.max_depth * p * 0.62)
        self.marker.radius = 0.12 + 0.18 * p
        self.marker.opacity = 0.30 + 0.15 * math.sin(self.age * 7.0) ** 2
        self.marker.color = color_mix(vector(0.50, 0.78, 1.0), vector(0.80, 0.42, 1.0), p)

    def pinch_off(self):
        cargo_count = max(2, len(self.captured))
        for p in self.captured:
            p.hide()

        ves_pos = self.n * (CELL_R - 0.78)
        ves = Vesicle(
            self.sim,
            pos=ves_pos,
            cargo_count=cargo_count,
            col=COL_VESICLE,
            origin="endocytosis"
        )
        ves.vel = -self.n * randf(0.04, 0.13) + random_tangent(self.n) * randf(0.02, 0.08)
        self.sim.vesicles.append(ves)

        self.sim.events.append(FusionFlash(
            self.sim,
            normal=self.n,
            col=vector(0.58, 0.54, 1.0),
            inward=True,
            max_radius=self.mouth_radius * 0.75,
            duration=0.75
        ))

        self.hide()
        self.done = True

    def update(self, dt):
        if self.done:
            return

        self.age += dt
        self.progress = clamp(self.age / self.duration, 0, 1)

        if self.progress < 0.92:
            self.capture_nearby_particles()

        self.arrange_captured_particles(dt)
        self.update_visual()

        if self.progress >= 1.0:
            self.pinch_off()


class Vesicle:
    def __init__(self, sim, pos=None, cargo_count=None, col=COL_EXO_VESICLE, origin="internal"):
        self.sim = sim
        self.pos = vector(pos) if pos is not None else random_unit() * randf(0.35, CELL_R - 0.9)
        self.prev_pos = vector(self.pos)
        self.vel = random_unit() * randf(0.035, 0.10)
        self.radius = VESICLE_R * randf(0.86, 1.18)
        self.cargo_count = cargo_count if cargo_count is not None else random.randint(4, 10)
        self.origin = origin
        self.state = "drift"
        self.target_n = None
        self.age = 0.0
        self.done = False
        self.selected = False
        self.orbiting = False
        self.orbit_axis = random_unit()

        self.obj = sphere(
            pos=self.pos,
            radius=self.radius,
            color=col,
            opacity=0.38,
            shininess=0.65
        )

        self.shell = sphere(
            pos=self.pos,
            radius=self.radius * 1.05,
            color=color.white,
            opacity=0.08,
            shininess=0.2
        )

        self.cargo_offsets = []
        self.cargo_objs = []
        for i in range(self.cargo_count):
            off = random_unit() * randf(0.02, self.radius * 0.58)
            self.cargo_offsets.append(off)
            c = sphere(
                pos=self.pos + off,
                radius=PARTICLE_R * 0.55,
                color=vector(1.0, 0.83, 0.38) if origin != "endocytosis" else vector(0.95, 0.46, 0.75),
                opacity=0.85
            )
            self.cargo_objs.append(c)

    def hide(self):
        self.done = True
        self.obj.visible = False
        self.shell.visible = False
        for c in self.cargo_objs:
            c.visible = False

    def command_to_membrane(self, normal=None):
        if self.done:
            return
        if normal is None:
            if mag(self.pos) > 0.01:
                normal = norm(self.pos)
            else:
                normal = random_unit()
        self.target_n = safe_norm(normal)
        self.state = "to_membrane"
        self.obj.color = COL_EXO_VESICLE
        self.obj.opacity = 0.50

    def nudge(self, direction):
        if self.done:
            return
        self.vel += direction * 0.35
        self.selected = True
        self.obj.color = vector(1.0, 0.52, 0.18)

    def fuse(self):
        if self.done:
            return
        n = self.target_n if self.target_n is not None else safe_norm(self.pos)
        self.sim.events.append(FusionFlash(
            self.sim,
            normal=n,
            col=COL_FUSION,
            inward=False,
            max_radius=self.radius * 2.5,
            duration=1.15
        ))
        self.sim.release_particles(n, self.cargo_count)
        self.hide()

    def update_cargo_visuals(self):
        for off, c in zip(self.cargo_offsets, self.cargo_objs):
            c.pos = self.pos + off.rotate(angle=self.age * 0.22, axis=self.orbit_axis)

    def update(self, dt):
        if self.done:
            return

        self.age += dt
        self.prev_pos = vector(self.pos)

        if self.state == "to_membrane":
            target = self.target_n * (CELL_R - self.radius * 0.45)
            to_target = target - self.pos
            self.vel += safe_norm(to_target, self.target_n) * 1.30 * dt
            self.vel *= (1.0 - 0.55 * dt)
            if mag(to_target) < 0.16:
                self.fuse()
                return
        else:
            # Drifting vesicles wander in cytoplasm
            self.vel += random_unit() * 0.11 * math.sqrt(max(dt, 0.0001))
            self.vel *= (1.0 - 0.35 * dt)

            # AI orbit / swirl interaction
            if self.sim.swirl_strength > 0.01:
                tangent = cross(self.sim.swirl_axis, self.pos)
                if mag(tangent) > 0.001:
                    self.vel += norm(tangent) * self.sim.swirl_strength * 0.20 * dt

        self.pos += self.vel * dt

        # Vesicles stay inside cell unless fusing
        allowed = CELL_R - self.radius * 1.25
        if mag(self.pos) > allowed and self.state != "to_membrane":
            n = safe_norm(self.pos)
            self.pos = n * allowed
            radial = dot(self.vel, n)
            if radial > 0:
                self.vel -= 1.55 * radial * n
            self.vel += -n * 0.035

        self.obj.pos = self.pos
        self.shell.pos = self.pos

        if self.selected:
            self.shell.color = vector(1.0, 0.72, 0.28)
            self.shell.opacity = 0.20 + 0.05 * math.sin(self.age * 8.0)
        else:
            self.shell.color = color.white
            self.shell.opacity = 0.08

        self.update_cargo_visuals()


class FusionFlash:
    def __init__(self, sim, normal, col=COL_FUSION, inward=False, max_radius=0.65, duration=1.0):
        self.sim = sim
        self.n = safe_norm(normal)
        self.age = 0.0
        self.duration = duration
        self.max_radius = max_radius
        self.done = False
        self.inward = inward
        self.col = col

        self.rings = []
        for i in range(4):
            tor = ring(
                pos=self.n * (CELL_R + (0.02 if not inward else -0.02)),
                axis=self.n,
                radius=0.10 + i * 0.035,
                thickness=0.020,
                color=col,
                opacity=0.62
            )
            self.rings.append(tor)

        self.sparkles = []
        for i in range(10):
            t1, t2 = tangent_basis(self.n)
            a = randf(0, 2 * math.pi)
            off = (math.cos(a) * t1 + math.sin(a) * t2) * randf(0.0, max_radius)
            s = sphere(
                pos=self.n * CELL_R + off,
                radius=0.028,
                color=col,
                opacity=0.75,
                emissive=False
            )
            self.sparkles.append((s, off, randf(0.6, 1.4)))

    def hide(self):
        for r in self.rings:
            r.visible = False
        for s, _, _ in self.sparkles:
            s.visible = False

    def update(self, dt):
        if self.done:
            return

        self.age += dt
        p = clamp(self.age / self.duration, 0, 1)
        eased = smoothstep(p)

        for i, r in enumerate(self.rings):
            f = (i + 1) / len(self.rings)
            r.radius = 0.08 + self.max_radius * eased * f
            r.thickness = 0.026 * (1 - p) + 0.006
            r.opacity = 0.58 * (1 - p) * (1.0 - 0.12 * i)
            r.pos = self.n * (CELL_R + (0.035 if not self.inward else -0.035) * math.sin(p * math.pi))
            r.color = color_mix(self.col, color.white, 0.25 * (1 - p))

        for s, off, speed in self.sparkles:
            s.pos = self.n * CELL_R + off * (1 + eased * speed * 0.7) + self.n * (0.08 * math.sin(p * math.pi))
            s.opacity = 0.75 * (1 - p)
            s.radius = 0.032 * (1 - 0.4 * p)

        if p >= 1.0:
            self.hide()
            self.done = True


# ============================================================
# Main simulation class
# ============================================================

class Simulation:
    def __init__(self):
        self.time = 0.0
        self.round_index = 0
        self.paused = False

        self.particles = []
        self.vesicles = []
        self.pits = []
        self.events = []

        self.swirl_strength = 0.0
        self.swirl_axis = norm(vector(0.25, 1.0, 0.18))
        self.diffusion_boost = 0.0

        self.selected_vesicle_index = 0
        self.last_activity_score = 0.0
        self.last_state_signature = None

        self.make_static_scene()
        self.ai = AIController(self)
        self.reset(initial=True)

    def make_static_scene(self):
        # Stationary translucent cell sphere / membrane
        self.cell = sphere(
            pos=vector(0, 0, 0),
            radius=CELL_R,
            color=COL_MEMBRANE,
            opacity=0.18,
            shininess=0.18
        )

        # Membrane outline rings
        self.mem_rings = [
            ring(pos=vector(0, 0, 0), axis=vector(0, 0, 1), radius=CELL_R, thickness=0.012,
                  color=COL_MEMBRANE_EDGE, opacity=0.32),
            ring(pos=vector(0, 0, 0), axis=vector(0, 1, 0), radius=CELL_R, thickness=0.012,
                  color=COL_MEMBRANE_EDGE, opacity=0.24),
            ring(pos=vector(0, 0, 0), axis=vector(1, 0, 0), radius=CELL_R, thickness=0.012,
                  color=COL_MEMBRANE_EDGE, opacity=0.20)
        ]

        # Gentle cytoplasm haze
        self.cytoplasm = sphere(
            pos=vector(0, 0, 0),
            radius=CELL_R * 0.94,
            color=vector(0.86, 1.0, 0.91),
            opacity=0.055,
            shininess=0.05
        )

        self.status = label(
            pos=vector(-6.4, 5.0, 0),
            text="",
            height=13,
            color=vector(0.16, 0.22, 0.36),
            box=False,
            opacity=0,
            align="left"
        )

        self.ai_label = label(
            pos=vector(0, -5.25, 0),
            text="",
            height=15,
            color=COL_AI,
            box=False,
            opacity=0
        )

        self.legend = label(
            pos=vector(5.4, 4.9, 0),
            text="Pink dots: external cargo\nBlue-purple cups: endocytosis\nGreen/orange spheres: vesicles\nGold bursts: exocytosis",
            height=12,
            color=vector(0.22, 0.29, 0.40),
            box=False,
            opacity=0,
            align="left"
        )

    def clear_dynamic(self):
        for p in self.particles:
            p.hide()
        for v in self.vesicles:
            v.hide()
        for pit in self.pits:
            pit.hide()
        for ev in self.events:
            ev.hide()

        self.particles = []
        self.vesicles = []
        self.pits = []
        self.events = []

    def reset(self, initial=False):
        self.clear_dynamic()
        self.round_index += 1
        self.time = 0.0
        self.swirl_strength = 0.0
        self.diffusion_boost = 0.0
        self.selected_vesicle_index = 0

        # External particles around the cell
        external_count = 82 if initial else random.randint(65, 105)
        for i in range(external_count):
            n = random_unit()
            tangent = random_tangent(n) * randf(-0.9, 0.9) + norm(cross(n, random_tangent(n))) * randf(-0.9, 0.9)
            pos = n * randf(CELL_R + 0.55, WORLD_R - 0.65) + tangent * randf(0.0, 0.55)
            vel = random_unit() * randf(0.03, 0.20)
            self.particles.append(Particle(self, pos, vel, kind="external", col=COL_PARTICLE, trail=False))

        # Internal vesicles
        for i in range(random.randint(5, 8)):
            self.spawn_internal_vesicle()

        # Start with a gentle visible process
        self.start_endocytosis(self.best_particle_dense_normal())
        if not initial:
            if random.random() < 0.55:
                self.command_exocytosis()

        if hasattr(self, "ai"):
            self.ai.after_reset()

    def spawn_internal_vesicle(self, pos=None):
        if pos is None:
            pos = random_unit() * randf(0.25, CELL_R - 1.0)
        v = Vesicle(self, pos=pos, cargo_count=random.randint(4, 10), col=COL_EXO_VESICLE, origin="internal")
        self.vesicles.append(v)
        self.update_selected_visual()
        return v

    def release_particles(self, normal, count):
        n = safe_norm(normal)
        t1, t2 = tangent_basis(n)
        for i in range(count):
            if len(self.particles) > MAX_PARTICLES:
                break
            angle = randf(0, 2 * math.pi)
            tangent = math.cos(angle) * t1 + math.sin(angle) * t2
            pos = n * (CELL_R + 0.18 + randf(0, 0.14)) + tangent * randf(0.0, 0.22)
            vel = n * randf(0.65, 1.35) + tangent * randf(0.15, 0.75) + random_unit() * 0.08
            p = Particle(self, pos, vel, kind="released", col=COL_RELEASED, trail=True)
            p.diffusion = randf(0.16, 0.38)
            self.particles.append(p)

    def start_endocytosis(self, normal=None, playful=False):
        active = [p for p in self.pits if not p.done]
        if len(active) >= MAX_ACTIVE_PITS:
            return None
        if normal is None:
            normal = self.best_particle_dense_normal()
        # Avoid stacking pits at almost same place
        for pit in active:
            if dot(pit.n, safe_norm(normal)) > 0.92:
                normal = safe_norm(normal + random_tangent(normal) * 0.55)
                break
        pit = EndocyticPit(self, normal, playful=playful)
        self.pits.append(pit)
        return pit

    def command_exocytosis(self, normal=None):
        candidates = [v for v in self.vesicles if not v.done and v.state == "drift"]
        if not candidates:
            if len(self.vesicles) < 10:
                candidates = [self.spawn_internal_vesicle()]
            else:
                return None

        if normal is None:
            # Prefer nearest vesicle direction, or random if near center
            v = min(candidates, key=lambda vv: mag(vv.pos - safe_norm(vv.pos) * CELL_R))
            normal = safe_norm(v.pos, random_unit())
        else:
            v = min(candidates, key=lambda vv: mag(vv.pos - normal * CELL_R))

        v.command_to_membrane(normal)
        return v

    def best_particle_dense_normal(self):
        # AI-readable state helper: choose membrane patch with many external particles nearby.
        best_n = random_unit()
        best_score = -1
        candidates = [random_unit() for _ in range(18)]

        # Add directions from some particles, making response state-dependent
        free_parts = [p for p in self.particles if p.alive and p.captured_by is None and mag(p.pos) > CELL_R]
        random.shuffle(free_parts)
        for p in free_parts[:18]:
            candidates.append(safe_norm(p.pos))

        for n in candidates:
            site = n * CELL_R
            score = 0.0
            for p in free_parts:
                d = mag(p.pos - site)
                align = dot(safe_norm(p.pos), n)
                if align > 0.45 and d < 1.45:
                    score += (1.45 - d) + 0.25 * align
            if score > best_score:
                best_score = score
                best_n = n

        return best_n

    def update_selected_visual(self):
        living = [v for v in self.vesicles if not v.done]
        if not living:
            return
        self.selected_vesicle_index %= len(living)
        for i, v in enumerate(living):
            v.selected = (i == self.selected_vesicle_index)

    def select_next_vesicle(self):
        living = [v for v in self.vesicles if not v.done]
        if not living:
            return
        self.selected_vesicle_index = (self.selected_vesicle_index + 1) % len(living)
        self.update_selected_visual()

    def nudge_selected(self, direction):
        living = [v for v in self.vesicles if not v.done]
        if not living:
            return
        self.selected_vesicle_index %= len(living)
        living[self.selected_vesicle_index].nudge(direction)
        self.ai.human_override(4.0)

    def get_state(self):
        free_external = 0
        released = 0
        captured = 0
        near_membrane = 0
        mean_particle_speed = 0.0
        particle_count = 0

        for p in self.particles:
            if not p.alive:
                continue
            particle_count += 1
            mean_particle_speed += mag(p.vel)
            if p.captured_by is not None:
                captured += 1
            elif p.kind == "released":
                released += 1
            else:
                free_external += 1
            if abs(mag(p.pos) - CELL_R) < 0.9:
                near_membrane += 1

        if particle_count > 0:
            mean_particle_speed /= particle_count

        active_pits = len([p for p in self.pits if not p.done])
        drifting_vesicles = len([v for v in self.vesicles if not v.done and v.state == "drift"])
        moving_vesicles = len([v for v in self.vesicles if not v.done and v.state == "to_membrane"])
        vesicle_count = len([v for v in self.vesicles if not v.done])
        active_events = len([e for e in self.events if not e.done])

        motion = 0.0
        for p in self.particles:
            if p.alive:
                motion += mag(p.pos - p.prev_pos)
        for v in self.vesicles:
            if not v.done:
                motion += mag(v.pos - v.prev_pos)

        signature = (
            round(free_external / 5),
            round(released / 5),
            active_pits,
            drifting_vesicles,
            moving_vesicles,
            active_events
        )

        return {
            "free_external": free_external,
            "released": released,
            "captured": captured,
            "near_membrane": near_membrane,
            "particle_count": particle_count,
            "mean_particle_speed": mean_particle_speed,
            "active_pits": active_pits,
            "drifting_vesicles": drifting_vesicles,
            "moving_vesicles": moving_vesicles,
            "vesicle_count": vesicle_count,
            "active_events": active_events,
            "motion": motion,
            "signature": signature
        }

    def cleanup(self):
        self.particles = [p for p in self.particles if p.alive]
        self.pits = [p for p in self.pits if not p.done]
        self.vesicles = [v for v in self.vesicles if not v.done]
        self.events = [e for e in self.events if not e.done]
        self.update_selected_visual()

    def update_labels(self):
        st = self.get_state()
        self.status.text = (
            f"Round {self.round_index}\n"
            f"AI: {'ON' if self.ai.enabled else 'OFF'} | Mode: {self.ai.mode}\n"
            f"Pause: {'YES' if self.paused else 'NO'}\n"
            f"External/free: {st['free_external']}  Released: {st['released']}\n"
            f"Captured/wrapping: {st['captured']}  Active pits: {st['active_pits']}\n"
            f"Vesicles: {st['vesicle_count']}  Moving to membrane: {st['moving_vesicles']}\n"
            f"Stagnation: {self.ai.stagnation_time:4.1f}s"
        )
        self.ai_label.text = self.ai.display_text()

    def update(self, dt):
        if self.paused:
            self.update_labels()
            return

        self.time += dt

        # Decay global fields unless AI sustains them
        self.swirl_strength *= (1.0 - 0.55 * dt)
        self.diffusion_boost *= (1.0 - 0.70 * dt)

        self.ai.update(dt)

        for pit in list(self.pits):
            pit.update(dt)

        for v in list(self.vesicles):
            v.update(dt)

        for p in list(self.particles):
            p.update(dt)

        for ev in list(self.events):
            ev.update(dt)

        if int(self.time * 5) != int((self.time - dt) * 5):
            self.cleanup()
            self.update_labels()


# ============================================================
# AI Controller
# ============================================================

class AIController:
    MODES = [
        "BALANCE",
        "HARVEST",
        "SECRETE",
        "ORBIT",
        "CAREFUL",
        "CHAOS",
        "ARTIST"
    ]

    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.mode = "BALANCE"
        self.mode_time = 0.0
        self.mode_duration = randf(8.0, 15.0)
        self.action_timer = 0.0
        self.override_until = 0.0
        self.stagnation_time = 0.0
        self.completion_countdown = None
        self.last_signature = None
        self.last_motion = 100.0
        self.artist_index = 0
        self.mode_history = []

    def after_reset(self):
        self.mode_time = 0.0
        self.action_timer = 0.0
        self.stagnation_time = 0.0
        self.completion_countdown = None
        self.last_signature = None
        self.last_motion = 100.0
        self.artist_index = 0
        self.choose_mode(force=random.choice(["BALANCE", "HARVEST", "SECRETE", "ARTIST"]))

    def display_text(self):
        if not self.enabled:
            return "AI disabled — human/manual simulation control"
        if self.sim.time < self.override_until:
            return f"AI waiting: human override ({self.override_until - self.sim.time:0.1f}s)"
        if self.completion_countdown is not None:
            return f"AI loop reset in {self.completion_countdown:0.1f}s — state complete/stable"
        return f"AI behavior: {self.mode}  | next mode in {max(0, self.mode_duration - self.mode_time):0.1f}s"

    def human_override(self, seconds=4.0):
        self.override_until = max(self.override_until, self.sim.time + seconds)

    def next_mode(self):
        current = self.mode
        choices = [m for m in self.MODES if m != current]

        st = self.sim.get_state()
        weighted = []

        if st["free_external"] > 35:
            weighted += ["HARVEST", "BALANCE", "CAREFUL"]
        if st["drifting_vesicles"] > 1:
            weighted += ["SECRETE", "BALANCE", "ARTIST"]
        if st["active_pits"] == 0 and st["moving_vesicles"] == 0:
            weighted += ["CHAOS", "ARTIST", "ORBIT"]
        if st["particle_count"] > 120:
            weighted += ["CAREFUL", "ORBIT", "SECRETE"]

        weighted += choices
        self.choose_mode(force=random.choice(weighted))

    def choose_mode(self, force=None):
        if force is None:
            force = random.choice(self.MODES)
        if force not in self.MODES:
            force = "BALANCE"

        # Avoid exact repetition unless requested by keyboard
        if force == self.mode and len(self.MODES) > 1:
            alts = [m for m in self.MODES if m != self.mode]
            force = random.choice(alts)

        self.mode = force
        self.mode_time = 0.0
        self.action_timer = 0.0
        self.mode_duration = randf(8.0, 16.5)
        self.mode_history.append(force)
        if len(self.mode_history) > 8:
            self.mode_history.pop(0)

    def cycle_mode(self):
        idx = self.MODES.index(self.mode) if self.mode in self.MODES else -1
        self.choose_mode(force=self.MODES[(idx + 1) % len(self.MODES)])

    def detect_stagnation_or_completion(self, st, dt):
        # Stable if the state signature barely changes and little motion occurs.
        sig = st["signature"]
        motion_low = st["motion"] < 0.035
        no_active_process = st["active_pits"] == 0 and st["moving_vesicles"] == 0 and st["active_events"] == 0
        external_depleted = st["free_external"] < 8 and st["drifting_vesicles"] < 1 and no_active_process
        too_empty = st["particle_count"] < 12 and st["vesicle_count"] < 1

        if self.last_signature == sig and motion_low and no_active_process:
            self.stagnation_time += dt
        else:
            self.stagnation_time = max(0.0, self.stagnation_time - 0.8 * dt)

        self.last_signature = sig

        completed = external_depleted or too_empty or self.stagnation_time > 11.0
        return completed

    def start_completion_loop(self):
        if self.completion_countdown is None:
            self.completion_countdown = 4.0
            self.choose_mode(force="ARTIST")

    def update_completion_loop(self, dt):
        if self.completion_countdown is None:
            return False
        self.completion_countdown -= dt
        self.sim.swirl_strength = max(self.sim.swirl_strength, 0.75)
        self.sim.diffusion_boost = max(self.sim.diffusion_boost, 0.45)

        # Make a final visible flourish
        if random.random() < 0.035:
            self.sim.command_exocytosis(random_unit())
        if random.random() < 0.025:
            self.sim.start_endocytosis(random_unit(), playful=True)

        if self.completion_countdown <= 0:
            self.completion_countdown = None
            self.sim.reset(initial=False)
            return True
        return False

    def update(self, dt):
        if not self.enabled:
            return

        st = self.sim.get_state()

        if self.detect_stagnation_or_completion(st, dt):
            self.start_completion_loop()

        if self.update_completion_loop(dt):
            return

        # Human can still control while AI is on; AI pauses action briefly.
        if self.sim.time < self.override_until:
            return

        self.mode_time += dt
        self.action_timer += dt

        if self.mode_time > self.mode_duration:
            self.next_mode()

        if self.mode == "BALANCE":
            self.behavior_balance(st, dt)
        elif self.mode == "HARVEST":
            self.behavior_harvest(st, dt)
        elif self.mode == "SECRETE":
            self.behavior_secrete(st, dt)
        elif self.mode == "ORBIT":
            self.behavior_orbit(st, dt)
        elif self.mode == "CAREFUL":
            self.behavior_careful(st, dt)
        elif self.mode == "CHAOS":
            self.behavior_chaos(st, dt)
        elif self.mode == "ARTIST":
            self.behavior_artist(st, dt)

    # ----------------------------
    # AI behavior modes
    # ----------------------------

    def behavior_balance(self, st, dt):
        self.sim.swirl_strength = max(self.sim.swirl_strength, 0.15)
        if self.action_timer > 2.2:
            self.action_timer = 0.0
            if st["free_external"] > st["drifting_vesicles"] * 6 and st["active_pits"] < 3:
                self.sim.start_endocytosis(self.sim.best_particle_dense_normal())
            else:
                self.sim.command_exocytosis()

    def behavior_harvest(self, st, dt):
        # Wrap external particles and mark the particles near chosen membrane patches.
        if self.action_timer > randf(1.6, 2.8):
            self.action_timer = 0.0
            n = self.sim.best_particle_dense_normal()
            self.sim.start_endocytosis(n)

            site = n * CELL_R
            for p in self.sim.particles:
                if p.alive and p.captured_by is None and mag(p.pos - site) < 1.6:
                    p.mark(vector(1.0, 0.36, 0.72))

    def behavior_secrete(self, st, dt):
        # Push internal vesicles outward and release cargo.
        if st["drifting_vesicles"] < 2 and len(self.sim.vesicles) < 12 and random.random() < 0.02:
            self.sim.spawn_internal_vesicle()

        if self.action_timer > randf(1.2, 2.2):
            self.action_timer = 0.0
            self.sim.command_exocytosis()

    def behavior_orbit(self, st, dt):
        # Make cytoplasmic vesicles orbit and send occasional ones outward.
        self.sim.swirl_strength = max(self.sim.swirl_strength, 1.15)
        self.sim.swirl_axis = norm(vector(
            math.sin(self.sim.time * 0.27) * 0.45 + 0.2,
            1.0,
            math.cos(self.sim.time * 0.21) * 0.45
        ))

        for v in self.sim.vesicles:
            if not v.done and v.state == "drift":
                tangent = cross(self.sim.swirl_axis, v.pos)
                if mag(tangent) > 0.001:
                    v.vel += norm(tangent) * 0.018

        if self.action_timer > 4.0:
            self.action_timer = 0.0
            if random.random() < 0.55:
                self.sim.command_exocytosis()
            else:
                self.sim.start_endocytosis(self.sim.best_particle_dense_normal(), playful=True)

    def behavior_careful(self, st, dt):
        # One process at a time, less chaotic.
        self.sim.swirl_strength = max(self.sim.swirl_strength, 0.03)
        if self.action_timer > 3.2:
            self.action_timer = 0.0
            if st["active_pits"] == 0 and st["free_external"] > 10:
                self.sim.start_endocytosis(self.sim.best_particle_dense_normal())
            elif st["moving_vesicles"] == 0 and st["drifting_vesicles"] > 0:
                self.sim.command_exocytosis()

    def behavior_chaos(self, st, dt):
        # Fast, playful, destructive/constructive: scatter, wrap, fuse.
        self.sim.swirl_strength = max(self.sim.swirl_strength, 1.6)
        self.sim.diffusion_boost = max(self.sim.diffusion_boost, 0.90)

        if random.random() < 0.045:
            for p in random.sample(self.sim.particles, min(8, len(self.sim.particles))):
                if p.alive and p.captured_by is None:
                    p.vel += random_unit() * randf(0.25, 0.75)

        if self.action_timer > randf(0.75, 1.35):
            self.action_timer = 0.0
            r = random.random()
            if r < 0.42:
                self.sim.start_endocytosis(random_unit(), playful=True)
            elif r < 0.82:
                self.sim.command_exocytosis(random_unit())
            else:
                self.sim.spawn_internal_vesicle(random_unit() * randf(0.2, CELL_R - 1.0))

    def behavior_artist(self, st, dt):
        # Ritual-like golden-angle placement of pits and releases.
        self.sim.swirl_strength = max(self.sim.swirl_strength, 0.45)

        palette = [
            vector(1.0, 0.55, 0.72),
            vector(1.0, 0.78, 0.22),
            vector(0.45, 0.74, 1.0),
            vector(0.56, 0.88, 0.60),
            vector(0.78, 0.55, 1.0)
        ]

        for i, p in enumerate(self.sim.particles):
            if p.alive and p.captured_by is None and random.random() < 0.006:
                p.obj.color = palette[(i + self.artist_index) % len(palette)]

        if self.action_timer > 2.0:
            self.action_timer = 0.0
            k = self.artist_index
            golden = math.pi * (3 - math.sqrt(5))
            z = 1 - 2 * ((k % 21) / 20.0)
            rr = math.sqrt(max(0, 1 - z * z))
            theta = k * golden
            n = norm(vector(math.cos(theta) * rr, z, math.sin(theta) * rr))
            self.artist_index += 1

            if self.artist_index % 2 == 0:
                self.sim.start_endocytosis(n, playful=True)
            else:
                self.sim.command_exocytosis(n)


# ============================================================
# Keyboard handling
# ============================================================

# ============================================================
# CSV storage settings
# ============================================================

CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
CSV_SAMPLE_INTERVAL = 0.10

_csv_output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
_csv_run_id = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

if _csv_output_dir:
    os.makedirs(_csv_output_dir, exist_ok=True)
    CSV_OUTPUT_PATH = os.path.join(
        _csv_output_dir,
        f"{_csv_run_id}-endocytosis-exocytosis-state-log.csv"
    )
else:
    CSV_OUTPUT_PATH = os.environ.get(
        "SIM_STATE_CSV_PATH",
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "endocytosis_exocytosis_state_log.csv"
        )
    )

csv_run_id = _csv_run_id

CSV_FIELDS = [
    "run_id",
    "record_time",
    "sim_time",
    "round_index",
    "row_type",
    "object_type",
    "object_id",
    "state",
    "kind",
    "origin",
    "x",
    "y",
    "z",
    "vx",
    "vy",
    "vz",
    "radius",
    "age",
    "progress",
    "cargo_count",
    "captured_count",
    "free_external",
    "released",
    "captured",
    "particle_count",
    "near_membrane",
    "mean_particle_speed",
    "active_pits",
    "drifting_vesicles",
    "moving_vesicles",
    "vesicle_count",
    "active_events",
    "motion",
    "ai_enabled",
    "ai_mode",
    "ai_mode_time",
    "ai_stagnation_time",
    "ai_completion_countdown",
    "ai_override_remaining",
    "swirl_strength",
    "swirl_axis_x",
    "swirl_axis_y",
    "swirl_axis_z",
    "diffusion_boost",
    "selected",
    "target_x",
    "target_y",
    "target_z",
    "normal_x",
    "normal_y",
    "normal_z",
    "done",
    "marked",
    "captured_by",
    "details",
]


def _csv_vec(v):
    if v is None:
        return ("", "", "")
    return (float(v.x), float(v.y), float(v.z))


def _csv_base_row(record_time, sim, row_type, object_type, object_id="", state="", kind="", origin=""):
    st = sim.get_state()
    ai = sim.ai
    override_remaining = max(0.0, ai.override_until - sim.time)
    completion_countdown = "" if ai.completion_countdown is None else ai.completion_countdown
    sx, sy, sz = _csv_vec(sim.swirl_axis)
    return {
        "run_id": csv_run_id,
        "record_time": record_time,
        "sim_time": sim.time,
        "round_index": sim.round_index,
        "row_type": row_type,
        "object_type": object_type,
        "object_id": object_id,
        "state": state,
        "kind": kind,
        "origin": origin,
        "x": "",
        "y": "",
        "z": "",
        "vx": "",
        "vy": "",
        "vz": "",
        "radius": "",
        "age": "",
        "progress": "",
        "cargo_count": "",
        "captured_count": "",
        "free_external": st["free_external"],
        "released": st["released"],
        "captured": st["captured"],
        "particle_count": st["particle_count"],
        "near_membrane": st["near_membrane"],
        "mean_particle_speed": st["mean_particle_speed"],
        "active_pits": st["active_pits"],
        "drifting_vesicles": st["drifting_vesicles"],
        "moving_vesicles": st["moving_vesicles"],
        "vesicle_count": st["vesicle_count"],
        "active_events": st["active_events"],
        "motion": st["motion"],
        "ai_enabled": ai.enabled,
        "ai_mode": ai.mode,
        "ai_mode_time": ai.mode_time,
        "ai_stagnation_time": ai.stagnation_time,
        "ai_completion_countdown": completion_countdown,
        "ai_override_remaining": override_remaining,
        "swirl_strength": sim.swirl_strength,
        "swirl_axis_x": sx,
        "swirl_axis_y": sy,
        "swirl_axis_z": sz,
        "diffusion_boost": sim.diffusion_boost,
        "selected": "",
        "target_x": "",
        "target_y": "",
        "target_z": "",
        "normal_x": "",
        "normal_y": "",
        "normal_z": "",
        "done": "",
        "marked": "",
        "captured_by": "",
        "details": "",
    }


def write_csv_snapshot(writer, record_time, sim):
    st = sim.get_state()

    row = _csv_base_row(record_time, sim, "summary", "simulation")
    row["details"] = f"signature={st['signature']}"
    writer.writerow(row)

    row = _csv_base_row(record_time, sim, "summary", "cell_membrane")
    row["radius"] = CELL_R
    row["details"] = f"world_radius={WORLD_R}; max_active_pits={MAX_ACTIVE_PITS}; max_particles={MAX_PARTICLES}"
    writer.writerow(row)

    for i, particle in enumerate(sim.particles):
        if not particle.alive:
            continue
        row = _csv_base_row(record_time, sim, "object", "particle", particle_id := i, particle.kind, particle.kind)
        px, py, pz = _csv_vec(particle.pos)
        vx, vy, vz = _csv_vec(particle.vel)
        row.update({
            "x": px,
            "y": py,
            "z": pz,
            "vx": vx,
            "vy": vy,
            "vz": vz,
            "radius": PARTICLE_R,
            "age": particle.age,
            "marked": particle.marked,
            "captured_by": "" if particle.captured_by is None else "pit",
        })
        writer.writerow(row)

    for i, vesicle in enumerate(sim.vesicles):
        if vesicle.done:
            continue
        px, py, pz = _csv_vec(vesicle.pos)
        vx, vy, vz = _csv_vec(vesicle.vel)
        tx, ty, tz = _csv_vec(vesicle.target_n)
        row = _csv_base_row(record_time, sim, "object", "vesicle", i, vesicle.state, "", vesicle.origin)
        row.update({
            "x": px,
            "y": py,
            "z": pz,
            "vx": vx,
            "vy": vy,
            "vz": vz,
            "radius": vesicle.radius,
            "age": vesicle.age,
            "cargo_count": vesicle.cargo_count,
            "selected": vesicle.selected,
            "target_x": tx,
            "target_y": ty,
            "target_z": tz,
            "done": vesicle.done,
            "details": f"orbiting={vesicle.orbiting}",
        })
        writer.writerow(row)

    for i, pit in enumerate(sim.pits):
        if pit.done:
            continue
        nx, ny, nz = _csv_vec(pit.n)
        row = _csv_base_row(record_time, sim, "object", "endocytic_pit", i, "active")
        row.update({
            "x": pit.n.x * CELL_R,
            "y": pit.n.y * CELL_R,
            "z": pit.n.z * CELL_R,
            "age": pit.age,
            "progress": pit.progress,
            "radius": pit.mouth_radius,
            "captured_count": len(pit.captured),
            "normal_x": nx,
            "normal_y": ny,
            "normal_z": nz,
            "done": pit.done,
            "details": f"duration={pit.duration}; max_depth={pit.max_depth}; max_cargo={pit.max_cargo}; playful={pit.playful}",
        })
        writer.writerow(row)

    for i, event in enumerate(sim.events):
        if event.done:
            continue
        nx, ny, nz = _csv_vec(event.n)
        row = _csv_base_row(record_time, sim, "object", "fusion_flash", i, "active")
        row.update({
            "x": event.n.x * CELL_R,
            "y": event.n.y * CELL_R,
            "z": event.n.z * CELL_R,
            "age": event.age,
            "progress": clamp(event.age / max(event.duration, 1e-9), 0, 1),
            "radius": event.max_radius,
            "normal_x": nx,
            "normal_y": ny,
            "normal_z": nz,
            "done": event.done,
            "details": f"inward={event.inward}; duration={event.duration}",
        })
        writer.writerow(row)

sim = Simulation()

def keydown(evt):
    key = evt.key.lower()

    if key in [" ", "p"]:
        sim.paused = not sim.paused

    elif key == "a":
        sim.ai.enabled = not sim.ai.enabled

    elif key == "r":
        sim.reset(initial=False)

    elif key == "e":
        sim.start_endocytosis(sim.best_particle_dense_normal(), playful=True)
        sim.ai.human_override(4.0)

    elif key == "x":
        sim.command_exocytosis()
        sim.ai.human_override(4.0)

    elif key == "v":
        sim.spawn_internal_vesicle()
        sim.ai.human_override(4.0)

    elif key == "n":
        sim.select_next_vesicle()
        sim.ai.human_override(4.0)

    elif key == "m":
        sim.ai.cycle_mode()
        sim.ai.human_override(1.0)

    elif key == "c":
        sim.ai.choose_mode(force="CHAOS")
        sim.ai.enabled = True

    elif key == "s":
        sim.ai.choose_mode(force="ORBIT")
        sim.ai.enabled = True

    elif key == "h":
        sim.ai.human_override(8.0)

    # Nudge selected vesicle
    elif key == "i":
        sim.nudge_selected(vector(0, 0.35, 0))
    elif key == "k":
        sim.nudge_selected(vector(0, -0.35, 0))
    elif key == "j":
        sim.nudge_selected(vector(-0.35, 0, 0))
    elif key == "l":
        sim.nudge_selected(vector(0.35, 0, 0))
    elif key == "u":
        sim.nudge_selected(vector(0, 0, 0.35))
    elif key == "o":
        sim.nudge_selected(vector(0, 0, -0.35))

scene.bind("keydown", keydown)

# ============================================================
# Main loop
# ============================================================

last = pytime.time()
sim.update_labels()

csv_elapsed = 0.0
csv_next_sample = 0.0
_csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
_csv_writer = csv.DictWriter(_csv_file, fieldnames=CSV_FIELDS)
_csv_writer.writeheader()

try:
    while csv_elapsed < CSV_RUN_SECONDS:
        rate(60)
        now = pytime.time()
        dt = clamp(now - last, 0.001, 0.045)
        last = now

        sim.update(dt)
        csv_elapsed += dt

        if csv_elapsed >= csv_next_sample:
            write_csv_snapshot(_csv_writer, csv_elapsed, sim)
            _csv_file.flush()
            csv_next_sample += CSV_SAMPLE_INTERVAL

    sim.status.text = (
        f"CSV recording complete: {CSV_RUN_SECONDS:0.0f}s saved to "
        f"{os.path.basename(CSV_OUTPUT_PATH)}"
    )
    sim.ai_label.text = "CSV run complete"
finally:
    try:
        write_csv_snapshot(_csv_writer, csv_elapsed, sim)
        _csv_file.flush()
    except Exception:
        pass
    _csv_file.close()
