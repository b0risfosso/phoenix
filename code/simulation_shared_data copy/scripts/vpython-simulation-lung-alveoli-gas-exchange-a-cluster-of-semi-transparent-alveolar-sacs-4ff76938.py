from vpython import *
import random
import math
import csv
import os
from datetime import datetime
import time

CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
_csv_output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
_csv_run_id = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

try:
    _script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _script_dir = os.getcwd()

if _csv_output_dir:
    CSV_OUTPUT_PATH = os.path.join(_csv_output_dir, f"{_csv_run_id}-simulation-state.csv")
else:
    CSV_OUTPUT_PATH = os.environ.get(
        "SIM_STATE_CSV_PATH",
        os.path.join(_script_dir, f"{_csv_run_id}-simulation-state.csv")
    )

CSV_ENV_REQUESTED = bool(
    os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
    or os.environ.get("SIM_STATE_CSV_PATH")
    or os.environ.get("SIMULATION_CSV_RUN_SECONDS")
)

os.makedirs(os.path.dirname(os.path.abspath(CSV_OUTPUT_PATH)), exist_ok=True)

scene.title = "AI-Controlled 3D Lung Alveoli Gas Exchange"
scene.width = 1250
scene.height = 760
scene.background = vector(0.94, 0.98, 1.0)
scene.forward = vector(-0.4, -0.25, -1)
scene.center = vector(0, 0.15, 0)
scene.range = 6.3
scene.ambient = color.gray(0.82)

O2_COLOR = vector(1.0, 0.16, 0.08)
O2_GLOW = vector(1.0, 0.48, 0.22)
CO2_COLOR = vector(0.05, 0.28, 1.0)
CO2_GLOW = vector(0.25, 0.65, 1.0)
MEMBRANE_COLOR = vector(1.0, 0.70, 0.74)
AIRSPACE_COLOR = vector(1.0, 0.88, 0.86)
DEOXY_COLOR = vector(0.10, 0.20, 0.85)
MID_BLOOD_COLOR = vector(0.66, 0.22, 0.70)
OXY_COLOR = vector(1.0, 0.07, 0.04)
CAPILLARY_GLASS = vector(0.92, 0.32, 0.38)
HEMO_COLOR = vector(0.72, 0.02, 0.03)
MARK_COLOR = vector(1.0, 0.82, 0.15)
PROBE_COLOR = vector(0.35, 0.98, 0.75)

random.seed()

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def lerp(a, b, t):
    t = clamp(t)
    return a * (1 - t) + b * t

def sat_color(s):
    s = clamp(s)
    if s < 0.5:
        return lerp(DEOXY_COLOR, MID_BLOOD_COLOR, s * 2)
    return lerp(MID_BLOOD_COLOR, OXY_COLOR, (s - 0.5) * 2)

def random_unit():
    v = vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
    if mag(v) < 1e-6:
        return vector(1, 0, 0)
    return norm(v)

def random_in_sphere(radius):
    return random_unit() * radius * (random.random() ** (1.0 / 3.0))

def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-8:
        return fallback
    return norm(v)

def rotate_about_axis(v, axis_vec, angle):
    axis_vec = safe_norm(axis_vec)
    return v * math.cos(angle) + cross(axis_vec, v) * math.sin(angle) + axis_vec * dot(axis_vec, v) * (1 - math.cos(angle))

class Alveolus:
    def __init__(self, idx, center, base_radius):
        self.idx = idx
        self.center = center
        self.base_radius = base_radius
        self.radius = base_radius
        self.local_squeeze = 0.0
        self.transfer_boost = 1.0
        self.marked = False
        self.sac = sphere(
            pos=center,
            radius=base_radius,
            color=AIRSPACE_COLOR,
            opacity=0.23,
            shininess=0.45
        )
        self.membrane = sphere(
            pos=center,
            radius=base_radius * 1.025,
            color=MEMBRANE_COLOR,
            opacity=0.12,
            shininess=0.8
        )
        self.inner_haze = sphere(
            pos=center,
            radius=base_radius * 0.72,
            color=vector(1.0, 0.94, 0.90),
            opacity=0.055,
            shininess=0.1
        )
        self.label = label(
            pos=center + vector(0, base_radius + 0.36, 0),
            text=f"Alveolus {idx + 1}",
            height=11,
            box=False,
            opacity=0,
            color=vector(0.25, 0.25, 0.28)
        )

    def set_radius(self, r):
        self.radius = r
        self.sac.radius = r
        self.membrane.radius = r * 1.025
        self.inner_haze.radius = r * 0.72
        self.label.pos = self.center + vector(0, r + 0.36, 0)

class CapillaryPath:
    def __init__(self, idx, alveolus):
        self.idx = idx
        self.alveolus = alveolus
        self.points = []
        self.segments = []
        self.lengths = []
        self.total_length = 0.0
        self.saturation = random.uniform(0.28, 0.43)
        self.local_transfer_flash = 0.0
        c = alveolus.center
        r = alveolus.base_radius * 1.24
        start = c + vector(-1.9, -1.15, -0.15)
        self.points.append(start)
        for i in range(15):
            theta = math.pi - i * math.pi / 14.0
            front_wave = 0.42 * math.sin(i * 0.73 + idx)
            p = c + vector(r * math.cos(theta), 0.08 + 0.95 * math.sin(theta), 0.72 + front_wave)
            self.points.append(p)
        end = c + vector(1.9, -1.08, -0.12)
        self.points.append(end)

        self.lengths = [0.0]
        for i in range(len(self.points) - 1):
            a = self.points[i]
            b = self.points[i + 1]
            seg_axis = b - a
            seg_len = mag(seg_axis)
            self.total_length += seg_len
            self.lengths.append(self.total_length)
            seg_obj = cylinder(
                pos=a,
                axis=seg_axis,
                radius=0.075,
                color=sat_color(self.saturation),
                opacity=0.62,
                shininess=0.35
            )
            self.segments.append(seg_obj)

    def point_at(self, u):
        u = u % 1.0
        d = u * self.total_length
        for i in range(len(self.points) - 1):
            if self.lengths[i] <= d <= self.lengths[i + 1]:
                seg_len = self.lengths[i + 1] - self.lengths[i]
                t = 0 if seg_len <= 1e-8 else (d - self.lengths[i]) / seg_len
                return self.points[i] * (1 - t) + self.points[i + 1] * t
        return self.points[-1]

    def tangent_at(self, u):
        p1 = self.point_at(u)
        p2 = self.point_at(u + 0.006)
        return safe_norm(p2 - p1, vector(1, 0, 0))

    def nearest_u(self, pos):
        best_u = 0.0
        best_d2 = 1e9
        for i in range(len(self.points) - 1):
            a = self.points[i]
            b = self.points[i + 1]
            ab = b - a
            ab2 = mag2(ab)
            if ab2 <= 1e-8:
                continue
            t = clamp(dot(pos - a, ab) / ab2)
            q = a + ab * t
            d2 = mag2(pos - q)
            if d2 < best_d2:
                seg_start = self.lengths[i]
                seg_len = self.lengths[i + 1] - self.lengths[i]
                best_u = (seg_start + seg_len * t) / self.total_length
                best_d2 = d2
        return best_u, math.sqrt(best_d2)

    def update_visual(self):
        self.saturation = clamp(self.saturation)
        for i, seg_obj in enumerate(self.segments):
            gradient = i / max(1, len(self.segments) - 1)
            flash = self.local_transfer_flash
            local_s = clamp(self.saturation * 0.78 + gradient * 0.20 + flash * 0.10)
            seg_obj.color = sat_color(local_s)
            seg_obj.radius = 0.075 + 0.012 * flash
        self.local_transfer_flash *= 0.86

class Carrier:
    def __init__(self, idx, path_idx, u):
        self.idx = idx
        self.path_idx = path_idx
        self.u = u
        self.phase = random.random() * 2 * math.pi
        self.saturation = random.uniform(0.18, 0.42)
        self.just_wrapped = False
        self.obj = sphere(
            pos=vector(0, 0, 0),
            radius=0.118,
            color=sat_color(self.saturation),
            opacity=0.86,
            shininess=0.45,
            make_trail=True,
            retain=14,
            trail_radius=0.012
        )

    def update(self, dt):
        global blood_flow_speed
        old_u = self.u
        self.u = (self.u + dt * blood_flow_speed * (0.045 + 0.012 * math.sin(self.phase))) % 1.0
        self.just_wrapped = self.u < old_u
        if self.just_wrapped:
            self.saturation *= 0.58
        path_obj = capillary_paths[self.path_idx]
        centerline = path_obj.point_at(self.u)
        tangent = path_obj.tangent_at(self.u)
        n1 = safe_norm(cross(tangent, vector(0, 1, 0)), vector(0, 0, 1))
        n2 = safe_norm(cross(tangent, n1), vector(0, 1, 0))
        wobble = n1 * (0.035 * math.sin(sim_time * 5.5 + self.phase)) + n2 * (0.022 * math.cos(sim_time * 4.7 + self.phase))
        self.obj.pos = centerline + wobble
        self.obj.color = sat_color(self.saturation)
        self.obj.trail_color = self.obj.color

class GasParticle:
    def __init__(self, species, state, alveolus_idx=None, path_idx=None, u=None, pos=None, carrier_idx=None):
        self.species = species
        self.state = state
        self.alveolus_idx = alveolus_idx
        self.path_idx = path_idx
        self.u = random.random() if u is None else u
        self.phase = random.random() * 2 * math.pi
        self.vel = random_unit() * random.uniform(0.12, 0.45)
        self.carrier_idx = carrier_idx
        self.attached = carrier_idx is not None
        self.age = 0.0
        self.marked = False
        col = O2_COLOR if species == "O2" else CO2_COLOR
        rad = 0.045 if species == "O2" else 0.052
        if pos is None:
            if state == "air":
                a = alveoli[alveolus_idx]
                pos = a.center + random_in_sphere(a.radius * 0.72)
            else:
                pos = capillary_paths[path_idx].point_at(self.u)
        self.obj = sphere(
            pos=pos,
            radius=rad,
            color=col,
            opacity=0.92,
            shininess=0.62,
            make_trail=True,
            retain=18,
            trail_radius=0.009
        )
        self.obj.trail_color = lerp(col, vector(1, 1, 1), 0.35)

    def set_species(self, species):
        self.species = species
        self.obj.color = O2_COLOR if species == "O2" else CO2_COLOR
        self.obj.radius = 0.045 if species == "O2" else 0.052
        self.obj.trail_color = lerp(self.obj.color, vector(1, 1, 1), 0.35)

    def attach_to_carrier(self, carrier_idx):
        self.attached = True
        self.carrier_idx = carrier_idx
        self.state = "blood"
        self.path_idx = carriers[carrier_idx].path_idx
        self.u = carriers[carrier_idx].u
        self.alveolus_idx = None

    def detach_to_air(self, alveolus_idx, pos):
        self.attached = False
        self.carrier_idx = None
        self.state = "air"
        self.alveolus_idx = alveolus_idx
        self.path_idx = None
        self.obj.pos = pos
        self.vel = safe_norm(alveoli[alveolus_idx].center - pos, random_unit()) * random.uniform(0.25, 0.55) + random_unit() * 0.10

    def update_visual_from_carrier(self):
        carrier = carriers[self.carrier_idx]
        self.u = carrier.u
        tangent = capillary_paths[carrier.path_idx].tangent_at(carrier.u)
        n1 = safe_norm(cross(tangent, vector(0, 1, 0)), vector(0, 0, 1))
        n2 = safe_norm(cross(tangent, n1), vector(0, 1, 0))
        orbit = n1 * (0.15 * math.cos(sim_time * 8 + self.phase)) + n2 * (0.15 * math.sin(sim_time * 8 + self.phase))
        self.obj.pos = carrier.obj.pos + orbit

alveolus_centers = [
    vector(-1.65, 0.35, 0.05),
    vector(0.0, 0.68, -0.18),
    vector(1.58, 0.26, 0.12),
    vector(-0.83, -0.98, 0.25),
    vector(0.90, -1.05, -0.03)
]

alveoli = []
for i, c in enumerate(alveolus_centers):
    alveoli.append(Alveolus(i, c, random.uniform(0.82, 1.02)))

airway_stem = cylinder(
    pos=vector(0, 2.9, -0.95),
    axis=vector(0, -1.65, 0.58),
    radius=0.18,
    color=vector(0.78, 0.92, 0.98),
    opacity=0.40,
    shininess=0.8
)
airway_left = cylinder(
    pos=vector(-0.05, 1.42, -0.42),
    axis=vector(-1.35, -0.65, 0.35),
    radius=0.115,
    color=vector(0.78, 0.92, 0.98),
    opacity=0.38
)
airway_right = cylinder(
    pos=vector(0.05, 1.42, -0.42),
    axis=vector(1.38, -0.70, 0.42),
    radius=0.115,
    color=vector(0.78, 0.92, 0.98),
    opacity=0.38
)
airway_lower = cylinder(
    pos=vector(0.0, 1.30, -0.46),
    axis=vector(0.0, -1.75, 0.62),
    radius=0.105,
    color=vector(0.78, 0.92, 0.98),
    opacity=0.36
)

main_inlet = cylinder(
    pos=vector(-4.6, -2.28, -0.28),
    axis=vector(9.2, 0.0, 0.0),
    radius=0.12,
    color=DEOXY_COLOR,
    opacity=0.54,
    shininess=0.45
)
main_outlet_glow = cylinder(
    pos=vector(-4.6, -2.28, -0.28),
    axis=vector(9.2, 0.0, 0.0),
    radius=0.065,
    color=OXY_COLOR,
    opacity=0.14
)

capillary_paths = []
for i, a in enumerate(alveoli):
    path_obj = CapillaryPath(i, a)
    capillary_paths.append(path_obj)
    branch_start = vector(-3.95 + i * 1.95, -2.28, -0.28)
    branch_end = path_obj.points[0]
    cylinder(
        pos=branch_start,
        axis=branch_end - branch_start,
        radius=0.055,
        color=DEOXY_COLOR,
        opacity=0.46
    )
    return_start = path_obj.points[-1]
    return_end = vector(-2.95 + i * 1.95, -2.28, -0.28)
    cylinder(
        pos=return_start,
        axis=return_end - return_start,
        radius=0.055,
        color=OXY_COLOR,
        opacity=0.42
    )

carriers = []
for path_idx in range(len(capillary_paths)):
    for k in range(7):
        carriers.append(Carrier(len(carriers), path_idx, (k / 7.0 + random.random() * 0.06) % 1.0))

particles = []
MAX_PARTICLES = 245

transfer_o2_to_blood = 0
transfer_co2_to_air = 0
collision_count = 0
attach_count = 0
detach_count = 0
spill_count = 0
mark_count = 0
reset_count = 0
tissue_exchange_count = 0
exhaled_count = 0

sim_time = 0.0
frame = 0
paused = False
human_override_until = 0.0
breathing_phase = 0.0
breathing_rate = 0.82
breathing_amplitude = 0.105
blood_flow_speed = 1.0
membrane_permeability = 1.0
ai_stir = vector(0, 0, 0)

def spawn_particle(species, state, alveolus_idx=None, path_idx=None, u=None, pos=None, carrier_idx=None):
    if len(particles) >= MAX_PARTICLES:
        for p in particles:
            if p.state == "air" and p.species == "CO2" and p.age > 8:
                p.obj.visible = False
                particles.remove(p)
                break
        if len(particles) >= MAX_PARTICLES:
            return None
    p = GasParticle(species, state, alveolus_idx, path_idx, u, pos, carrier_idx)
    particles.append(p)
    return p

def initialize_particles():
    for p in particles:
        p.obj.visible = False
        p.obj.clear_trail()
    particles[:] = []
    for a in alveoli:
        for _ in range(16):
            spawn_particle("O2", "air", alveolus_idx=a.idx)
        for _ in range(5):
            spawn_particle("CO2", "air", alveolus_idx=a.idx)
    for path_idx in range(len(capillary_paths)):
        for _ in range(10):
            spawn_particle("CO2", "blood", path_idx=path_idx, u=random.random())
        for _ in range(2):
            carrier_options = [c.idx for c in carriers if c.path_idx == path_idx]
            ci = random.choice(carrier_options)
            p = spawn_particle("O2", "blood", path_idx=path_idx, carrier_idx=ci)
            if p:
                p.attach_to_carrier(ci)

initialize_particles()

selected_alveolus = 0
selection_loop = ring(
    pos=alveoli[selected_alveolus].center,
    axis=vector(0, 1, 0),
    radius=alveoli[selected_alveolus].radius * 1.22,
    thickness=0.025,
    color=MARK_COLOR,
    opacity=0.72
)
probe = sphere(
    pos=vector(-3.2, 1.8, 1.2),
    radius=0.145,
    color=PROBE_COLOR,
    emissive=True,
    make_trail=True,
    retain=45,
    trail_radius=0.018
)
probe_light = local_light(pos=probe.pos, color=PROBE_COLOR * 0.55)
probe_arrow = arrow(
    pos=probe.pos,
    axis=vector(0.4, 0, 0),
    shaftwidth=0.035,
    color=PROBE_COLOR,
    opacity=0.72
)

status = label(
    pos=vector(0, 3.55, 0),
    text="AI: careful_breath | Space pause | A AI | M mode | R reset | O/C spill gases",
    height=13,
    box=True,
    border=8,
    opacity=0.16,
    color=vector(0.10, 0.12, 0.15),
    background=vector(1, 1, 1)
)

gradient_bar_segments = []
for i in range(24):
    s = i / 23.0
    gradient_bar_segments.append(
        box(
            pos=vector(-3.65 + i * 0.095, 3.12, 0),
            size=vector(0.088, 0.14, 0.035),
            color=sat_color(s),
            opacity=0.86
        )
    )
label(pos=vector(-3.62, 3.35, 0), text="low O₂ blood", height=10, box=False, opacity=0, color=DEOXY_COLOR)
label(pos=vector(-1.45, 3.35, 0), text="high O₂ saturation", height=10, box=False, opacity=0, color=OXY_COLOR)
label(pos=vector(2.15, 3.25, 0), text="O₂ red/orange  → blood    CO₂ blue → air", height=12, box=False, opacity=0, color=vector(0.18, 0.18, 0.22))

AI_BEHAVIOR_MODES = [
    "careful_breath",
    "curious_probe",
    "constructive_oxygenation",
    "chaotic_cough",
    "artistic_spiral",
    "destructive_hypoxia",
    "ritual_reset"
]

class AIController:
    def __init__(self):
        self.enabled = True
        self.mode = "careful_breath"
        self.mode_index = 0
        self.mode_elapsed = 0.0
        self.mode_duration = 9.0
        self.action_timer = 0.0
        self.target_alveolus = 0
        self.orbit_angle = 0.0
        self.stagnation_timer = 0.0
        self.last_avg_sat = 0.0
        self.last_transfer_total = 0
        self.round = 1
        self.completion_timer = 0.0
        self.override = False
        self.ritual_pulse = 0.0

    def set_mode(self, mode):
        if mode in AI_BEHAVIOR_MODES:
            self.mode = mode
            self.mode_index = AI_BEHAVIOR_MODES.index(mode)
            self.mode_elapsed = 0.0
            self.action_timer = 0.0
            self.mode_duration = random.uniform(6.5, 14.0)

    def next_mode(self):
        self.mode_index = (self.mode_index + 1) % len(AI_BEHAVIOR_MODES)
        self.set_mode(AI_BEHAVIOR_MODES[self.mode_index])

    def read_state(self):
        avg_sat = sum(c.saturation for c in carriers) / max(1, len(carriers))
        path_sats = [p.saturation for p in capillary_paths]
        low_idx = min(range(len(path_sats)), key=lambda i: path_sats[i])
        high_idx = max(range(len(path_sats)), key=lambda i: path_sats[i])
        air_o2 = sum(1 for p in particles if p.state == "air" and p.species == "O2")
        air_co2 = sum(1 for p in particles if p.state == "air" and p.species == "CO2")
        blood_co2 = sum(1 for p in particles if p.state == "blood" and p.species == "CO2")
        total_transfer = transfer_o2_to_blood + transfer_co2_to_air
        return {
            "avg_sat": avg_sat,
            "path_sats": path_sats,
            "low_idx": low_idx,
            "high_idx": high_idx,
            "air_o2": air_o2,
            "air_co2": air_co2,
            "blood_co2": blood_co2,
            "total_transfer": total_transfer
        }

    def detect_stagnation_or_completion(self, dt, state):
        transfer_change = state["total_transfer"] - self.last_transfer_total
        sat_change = abs(state["avg_sat"] - self.last_avg_sat)
        if transfer_change < 1 and sat_change < 0.0018:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0.0, self.stagnation_timer - dt * 2.0)
        if state["avg_sat"] > 0.82 and state["blood_co2"] < 10:
            self.completion_timer += dt
        else:
            self.completion_timer = max(0.0, self.completion_timer - dt)
        self.last_transfer_total = state["total_transfer"]
        self.last_avg_sat = state["avg_sat"]
        return self.stagnation_timer > 10.0 or self.completion_timer > 7.0 or len(particles) < 45

    def update_probe_orbit(self, dt, alveolus_idx, height=0.15, radius_scale=1.62, speed=1.0):
        self.orbit_angle += dt * speed
        a = alveoli[alveolus_idx]
        radius = a.radius * radius_scale
        desired = a.center + vector(math.cos(self.orbit_angle) * radius, height + 0.38 * math.sin(self.orbit_angle * 1.7), math.sin(self.orbit_angle) * radius)
        probe.pos = probe.pos * 0.90 + desired * 0.10
        probe_light.pos = probe.pos
        direction = safe_norm(a.center - probe.pos, vector(1, 0, 0))
        probe_arrow.pos = probe.pos
        probe_arrow.axis = direction * 0.42

    def mark_target(self, alveolus_idx, color_vec=MARK_COLOR):
        global selected_alveolus, mark_count
        selected_alveolus = alveolus_idx
        a = alveoli[selected_alveolus]
        selection_loop.pos = a.center
        selection_loop.radius = a.radius * 1.24
        selection_loop.color = color_vec
        selection_loop.axis = rotate_about_axis(vector(0, 1, 0), vector(1, 0, 0), 0.35 * math.sin(sim_time * 2.0))
        selection_loop.opacity = 0.75 + 0.18 * math.sin(sim_time * 6)
        if not a.marked:
            a.marked = True
            mark_count += 1

    def choose_mode(self, state):
        if self.stagnation_timer > 7.5 or self.completion_timer > 5.0:
            self.set_mode("ritual_reset")
            return
        if state["avg_sat"] < 0.34:
            self.set_mode("constructive_oxygenation")
            return
        if state["air_co2"] > state["air_o2"] * 0.85:
            self.set_mode("chaotic_cough")
            return
        self.next_mode()

    def act(self, dt):
        global breathing_rate, breathing_amplitude, blood_flow_speed, membrane_permeability, ai_stir, spill_count
        if not self.enabled or sim_time < human_override_until:
            ai_stir = ai_stir * 0.88
            return

        state = self.read_state()
        halted = self.detect_stagnation_or_completion(dt, state)
        self.mode_elapsed += dt
        self.action_timer += dt

        if halted and self.mode != "ritual_reset":
            self.set_mode("ritual_reset")

        if self.mode_elapsed > self.mode_duration:
            self.choose_mode(state)

        low_idx = state["low_idx"]
        self.target_alveolus = low_idx if self.mode in ("careful_breath", "curious_probe", "constructive_oxygenation") else (self.target_alveolus + (1 if self.action_timer > 2.6 else 0)) % len(alveoli)
        target = self.target_alveolus

        if self.mode == "careful_breath":
            breathing_rate = breathing_rate * 0.985 + 0.72 * 0.015
            breathing_amplitude = breathing_amplitude * 0.985 + 0.105 * 0.015
            blood_flow_speed = blood_flow_speed * 0.985 + 1.0 * 0.015
            membrane_permeability = membrane_permeability * 0.985 + 1.15 * 0.015
            self.mark_target(low_idx, vector(1.0, 0.82, 0.20))
            self.update_probe_orbit(dt, low_idx, speed=0.92)
            ai_stir = ai_stir * 0.9 + random_unit() * 0.004

        elif self.mode == "curious_probe":
            breathing_rate = breathing_rate * 0.97 + 0.94 * 0.03
            blood_flow_speed = blood_flow_speed * 0.97 + 0.92 * 0.03
            membrane_permeability = membrane_permeability * 0.96 + 1.75 * 0.04
            self.mark_target(low_idx, vector(0.38, 1.0, 0.76))
            self.update_probe_orbit(dt, low_idx, height=-0.1, radius_scale=1.18, speed=1.8)
            alveoli[low_idx].transfer_boost = 2.15
            ai_stir = (alveoli[low_idx].center - probe.pos) * 0.012

        elif self.mode == "constructive_oxygenation":
            breathing_rate = breathing_rate * 0.96 + 1.08 * 0.04
            breathing_amplitude = breathing_amplitude * 0.96 + 0.16 * 0.04
            blood_flow_speed = blood_flow_speed * 0.96 + 1.22 * 0.04
            membrane_permeability = membrane_permeability * 0.96 + 1.65 * 0.04
            self.mark_target(low_idx, vector(0.95, 1.0, 0.30))
            self.update_probe_orbit(dt, low_idx, speed=1.35)
            if self.action_timer > 0.42:
                self.action_timer = 0.0
                for _ in range(3):
                    a = alveoli[low_idx]
                    pos = a.center + random_in_sphere(a.radius * 0.48)
                    p = spawn_particle("O2", "air", alveolus_idx=low_idx, pos=pos)
                    if p:
                        p.vel = random_unit() * 0.38
                        spill_count += 1
            ai_stir = ai_stir * 0.72 + random_unit() * 0.018

        elif self.mode == "chaotic_cough":
            breathing_rate = breathing_rate * 0.93 + 1.85 * 0.07
            breathing_amplitude = breathing_amplitude * 0.93 + 0.22 * 0.07
            blood_flow_speed = blood_flow_speed * 0.95 + 1.35 * 0.05
            membrane_permeability = membrane_permeability * 0.98 + 1.05 * 0.02
            self.mark_target(random.randrange(len(alveoli)), vector(1.0, 0.48, 0.18))
            self.update_probe_orbit(dt, selected_alveolus, height=0.3, radius_scale=2.0, speed=3.2)
            ai_stir = random_unit() * 0.16
            if self.action_timer > 1.1:
                self.action_timer = 0.0
                path_idx = random.randrange(len(capillary_paths))
                for _ in range(4):
                    p = spawn_particle("CO2", "blood", path_idx=path_idx, u=random.random())
                    if p:
                        p.vel = random_unit() * 0.3
                        spill_count += 1

        elif self.mode == "artistic_spiral":
            breathing_rate = breathing_rate * 0.96 + (0.62 + 0.22 * math.sin(sim_time)) * 0.04
            breathing_amplitude = breathing_amplitude * 0.96 + 0.13 * 0.04
            blood_flow_speed = blood_flow_speed * 0.97 + (0.85 + 0.22 * math.sin(sim_time * 0.7)) * 0.03
            membrane_permeability = membrane_permeability * 0.97 + 1.28 * 0.03
            target = int((sim_time * 0.45) % len(alveoli))
            self.mark_target(target, vector(0.82, 0.44, 1.0))
            self.update_probe_orbit(dt, target, height=0.55 * math.sin(sim_time * 1.3), radius_scale=1.85, speed=1.45)
            selection_loop.axis = safe_norm(vector(math.sin(sim_time), 1.0, math.cos(sim_time * 0.8)), vector(0, 1, 0))
            if self.action_timer > 0.68:
                self.action_timer = 0.0
                a = alveoli[target]
                species = "O2" if random.random() < 0.65 else "CO2"
                p = spawn_particle(species, "air", alveolus_idx=target, pos=a.center + random_in_sphere(a.radius * 0.35))
                if p:
                    p.vel = rotate_about_axis(random_unit(), vector(0, 1, 0), sim_time) * 0.55
                    spill_count += 1
            ai_stir = vector(math.sin(sim_time * 2.1), math.cos(sim_time * 1.7), math.sin(sim_time * 0.9)) * 0.028

        elif self.mode == "destructive_hypoxia":
            breathing_rate = breathing_rate * 0.96 + 0.42 * 0.04
            breathing_amplitude = breathing_amplitude * 0.96 + 0.055 * 0.04
            blood_flow_speed = blood_flow_speed * 0.96 + 0.58 * 0.04
            membrane_permeability = membrane_permeability * 0.96 + 0.58 * 0.04
            target = state["high_idx"]
            self.mark_target(target, vector(0.28, 0.38, 1.0))
            self.update_probe_orbit(dt, target, height=-0.25, radius_scale=1.35, speed=1.05)
            if self.action_timer > 0.82:
                self.action_timer = 0.0
                a = alveoli[target]
                for _ in range(2):
                    p = spawn_particle("CO2", "air", alveolus_idx=target, pos=a.center + random_in_sphere(a.radius * 0.58))
                    if p:
                        p.vel = random_unit() * 0.33
                        spill_count += 1
            ai_stir = ai_stir * 0.86 - safe_norm(probe.pos - alveoli[target].center) * 0.012

        elif self.mode == "ritual_reset":
            breathing_rate = breathing_rate * 0.94 + 1.22 * 0.06
            breathing_amplitude = breathing_amplitude * 0.93 + 0.24 * 0.07
            blood_flow_speed = blood_flow_speed * 0.96 + 1.45 * 0.04
            membrane_permeability = membrane_permeability * 0.95 + 1.95 * 0.05
            self.ritual_pulse += dt * 5.0
            target = int((self.ritual_pulse / 1.2) % len(alveoli))
            self.mark_target(target, vector(1.0, 0.95, 0.48))
            self.update_probe_orbit(dt, target, height=0.2, radius_scale=2.35, speed=2.4)
            for a in alveoli:
                a.local_squeeze = 0.05 * math.sin(self.ritual_pulse + a.idx * 1.25)
            ai_stir = random_unit() * 0.04
            if self.mode_elapsed > 5.2:
                reset_simulation(new_round=True)
                self.set_mode("careful_breath")

ai = AIController()

def reset_simulation(new_round=False):
    global transfer_o2_to_blood, transfer_co2_to_air, collision_count, attach_count, detach_count
    global spill_count, mark_count, reset_count, tissue_exchange_count, exhaled_count
    global breathing_phase, blood_flow_speed, membrane_permeability, breathing_rate, breathing_amplitude
    transfer_o2_to_blood = 0
    transfer_co2_to_air = 0
    collision_count = 0
    attach_count = 0
    detach_count = 0
    spill_count = 0
    mark_count = 0
    tissue_exchange_count = 0
    exhaled_count = 0
    reset_count += 1
    breathing_phase = 0.0
    blood_flow_speed = 1.0
    membrane_permeability = 1.0
    breathing_rate = 0.82
    breathing_amplitude = 0.105
    for a in alveoli:
        a.local_squeeze = 0.0
        a.transfer_boost = 1.0
        a.marked = False
    for path_obj in capillary_paths:
        path_obj.saturation = random.uniform(0.26, 0.42)
        path_obj.local_transfer_flash = 0.0
    for c in carriers:
        c.u = random.random()
        c.saturation = random.uniform(0.16, 0.42)
        c.obj.clear_trail()
    initialize_particles()
    ai.stagnation_timer = 0.0
    ai.completion_timer = 0.0
    ai.last_transfer_total = 0
    ai.last_avg_sat = 0.0
    if new_round:
        ai.round += 1

def keydown(evt):
    global paused, human_override_until, blood_flow_speed, breathing_rate, breathing_amplitude
    global membrane_permeability, selected_alveolus, spill_count
    k = evt.key
    human_override_until = sim_time + 5.0
    if k == " ":
        paused = not paused
    elif k in ("a", "A"):
        ai.enabled = not ai.enabled
    elif k in ("m", "M"):
        ai.next_mode()
        human_override_until = 0.0
    elif k in ("r", "R"):
        reset_simulation(new_round=True)
    elif k in ("o", "O"):
        a = alveoli[selected_alveolus]
        for _ in range(8):
            p = spawn_particle("O2", "air", alveolus_idx=selected_alveolus, pos=a.center + random_in_sphere(a.radius * 0.55))
            if p:
                p.vel = random_unit() * 0.45
                spill_count += 1
    elif k in ("c", "C"):
        path_idx = selected_alveolus
        for _ in range(8):
            p = spawn_particle("CO2", "blood", path_idx=path_idx, u=random.random())
            if p:
                spill_count += 1
    elif k == "up":
        blood_flow_speed = clamp(blood_flow_speed + 0.12, 0.25, 2.3)
    elif k == "down":
        blood_flow_speed = clamp(blood_flow_speed - 0.12, 0.25, 2.3)
    elif k == "right":
        breathing_rate = clamp(breathing_rate + 0.08, 0.25, 2.5)
    elif k == "left":
        breathing_rate = clamp(breathing_rate - 0.08, 0.25, 2.5)
    elif k in ("[", "{"):
        selected_alveolus = (selected_alveolus - 1) % len(alveoli)
    elif k in ("]", "}"):
        selected_alveolus = (selected_alveolus + 1) % len(alveoli)
    elif k in ("p", "P"):
        membrane_permeability = clamp(membrane_permeability + 0.2, 0.2, 2.6)
    elif k in ("l", "L"):
        membrane_permeability = clamp(membrane_permeability - 0.2, 0.2, 2.6)
    elif k.isdigit():
        n = int(k)
        if 1 <= n <= len(AI_BEHAVIOR_MODES):
            ai.set_mode(AI_BEHAVIOR_MODES[n - 1])
            human_override_until = 0.0

scene.bind("keydown", keydown)

def update_breathing(dt):
    global breathing_phase
    breathing_phase += dt * breathing_rate * 2 * math.pi
    breath = math.sin(breathing_phase)
    exhale_strength = clamp(-math.cos(breathing_phase))
    for a in alveoli:
        a.transfer_boost = a.transfer_boost * 0.92 + 1.0 * 0.08
        r = a.base_radius * (1.0 + breathing_amplitude * breath + a.local_squeeze)
        r = max(a.base_radius * 0.72, r)
        a.set_radius(r)
        a.local_squeeze *= 0.88
    return breath, exhale_strength

def update_selection_visual():
    a = alveoli[selected_alveolus]
    selection_loop.pos = a.center
    selection_loop.radius = a.radius * (1.24 + 0.035 * math.sin(sim_time * 4.0))
    selection_loop.axis = safe_norm(selection_loop.axis, vector(0, 1, 0))

def find_nearest_carrier(path_idx, u):
    best = None
    best_d = 999
    for c in carriers:
        if c.path_idx != path_idx:
            continue
        du = abs(c.u - u)
        du = min(du, 1.0 - du)
        if du < best_d:
            best_d = du
            best = c
    return best

def transfer_air_o2_to_blood(p, a, path_obj, local_boost):
    global transfer_o2_to_blood, attach_count
    u, dist_to_tube = path_obj.nearest_u(p.obj.pos)
    membrane_dist = abs(mag(p.obj.pos - a.center) - a.radius)
    chance = 0.040 * membrane_permeability * a.transfer_boost * local_boost
    if membrane_dist < 0.27 and dist_to_tube < 0.55 and random.random() < chance:
        carrier = find_nearest_carrier(path_obj.idx, u)
        if carrier:
            p.attach_to_carrier(carrier.idx)
            carrier.saturation = clamp(carrier.saturation + 0.12)
            path_obj.saturation = clamp(path_obj.saturation + 0.035)
            path_obj.local_transfer_flash = 1.0
            transfer_o2_to_blood += 1
            attach_count += 1

def transfer_blood_co2_to_air(p, path_obj):
    global transfer_co2_to_air, detach_count
    a = alveoli[path_obj.alveolus.idx]
    tube_pos = path_obj.point_at(p.u)
    dist_membrane = abs(mag(tube_pos - a.center) - a.radius)
    chance = 0.032 * membrane_permeability * a.transfer_boost
    if dist_membrane < 0.38 and random.random() < chance:
        n = safe_norm(tube_pos - a.center, random_unit())
        air_pos = a.center + n * (a.radius * 0.91)
        p.detach_to_air(a.idx, air_pos)
        p.set_species("CO2")
        path_obj.saturation = clamp(path_obj.saturation + 0.009)
        path_obj.local_transfer_flash = 0.78
        transfer_co2_to_air += 1
        detach_count += 1

def update_particles(dt, breath, exhale_strength):
    global collision_count, tissue_exchange_count, exhaled_count
    local_probe_alveolus = selected_alveolus
    for i, a in enumerate(alveoli):
        if mag(probe.pos - a.center) < a.radius * 1.45:
            local_probe_alveolus = i
            break

    for p in list(particles):
        p.age += dt
        if p.attached:
            if p.carrier_idx is None or p.carrier_idx >= len(carriers):
                p.attached = False
            else:
                c = carriers[p.carrier_idx]
                p.update_visual_from_carrier()
                if c.just_wrapped and p.species == "O2" and random.random() < 0.38:
                    p.attached = False
                    p.carrier_idx = None
                    p.path_idx = c.path_idx
                    p.u = 0.02 + random.random() * 0.04
                    p.set_species("CO2")
                    p.state = "blood"
                    tissue_exchange_count += 1
                continue

        if p.state == "air":
            if p.alveolus_idx is None:
                p.alveolus_idx = random.randrange(len(alveoli))
            a = alveoli[p.alveolus_idx]
            radial = p.obj.pos - a.center
            rmag = mag(radial)
            n = safe_norm(radial, random_unit())
            brownian = random_unit() * (0.38 if p.species == "O2" else 0.32)
            breathing_flow = n * (0.20 * math.cos(breathing_phase))
            p.vel += (brownian + breathing_flow + ai_stir) * dt
            p.vel *= 0.986
            p.obj.pos += p.vel * dt

            radial = p.obj.pos - a.center
            rmag = mag(radial)
            if rmag > a.radius * 0.95:
                n = safe_norm(radial, random_unit())
                p.obj.pos = a.center + n * a.radius * 0.95
                p.vel = p.vel - 2 * dot(p.vel, n) * n
                p.vel *= 0.72
                collision_count += 1

            if p.species == "O2":
                boost = 2.0 if p.alveolus_idx == local_probe_alveolus and ai.mode == "curious_probe" else 1.0
                transfer_air_o2_to_blood(p, a, capillary_paths[p.alveolus_idx], boost)
            elif p.species == "CO2":
                airway_vector = safe_norm(vector(0, 2.5, -0.9) - a.center)
                if exhale_strength > 0.55:
                    p.vel += airway_vector * exhale_strength * dt * 0.45
                if exhale_strength > 0.72 and dot(p.obj.pos - a.center, airway_vector) > a.radius * 0.52 and random.random() < 0.012:
                    p.set_species("O2")
                    p.obj.pos = a.center - airway_vector * a.radius * 0.35 + random_in_sphere(a.radius * 0.22)
                    p.vel = random_unit() * 0.25
                    exhaled_count += 1

        elif p.state == "blood":
            if p.path_idx is None:
                p.path_idx = random.randrange(len(capillary_paths))
            path_obj = capillary_paths[p.path_idx]
            p.u = (p.u + dt * blood_flow_speed * random.uniform(0.040, 0.066)) % 1.0
            tangent = path_obj.tangent_at(p.u)
            centerline = path_obj.point_at(p.u)
            n1 = safe_norm(cross(tangent, vector(0, 1, 0)), vector(0, 0, 1))
            n2 = safe_norm(cross(tangent, n1), vector(0, 1, 0))
            p.phase += dt * 4.6
            offset = n1 * (0.115 * math.cos(p.phase)) + n2 * (0.07 * math.sin(p.phase * 1.4))
            p.obj.pos = centerline + offset
            if p.species == "CO2":
                transfer_blood_co2_to_air(p, path_obj)
            elif p.species == "O2":
                carrier = find_nearest_carrier(p.path_idx, p.u)
                if carrier and random.random() < 0.012:
                    p.attach_to_carrier(carrier.idx)

def update_carriers_and_capillaries(dt):
    for c in carriers:
        c.update(dt)
    for path_obj in capillary_paths:
        carriers_on_path = [c.saturation for c in carriers if c.path_idx == path_obj.idx]
        if carriers_on_path:
            target_sat = sum(carriers_on_path) / len(carriers_on_path)
            path_obj.saturation = path_obj.saturation * 0.982 + target_sat * 0.018
        path_obj.saturation = clamp(path_obj.saturation - 0.00035 * dt)
        path_obj.update_visual()
    avg_sat = sum(p.saturation for p in capillary_paths) / max(1, len(capillary_paths))
    main_inlet.color = sat_color(avg_sat * 0.55)
    main_outlet_glow.color = sat_color(clamp(avg_sat + 0.24))
    main_outlet_glow.opacity = 0.12 + 0.24 * avg_sat

csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
csv_writer = csv.writer(csv_file)
csv_writer.writerow([
    "run_id",
    "frame",
    "elapsed_seconds",
    "ai_enabled",
    "ai_mode",
    "ai_round",
    "paused",
    "selected_alveolus",
    "probe_x",
    "probe_y",
    "probe_z",
    "probe_vx",
    "probe_vy",
    "probe_vz",
    "breathing_phase",
    "breathing_rate",
    "breathing_amplitude",
    "blood_flow_speed",
    "membrane_permeability",
    "avg_capillary_saturation",
    "avg_carrier_saturation",
    "air_o2_count",
    "air_co2_count",
    "blood_o2_count",
    "blood_co2_count",
    "o2_to_blood_transfers",
    "co2_to_air_transfers",
    "attach_count",
    "detach_count",
    "collision_count",
    "spill_count",
    "mark_count",
    "reset_count",
    "tissue_exchange_count",
    "exhaled_count",
    "stagnation_timer",
    "completion_timer",
    "alveolus_1_radius",
    "alveolus_2_radius",
    "alveolus_3_radius",
    "alveolus_4_radius",
    "alveolus_5_radius",
    "path_1_saturation",
    "path_2_saturation",
    "path_3_saturation",
    "path_4_saturation",
    "path_5_saturation"
])
csv_file.flush()

csv_active = True
csv_closed_label_shown = False
csv_last_log = 0.0
csv_last_flush = 0.0
start_wall = time.time()
last_wall = start_wall
last_probe_pos = vector(probe.pos.x, probe.pos.y, probe.pos.z)

try:
    while True:
        rate(60)
        now = time.time()
        dt = clamp(now - last_wall, 0.001, 0.05)
        last_wall = now

        if not paused:
            sim_time += dt
            frame += 1
            breath, exhale_strength = update_breathing(dt)
            ai.act(dt)
            update_carriers_and_capillaries(dt)
            update_particles(dt, breath, exhale_strength)
            for a in alveoli:
                a.transfer_boost = a.transfer_boost * 0.94 + 1.0 * 0.06
            update_selection_visual()

        avg_path_sat = sum(p.saturation for p in capillary_paths) / max(1, len(capillary_paths))
        avg_carrier_sat = sum(c.saturation for c in carriers) / max(1, len(carriers))
        air_o2_count = sum(1 for p in particles if p.state == "air" and p.species == "O2")
        air_co2_count = sum(1 for p in particles if p.state == "air" and p.species == "CO2")
        blood_o2_count = sum(1 for p in particles if p.state == "blood" and p.species == "O2")
        blood_co2_count = sum(1 for p in particles if p.state == "blood" and p.species == "CO2")

        ai_text = "ON" if ai.enabled else "OFF"
        override_text = " | human override" if sim_time < human_override_until else ""
        pause_text = "PAUSED | " if paused else ""
        status.text = (
            f"{pause_text}AI {ai_text}: {ai.mode}{override_text} | round {ai.round} | "
            f"O₂ sat {avg_carrier_sat:.2f} | O₂→blood {transfer_o2_to_blood} | CO₂→air {transfer_co2_to_air} | "
            f"flow {blood_flow_speed:.2f} | permeability {membrane_permeability:.2f}"
        )

        probe_velocity = (probe.pos - last_probe_pos) / max(dt, 1e-6)
        last_probe_pos = vector(probe.pos.x, probe.pos.y, probe.pos.z)

        elapsed_wall = now - start_wall
        if csv_active and elapsed_wall - csv_last_log >= 0.25:
            csv_last_log = elapsed_wall
            row = [
                _csv_run_id,
                frame,
                round(elapsed_wall, 4),
                int(ai.enabled),
                ai.mode,
                ai.round,
                int(paused),
                selected_alveolus,
                round(probe.pos.x, 5),
                round(probe.pos.y, 5),
                round(probe.pos.z, 5),
                round(probe_velocity.x, 5),
                round(probe_velocity.y, 5),
                round(probe_velocity.z, 5),
                round(breathing_phase, 5),
                round(breathing_rate, 5),
                round(breathing_amplitude, 5),
                round(blood_flow_speed, 5),
                round(membrane_permeability, 5),
                round(avg_path_sat, 5),
                round(avg_carrier_sat, 5),
                air_o2_count,
                air_co2_count,
                blood_o2_count,
                blood_co2_count,
                transfer_o2_to_blood,
                transfer_co2_to_air,
                attach_count,
                detach_count,
                collision_count,
                spill_count,
                mark_count,
                reset_count,
                tissue_exchange_count,
                exhaled_count,
                round(ai.stagnation_timer, 5),
                round(ai.completion_timer, 5)
            ]
            row.extend([round(a.radius, 5) for a in alveoli])
            row.extend([round(p.saturation, 5) for p in capillary_paths])
            csv_writer.writerow(row)

        if csv_active and elapsed_wall - csv_last_flush >= 2.0:
            csv_last_flush = elapsed_wall
            csv_file.flush()

        if csv_active and elapsed_wall >= CSV_RUN_SECONDS:
            csv_file.flush()
            csv_file.close()
            csv_active = False
            if not csv_closed_label_shown:
                label(
                    pos=vector(2.35, -3.28, 0),
                    text="CSV recording complete: saved run data",
                    height=11,
                    box=True,
                    border=6,
                    opacity=0.16,
                    color=vector(0.12, 0.18, 0.14),
                    background=vector(0.94, 1.0, 0.94)
                )
                csv_closed_label_shown = True
            if CSV_ENV_REQUESTED:
                break

except KeyboardInterrupt:
    pass
finally:
    if csv_active:
        csv_file.flush()
        csv_file.close()
