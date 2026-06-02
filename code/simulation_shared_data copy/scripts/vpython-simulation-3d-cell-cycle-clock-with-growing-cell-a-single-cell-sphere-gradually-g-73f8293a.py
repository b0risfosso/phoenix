from vpython import *
import random
import math

# ------------------------------------------------------------
# 3D Cell Cycle Clock with Growing Cell + Expressive AI Controller
# Requires: pip install vpython
# Run: python this_file.py
# ------------------------------------------------------------

scene = canvas(
    title="3D Cell Cycle Clock with Growing Cell + AI Controller",
    width=1200,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0.15, 0),
)
scene.forward = vector(0, -0.12, -1.9)
scene.range = 5.6
scene.lights = []
distant_light(direction=vector(0.4, -0.7, -0.5), color=vector(0.95, 0.95, 0.92))
distant_light(direction=vector(-0.5, -0.35, -0.8), color=vector(0.58, 0.65, 0.75))

# ------------------------------
# Utility functions
# ------------------------------

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def lerp(a, b, t):
    return a + (b - a) * clamp(t)

def mix_color(c1, c2, t):
    t = clamp(t)
    return c1 * (1 - t) + c2 * t

def rand_vec_in_sphere(scale=1.0):
    while True:
        v = vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        if mag(v) <= 1 and mag(v) > 0.001:
            return v * scale

def spherical_pos(theta, phi, radius):
    return vector(
        math.cos(theta) * math.sin(phi) * radius,
        math.cos(phi) * radius,
        math.sin(theta) * math.sin(phi) * radius,
    )

def safe_norm(v):
    if mag(v) < 1e-6:
        return vector(1, 0, 0)
    return norm(v)

# ------------------------------
# Simulation
# ------------------------------

class CellCycleSimulation:
    def __init__(self):
        self.cell_base = vector(-2.55, 0.05, 0)
        self.clock_center = vector(2.45, 0.1, 0)
        self.clock_radius = 1.35

        self.phase_names = ["G1", "S", "G2", "M"]
        self.phase_durations = {"G1": 7.0, "S": 8.0, "G2": 6.0, "M": 5.0}
        self.phase_colors = {
            "G1": vector(0.30, 0.75, 0.92),
            "S":  vector(0.72, 0.48, 0.94),
            "G2": vector(1.00, 0.70, 0.34),
            "M":  vector(1.00, 0.42, 0.46),
        }
        self.total_duration = sum(self.phase_durations.values())
        self.m_start_time = self.phase_durations["G1"] + self.phase_durations["S"] + self.phase_durations["G2"]

        self.min_radius = 0.55
        self.max_radius = 1.02
        self.daughter_radius = self.max_radius * (0.5 ** (1 / 3)) * 0.94

        self.human_speed = 1.0
        self.ai_speed = 1.0
        self.ai_swirl = 0.0
        self.paused = False
        self.completed = False
        self.round_index = 1

        self.dynamic_objects = []
        self.dna = []
        self.free_particles = []

        self.cycle_time = 0.0
        self.current_radius = self.min_radius
        self.current_phase = "G1"
        self.current_phase_progress = 0.0
        self.visual_clock_rotation = 0.0

        self.create_static_scene()
        self.reset(full=False)

    def register(self, obj):
        self.dynamic_objects.append(obj)
        return obj

    def create_static_scene(self):
        self.floor = box(
            pos=vector(0, -1.38, 0),
            size=vector(8.8, 0.035, 4.3),
            color=vector(0.88, 0.93, 0.94),
            opacity=0.42,
        )

        self.title_label = label(
            pos=vector(0, 2.55, 0),
            text="3D Cell Cycle Clock: Growing Cell, DNA Duplication, Mitosis",
            height=20,
            color=vector(0.18, 0.22, 0.28),
            box=False,
            opacity=0,
        )

        self.status_label = label(
            pos=vector(-2.55, 1.85, 0),
            text="",
            height=15,
            color=vector(0.13, 0.16, 0.20),
            box=False,
            opacity=0,
        )

        self.clock_title = label(
            pos=self.clock_center + vector(0, 1.95, 0),
            text="Cell Cycle Clock",
            height=17,
            color=vector(0.18, 0.22, 0.28),
            box=False,
            opacity=0,
        )

        self.control_label = label(
            pos=vector(0, -2.12, 0),
            text=(
                "Controls: SPACE pause/resume | R reset | B AI on/off | Z pause AI | +/- speed | "
                "IJKL/UO move AI orb override | N step phase"
            ),
            height=12,
            color=vector(0.26, 0.30, 0.35),
            box=False,
            opacity=0,
        )

        self.clock_back_ring = ring(
            pos=self.clock_center,
            axis=vector(0, 0, 1),
            radius=self.clock_radius,
            thickness=0.018,
            color=vector(0.75, 0.79, 0.82),
            opacity=0.35,
        )

        self.clock_segments = []
        n = 128
        for i in range(n):
            frac = i / n
            ph, _ = self.phase_from_time(frac * self.total_duration)
            angle = math.pi / 2 - 2 * math.pi * frac
            r = self.clock_radius
            bead = sphere(
                pos=self.clock_center + vector(math.cos(angle), math.sin(angle), 0) * r,
                radius=0.035,
                color=mix_color(self.phase_colors[ph], vector(1, 1, 1), 0.28),
                opacity=0.82,
            )
            self.clock_segments.append(bead)

        cum = 0.0
        for ph in self.phase_names:
            dur = self.phase_durations[ph]
            mid_frac = (cum + dur * 0.5) / self.total_duration
            ang = math.pi / 2 - 2 * math.pi * mid_frac
            label(
                pos=self.clock_center + vector(math.cos(ang), math.sin(ang), 0) * (self.clock_radius + 0.38),
                text=ph,
                height=18,
                color=self.phase_colors[ph] * 0.75,
                box=False,
                opacity=0,
            )

            boundary_frac = cum / self.total_duration
            bang = math.pi / 2 - 2 * math.pi * boundary_frac
            cylinder(
                pos=self.clock_center,
                axis=vector(math.cos(bang), math.sin(bang), 0) * self.clock_radius,
                radius=0.008,
                color=vector(0.72, 0.75, 0.78),
                opacity=0.45,
            )
            cum += dur

        self.clock_pointer = arrow(
            pos=self.clock_center,
            axis=vector(0, self.clock_radius * 0.88, 0),
            shaftwidth=0.045,
            headwidth=0.13,
            headlength=0.18,
            color=vector(0.18, 0.22, 0.28),
        )
        self.clock_pointer_tip = sphere(
            pos=self.clock_center + vector(0, self.clock_radius * 0.98, 0),
            radius=0.085,
            color=vector(1, 1, 1),
            emissive=True,
        )
        self.phase_label = label(
            pos=self.clock_center + vector(0, -1.8, 0),
            text="",
            height=16,
            color=vector(0.18, 0.22, 0.28),
            box=False,
            opacity=0,
        )

    def phase_from_time(self, t):
        t = clamp(t, 0, self.total_duration)
        cum = 0.0
        for ph in self.phase_names:
            dur = self.phase_durations[ph]
            if t <= cum + dur or ph == self.phase_names[-1]:
                return ph, clamp((t - cum) / dur)
            cum += dur
        return "M", 1.0

    def clear_dynamic(self):
        for obj in self.dynamic_objects:
            try:
                obj.visible = False
            except Exception:
                pass
        self.dynamic_objects = []
        self.dna = []
        self.free_particles = []

    def reset(self, full=True):
        self.clear_dynamic()
        self.cycle_time = 0.0
        self.current_phase = "G1"
        self.current_phase_progress = 0.0
        self.current_radius = self.min_radius
        self.completed = False
        self.ai_speed = 1.0
        self.ai_swirl = 0.0

        if full:
            self.round_index += 1

        self.parent_cell = self.register(sphere(
            pos=self.cell_base,
            radius=self.min_radius,
            color=self.phase_colors["G1"],
            opacity=0.62,
            shininess=0.65,
        ))

        self.cell_shell = self.register(sphere(
            pos=self.cell_base,
            radius=self.min_radius * 1.015,
            color=vector(1, 1, 1),
            opacity=0.13,
            shininess=0.2,
        ))

        self.nucleus = self.register(sphere(
            pos=self.cell_base,
            radius=self.min_radius * 0.42,
            color=vector(0.82, 0.90, 1.0),
            opacity=0.25,
        ))

        self.daughter_left = self.register(sphere(
            pos=self.cell_base,
            radius=0.05,
            color=self.phase_colors["M"],
            opacity=0.0,
            visible=False,
        ))
        self.daughter_right = self.register(sphere(
            pos=self.cell_base,
            radius=0.05,
            color=self.phase_colors["M"],
            opacity=0.0,
            visible=False,
        ))

        self.cleavage_groove = self.register(ring(
            pos=self.cell_base,
            axis=vector(1, 0, 0),
            radius=self.min_radius * 0.55,
            thickness=0.01,
            color=vector(0.72, 0.18, 0.25),
            opacity=0.0,
            visible=False,
        ))

        random.seed(11 + self.round_index)
        dna_count = 12
        for i in range(dna_count):
            local = rand_vec_in_sphere(0.55)
            offset = safe_norm(rand_vec_in_sphere(0.12))
            side = -1 if i % 2 == 0 else 1
            dot1 = self.register(sphere(
                pos=self.cell_base + local * self.min_radius,
                radius=0.045,
                color=vector(1.0, 0.88, 0.22),
                emissive=True,
                opacity=0.95,
            ))
            dot2 = self.register(sphere(
                pos=self.cell_base + local * self.min_radius,
                radius=0.040,
                color=vector(0.98, 0.62, 0.18),
                emissive=True,
                opacity=0.0,
                visible=False,
            ))
            self.dna.append({
                "a": dot1,
                "b": dot2,
                "local": local,
                "offset": offset,
                "side": side,
                "seed": random.random() * 100.0,
            })

        self.spawn_birth_sparkles()
        self.update(0.0, advance_cycle=False, advance_particles=False)

    def spawn_birth_sparkles(self):
        for _ in range(22):
            direction = safe_norm(rand_vec_in_sphere(1))
            self.spawn_particle(
                pos=self.cell_base + direction * (self.min_radius + 0.05),
                vel=direction * random.uniform(0.08, 0.24),
                col=vector(0.56, 0.95, 0.92),
                radius=random.uniform(0.018, 0.033),
                life=random.uniform(3.5, 6.5),
                behavior="attach",
            )

    def get_cell_bodies(self):
        bodies = []
        if self.parent_cell.visible and self.parent_cell.opacity > 0.08:
            bodies.append((self.parent_cell.pos, self.current_radius))
        if self.daughter_left.visible and self.daughter_left.opacity > 0.08:
            bodies.append((self.daughter_left.pos, self.daughter_left.radius))
        if self.daughter_right.visible and self.daughter_right.opacity > 0.08:
            bodies.append((self.daughter_right.pos, self.daughter_right.radius))
        return bodies

    def spawn_particle(self, pos, vel, col, radius=0.025, life=5.0, behavior="spill", target=None):
        if len(self.free_particles) > 260:
            old = self.free_particles.pop(0)
            old["obj"].visible = False

        obj = self.register(sphere(
            pos=pos,
            radius=radius,
            color=col,
            opacity=0.82,
            emissive=True,
        ))
        p = {
            "obj": obj,
            "vel": vel,
            "age": 0.0,
            "life": life,
            "behavior": behavior,
            "target": target,
            "attached": False,
            "theta": random.random() * 2 * math.pi,
            "phi": random.uniform(0.45, 2.65),
            "spin": random.choice([-1, 1]) * random.uniform(0.35, 1.4),
            "body_index": random.randint(0, 2),
            "seed": random.random() * 1000,
        }
        self.free_particles.append(p)
        return p

    def update_phase_and_growth(self):
        self.current_phase, self.current_phase_progress = self.phase_from_time(self.cycle_time)

        if self.cycle_time < self.m_start_time:
            growth_progress = clamp(self.cycle_time / self.m_start_time)
        else:
            growth_progress = 1.0

        self.current_radius = lerp(self.min_radius, self.max_radius, growth_progress)
        base_col = self.phase_colors[self.current_phase]
        pulse = 0.08 * (0.5 + 0.5 * math.sin(self.cycle_time * 2.1))
        cell_col = mix_color(base_col, vector(1, 1, 1), 0.12 + pulse)

        self.parent_cell.color = cell_col
        self.cell_shell.color = mix_color(cell_col, vector(1, 1, 1), 0.55)
        self.nucleus.color = mix_color(base_col, vector(0.83, 0.94, 1.0), 0.62)

        if self.current_phase != "M":
            self.parent_cell.visible = True
            self.cell_shell.visible = True
            self.nucleus.visible = True
            self.parent_cell.opacity = 0.62
            self.cell_shell.opacity = 0.13
            self.nucleus.opacity = 0.25
            self.parent_cell.pos = self.cell_base
            self.cell_shell.pos = self.cell_base
            self.nucleus.pos = self.cell_base
            self.parent_cell.radius = self.current_radius
            self.parent_cell.size = vector(2, 2, 2) * self.current_radius
            self.cell_shell.radius = self.current_radius * 1.015
            self.nucleus.radius = self.current_radius * 0.42
            self.daughter_left.visible = False
            self.daughter_right.visible = False
            self.cleavage_groove.visible = False
        else:
            p = self.current_phase_progress
            split_distance = lerp(0.0, 1.18, p ** 1.25)
            squeeze = clamp(p * 1.35)

            self.parent_cell.visible = True
            self.cell_shell.visible = True
            self.nucleus.visible = p < 0.72
            self.parent_cell.pos = self.cell_base
            self.cell_shell.pos = self.cell_base
            self.nucleus.pos = self.cell_base
            self.parent_cell.opacity = lerp(0.62, 0.02, p)
            self.cell_shell.opacity = lerp(0.13, 0.02, p)
            self.nucleus.opacity = lerp(0.22, 0.0, p)
            self.parent_cell.size = vector(
                2 * self.max_radius * (1.0 + 0.32 * squeeze),
                2 * self.max_radius * (1.0 - 0.46 * squeeze),
                2 * self.max_radius * (1.0 - 0.46 * squeeze),
            )
            self.cell_shell.size = self.parent_cell.size * 1.02
            self.nucleus.radius = self.max_radius * 0.35 * (1 - p)

            self.daughter_left.visible = True
            self.daughter_right.visible = True
            self.daughter_left.pos = self.cell_base + vector(-split_distance, 0, 0)
            self.daughter_right.pos = self.cell_base + vector(split_distance, 0, 0)
            dr = lerp(0.16, self.daughter_radius, clamp((p - 0.08) / 0.75))
            self.daughter_left.radius = dr
            self.daughter_right.radius = dr
            self.daughter_left.color = mix_color(self.phase_colors["M"], self.phase_colors["G1"], p * 0.45)
            self.daughter_right.color = self.daughter_left.color
            self.daughter_left.opacity = clamp(p * 1.6) * 0.65
            self.daughter_right.opacity = clamp(p * 1.6) * 0.65

            self.cleavage_groove.visible = p < 0.88
            self.cleavage_groove.pos = self.cell_base
            self.cleavage_groove.radius = self.max_radius * lerp(0.73, 0.18, p)
            self.cleavage_groove.opacity = 0.56 * math.sin(math.pi * clamp(p))

    def update_dna(self, dt):
        ph = self.current_phase
        phase_p = self.current_phase_progress
        swirl = 0.18 + self.ai_swirl

        for i, d in enumerate(self.dna):
            a = d["a"]
            b = d["b"]
            local = d["local"]
            offset = d["offset"]
            slow_angle = self.cycle_time * swirl + d["seed"]
            rotated = local.rotate(angle=slow_angle, axis=vector(0.25, 1, 0.15))

            if ph != "M":
                center = self.cell_base
                nuc_scale = self.current_radius * 0.58
                a.visible = True
                a.opacity = 0.95
                a.radius = 0.042 + 0.008 * math.sin(self.cycle_time * 3.0 + i)
                a.pos = center + rotated * nuc_scale

                if ph == "S":
                    start = i / len(self.dna) * 0.62
                    dup_p = clamp((phase_p - start) / 0.36)
                elif self.cycle_time > self.phase_durations["G1"] + self.phase_durations["S"]:
                    dup_p = 1.0
                else:
                    dup_p = 0.0

                b.visible = dup_p > 0.02
                b.opacity = 0.90 * dup_p
                b.radius = 0.035 + 0.006 * dup_p
                sep = offset.rotate(angle=slow_angle * 0.7, axis=vector(0, 1, 0)) * self.current_radius * 0.32 * dup_p
                b.pos = a.pos + sep
            else:
                p = phase_p
                split_distance = lerp(0.0, 1.18, p ** 1.25)
                side = d["side"]
                daughter_center = self.cell_base + vector(side * split_distance, 0, 0)
                side_local = vector(abs(local.x) * side * 0.45, local.y, local.z)
                side_rot = side_local.rotate(angle=self.cycle_time * 0.55 + d["seed"], axis=vector(0, 1, 0.2))
                target = daughter_center + side_rot * self.daughter_radius * 0.62
                old_parent_pos = self.cell_base + rotated * self.max_radius * 0.50
                pos = old_parent_pos * (1 - p) + target * p
                a.visible = True
                b.visible = True
                a.opacity = 0.95
                b.opacity = 0.85
                a.pos = pos
                b.pos = pos + vector(0.06 * side, 0.03 * math.sin(i), 0.04 * math.cos(i))
                a.radius = 0.040
                b.radius = 0.036

        self.ai_swirl *= max(0, 1 - dt * 1.2)

    def update_clock(self):
        frac = clamp(self.cycle_time / self.total_duration)
        angle = math.pi / 2 - 2 * math.pi * frac + self.visual_clock_rotation
        axis = vector(math.cos(angle), math.sin(angle), 0) * (self.clock_radius * 0.88)
        self.clock_pointer.axis = axis
        self.clock_pointer.color = mix_color(self.phase_colors[self.current_phase], vector(0.15, 0.18, 0.22), 0.35)
        self.clock_pointer_tip.pos = self.clock_center + safe_norm(axis) * (self.clock_radius * 0.98)
        self.clock_pointer_tip.color = mix_color(self.phase_colors[self.current_phase], vector(1, 1, 1), 0.25)
        self.phase_label.text = f"Phase: {self.current_phase}   progress {int(self.current_phase_progress * 100)}%"
        self.phase_label.color = self.phase_colors[self.current_phase] * 0.75

    def update_particles(self, dt, advance=True):
        if not advance:
            return

        bodies = self.get_cell_bodies()
        survivors = []

        for p in self.free_particles:
            obj = p["obj"]
            if not obj.visible:
                continue

            p["age"] += dt
            if p["age"] > p["life"]:
                obj.visible = False
                continue

            fade = clamp(1 - p["age"] / p["life"])
            obj.opacity = 0.12 + 0.78 * fade

            if p["attached"] and bodies:
                idx = p["body_index"] % len(bodies)
                center, r = bodies[idx]
                p["theta"] += dt * p["spin"]
                p["phi"] += 0.13 * math.sin(self.cycle_time + p["seed"]) * dt
                obj.pos = center + spherical_pos(p["theta"], p["phi"], r + obj.radius * 1.7)
                survivors.append(p)
                continue

            if p["behavior"] == "organize":
                if p["target"] is None:
                    ang = p["seed"] % (2 * math.pi)
                    p["target"] = self.clock_center + vector(math.cos(ang), math.sin(ang), 0) * (self.clock_radius + 0.16)
                to_target = p["target"] - obj.pos
                p["vel"] += safe_norm(to_target) * dt * 1.55
                p["vel"] *= 0.972
                if mag(to_target) < 0.08:
                    tangent = vector(-to_target.y, to_target.x, 0)
                    if mag(tangent) > 0.001:
                        p["vel"] += norm(tangent) * 0.025

            elif p["behavior"] == "orbit":
                center = self.clock_center if random.random() < 0.5 else self.cell_base
                radial = obj.pos - center
                tangent = vector(-radial.y, radial.x, 0)
                if mag(tangent) > 0.001:
                    p["vel"] += norm(tangent) * dt * 0.42
                if mag(radial) > 2.3:
                    p["vel"] += safe_norm(center - obj.pos) * dt * 0.55

            elif p["behavior"] == "spill":
                p["vel"] += vector(0, -0.16, 0) * dt

            obj.pos += p["vel"] * dt

            if obj.pos.y < -1.31:
                obj.pos.y = -1.31
                p["vel"].y = abs(p["vel"].y) * 0.68
                p["vel"].x *= 0.82
                p["vel"].z *= 0.82

            for bi, (center, r) in enumerate(bodies):
                diff = obj.pos - center
                dist = mag(diff)
                if dist < r + obj.radius and dist > 0.001:
                    n = norm(diff)
                    obj.pos = center + n * (r + obj.radius)
                    if p["behavior"] in ("attach", "mark", "careful"):
                        p["attached"] = True
                        p["body_index"] = bi
                        p["theta"] = math.atan2(n.z, n.x)
                        p["phi"] = math.acos(clamp(n.y, -1, 1))
                        obj.color = mix_color(obj.color, vector(1, 1, 1), 0.18)
                    else:
                        p["vel"] = p["vel"] - 2 * dot(p["vel"], n) * n
                        p["vel"] *= 0.72
                        obj.color = mix_color(obj.color, self.phase_colors[self.current_phase], 0.35)

            survivors.append(p)

        self.free_particles = survivors

    def update_status(self):
        pause_text = "PAUSED" if self.paused else "running"
        done_text = " | complete: two daughter cells" if self.completed else ""
        self.status_label.text = (
            f"Round {self.round_index} | {pause_text} | speed x{self.human_speed * self.ai_speed:.2f}\n"
            f"Cell radius {self.current_radius:.2f} | DNA dots duplicate in S phase{done_text}"
        )
        self.status_label.color = mix_color(self.phase_colors[self.current_phase], vector(0.08, 0.10, 0.12), 0.55)

    def force_next_phase(self):
        ph, p = self.phase_from_time(self.cycle_time)
        cum = 0.0
        for name in self.phase_names:
            dur = self.phase_durations[name]
            if name == ph:
                self.cycle_time = min(cum + dur + 0.02, self.total_duration)
                return
            cum += dur

    def update(self, dt, advance_cycle=True, advance_particles=True):
        if advance_cycle and not self.completed:
            self.cycle_time += dt * self.human_speed * self.ai_speed
            if self.cycle_time >= self.total_duration:
                self.cycle_time = self.total_duration
                self.completed = True

        self.update_phase_and_growth()
        self.update_dna(dt)
        self.update_clock()
        self.update_particles(dt, advance=advance_particles)
        self.update_status()

# ------------------------------
# AI Controller
# ------------------------------

class AIController:
    MODES = [
        "OBSERVE",
        "CLOCK_SPIN",
        "CAREFUL_GROW",
        "DUPLICATION_GUIDE",
        "MITOSIS_HELPER",
        "CHAOS_SPILL",
        "ORGANIZE",
        "ARTISTIC_WRAP",
        "RESET_LOOP",
    ]

    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.paused = False
        self.override_timer = 0.0

        self.mode = "OBSERVE"
        self.previous_mode = None
        self.mode_timer = 0.0
        self.mode_duration = 5.0
        self.round_timer = 0.0
        self.completion_timer = 0.0
        self.stagnation_timer = 0.0
        self.last_signature = None
        self.last_cycle_time = sim.cycle_time

        self.helper = sphere(
            pos=vector(0, 1.25, 0),
            radius=0.105,
            color=vector(0.1, 0.72, 1.0),
            opacity=0.78,
            emissive=True,
            make_trail=True,
            retain=90,
            trail_radius=0.012,
            trail_color=vector(0.28, 0.82, 1.0),
        )
        self.helper_label = label(
            pos=self.helper.pos + vector(0, 0.22, 0),
            text="AI",
            height=10,
            color=vector(0.1, 0.35, 0.48),
            box=False,
            opacity=0,
        )

        self.clock_beads = []
        for i in range(4):
            self.clock_beads.append(sphere(
                pos=sim.clock_center,
                radius=0.055,
                color=vector(0.28, 0.86, 1.0),
                opacity=0.50,
                emissive=True,
            ))

        self.wrap_beads = []
        for i in range(56):
            self.wrap_beads.append(sphere(
                pos=sim.cell_base,
                radius=0.018,
                color=vector(0.28, 0.95, 0.80),
                opacity=0.0,
                emissive=True,
                visible=False,
            ))

        self.mode_label = label(
            pos=vector(0, 2.18, 0),
            text="",
            height=14,
            color=vector(0.15, 0.30, 0.38),
            box=False,
            opacity=0,
        )

        self.switch_mode("OBSERVE")

    def signature(self):
        sim = self.sim
        return (
            sim.current_phase,
            round(sim.cycle_time, 1),
            int(sim.completed),
            len(sim.free_particles),
            len(sim.get_cell_bodies()),
        )

    def switch_mode(self, new_mode=None):
        if new_mode is None:
            new_mode = self.choose_mode()
        if new_mode == self.mode and len(self.MODES) > 1:
            candidates = [m for m in self.MODES if m != self.mode and m != "RESET_LOOP"]
            new_mode = random.choice(candidates)

        self.previous_mode = self.mode
        self.mode = new_mode
        self.mode_timer = 0.0
        self.mode_duration = random.uniform(4.0, 8.5)

        if self.mode == "CHAOS_SPILL":
            self.mode_duration = random.uniform(2.3, 4.2)
        elif self.mode == "ARTISTIC_WRAP":
            self.mode_duration = random.uniform(5.5, 9.5)
        elif self.mode == "RESET_LOOP":
            self.mode_duration = 1.0

    def choose_mode(self):
        sim = self.sim
        ph = sim.current_phase

        if sim.completed:
            return "RESET_LOOP"

        weighted = []
        weighted += ["OBSERVE"] * 2
        weighted += ["CLOCK_SPIN"] * 2
        weighted += ["ARTISTIC_WRAP"] * 2
        weighted += ["ORGANIZE"] * 2

        if ph in ("G1", "G2"):
            weighted += ["CAREFUL_GROW"] * 4
        if ph == "S":
            weighted += ["DUPLICATION_GUIDE"] * 6
        if ph == "M":
            weighted += ["MITOSIS_HELPER"] * 7
        if len(sim.free_particles) < 45:
            weighted += ["CHAOS_SPILL"] * 2
        if len(sim.free_particles) > 80:
            weighted += ["ORGANIZE"] * 4

        if self.previous_mode in weighted and len(weighted) > 4:
            weighted = [m for m in weighted if m != self.previous_mode] or weighted

        return random.choice(weighted)

    def reset_detection(self, dt):
        sim = self.sim

        sig = self.signature()
        if sig == self.last_signature:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = 0.0
            self.last_signature = sig

        if abs(sim.cycle_time - self.last_cycle_time) < 0.002 and not sim.paused:
            self.stagnation_timer += dt * 0.35
        self.last_cycle_time = sim.cycle_time

        if sim.completed:
            self.completion_timer += dt
        else:
            self.completion_timer = 0.0

        if self.completion_timer > 4.5 or self.stagnation_timer > 13.0:
            self.switch_mode("RESET_LOOP")

    def reset_round(self):
        self.clear_ai_visuals()
        self.sim.reset(full=True)
        self.completion_timer = 0.0
        self.stagnation_timer = 0.0
        self.last_signature = None
        self.last_cycle_time = self.sim.cycle_time
        self.switch_mode("OBSERVE")

    def clear_ai_visuals(self):
        for p in self.sim.free_particles:
            try:
                p["obj"].visible = False
            except Exception:
                pass
        self.sim.free_particles = []
        for b in self.wrap_beads:
            b.visible = False
            b.opacity = 0.0

    def set_override(self, seconds=2.5):
        self.override_timer = max(self.override_timer, seconds)

    def human_move_helper(self, delta):
        self.helper.pos += delta
        self.set_override(3.0)

    def update_clock_beads(self, dt):
        sim = self.sim
        speed = 0.9 if self.mode != "CLOCK_SPIN" else 2.7
        for i, b in enumerate(self.clock_beads):
            ang = self.round_timer * speed + i * 2 * math.pi / len(self.clock_beads)
            rad = sim.clock_radius + 0.22 + 0.05 * math.sin(self.round_timer * 2.1 + i)
            b.pos = sim.clock_center + vector(math.cos(ang), math.sin(ang), 0.04 * math.sin(ang * 2)) * rad
            b.opacity = 0.28 if not self.enabled or self.paused else 0.58
            b.color = mix_color(sim.phase_colors[sim.current_phase], vector(0.15, 0.88, 1.0), 0.55)

    def move_helper_toward(self, target, dt, stiffness=2.0):
        self.helper.pos += (target - self.helper.pos) * clamp(dt * stiffness)

    def update_wrap_beads(self, dt, active):
        sim = self.sim
        if not active:
            for b in self.wrap_beads:
                b.opacity = max(0.0, b.opacity - dt * 2.5)
                if b.opacity <= 0.02:
                    b.visible = False
            return

        bodies = sim.get_cell_bodies()
        if not bodies:
            return

        center, r = bodies[0]
        turns = 2.4
        for i, b in enumerate(self.wrap_beads):
            f = i / (len(self.wrap_beads) - 1)
            theta = self.round_timer * 1.2 + f * turns * 2 * math.pi
            y = (f - 0.5) * r * 1.55
            band_r = max(0.05, math.sqrt(max(0.0, (r * 1.05) ** 2 - y ** 2)))
            b.pos = center + vector(math.cos(theta) * band_r, y, math.sin(theta) * band_r)
            b.visible = True
            b.opacity = lerp(b.opacity, 0.72, dt * 4)
            b.radius = 0.016 + 0.006 * math.sin(self.round_timer * 4 + i)
            b.color = mix_color(vector(0.20, 0.95, 0.75), sim.phase_colors[sim.current_phase], 0.35)

    def action_observe(self, dt):
        sim = self.sim
        sim.ai_speed = lerp(sim.ai_speed, 1.0, dt * 2)
        ang = self.round_timer * 0.55
        target = vector(
            0.15 + math.cos(ang) * 2.7,
            1.15 + 0.22 * math.sin(ang * 1.7),
            math.sin(ang) * 0.45,
        )
        self.move_helper_toward(target, dt, 1.5)

    def action_clock_spin(self, dt):
        sim = self.sim
        sim.ai_speed = lerp(sim.ai_speed, 1.25, dt * 2.0)
        sim.visual_clock_rotation += dt * 0.08
        ang = self.round_timer * 1.8
        target = sim.clock_center + vector(math.cos(ang), math.sin(ang), 0.12 * math.sin(ang * 2)) * (sim.clock_radius + 0.55)
        self.move_helper_toward(target, dt, 2.4)

        if random.random() < dt * 6:
            direction = safe_norm(self.helper.pos - sim.clock_center)
            sim.spawn_particle(
                pos=self.helper.pos,
                vel=direction * random.uniform(0.1, 0.28),
                col=mix_color(sim.phase_colors[sim.current_phase], vector(1, 1, 1), 0.15),
                radius=random.uniform(0.018, 0.034),
                life=random.uniform(3.2, 5.2),
                behavior="orbit",
            )

    def action_careful_grow(self, dt):
        sim = self.sim
        sim.ai_speed = lerp(sim.ai_speed, 0.92, dt * 2.0)
        bodies = sim.get_cell_bodies()
        if not bodies:
            return
        center, r = bodies[0]
        ang = self.round_timer * 0.95
        target = center + vector(math.cos(ang), 0.7 + 0.16 * math.sin(ang * 2), math.sin(ang)) * (r + 0.62)
        self.move_helper_toward(target, dt, 2.1)

        if random.random() < dt * 7:
            inward = safe_norm(center - self.helper.pos)
            sim.spawn_particle(
                pos=self.helper.pos,
                vel=inward * random.uniform(0.18, 0.38),
                col=vector(0.42, 0.95, 0.70),
                radius=random.uniform(0.014, 0.028),
                life=random.uniform(4.0, 7.0),
                behavior="careful",
            )

    def action_duplication_guide(self, dt):
        sim = self.sim
        if sim.current_phase != "S":
            sim.ai_speed = lerp(sim.ai_speed, 1.35, dt * 1.5)
        else:
            sim.ai_speed = lerp(sim.ai_speed, 0.86, dt * 2.0)

        angle = self.round_timer * 1.25
        target = sim.cell_base + vector(math.cos(angle), 0.25 + 0.35 * math.sin(angle * 1.6), math.sin(angle)) * (sim.current_radius + 0.48)
        self.move_helper_toward(target, dt, 2.5)
        sim.ai_swirl = max(sim.ai_swirl, 0.42)

        if random.random() < dt * 10:
            inward = safe_norm(sim.cell_base - self.helper.pos)
            sim.spawn_particle(
                pos=self.helper.pos,
                vel=inward * random.uniform(0.26, 0.55),
                col=vector(1.0, 0.87, 0.22),
                radius=random.uniform(0.015, 0.026),
                life=random.uniform(2.5, 4.5),
                behavior="mark",
            )

    def action_mitosis_helper(self, dt):
        sim = self.sim
        if sim.current_phase != "M":
            sim.ai_speed = lerp(sim.ai_speed, 1.35, dt * 1.3)
        else:
            sim.ai_speed = lerp(sim.ai_speed, 0.82, dt * 2.2)

        p = sim.current_phase_progress if sim.current_phase == "M" else 0.0
        side = -1 if math.sin(self.round_timer * 1.7) < 0 else 1
        split_distance = lerp(0.3, 1.45, p)
        target = sim.cell_base + vector(side * split_distance, 0.8 + 0.15 * math.sin(self.round_timer * 3), 0.15 * math.cos(self.round_timer))
        self.move_helper_toward(target, dt, 2.2)

        if random.random() < dt * 12:
            col = vector(1.0, 0.42, 0.50)
            direction = vector(side, random.uniform(-0.15, 0.1), random.uniform(-0.18, 0.18))
            sim.spawn_particle(
                pos=sim.cell_base + vector(0, random.uniform(-0.25, 0.35), random.uniform(-0.25, 0.25)),
                vel=safe_norm(direction) * random.uniform(0.24, 0.50),
                col=col,
                radius=random.uniform(0.016, 0.030),
                life=random.uniform(2.8, 5.2),
                behavior="spill",
            )

    def action_chaos_spill(self, dt):
        sim = self.sim
        sim.ai_speed = lerp(sim.ai_speed, 1.55, dt * 2.5)
        sim.ai_swirl = max(sim.ai_swirl, 0.75)

        ang = self.round_timer * 3.1
        target = vector(
            random.uniform(-2.6, 2.7) * 0.7 + math.cos(ang) * 0.8,
            random.uniform(0.35, 1.8),
            random.uniform(-0.75, 0.75),
        )
        self.move_helper_toward(target, dt, 5.0)

        for _ in range(2):
            if random.random() < dt * 16:
                col = random.choice([
                    vector(0.30, 0.82, 1.0),
                    vector(1.0, 0.55, 0.30),
                    vector(0.95, 0.38, 0.82),
                    vector(0.55, 1.0, 0.58),
                    vector(1.0, 0.92, 0.24),
                ])
                sim.spawn_particle(
                    pos=self.helper.pos,
                    vel=rand_vec_in_sphere(random.uniform(0.35, 0.95)) + vector(0, random.uniform(0.0, 0.35), 0),
                    col=col,
                    radius=random.uniform(0.014, 0.034),
                    life=random.uniform(3.0, 6.4),
                    behavior="spill",
                )

    def action_organize(self, dt):
        sim = self.sim
        sim.ai_speed = lerp(sim.ai_speed, 0.75, dt * 2)
        ang = self.round_timer * 1.1
        target = sim.clock_center + vector(math.cos(ang), math.sin(ang), 0) * (sim.clock_radius + 0.65)
        self.move_helper_toward(target, dt, 2.0)

        for p in sim.free_particles:
            if random.random() < dt * 0.8:
                p["behavior"] = "organize"
                a = random.random() * 2 * math.pi
                p["target"] = sim.clock_center + vector(math.cos(a), math.sin(a), 0) * (sim.clock_radius + random.uniform(0.08, 0.26))

        if random.random() < dt * 5:
            sim.spawn_particle(
                pos=self.helper.pos,
                vel=safe_norm(sim.clock_center - self.helper.pos) * random.uniform(0.18, 0.42),
                col=vector(0.35, 0.77, 1.0),
                radius=random.uniform(0.015, 0.027),
                life=random.uniform(4.5, 7.5),
                behavior="organize",
            )

    def action_artistic_wrap(self, dt):
        sim = self.sim
        sim.ai_speed = lerp(sim.ai_speed, 1.02, dt * 2)
        bodies = sim.get_cell_bodies()
        if bodies:
            center, r = bodies[0]
            ang = self.round_timer * 1.55
            target = center + vector(math.cos(ang), 0.15 * math.sin(ang * 2), math.sin(ang)) * (r + 0.7)
            self.move_helper_toward(target, dt, 2.3)

            if random.random() < dt * 5:
                sim.spawn_particle(
                    pos=self.helper.pos,
                    vel=safe_norm(center - self.helper.pos) * random.uniform(0.12, 0.28),
                    col=vector(0.22, 0.95, 0.77),
                    radius=random.uniform(0.012, 0.024),
                    life=random.uniform(4.0, 7.0),
                    behavior="attach",
                )

    def update(self, dt):
        self.round_timer += dt
        self.update_clock_beads(dt)

        self.helper_label.pos = self.helper.pos + vector(0, 0.22, 0)
        self.helper_label.text = "AI" if self.enabled else "AI off"
        self.helper.opacity = 0.78 if self.enabled and not self.paused else 0.25

        if not self.enabled:
            self.sim.ai_speed = lerp(self.sim.ai_speed, 1.0, dt * 3)
            self.mode_label.text = "AI disabled"
            self.update_wrap_beads(dt, False)
            return

        if self.paused:
            self.sim.ai_speed = lerp(self.sim.ai_speed, 1.0, dt * 3)
            self.mode_label.text = f"AI paused | last mode: {self.mode}"
            self.update_wrap_beads(dt, False)
            return

        self.reset_detection(dt)

        if self.override_timer > 0:
            self.override_timer -= dt
            self.sim.ai_speed = lerp(self.sim.ai_speed, 1.0, dt * 2)
            self.mode_label.text = f"Human override | AI mode waiting: {self.mode}"
            self.update_wrap_beads(dt, self.mode == "ARTISTIC_WRAP")
            return

        self.mode_timer += dt
        if self.mode_timer > self.mode_duration:
            self.switch_mode()

        if self.mode != "ARTISTIC_WRAP":
            self.update_wrap_beads(dt, False)

        if self.mode == "OBSERVE":
            self.action_observe(dt)
        elif self.mode == "CLOCK_SPIN":
            self.action_clock_spin(dt)
        elif self.mode == "CAREFUL_GROW":
            self.action_careful_grow(dt)
        elif self.mode == "DUPLICATION_GUIDE":
            self.action_duplication_guide(dt)
        elif self.mode == "MITOSIS_HELPER":
            self.action_mitosis_helper(dt)
        elif self.mode == "CHAOS_SPILL":
            self.action_chaos_spill(dt)
        elif self.mode == "ORGANIZE":
            self.action_organize(dt)
        elif self.mode == "ARTISTIC_WRAP":
            self.action_artistic_wrap(dt)
            self.update_wrap_beads(dt, True)
        elif self.mode == "RESET_LOOP":
            self.mode_label.text = "AI mode: RESET LOOP — starting a new round"
            if self.mode_timer > 0.75:
                self.reset_round()
            return

        self.mode_label.text = (
            f"AI mode: {self.mode} | auto state machine | "
            f"stability {self.stagnation_timer:.1f}s"
        )
        self.mode_label.color = mix_color(self.sim.phase_colors[self.sim.current_phase], vector(0.05, 0.22, 0.30), 0.58)

# ------------------------------
# Instantiate
# ------------------------------

sim = CellCycleSimulation()
ai = AIController(sim)

# ------------------------------
# Keyboard controls
# ------------------------------

def on_keydown(evt):
    k = evt.key.lower()

    if k == " ":
        sim.paused = not sim.paused
    elif k == "r":
        ai.clear_ai_visuals()
        sim.reset(full=True)
        ai.switch_mode("OBSERVE")
    elif k == "b":
        ai.enabled = not ai.enabled
        if not ai.enabled:
            sim.ai_speed = 1.0
    elif k == "z":
        ai.paused = not ai.paused
        if ai.paused:
            sim.ai_speed = 1.0
    elif k in ("+", "="):
        sim.human_speed = clamp(sim.human_speed + 0.15, 0.1, 4.0)
    elif k in ("-", "_"):
        sim.human_speed = clamp(sim.human_speed - 0.15, 0.1, 4.0)
    elif k == "0":
        sim.human_speed = 1.0
    elif k == "n":
        sim.force_next_phase()
        ai.set_override(1.25)
    elif k == "1":
        ai.switch_mode("OBSERVE")
    elif k == "2":
        ai.switch_mode("CLOCK_SPIN")
    elif k == "3":
        ai.switch_mode("CAREFUL_GROW")
    elif k == "4":
        ai.switch_mode("DUPLICATION_GUIDE")
    elif k == "5":
        ai.switch_mode("MITOSIS_HELPER")
    elif k == "6":
        ai.switch_mode("CHAOS_SPILL")
    elif k == "7":
        ai.switch_mode("ORGANIZE")
    elif k == "8":
        ai.switch_mode("ARTISTIC_WRAP")

scene.bind("keydown", on_keydown)

def handle_held_keys(dt):
    keys = keysdown()
    move = vector(0, 0, 0)
    speed = 1.8 * dt

    if "i" in keys:
        move.y += speed
    if "k" in keys:
        move.y -= speed
    if "j" in keys:
        move.x -= speed
    if "l" in keys:
        move.x += speed
    if "u" in keys:
        move.z += speed
    if "o" in keys:
        move.z -= speed

    if mag(move) > 0:
        ai.human_move_helper(move)

# ------------------------------
# Main loop
# ------------------------------

dt = 1 / 60

while True:
    rate(60)

    handle_held_keys(dt)

    advance_cycle = not sim.paused
    advance_particles = not sim.paused or (ai.enabled and not ai.paused)

    ai.update(dt)
    sim.update(dt, advance_cycle=advance_cycle, advance_particles=advance_particles)
