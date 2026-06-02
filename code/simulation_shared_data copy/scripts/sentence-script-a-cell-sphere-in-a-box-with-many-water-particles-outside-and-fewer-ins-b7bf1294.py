from vpython import *
import random as pyrandom
import math
import csv
import json
import os
from datetime import datetime

# 3D Osmosis and Cell Swelling/Shrinking Simulation with Expressive AI Controller
# Controls:
#   P pause/resume
#   A toggle AI
#   M force next AI behavior
#   R reset round
#   SPACE human stir/kick
#   W/S increase/decrease membrane permeability
#   I/K add/remove internal osmoles
#   O/L add/remove external osmoles
#   C chaotic kick
#   B balance tonicity
#   X attach/detach AI probe to membrane
#   Arrow keys move AI probe manually

scene.title = "3D Osmosis: Semi-permeable Cell Membrane, Swelling/Shrinking, and AI Controller"
scene.width = 1180
scene.height = 760
scene.background = vector(0.94, 0.98, 1.0)
scene.center = vector(0, 0, 0)
scene.forward = vector(-1.15, -0.68, -1.05)
scene.range = 11.5
scene.autoscale = False
scene.caption = (
    "Light-blue particles are water. Orange/purple particles are solute and cannot cross the membrane. "
    "The transparent membrane allows biased water transfer. AI can stir, mark, swell, shrink, reset, and loop.\n"
)

WATER_RADIUS = 0.075
SOLUTE_RADIUS = 0.12
EPS = 1e-7


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def safe_norm(v):
    m = mag(v)
    if m < EPS:
        return vector(1, 0, 0)
    return v / m


def rand_unit():
    z = pyrandom.uniform(-1, 1)
    t = pyrandom.uniform(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(t), r * math.sin(t), z)


def rand_in_sphere(radius):
    return rand_unit() * (radius * (pyrandom.random() ** (1 / 3)))


def rand_in_box(box_size):
    h = box_size / 2
    return vector(pyrandom.uniform(-h, h), pyrandom.uniform(-h, h), pyrandom.uniform(-h, h))


def color_mix(a, b, t):
    t = clamp(t, 0, 1)
    return a * (1 - t) + b * t


class WaterParticle:
    def __init__(self, pos, vel, inside=False, trail=False):
        c = vector(0.18, 0.62, 1.0) if not inside else vector(0.05, 0.48, 0.95)
        self.obj = sphere(
            pos=pos,
            radius=WATER_RADIUS,
            color=c,
            opacity=0.74,
            shininess=0.35,
            make_trail=trail,
            retain=42,
            trail_radius=0.012,
            trail_color=vector(0.50, 0.78, 1.0),
        )
        self.vel = vel
        self.inside = inside
        self.marked = False


class SoluteParticle:
    def __init__(self, pos, inside=False):
        self.inside = inside
        self.vel = rand_unit() * pyrandom.uniform(0.05, 0.18)
        if inside:
            c = vector(1.0, 0.50, 0.12)
            op = 0.82
        else:
            c = vector(0.72, 0.24, 0.98)
            op = 0.68
        self.obj = sphere(
            pos=pos,
            radius=SOLUTE_RADIUS,
            color=c,
            opacity=op,
            shininess=0.5,
        )


class OsmosisSimulation:
    def __init__(self):
        self.box_size = 16.0
        self.half = self.box_size / 2
        self.round_index = 0

        self.water = []
        self.solutes = []
        self.crossing_marks = []
        self.wrap_rings = []
        self.grid_objects = []
        self.dynamic_objects = []

        self.paused = False
        self.human_override_timer = 0.0

        self.initial_radius = 3.0
        self.radius = self.initial_radius
        self.initial_volume = (4 / 3) * math.pi * self.initial_radius ** 3
        self.cell_volume = self.initial_volume
        self.initial_inside_water = 45

        self.solute_inside_osmoles = 34.0
        self.solute_outside_osmoles = 145.0
        self.membrane_permeability = 0.52
        self.permeability_pulse = 0.0

        self.water_noise = 0.38
        self.cross_in_second = 0
        self.cross_out_second = 0
        self.flux_rate = 0.0
        self.second_timer = 0.0
        self.grid_timer = 0.0
        self.total_crossings = 0

        self._make_stationary_box()

        self.membrane = None
        self.volume_label = label(
            pos=vector(0, self.half + 1.05, 0),
            text="",
            height=16,
            border=8,
            box=True,
            line=True,
            color=vector(0.05, 0.12, 0.18),
            background=vector(0.92, 0.97, 1.0),
            opacity=0.82,
        )
        self.mode_label = label(
            pos=vector(-self.half, self.half + 0.7, 0),
            text="",
            height=13,
            border=6,
            box=True,
            line=False,
            color=vector(0.18, 0.08, 0.24),
            background=vector(1.0, 0.96, 0.90),
            opacity=0.78,
        )

        self.ai_probe = sphere(
            pos=vector(self.radius * 1.7, 0, 0),
            radius=0.18,
            color=vector(1.0, 0.18, 0.72),
            opacity=0.95,
            shininess=0.9,
            emissive=False,
            make_trail=True,
            trail_radius=0.018,
            trail_color=vector(1.0, 0.50, 0.82),
            retain=110,
        )
        self.probe_attached = False
        self.probe_manual_offset = vector(0, 0, 0)

        self.reset()

    def _make_stationary_box(self):
        h = self.half
        box(
            pos=vector(0, 0, 0),
            size=vector(self.box_size, self.box_size, self.box_size),
            color=vector(0.70, 0.86, 1.0),
            opacity=0.055,
        )

        pts = [
            vector(-h, -h, -h), vector(h, -h, -h), vector(h, h, -h), vector(-h, h, -h),
            vector(-h, -h, h), vector(h, -h, h), vector(h, h, h), vector(-h, h, h),
        ]
        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        ]
        for a, b in edges:
            curve(pos=[pts[a], pts[b]], radius=0.018, color=vector(0.55, 0.68, 0.78), opacity=0.55)

        label(
            pos=vector(0, -h - 0.65, 0),
            text="stationary osmotic chamber / elastic cell membrane / water may transfer / solute blocked",
            height=11,
            border=4,
            box=False,
            color=vector(0.18, 0.26, 0.32),
        )

    def clear_dynamic(self):
        for w in self.water:
            w.obj.visible = False
            w.obj.clear_trail()
        for s in self.solutes:
            s.obj.visible = False
        for m in self.crossing_marks:
            m["obj"].visible = False
        for r in self.wrap_rings:
            r["obj"].visible = False
        for g in self.grid_objects:
            g.visible = False
        if self.membrane is not None:
            self.membrane.visible = False
        self.water = []
        self.solutes = []
        self.crossing_marks = []
        self.wrap_rings = []
        self.grid_objects = []
        self.dynamic_objects = []

    def reset(self):
        self.clear_dynamic()

        self.radius = self.initial_radius
        self.initial_volume = (4 / 3) * math.pi * self.radius ** 3
        self.cell_volume = self.initial_volume
        self.initial_inside_water = 45

        # Alternate starting tonicities slightly so each loop feels different.
        if self.round_index % 3 == 0:
            self.solute_inside_osmoles = 34.0
            self.solute_outside_osmoles = 145.0
        elif self.round_index % 3 == 1:
            self.solute_inside_osmoles = 25.0
            self.solute_outside_osmoles = 330.0
        else:
            self.solute_inside_osmoles = 31.0
            self.solute_outside_osmoles = 220.0

        self.membrane_permeability = 0.52
        self.permeability_pulse = 0.0
        self.cross_in_second = 0
        self.cross_out_second = 0
        self.flux_rate = 0.0
        self.second_timer = 0.0
        self.grid_timer = 0.0
        self.total_crossings = 0
        self.water_noise = 0.38

        self.membrane = sphere(
            pos=vector(0, 0, 0),
            radius=self.radius,
            color=vector(0.55, 0.84, 1.0),
            opacity=0.20,
            shininess=0.65,
        )

        for i in range(45):
            pos = rand_in_sphere(self.radius * 0.78)
            vel = rand_unit() * pyrandom.uniform(0.45, 1.15)
            self.water.append(WaterParticle(pos, vel, inside=True, trail=(i < 7)))

        for i in range(175):
            pos = self.random_outside_position(margin=0.45)
            vel = rand_unit() * pyrandom.uniform(0.45, 1.25)
            self.water.append(WaterParticle(pos, vel, inside=False, trail=(i < 13)))

        for _ in range(27):
            self.add_visual_solute(inside=True)

        for _ in range(54):
            self.add_visual_solute(inside=False)

        self.ai_probe.clear_trail()
        self.ai_probe.pos = vector(self.radius * 1.7, 0.0, 0.0)
        self.probe_attached = False
        self.probe_manual_offset = vector(0, 0, 0)

        self.create_radial_grid()
        self.update_labels("RESETTING")

    def random_outside_position(self, margin=0.25):
        for _ in range(500):
            p = rand_in_box(self.box_size - 0.6)
            if mag(p) > self.radius + margin:
                return p
        return vector(self.radius + 1.2, 0, 0)

    def add_visual_solute(self, inside=True):
        if inside:
            pos = rand_in_sphere(max(0.35, self.radius - 0.45))
        else:
            pos = self.random_outside_position(margin=0.7)
        self.solutes.append(SoluteParticle(pos, inside=inside))

    def create_radial_grid(self):
        for g in self.grid_objects:
            g.visible = False
        self.grid_objects = []

        r = self.radius * 1.006
        grid_col = vector(0.48, 0.72, 0.86)

        # Spokes in three orthogonal planes
        for plane in ["xy", "xz", "yz"]:
            for i in range(18):
                a = 2 * math.pi * i / 18
                if plane == "xy":
                    p = vector(math.cos(a), math.sin(a), 0) * r
                elif plane == "xz":
                    p = vector(math.cos(a), 0, math.sin(a)) * r
                else:
                    p = vector(0, math.cos(a), math.sin(a)) * r
                self.grid_objects.append(curve(pos=[vector(0, 0, 0), p], radius=0.0065, color=grid_col, opacity=0.28))

        # Rings on equator and offset latitudes
        for plane in ["xy", "xz", "yz"]:
            for rr in [0.33, 0.66, 1.0]:
                pts = []
                steps = 72
                rad = r * rr
                for i in range(steps + 1):
                    a = 2 * math.pi * i / steps
                    if plane == "xy":
                        pts.append(vector(math.cos(a) * rad, math.sin(a) * rad, 0))
                    elif plane == "xz":
                        pts.append(vector(math.cos(a) * rad, 0, math.sin(a) * rad))
                    else:
                        pts.append(vector(0, math.cos(a) * rad, math.sin(a) * rad))
                self.grid_objects.append(curve(pos=pts, radius=0.0065, color=grid_col, opacity=0.30))

    def concentrations(self):
        box_volume = self.box_size ** 3
        outside_volume = max(20.0, box_volume - self.cell_volume)
        c_in = self.solute_inside_osmoles / max(4.0, self.cell_volume)
        c_out = self.solute_outside_osmoles / outside_volume
        return c_in, c_out

    def crossing_probability(self, outside_to_inside):
        c_in, c_out = self.concentrations()
        diff = (c_in - c_out) / (abs(c_in) + abs(c_out) + EPS)
        effective_perm = clamp(self.membrane_permeability + self.permeability_pulse, 0.01, 1.0)

        if outside_to_inside:
            favor = (diff + 1.0) * 0.5
        else:
            favor = (-diff + 1.0) * 0.5

        p = 0.025 + effective_perm * (0.20 + 0.72 * favor)
        return clamp(p, 0.015, 0.96)

    def add_crossing_mark(self, pos, inward=True):
        n = safe_norm(pos)
        c = vector(0.10, 0.68, 1.0) if inward else vector(0.90, 0.22, 1.0)
        mark = sphere(
            pos=n * (self.radius * 1.015),
            radius=0.055,
            color=c,
            opacity=0.78,
            shininess=0.2,
        )
        self.crossing_marks.append({"obj": mark, "ttl": 1.65, "max": 1.65})

    def add_ai_marker(self, pos, col=vector(1, 0.35, 0.65), size=0.08, ttl=2.8):
        mark = sphere(pos=pos, radius=size, color=col, opacity=0.74, shininess=0.55)
        self.crossing_marks.append({"obj": mark, "ttl": ttl, "max": ttl})

    def add_wrap_ring(self, col=vector(1.0, 0.68, 0.22), ttl=4.0, tilt=0.0, scale=1.18):
        r = self.radius * scale
        pts = []
        steps = 96
        for i in range(steps + 1):
            a = 2 * math.pi * i / steps
            x = math.cos(a) * r
            y = math.sin(a) * r * math.cos(tilt)
            z = math.sin(a) * r * math.sin(tilt)
            pts.append(vector(x, y, z))
        ring = curve(pos=pts, radius=0.018, color=col, opacity=0.58)
        self.wrap_rings.append({"obj": ring, "ttl": ttl, "max": ttl})

    def update_cell_volume(self, dt):
        inside_count = sum(1 for w in self.water if w.inside)
        swelling_ratio = clamp(inside_count / max(1, self.initial_inside_water), 0.50, 1.95)
        target_volume = self.initial_volume * swelling_ratio
        self.cell_volume += (target_volume - self.cell_volume) * clamp(dt * 0.42, 0, 1)
        self.cell_volume = clamp(self.cell_volume, self.initial_volume * 0.48, self.initial_volume * 2.05)
        self.radius = (3 * self.cell_volume / (4 * math.pi)) ** (1 / 3)

        if self.membrane is not None:
            self.membrane.radius = self.radius
            perm = clamp(self.membrane_permeability + self.permeability_pulse, 0, 1)
            self.membrane.opacity = 0.13 + 0.16 * perm
            self.membrane.color = color_mix(vector(0.52, 0.86, 1.0), vector(0.95, 0.48, 1.0), perm)

    def update_water(self, dt):
        h = self.half - WATER_RADIUS
        c_in, c_out = self.concentrations()
        osmotic_diff = c_in - c_out

        for w in self.water:
            jitter = rand_unit() * self.water_noise * math.sqrt(dt)
            w.vel += jitter

            sp = mag(w.vel)
            if sp > 3.6:
                w.vel *= 3.6 / sp

            newpos = w.obj.pos + w.vel * dt

            # Stationary chamber wall collision.
            for axis_name in ["x", "y", "z"]:
                val = getattr(newpos, axis_name)
                if val > h:
                    setattr(newpos, axis_name, h)
                    setattr(w.vel, axis_name, -abs(getattr(w.vel, axis_name)) * 0.92)
                elif val < -h:
                    setattr(newpos, axis_name, -h)
                    setattr(w.vel, axis_name, abs(getattr(w.vel, axis_name)) * 0.92)

            rmag = mag(newpos)
            n = safe_norm(newpos)

            if w.inside:
                if rmag > self.radius - WATER_RADIUS:
                    p = self.crossing_probability(outside_to_inside=False)
                    if pyrandom.random() < p:
                        w.inside = False
                        newpos = n * (self.radius + WATER_RADIUS * 1.8)
                        w.obj.color = vector(0.18, 0.62, 1.0)
                        self.cross_out_second += 1
                        self.total_crossings += 1
                        self.add_crossing_mark(newpos, inward=False)
                    else:
                        newpos = n * (self.radius - WATER_RADIUS * 1.8)
                        w.vel = w.vel - 2 * dot(w.vel, n) * n
                        w.vel *= 0.93
            else:
                if rmag < self.radius + WATER_RADIUS:
                    p = self.crossing_probability(outside_to_inside=True)
                    if pyrandom.random() < p:
                        w.inside = True
                        newpos = n * max(0.12, self.radius - WATER_RADIUS * 1.8)
                        w.obj.color = vector(0.05, 0.48, 0.95)
                        self.cross_in_second += 1
                        self.total_crossings += 1
                        self.add_crossing_mark(newpos, inward=True)
                    else:
                        newpos = n * (self.radius + WATER_RADIUS * 2.0)
                        w.vel = w.vel - 2 * dot(w.vel, n) * n
                        w.vel *= 0.93

            # Weak osmotic drift near membrane to make gradients visible without replacing randomness.
            near = abs(mag(newpos) - self.radius)
            if near < 1.1:
                if osmotic_diff > 0 and not w.inside:
                    w.vel += -safe_norm(newpos) * 0.025 * dt
                elif osmotic_diff < 0 and w.inside:
                    w.vel += safe_norm(newpos) * 0.025 * dt

            w.obj.pos = newpos

    def update_solutes(self, dt):
        h = self.half - SOLUTE_RADIUS
        for s in self.solutes:
            s.vel += rand_unit() * 0.045 * math.sqrt(dt)
            if mag(s.vel) > 0.55:
                s.vel *= 0.55 / mag(s.vel)

            newpos = s.obj.pos + s.vel * dt

            if s.inside:
                n = safe_norm(newpos)
                if mag(newpos) > self.radius - SOLUTE_RADIUS * 2.0:
                    newpos = n * (self.radius - SOLUTE_RADIUS * 2.0)
                    s.vel = s.vel - 2 * dot(s.vel, n) * n
                    s.vel *= 0.82
            else:
                for axis_name in ["x", "y", "z"]:
                    val = getattr(newpos, axis_name)
                    if val > h:
                        setattr(newpos, axis_name, h)
                        setattr(s.vel, axis_name, -abs(getattr(s.vel, axis_name)) * 0.85)
                    elif val < -h:
                        setattr(newpos, axis_name, -h)
                        setattr(s.vel, axis_name, abs(getattr(s.vel, axis_name)) * 0.85)

                n = safe_norm(newpos)
                if mag(newpos) < self.radius + SOLUTE_RADIUS * 2.5:
                    newpos = n * (self.radius + SOLUTE_RADIUS * 2.5)
                    s.vel = s.vel - 2 * dot(s.vel, n) * n
                    s.vel *= 0.82

            s.obj.pos = newpos

    def fade_marks_and_rings(self, dt):
        kept = []
        for m in self.crossing_marks:
            m["ttl"] -= dt
            if m["ttl"] > 0:
                frac = m["ttl"] / m["max"]
                m["obj"].opacity = 0.78 * frac
                m["obj"].radius *= 1.0 + 0.20 * dt
                kept.append(m)
            else:
                m["obj"].visible = False
        self.crossing_marks = kept

        kept_rings = []
        for r in self.wrap_rings:
            r["ttl"] -= dt
            if r["ttl"] > 0:
                frac = r["ttl"] / r["max"]
                r["obj"].opacity = 0.58 * frac
                kept_rings.append(r)
            else:
                r["obj"].visible = False
        self.wrap_rings = kept_rings

    def update_flux_timer(self, dt):
        self.second_timer += dt
        if self.second_timer >= 1.0:
            self.flux_rate = (self.cross_in_second - self.cross_out_second) / self.second_timer
            self.cross_in_second = 0
            self.cross_out_second = 0
            self.second_timer = 0.0

    def update_labels(self, mode_name=""):
        inside_count = sum(1 for w in self.water if w.inside)
        outside_count = len(self.water) - inside_count
        c_in, c_out = self.concentrations()
        vol_pct = 100 * self.cell_volume / self.initial_volume
        perm = clamp(self.membrane_permeability + self.permeability_pulse, 0, 1)

        self.volume_label.pos = vector(0, self.half + 1.05, 0)
        self.volume_label.text = (
            f"Cell volume: {self.cell_volume:6.1f}  ({vol_pct:5.1f}% of start)\n"
            f"Radius: {self.radius:4.2f}   Water inside/outside: {inside_count}/{outside_count}   Net flux: {self.flux_rate:+4.1f}/s\n"
            f"Internal tonicity: {c_in:5.3f}   External tonicity: {c_out:5.3f}   Membrane permeability: {perm:4.2f}"
        )
        controller_ref = globals().get("controller", None)
        ai_state = "ON" if controller_ref is None else ("ON" if controller_ref.enabled else "OFF")
        paused = "PAUSED" if self.paused else "RUNNING"
        self.mode_label.text = f"AI: {ai_state} | Mode: {mode_name} | {paused} | Round {self.round_index + 1}"

    def update(self, dt, mode_name=""):
        self.permeability_pulse *= math.exp(-dt * 1.9)
        self.human_override_timer = max(0.0, self.human_override_timer - dt)

        self.update_cell_volume(dt)
        self.update_water(dt)
        self.update_solutes(dt)
        self.fade_marks_and_rings(dt)
        self.update_flux_timer(dt)

        self.grid_timer += dt
        if self.grid_timer > 0.34:
            self.create_radial_grid()
            self.grid_timer = 0.0

        self.update_labels(mode_name)

    def stir_all(self, strength=0.8, axis=vector(0, 1, 0)):
        axis = safe_norm(axis)
        for w in self.water:
            r = w.obj.pos
            tang = cross(axis, r)
            if mag(tang) > EPS:
                w.vel += safe_norm(tang) * strength * pyrandom.uniform(0.25, 1.0)

    def random_kick(self, strength=1.2, fraction=0.35):
        for w in self.water:
            if pyrandom.random() < fraction:
                w.vel += rand_unit() * strength * pyrandom.uniform(0.2, 1.0)

    def radial_push(self, outward=True, strength=0.55, inside_only=False, outside_only=False):
        for w in self.water:
            if inside_only and not w.inside:
                continue
            if outside_only and w.inside:
                continue
            n = safe_norm(w.obj.pos)
            w.vel += n * strength * (1 if outward else -1)

    def local_probe_force(self, strength=0.65, swirl=False, attract=True):
        p = self.ai_probe.pos
        for w in self.water:
            d = w.obj.pos - p
            md = mag(d)
            if md < 2.2:
                if attract:
                    w.vel += -safe_norm(d) * strength * (1 - md / 2.2)
                if swirl:
                    tang = cross(safe_norm(p + vector(0.1, 0.2, 0.05)), d)
                    if mag(tang) > EPS:
                        w.vel += safe_norm(tang) * strength * 0.85 * (1 - md / 2.2)

    def spill_water_from_corner(self, count=4):
        if len(self.water) > 330:
            return
        corner = vector(-self.half + 0.45, self.half - 0.45, -self.half + 0.45)
        for i in range(count):
            pos = corner + rand_unit() * 0.28
            vel = safe_norm(-corner + rand_unit() * 0.65) * pyrandom.uniform(1.0, 2.1)
            self.water.append(WaterParticle(pos, vel, inside=False, trail=(pyrandom.random() < 0.18)))
        self.add_ai_marker(corner, col=vector(0.20, 0.70, 1.0), size=0.13, ttl=2.3)

    def adjust_internal_osmoles(self, amount):
        self.solute_inside_osmoles = max(1.0, self.solute_inside_osmoles + amount)
        if amount > 0 and len([s for s in self.solutes if s.inside]) < 65 and pyrandom.random() < 0.65:
            self.add_visual_solute(inside=True)

    def adjust_external_osmoles(self, amount):
        self.solute_outside_osmoles = max(1.0, self.solute_outside_osmoles + amount)
        if amount > 0 and len([s for s in self.solutes if not s.inside]) < 115 and pyrandom.random() < 0.50:
            self.add_visual_solute(inside=False)

    def balance_tonicity(self):
        c_in, c_out = self.concentrations()
        outside_volume = max(20.0, self.box_size ** 3 - self.cell_volume)
        target_out = c_in * outside_volume
        self.solute_outside_osmoles += (target_out - self.solute_outside_osmoles) * 0.28


class ExpressiveAIController:
    MODES = [
        "OBSERVE",
        "SWELL_INVITE",
        "SHRINK_WITHDRAW",
        "STIR_MIX",
        "ORBIT_AND_DIP",
        "MARK_MEMBRANE",
        "CAREFUL_BALANCE",
        "CHAOS_SPILL",
        "RESET_RITUAL",
    ]

    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.mode = "OBSERVE"
        self.previous_modes = []
        self.mode_timer = 0.0
        self.mode_duration = 7.5
        self.orbit_angle = 0.0
        self.dip_phase = 0.0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.history_timer = 0.0
        self.volume_history = []
        self.last_total_crossings = 0
        self.round_pause = 0.0
        self.reset_requested = False
        self.marker_timer = 0.0
        self.wrap_timer = 0.0
        self.spill_timer = 0.0

    def force_next_mode(self):
        self.choose_next_mode(force=True)

    def set_mode(self, m):
        self.previous_modes.append(self.mode)
        self.previous_modes = self.previous_modes[-3:]
        self.mode = m
        self.mode_timer = 0.0
        self.marker_timer = 0.0
        self.wrap_timer = 0.0
        if m == "RESET_RITUAL":
            self.mode_duration = 3.8
        else:
            self.mode_duration = pyrandom.uniform(6.5, 13.0)

    def choose_next_mode(self, force=False):
        vol_ratio = self.sim.cell_volume / self.sim.initial_volume
        c_in, c_out = self.sim.concentrations()
        choices = []

        if vol_ratio > 1.55:
            choices += ["SHRINK_WITHDRAW", "CAREFUL_BALANCE", "MARK_MEMBRANE"]
        elif vol_ratio < 0.70:
            choices += ["SWELL_INVITE", "CAREFUL_BALANCE", "STIR_MIX"]
        elif abs(c_in - c_out) < 0.018:
            choices += ["CHAOS_SPILL", "SWELL_INVITE", "SHRINK_WITHDRAW", "ORBIT_AND_DIP"]
        else:
            choices += ["OBSERVE", "STIR_MIX", "ORBIT_AND_DIP", "MARK_MEMBRANE", "CAREFUL_BALANCE"]

        if self.stagnation_timer > 8.0:
            choices += ["CHAOS_SPILL", "STIR_MIX", "SWELL_INVITE", "SHRINK_WITHDRAW"]

        filtered = [c for c in choices if c not in self.previous_modes[-2:] and c != self.mode]
        if not filtered:
            filtered = [c for c in self.MODES if c != "RESET_RITUAL" and c != self.mode]
        self.set_mode(pyrandom.choice(filtered))

    def detect_stagnation_and_completion(self, dt):
        self.history_timer += dt
        if self.history_timer >= 1.0:
            self.volume_history.append(self.sim.cell_volume)
            self.volume_history = self.volume_history[-14:]

            crossing_delta = self.sim.total_crossings - self.last_total_crossings
            self.last_total_crossings = self.sim.total_crossings

            if len(self.volume_history) >= 10:
                spread = max(self.volume_history) - min(self.volume_history)
                if spread < 1.15 and crossing_delta < 3:
                    self.stagnation_timer += 1.0
                else:
                    self.stagnation_timer = max(0.0, self.stagnation_timer - 1.6)

            self.history_timer = 0.0

        vol_ratio = self.sim.cell_volume / self.sim.initial_volume
        too_large_or_small = vol_ratio > 1.88 or vol_ratio < 0.54
        long_stable = self.stagnation_timer > 16.0

        if too_large_or_small or long_stable:
            self.completion_timer += dt
        else:
            self.completion_timer = max(0.0, self.completion_timer - dt * 0.6)

        if self.completion_timer > 2.5 and self.mode != "RESET_RITUAL":
            self.set_mode("RESET_RITUAL")

    def update_probe(self, dt):
        self.orbit_angle += dt * (0.75 + 0.28 * math.sin(self.mode_timer * 0.7))
        self.dip_phase += dt * 1.35

        base_radius = self.sim.radius * 1.58
        if self.mode == "ORBIT_AND_DIP":
            base_radius = self.sim.radius * (1.04 + 0.60 * (0.5 + 0.5 * math.sin(self.dip_phase)))
        elif self.mode == "MARK_MEMBRANE" or self.sim.probe_attached:
            base_radius = self.sim.radius * 1.045
        elif self.mode == "CHAOS_SPILL":
            base_radius = self.sim.radius * (1.25 + 0.35 * math.sin(self.dip_phase * 2.1))

        target = vector(
            math.cos(self.orbit_angle) * base_radius,
            math.sin(self.orbit_angle * 0.71) * self.sim.radius * 0.45,
            math.sin(self.orbit_angle) * base_radius,
        )

        if self.sim.probe_attached:
            target = safe_norm(target + vector(0.08, 0.03, 0.02)) * self.sim.radius * 1.045

        target += self.sim.probe_manual_offset
        self.sim.ai_probe.pos += (target - self.sim.ai_probe.pos) * clamp(dt * 2.5, 0, 1)

    def apply_mode(self, dt):
        sim = self.sim

        if sim.human_override_timer > 0:
            # Human still permits AI to observe and gently trail, but suppresses strong automatic intervention.
            sim.membrane_permeability += (0.48 - sim.membrane_permeability) * dt * 0.6
            if pyrandom.random() < 0.01:
                sim.add_ai_marker(sim.ai_probe.pos, col=vector(1.0, 0.85, 0.25), size=0.055, ttl=1.2)
            return

        if self.mode == "OBSERVE":
            sim.membrane_permeability += (0.42 - sim.membrane_permeability) * dt * 0.55
            if pyrandom.random() < 0.015:
                sim.add_ai_marker(sim.ai_probe.pos, col=vector(1.0, 0.78, 0.20), size=0.045, ttl=1.1)

        elif self.mode == "SWELL_INVITE":
            sim.membrane_permeability += (0.78 - sim.membrane_permeability) * dt * 0.9
            sim.adjust_internal_osmoles(0.85 * dt)
            sim.radial_push(outward=False, strength=0.030, outside_only=True)
            sim.local_probe_force(strength=0.24, swirl=False, attract=True)
            self.spill_timer += dt
            if self.spill_timer > 3.4:
                sim.spill_water_from_corner(count=3)
                self.spill_timer = 0.0

        elif self.mode == "SHRINK_WITHDRAW":
            sim.membrane_permeability += (0.82 - sim.membrane_permeability) * dt * 0.9
            sim.adjust_external_osmoles(9.0 * dt)
            sim.radial_push(outward=True, strength=0.032, inside_only=True)
            sim.local_probe_force(strength=0.16, swirl=True, attract=False)

        elif self.mode == "STIR_MIX":
            sim.membrane_permeability += (0.56 - sim.membrane_permeability) * dt * 0.9
            axis = safe_norm(vector(0.35 * math.sin(self.mode_timer), 1, 0.45 * math.cos(self.mode_timer * 0.8)))
            sim.stir_all(strength=0.018, axis=axis)
            if pyrandom.random() < 0.025:
                sim.permeability_pulse += 0.10

        elif self.mode == "ORBIT_AND_DIP":
            sim.membrane_permeability += (0.64 - sim.membrane_permeability) * dt * 0.8
            sim.local_probe_force(strength=0.34, swirl=True, attract=True)
            if math.sin(self.dip_phase) > 0.94:
                sim.permeability_pulse += 0.035

        elif self.mode == "MARK_MEMBRANE":
            sim.membrane_permeability += (0.50 - sim.membrane_permeability) * dt * 0.7
            self.marker_timer += dt
            self.wrap_timer += dt
            if self.marker_timer > 0.42:
                n = safe_norm(sim.ai_probe.pos)
                sim.add_ai_marker(n * sim.radius * 1.075, col=vector(1.0, 0.38, 0.76), size=0.070, ttl=2.5)
                self.marker_timer = 0.0
            if self.wrap_timer > 2.4:
                sim.add_wrap_ring(col=vector(1.0, 0.64, 0.22), ttl=4.2, tilt=pyrandom.uniform(0, math.pi), scale=pyrandom.uniform(1.08, 1.24))
                self.wrap_timer = 0.0

        elif self.mode == "CAREFUL_BALANCE":
            sim.membrane_permeability += (0.36 - sim.membrane_permeability) * dt * 0.95
            sim.balance_tonicity()
            for w in sim.water:
                w.vel *= (1.0 - clamp(0.055 * dt, 0, 0.2))
            if pyrandom.random() < 0.012:
                sim.add_ai_marker(sim.ai_probe.pos, col=vector(0.18, 0.82, 0.50), size=0.06, ttl=1.8)

        elif self.mode == "CHAOS_SPILL":
            sim.membrane_permeability += (pyrandom.uniform(0.35, 0.92) - sim.membrane_permeability) * dt * 1.3
            if pyrandom.random() < 0.12:
                sim.random_kick(strength=0.45, fraction=0.15)
            if pyrandom.random() < 0.035:
                sim.permeability_pulse += 0.22
            self.spill_timer += dt
            if self.spill_timer > 2.1:
                sim.spill_water_from_corner(count=5)
                sim.add_wrap_ring(col=vector(0.28, 0.80, 1.0), ttl=2.5, tilt=pyrandom.uniform(0, math.pi), scale=1.35)
                self.spill_timer = 0.0

        elif self.mode == "RESET_RITUAL":
            sim.membrane_permeability += (0.18 - sim.membrane_permeability) * dt * 1.4
            for w in sim.water:
                w.vel *= (1.0 - clamp(0.12 * dt, 0, 0.25))
            self.wrap_timer += dt
            if self.wrap_timer > 0.55:
                sim.add_wrap_ring(col=vector(1.0, 0.80, 0.28), ttl=1.9, tilt=pyrandom.uniform(0, math.pi), scale=1.02 + 0.22 * pyrandom.random())
                self.wrap_timer = 0.0
            if self.mode_timer > self.mode_duration:
                sim.round_index += 1
                sim.reset()
                self.volume_history = []
                self.stagnation_timer = 0.0
                self.completion_timer = 0.0
                self.last_total_crossings = 0
                self.set_mode("OBSERVE")

    def update(self, dt):
        self.update_probe(dt)
        if not self.enabled:
            self.sim.membrane_permeability += (0.52 - self.sim.membrane_permeability) * dt * 0.25
            return

        self.mode_timer += dt
        self.detect_stagnation_and_completion(dt)

        if self.mode != "RESET_RITUAL" and self.mode_timer > self.mode_duration:
            self.choose_next_mode()

        self.apply_mode(dt)


sim = OsmosisSimulation()
controller = ExpressiveAIController(sim)

# ------------------------------------------------------------
# CSV logging support for core sentence branching web app
# ------------------------------------------------------------
CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
CSV_SAMPLE_HZ = float(os.environ.get("SIMULATION_CSV_SAMPLE_HZ", "10"))
CSV_SAMPLE_INTERVAL = 1.0 / max(0.001, CSV_SAMPLE_HZ)

_csv_output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
_csv_run_id = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

if _csv_output_dir:
    os.makedirs(_csv_output_dir, exist_ok=True)
    CSV_OUTPUT_PATH = os.path.join(_csv_output_dir, f"{_csv_run_id}-osmosis-state-log.csv")
else:
    CSV_OUTPUT_PATH = os.environ.get(
        "SIM_STATE_CSV_PATH",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "osmosis_state_log.csv")
    )
    parent = os.path.dirname(CSV_OUTPUT_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)

CSV_METADATA_PATH = os.path.splitext(CSV_OUTPUT_PATH)[0] + ".metadata.json"

CSV_FIELDNAMES = [
    "csv_run_id", "csv_elapsed_seconds", "simulation_time", "frame",
    "row_type", "object_id", "object_kind",
    "round_index", "ai_enabled", "ai_mode", "paused", "human_override_timer",
    "cell_radius", "cell_volume", "initial_volume", "volume_percent",
    "inside_water_count", "outside_water_count", "total_water_count",
    "inside_solute_count", "outside_solute_count", "total_solute_count",
    "solute_inside_osmoles", "solute_outside_osmoles",
    "internal_tonicity", "external_tonicity",
    "membrane_permeability", "permeability_pulse", "effective_permeability",
    "flux_rate", "cross_in_second", "cross_out_second", "total_crossings",
    "crossing_mark_count", "wrap_ring_count",
    "stagnation_timer", "completion_timer", "mode_timer", "mode_duration",
    "probe_attached", "probe_x", "probe_y", "probe_z",
    "x", "y", "z", "vx", "vy", "vz",
    "inside", "marked", "particle_type", "opacity", "radius"
]

_csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
_csv_writer = csv.DictWriter(_csv_file, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
_csv_writer.writeheader()
_csv_file.flush()


def _vec_tuple(v):
    return (float(v.x), float(v.y), float(v.z))


def _state_counts():
    inside_water = sum(1 for w in sim.water if w.inside)
    outside_water = len(sim.water) - inside_water
    inside_solutes = sum(1 for s in sim.solutes if s.inside)
    outside_solutes = len(sim.solutes) - inside_solutes
    c_in, c_out = sim.concentrations()
    return inside_water, outside_water, inside_solutes, outside_solutes, c_in, c_out


def _base_csv_row(csv_elapsed_seconds, frame, row_type, object_id="", object_kind=""):
    inside_water, outside_water, inside_solutes, outside_solutes, c_in, c_out = _state_counts()
    px, py, pz = _vec_tuple(sim.ai_probe.pos)
    effective_perm = clamp(sim.membrane_permeability + sim.permeability_pulse, 0.0, 1.0)
    return {
        "csv_run_id": _csv_run_id,
        "csv_elapsed_seconds": round(csv_elapsed_seconds, 4),
        "simulation_time": round(csv_elapsed_seconds, 4),
        "frame": frame,
        "row_type": row_type,
        "object_id": object_id,
        "object_kind": object_kind,
        "round_index": sim.round_index + 1,
        "ai_enabled": controller.enabled,
        "ai_mode": controller.mode,
        "paused": sim.paused,
        "human_override_timer": round(sim.human_override_timer, 4),
        "cell_radius": round(sim.radius, 6),
        "cell_volume": round(sim.cell_volume, 6),
        "initial_volume": round(sim.initial_volume, 6),
        "volume_percent": round(100.0 * sim.cell_volume / max(1e-9, sim.initial_volume), 6),
        "inside_water_count": inside_water,
        "outside_water_count": outside_water,
        "total_water_count": len(sim.water),
        "inside_solute_count": inside_solutes,
        "outside_solute_count": outside_solutes,
        "total_solute_count": len(sim.solutes),
        "solute_inside_osmoles": round(sim.solute_inside_osmoles, 6),
        "solute_outside_osmoles": round(sim.solute_outside_osmoles, 6),
        "internal_tonicity": round(c_in, 8),
        "external_tonicity": round(c_out, 8),
        "membrane_permeability": round(sim.membrane_permeability, 6),
        "permeability_pulse": round(sim.permeability_pulse, 6),
        "effective_permeability": round(effective_perm, 6),
        "flux_rate": round(sim.flux_rate, 6),
        "cross_in_second": sim.cross_in_second,
        "cross_out_second": sim.cross_out_second,
        "total_crossings": sim.total_crossings,
        "crossing_mark_count": len(sim.crossing_marks),
        "wrap_ring_count": len(sim.wrap_rings),
        "stagnation_timer": round(controller.stagnation_timer, 6),
        "completion_timer": round(controller.completion_timer, 6),
        "mode_timer": round(controller.mode_timer, 6),
        "mode_duration": round(controller.mode_duration, 6),
        "probe_attached": sim.probe_attached,
        "probe_x": round(px, 6),
        "probe_y": round(py, 6),
        "probe_z": round(pz, 6),
    }


def write_csv_snapshot(csv_elapsed_seconds, frame):
    _csv_writer.writerow(_base_csv_row(csv_elapsed_seconds, frame, "summary", "osmosis", "simulation"))

    for i, w in enumerate(sim.water):
        x, y, z = _vec_tuple(w.obj.pos)
        vx, vy, vz = _vec_tuple(w.vel)
        row = _base_csv_row(csv_elapsed_seconds, frame, "water", f"water_{i}", "water")
        row.update({
            "x": round(x, 6), "y": round(y, 6), "z": round(z, 6),
            "vx": round(vx, 6), "vy": round(vy, 6), "vz": round(vz, 6),
            "inside": w.inside,
            "marked": w.marked,
            "particle_type": "water",
            "opacity": getattr(w.obj, "opacity", ""),
            "radius": getattr(w.obj, "radius", ""),
        })
        _csv_writer.writerow(row)

    for i, s in enumerate(sim.solutes):
        x, y, z = _vec_tuple(s.obj.pos)
        vx, vy, vz = _vec_tuple(s.vel)
        row = _base_csv_row(csv_elapsed_seconds, frame, "solute", f"solute_{i}", "solute")
        row.update({
            "x": round(x, 6), "y": round(y, 6), "z": round(z, 6),
            "vx": round(vx, 6), "vy": round(vy, 6), "vz": round(vz, 6),
            "inside": s.inside,
            "particle_type": "solute",
            "opacity": getattr(s.obj, "opacity", ""),
            "radius": getattr(s.obj, "radius", ""),
        })
        _csv_writer.writerow(row)

    _csv_file.flush()


def write_csv_metadata(completed=False, csv_elapsed_seconds=0.0, frame=0):
    inside_water, outside_water, inside_solutes, outside_solutes, c_in, c_out = _state_counts()
    metadata = {
        "csv_run_id": _csv_run_id,
        "csv_output_path": CSV_OUTPUT_PATH,
        "csv_metadata_path": CSV_METADATA_PATH,
        "script_name": "osmosis_vpython_full_csv.py",
        "simulation_name": "3D Osmosis and Cell Swelling/Shrinking Simulation",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "completed": bool(completed),
        "configured_run_seconds": CSV_RUN_SECONDS,
        "sample_hz": CSV_SAMPLE_HZ,
        "elapsed_seconds": round(csv_elapsed_seconds, 4),
        "frame": frame,
        "final_round_index": sim.round_index + 1,
        "final_ai_mode": controller.mode,
        "final_cell_radius": sim.radius,
        "final_cell_volume": sim.cell_volume,
        "final_volume_percent": 100.0 * sim.cell_volume / max(1e-9, sim.initial_volume),
        "final_inside_water_count": inside_water,
        "final_outside_water_count": outside_water,
        "final_inside_solute_count": inside_solutes,
        "final_outside_solute_count": outside_solutes,
        "final_internal_tonicity": c_in,
        "final_external_tonicity": c_out,
        "final_total_crossings": sim.total_crossings,
        "environment_variables": {
            "SIMULATION_CSV_OUTPUT_DIR": os.environ.get("SIMULATION_CSV_OUTPUT_DIR", ""),
            "SIMULATION_CSV_RUN_ID": os.environ.get("SIMULATION_CSV_RUN_ID", ""),
            "SIMULATION_CSV_RUN_SECONDS": os.environ.get("SIMULATION_CSV_RUN_SECONDS", ""),
            "SIMULATION_CSV_SAMPLE_HZ": os.environ.get("SIMULATION_CSV_SAMPLE_HZ", ""),
            "SIM_STATE_CSV_PATH": os.environ.get("SIM_STATE_CSV_PATH", ""),
        },
    }
    with open(CSV_METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)


def close_csv_logger(completed=False, csv_elapsed_seconds=0.0, frame=0):
    try:
        write_csv_metadata(completed=completed, csv_elapsed_seconds=csv_elapsed_seconds, frame=frame)
    finally:
        _csv_file.flush()
        _csv_file.close()



def on_keydown(evt):
    k = evt.key
    sim.human_override_timer = 3.5

    if k in ["p", "P"]:
        sim.paused = not sim.paused

    elif k in ["a", "A"]:
        controller.enabled = not controller.enabled

    elif k in ["m", "M"]:
        controller.force_next_mode()

    elif k in ["r", "R"]:
        sim.round_index += 1
        sim.reset()
        controller.volume_history = []
        controller.stagnation_timer = 0.0
        controller.completion_timer = 0.0
        controller.set_mode("OBSERVE")

    elif k == " ":
        sim.stir_all(strength=0.85, axis=vector(0, 1, 0))
        sim.random_kick(strength=0.55, fraction=0.22)
        sim.permeability_pulse += 0.18

    elif k in ["w", "W"]:
        sim.membrane_permeability = clamp(sim.membrane_permeability + 0.08, 0.02, 1.0)

    elif k in ["s", "S"]:
        sim.membrane_permeability = clamp(sim.membrane_permeability - 0.08, 0.02, 1.0)

    elif k in ["i", "I"]:
        sim.adjust_internal_osmoles(5.0)
        sim.add_ai_marker(vector(0, sim.radius * 0.7, 0), col=vector(1.0, 0.48, 0.12), size=0.12, ttl=2.0)

    elif k in ["k", "K"]:
        sim.adjust_internal_osmoles(-5.0)

    elif k in ["o", "O"]:
        sim.adjust_external_osmoles(60.0)
        sim.add_ai_marker(vector(sim.radius * 1.4, 0, 0), col=vector(0.72, 0.24, 0.98), size=0.12, ttl=2.0)

    elif k in ["l", "L"]:
        sim.adjust_external_osmoles(-60.0)

    elif k in ["c", "C"]:
        sim.random_kick(strength=1.65, fraction=0.65)
        sim.permeability_pulse += 0.35
        sim.add_wrap_ring(col=vector(0.28, 0.80, 1.0), ttl=2.3, tilt=pyrandom.uniform(0, math.pi), scale=1.35)

    elif k in ["b", "B"]:
        sim.balance_tonicity()
        controller.set_mode("CAREFUL_BALANCE")

    elif k in ["x", "X"]:
        sim.probe_attached = not sim.probe_attached

    elif k == "up":
        sim.probe_manual_offset += vector(0, 0.35, 0)

    elif k == "down":
        sim.probe_manual_offset += vector(0, -0.35, 0)

    elif k == "left":
        sim.probe_manual_offset += vector(-0.35, 0, 0)

    elif k == "right":
        sim.probe_manual_offset += vector(0.35, 0, 0)

    elif k in ["q", "Q"]:
        sim.probe_manual_offset += vector(0, 0, 0.35)

    elif k in ["e", "E"]:
        sim.probe_manual_offset += vector(0, 0, -0.35)

    elif k in ["z", "Z"]:
        sim.probe_manual_offset = vector(0, 0, 0)


scene.bind("keydown", on_keydown)

dt = 1 / 60
csv_elapsed_seconds = 0.0
csv_sample_timer = CSV_SAMPLE_INTERVAL
csv_frame = 0

try:
    write_csv_metadata(completed=False, csv_elapsed_seconds=0.0, frame=0)

    while csv_elapsed_seconds < CSV_RUN_SECONDS:
        rate(60)
        csv_frame += 1
        csv_elapsed_seconds += dt
        csv_sample_timer += dt

        if not sim.paused:
            controller.update(dt)
            sim.update(dt, controller.mode)
        else:
            sim.update_labels(controller.mode)

        if csv_sample_timer >= CSV_SAMPLE_INTERVAL:
            csv_sample_timer = 0.0
            write_csv_snapshot(csv_elapsed_seconds, csv_frame)

    write_csv_snapshot(csv_elapsed_seconds, csv_frame)
    sim.volume_label.text = (
        f"CSV recording complete: {CSV_RUN_SECONDS:0.0f}s saved to "
        f"{os.path.basename(CSV_OUTPUT_PATH)}\n"
        f"Final cell volume: {sim.cell_volume:6.1f} | Radius: {sim.radius:4.2f} | "
        f"Total crossings: {sim.total_crossings}"
    )
finally:
    close_csv_logger(completed=True, csv_elapsed_seconds=csv_elapsed_seconds, frame=csv_frame)
