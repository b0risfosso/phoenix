from vpython import *
import random
import math
import csv
import os
import json
from datetime import datetime

# Lysosome Fusion and Cargo Degradation
# Full standalone VPython simulation with CSV logging support.
# Controls:
#   SPACE pause/resume
#   I/A   toggle AI
#   R     reset round
#   TAB   select next cargo vesicle
#   W/S/A/D or arrow keys move selected cargo
#   Q/E   move selected cargo down/up
#   O     attach/detach selected cargo to orbit around nearest lysosome
#   X     spill selected cargo
#   F     force-fuse selected cargo with nearest lysosome
#   M     mark/recolor selected cargo
#   C     switch AI mode
#   P     pause/resume AI only

scene.title = "Lysosome Fusion and Cargo Degradation - VPython CSV Logger"
scene.background = vector(0.94, 0.97, 1.0)
scene.width = 1200
scene.height = 760
scene.forward = vector(-0.7, -0.45, -0.7)
scene.up = vector(0, 1, 0)
scene.userspin = True
scene.userzoom = True
scene.caption = (
    "\nLysosome fusion/degradation simulation. CSV logging is integrated into the visible VPython run.\n"
    "Controls: SPACE pause | I/A AI | R reset | TAB select | WASD/arrows/QE move | "
    "O orbit | X spill | F fuse | M mark | C mode | P pause AI\n\n"
)

ENABLE_TRAILS = False
DT = 1.0 / 60.0

# ------------------------------------------------------------
# CSV logging configuration
# ------------------------------------------------------------

def _env_float(name, default):
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return float(default)

CSV_RUN_SECONDS = max(0.0, _env_float("SIMULATION_CSV_RUN_SECONDS", 60.0))
CSV_SAMPLE_HZ = max(0.05, _env_float("SIMULATION_CSV_SAMPLE_HZ", 10.0))
CSV_SAMPLE_INTERVAL = 1.0 / CSV_SAMPLE_HZ
CSV_OUTPUT_DIR = os.environ.get("SIMULATION_CSV_OUTPUT_DIR", "").strip()
CSV_RUN_ID = os.environ.get("SIMULATION_CSV_RUN_ID", "").strip() or datetime.now().strftime("%Y%m%d_%H%M%S")

if CSV_OUTPUT_DIR:
    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
    CSV_OUTPUT_PATH = os.path.join(CSV_OUTPUT_DIR, f"{CSV_RUN_ID}-lysosome-fusion-state-log.csv")
else:
    fallback = os.environ.get("SIM_STATE_CSV_PATH", "").strip()
    if fallback:
        CSV_OUTPUT_PATH = fallback
        parent = os.path.dirname(os.path.abspath(CSV_OUTPUT_PATH))
        if parent:
            os.makedirs(parent, exist_ok=True)
    else:
        CSV_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lysosome_fusion_state_log.csv")

CSV_METADATA_PATH = os.path.splitext(CSV_OUTPUT_PATH)[0] + ".metadata.json"

CSV_FIELDNAMES = [
    "csv_run_id", "csv_elapsed_seconds", "simulation_time", "frame", "row_type", "object_id", "object_kind",
    "round_number", "paused", "last_reset_reason", "ai_enabled", "ai_paused", "ai_mode", "ai_previous_mode",
    "ai_mode_time", "ai_stagnation_time", "ai_completion_time", "manual_override_remaining", "selected_index", "selected_cargo",
    "lysosome_count", "cargo_count", "active_cargo_count", "fused_cargo_count", "spilled_cargo_count",
    "particle_count", "in_cargo_particle_count", "free_particle_count", "degrading_particle_count", "dead_particle_count",
    "effect_count", "dynamic_visual_count", "digest_total", "avg_cargo_speed", "nearest_fusion_gap",
    "name", "state", "kind", "target_name", "lysosome_name", "x", "y", "z", "vx", "vy", "vz",
    "radius", "base_radius", "age", "life", "ttl", "opacity", "cargo_active", "cargo_fused", "cargo_spilled",
    "cargo_marked", "cargo_ai_attached", "cargo_particle_count", "cargo_alive_particle_count", "orbit_phase", "spin", "hue",
    "lysosome_digest_count", "lysosome_glow_timer", "particle_state", "particle_dead", "particle_radius0",
]

_csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
_csv_writer = csv.DictWriter(_csv_file, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
_csv_writer.writeheader()
_csv_file.flush()


def write_csv_metadata():
    metadata = {
        "csv_run_id": CSV_RUN_ID,
        "csv_output_path": CSV_OUTPUT_PATH,
        "csv_metadata_path": CSV_METADATA_PATH,
        "simulation_name": "Lysosome Fusion and Cargo Degradation",
        "script_type": "full_vpython_csv_logger",
        "run_seconds": CSV_RUN_SECONDS,
        "sample_hz": CSV_SAMPLE_HZ,
        "sample_interval": CSV_SAMPLE_INTERVAL,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "row_types": ["summary", "lysosome", "cargo", "particle", "effect"],
        "environment_variables": {
            "SIMULATION_CSV_OUTPUT_DIR": CSV_OUTPUT_DIR,
            "SIMULATION_CSV_RUN_ID": CSV_RUN_ID,
            "SIMULATION_CSV_RUN_SECONDS": CSV_RUN_SECONDS,
            "SIMULATION_CSV_SAMPLE_HZ": CSV_SAMPLE_HZ,
            "SIM_STATE_CSV_PATH": os.environ.get("SIM_STATE_CSV_PATH", ""),
        },
    }
    with open(CSV_METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

write_csv_metadata()

# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def randf(a, b):
    return random.uniform(a, b)


def random_unit():
    while True:
        v = vector(randf(-1, 1), randf(-1, 1), randf(-1, 1))
        if mag(v) > 0.0001:
            return norm(v)


def random_inside_sphere(radius):
    return random_unit() * (radius * (random.random() ** (1.0 / 3.0)))


def clamp_mag(v, max_m):
    m = mag(v)
    if m > max_m and m > 0:
        return norm(v) * max_m
    return v


def mix_color(a, b, t):
    t = max(0, min(1, t))
    return a * (1 - t) + b * t


def hsv(h, s, v):
    return color.hsv_to_rgb(vector(h % 1.0, s, v))


def vdict(v, prefix=""):
    return {f"{prefix}x": float(v.x), f"{prefix}y": float(v.y), f"{prefix}z": float(v.z)}


def hide_obj(obj):
    try:
        if hasattr(obj, "clear_trail"):
            obj.clear_trail()
    except Exception:
        pass
    try:
        obj.visible = False
    except Exception:
        pass


def bounce_in_box(pos, vel, radius, bounds, damping=0.83):
    p = vector(pos.x, pos.y, pos.z)
    v = vector(vel.x, vel.y, vel.z)
    if p.x > bounds - radius:
        p.x = bounds - radius
        v.x = -abs(v.x) * damping
    elif p.x < -bounds + radius:
        p.x = -bounds + radius
        v.x = abs(v.x) * damping
    if p.y > bounds - radius:
        p.y = bounds - radius
        v.y = -abs(v.y) * damping
    elif p.y < -bounds + radius:
        p.y = -bounds + radius
        v.y = abs(v.y) * damping
    if p.z > bounds - radius:
        p.z = bounds - radius
        v.z = -abs(v.z) * damping
    elif p.z < -bounds + radius:
        p.z = -bounds + radius
        v.z = abs(v.z) * damping
    return p, v

# ------------------------------------------------------------
# Scene classes
# ------------------------------------------------------------

class TransientEffect:
    def __init__(self, sim, visual, ttl=1.0, expand=0.0, fade=True):
        self.sim = sim
        self.visual = visual
        self.ttl = ttl
        self.life = ttl
        self.expand = expand
        self.fade = fade
        self.start_opacity = getattr(visual, "opacity", 1.0)
        self.start_radius = getattr(visual, "radius", 1.0)
        sim.dynamic_visuals.append(visual)

    def update(self, dt):
        self.life -= dt
        t = max(0, self.life / max(0.001, self.ttl))
        if self.fade and hasattr(self.visual, "opacity"):
            self.visual.opacity = self.start_opacity * t
        if self.expand and hasattr(self.visual, "radius"):
            self.visual.radius = self.start_radius + self.expand * (1 - t)
        if self.life <= 0:
            hide_obj(self.visual)
            return False
        return True


class Lysosome:
    def __init__(self, sim, pos, radius, name, hue):
        self.sim = sim
        self.pos = vector(pos)
        self.radius = radius
        self.name = name
        self.hue = hue
        self.base_color = hsv(hue, 0.62, 0.95)
        self.acid_color = hsv(hue + 0.06, 0.82, 1.0)
        self.glow_timer = 0.0
        self.digest_count = 0
        self.halo = sphere(pos=self.pos, radius=radius * 1.45, color=self.acid_color, opacity=0.07, shininess=0, emissive=True)
        self.shell = sphere(pos=self.pos, radius=radius, color=self.base_color, opacity=0.28, shininess=0.45)
        self.core = sphere(pos=self.pos, radius=radius * 0.62, color=mix_color(self.base_color, color.white, 0.25), opacity=0.15, emissive=True, shininess=0)
        self.label = label(pos=self.pos + vector(0, radius + 0.75, 0), text=name + "\nacidic lysosome", height=10, color=vector(0.22, 0.16, 0.30), box=False, opacity=0)
        sim.dynamic_visuals += [self.halo, self.shell, self.core, self.label]

    def brighten(self, amount=1.0):
        self.glow_timer = max(self.glow_timer, 1.25 * amount)
        self.digest_count += 1

    def ingest_particle(self, particle):
        particle.start_degrading(self)
        self.brighten(1.0)

    def update(self, dt):
        self.glow_timer = max(0, self.glow_timer - dt)
        glow = min(1, self.glow_timer / 1.25)
        self.halo.radius = self.radius * (1.45 + 0.38 * glow)
        self.halo.opacity = 0.055 + 0.22 * glow
        self.halo.color = mix_color(self.base_color, color.white, glow * 0.58)
        self.shell.opacity = 0.25 + 0.17 * glow
        self.shell.color = mix_color(self.base_color, color.white, glow * 0.43)
        self.core.opacity = 0.13 + 0.24 * glow
        self.core.color = mix_color(self.acid_color, color.white, glow * 0.68)
        self.label.text = f"{self.name}\nacidic lysosome\ncargo degraded: {self.digest_count}"


class CargoParticle:
    def __init__(self, sim, cargo, local_pos, radius, col):
        self.sim = sim
        self.cargo = cargo
        self.local_pos = vector(local_pos)
        self.local_vel = random_unit() * randf(0.12, 0.42)
        self.pos = cargo.pos + self.local_pos
        self.vel = vector(0, 0, 0)
        self.radius0 = radius
        self.radius = radius
        self.color0 = col
        self.state = "in_cargo"
        self.lysosome = None
        self.dead = False
        self.age = 0.0
        self.visual = sphere(pos=self.pos, radius=self.radius, color=col, opacity=0.95, shininess=0.5, emissive=True)
        sim.dynamic_visuals.append(self.visual)

    def update_inside_cargo(self, dt):
        if not self.cargo or not self.cargo.active:
            return
        self.age += dt
        self.local_vel += random_unit() * randf(0.02, 0.08)
        self.local_vel += cross(vector(0, 1, 0), self.local_pos) * self.cargo.spin * dt * 0.7
        self.local_vel *= 0.965
        self.local_pos += self.local_vel * dt
        limit = self.cargo.radius * 0.66
        if mag(self.local_pos) > limit:
            n = norm(self.local_pos)
            self.local_pos = n * limit
            self.local_vel -= 2 * dot(self.local_vel, n) * n
            self.local_vel *= 0.75
        self.pos = self.cargo.pos + self.local_pos
        self.visual.pos = self.pos
        self.visual.radius = max(0.025, self.radius * (1 + 0.08 * math.sin(self.age * 4.5 + self.radius0 * 30)))

    def become_free(self, inherited_vel):
        self.state = "free"
        self.cargo = None
        self.vel = inherited_vel + random_unit() * randf(0.55, 1.55)
        self.visual.opacity = 0.9
        if ENABLE_TRAILS:
            self.visual.make_trail = True
            self.visual.retain = 24
            self.visual.trail_color = self.visual.color

    def start_degrading(self, lysosome):
        self.state = "degrading"
        self.cargo = None
        self.lysosome = lysosome
        if mag(self.pos - lysosome.pos) > lysosome.radius * 0.83:
            direction = self.pos - lysosome.pos
            if mag(direction) < 0.001:
                direction = random_unit()
            self.pos = lysosome.pos + norm(direction) * lysosome.radius * randf(0.35, 0.78)
        self.vel = random_unit() * randf(0.35, 1.2) + cross(vector(0, 1, 0), self.pos - lysosome.pos) * 0.28
        self.visual.pos = self.pos
        self.visual.opacity = 0.95
        self.visual.emissive = True

    def update_free(self, dt):
        self.age += dt
        self.vel += random_unit() * 0.18 * dt
        self.vel *= 0.992
        self.pos += self.vel * dt
        self.pos, self.vel = bounce_in_box(self.pos, self.vel, self.radius, self.sim.bounds, damping=0.86)
        self.visual.pos = self.pos
        self.visual.radius = self.radius * (1 + 0.08 * math.sin(self.age * 8))
        for lys in self.sim.lysosomes:
            if mag(self.pos - lys.pos) < lys.radius * 0.92:
                lys.ingest_particle(self)
                break

    def update_degrading(self, dt):
        if not self.lysosome:
            return
        self.age += dt
        rvec = self.pos - self.lysosome.pos
        if mag(rvec) < 0.001:
            rvec = random_unit() * 0.01
        tangent = cross(vector(0, 1, 0), rvec)
        if mag(tangent) < 0.001:
            tangent = cross(vector(1, 0, 0), rvec)
        tangent = norm(tangent)
        inward = -norm(rvec) * 0.20
        swirl = tangent * (0.92 / max(0.3, mag(rvec)))
        jitter = random_unit() * 0.12
        self.vel += (inward + swirl + jitter) * dt
        self.vel *= 0.982
        self.pos += self.vel * dt
        inner = self.lysosome.radius * 0.78
        if mag(self.pos - self.lysosome.pos) > inner:
            n = norm(self.pos - self.lysosome.pos)
            self.pos = self.lysosome.pos + n * inner
            self.vel -= 2 * dot(self.vel, n) * n
            self.vel *= 0.72
        acid_speed = 0.022 + 0.018 * (self.lysosome.glow_timer > 0)
        self.radius -= acid_speed * dt
        self.visual.radius = max(0.004, self.radius)
        self.visual.opacity = max(0, min(0.95, self.radius / self.radius0))
        self.visual.color = mix_color(self.color0, self.lysosome.acid_color, 0.45 + 0.35 * math.sin(self.age * 3) ** 2)
        self.visual.pos = self.pos
        if self.radius <= self.radius0 * 0.08:
            self.dead = True
            hide_obj(self.visual)

    def update(self, dt):
        if self.dead:
            return
        if self.state == "in_cargo":
            return
        if self.state == "free":
            self.update_free(dt)
        elif self.state == "degrading":
            self.update_degrading(dt)


class CargoVesicle:
    def __init__(self, sim, pos, radius, hue, name):
        self.sim = sim
        self.name = name
        self.pos = vector(pos)
        self.vel = random_unit() * randf(0.35, 0.95)
        self.radius = radius
        self.hue = hue
        self.base_color = hsv(hue, 0.72, 1.0)
        self.active = True
        self.fused = False
        self.spilled = False
        self.marked = False
        self.ai_attached = False
        self.orbit_target = None
        self.orbit_phase = randf(0, 2 * math.pi)
        self.orbit_axis = random_unit()
        self.spin = randf(-0.6, 0.6)
        self.age = 0.0
        self.shell = sphere(pos=self.pos, radius=radius, color=self.base_color, opacity=0.23, shininess=0.65, make_trail=ENABLE_TRAILS, retain=45, trail_color=mix_color(self.base_color, color.white, 0.3))
        self.mem = sphere(pos=self.pos, radius=radius * 1.04, color=mix_color(self.base_color, color.white, 0.32), opacity=0.075, shininess=0.2)
        self.label = label(pos=self.pos + vector(0, radius + 0.34, 0), text=name, height=8, color=vector(0.16, 0.22, 0.28), box=False, opacity=0)
        sim.dynamic_visuals += [self.shell, self.mem, self.label]
        self.particles = []
        for _ in range(random.randint(6, 10)):
            ph = (hue + randf(-0.15, 0.22)) % 1.0
            col = hsv(ph, randf(0.55, 0.95), randf(0.85, 1.0))
            p = CargoParticle(sim, self, random_inside_sphere(radius * 0.55), randf(0.055, 0.095), col)
            self.particles.append(p)
            sim.particles.append(p)

    def alive_particles(self):
        return [p for p in self.particles if not p.dead]

    def apply_force(self, force, dt):
        if self.active:
            self.vel += force * dt

    def mark(self):
        self.marked = True
        self.base_color = hsv(randf(0, 1), 0.85, 1.0)
        self.shell.color = self.base_color
        self.mem.color = mix_color(self.base_color, color.white, 0.5)
        for p in self.particles:
            if p.state == "in_cargo":
                p.color0 = hsv(randf(0, 1), 0.9, 1.0)
                p.visual.color = p.color0

    def attach_orbit(self, lysosome):
        self.ai_attached = True
        self.orbit_target = lysosome
        self.orbit_phase = randf(0, 2 * math.pi)
        self.orbit_axis = random_unit()

    def detach_orbit(self):
        self.ai_attached = False
        self.orbit_target = None
        self.vel += random_unit() * 0.7

    def spill(self):
        if not self.active:
            return
        self.active = False
        self.spilled = True
        self.shell.opacity = 0.03
        self.mem.opacity = 0.02
        self.label.visible = False
        burst = sphere(pos=self.pos, radius=self.radius * 0.75, color=mix_color(self.base_color, color.white, 0.55), opacity=0.22, emissive=True)
        self.sim.effects.append(TransientEffect(self.sim, burst, ttl=0.85, expand=self.radius * 1.45, fade=True))
        for p in self.particles:
            if not p.dead and p.state == "in_cargo":
                p.become_free(self.vel)

    def fuse_with(self, lysosome):
        if not self.active:
            return
        self.active = False
        self.fused = True
        self.ai_attached = False
        direction = self.pos - lysosome.pos
        if mag(direction) < 0.001:
            direction = random_unit()
        n = norm(direction)
        contact = lysosome.pos + n * lysosome.radius * 0.94
        hide_obj(self.shell)
        hide_obj(self.mem)
        hide_obj(self.label)
        fusion_ring = ring(pos=contact, axis=n, radius=self.radius * 0.78, thickness=0.035, color=mix_color(self.base_color, color.white, 0.35), opacity=0.58, emissive=True)
        wrap = sphere(pos=contact, radius=self.radius * 0.45, color=self.base_color, opacity=0.18, emissive=True)
        self.sim.effects.append(TransientEffect(self.sim, fusion_ring, ttl=1.25, expand=0.22, fade=True))
        self.sim.effects.append(TransientEffect(self.sim, wrap, ttl=1.05, expand=0.65, fade=True))
        lysosome.brighten(1.35)
        for p in self.particles:
            if not p.dead and p.state == "in_cargo":
                offset = p.local_pos
                p.pos = contact * 0.52 + (lysosome.pos + offset) * 0.48
                p.start_degrading(lysosome)

    def update(self, dt):
        if not self.active:
            return
        self.age += dt
        self.spin += randf(-0.35, 0.35) * dt
        self.spin = max(-2.5, min(2.5, self.spin))
        self.vel += random_unit() * randf(0.06, 0.16) * dt
        self.vel *= 0.992
        self.vel = clamp_mag(self.vel, 3.2)
        self.pos += self.vel * dt
        self.pos, self.vel = bounce_in_box(self.pos, self.vel, self.radius, self.sim.bounds, damping=0.82)
        pulse = 1 + 0.025 * math.sin(self.age * 3.3 + self.hue * 10)
        self.shell.pos = self.pos
        self.mem.pos = self.pos
        self.shell.radius = self.radius * pulse
        self.mem.radius = self.radius * (1.04 + 0.02 * math.sin(self.age * 2.7))
        self.label.pos = self.pos + vector(0, self.radius + 0.34, 0)
        if self.marked:
            self.mem.opacity = 0.11 + 0.05 * math.sin(self.age * 5) ** 2
        for p in self.particles:
            if p.state == "in_cargo" and not p.dead:
                p.update_inside_cargo(dt)
        for lys in self.sim.lysosomes:
            if mag(self.pos - lys.pos) < lys.radius + self.radius * 0.78:
                self.fuse_with(lys)
                break


class AIController:
    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.paused = False
        self.modes = ["EXPLORE", "HERD_TO_ACID", "CAREFUL_ONE_BY_ONE", "ORBIT_RITUAL", "DIP_AND_PULL", "SPILL_AND_MIX", "MARK_AND_SORT", "CHAOTIC_STIR", "ARTISTIC_SPIRAL"]
        self.mode = "EXPLORE"
        self.previous_mode = None
        self.mode_time = 0.0
        self.next_switch = randf(5.5, 10.0)
        self.last_signature = None
        self.stagnation_time = 0.0
        self.completion_time = 0.0
        self.loop_delay = 3.0
        self.action_cooldown = 0.0
        self.rounds_started_by_ai = 0

    def active_cargos(self):
        return [c for c in self.sim.cargos if c.active]

    def free_particles(self):
        return [p for p in self.sim.particles if (not p.dead and p.state == "free")]

    def degrading_particles(self):
        return [p for p in self.sim.particles if (not p.dead and p.state == "degrading")]

    def nearest_lysosome(self, pos):
        return min(self.sim.lysosomes, key=lambda l: mag(l.pos - pos)) if self.sim.lysosomes else None

    def simulation_signature(self):
        active = len(self.active_cargos())
        free = len(self.free_particles())
        degrading = len(self.degrading_particles())
        in_cargo = len([p for p in self.sim.particles if (not p.dead and p.state == "in_cargo")])
        dead = len([p for p in self.sim.particles if p.dead])
        digestion = sum(l.digest_count for l in self.sim.lysosomes)
        return (active, free, degrading, in_cargo, dead, digestion)

    def state_summary(self):
        active = self.active_cargos()
        free = self.free_particles()
        degrading = self.degrading_particles()
        avg_speed = sum(mag(c.vel) for c in active) / max(1, len(active))
        distances = []
        for c in active:
            lys = self.nearest_lysosome(c.pos)
            if lys:
                distances.append(max(0, mag(c.pos - lys.pos) - lys.radius - c.radius))
        return {
            "active_cargos": len(active),
            "free_particles": len(free),
            "degrading_particles": len(degrading),
            "avg_cargo_speed": avg_speed,
            "nearest_fusion_gap": min(distances) if distances else None,
            "total_alive_particles": len([p for p in self.sim.particles if not p.dead]),
        }

    def choose_new_mode(self, reason="time"):
        summary = self.state_summary()
        choices = list(self.modes)
        if summary["active_cargos"] <= 0:
            choices = ["CHAOTIC_STIR", "ARTISTIC_SPIRAL", "EXPLORE"]
        elif summary["active_cargos"] <= 2:
            choices = ["CAREFUL_ONE_BY_ONE", "HERD_TO_ACID", "DIP_AND_PULL", "MARK_AND_SORT"]
        elif summary["free_particles"] > 8:
            choices = ["HERD_TO_ACID", "CHAOTIC_STIR", "ARTISTIC_SPIRAL"]
        elif self.stagnation_time > 5:
            choices = ["CHAOTIC_STIR", "SPILL_AND_MIX", "HERD_TO_ACID"]
        elif reason == "play":
            choices = ["ORBIT_RITUAL", "MARK_AND_SORT", "ARTISTIC_SPIRAL", "DIP_AND_PULL"]
        if self.mode in choices and len(choices) > 1:
            choices.remove(self.mode)
        self.previous_mode = self.mode
        self.mode = random.choice(choices)
        self.mode_time = 0.0
        self.next_switch = randf(5.5, 12.0)
        self.action_cooldown = 0.0
        if self.previous_mode in ["ORBIT_RITUAL", "ARTISTIC_SPIRAL"] and self.mode not in ["ORBIT_RITUAL", "ARTISTIC_SPIRAL"]:
            for c in self.active_cargos():
                if random.random() < 0.55:
                    c.detach_orbit()

    def steer_cargo_to(self, cargo, target, dt, strength=1.8, max_speed=2.2):
        desired = target - cargo.pos
        if mag(desired) < 0.001:
            return
        desired_v = norm(desired) * max_speed
        cargo.apply_force((desired_v - cargo.vel) * strength, dt)

    def steer_particle_to(self, particle, target, dt, strength=1.2, max_speed=1.6):
        desired = target - particle.pos
        if mag(desired) < 0.001:
            return
        particle.vel += (norm(desired) * max_speed - particle.vel) * strength * dt

    def execute_explore(self, dt):
        for c in self.active_cargos():
            c.apply_force(random_unit() * 0.55, dt)
            if random.random() < 0.004:
                c.detach_orbit()

    def execute_herd(self, dt):
        for c in self.active_cargos():
            lys = self.nearest_lysosome(c.pos)
            if lys:
                away = c.pos - lys.pos
                if mag(away) < 0.001:
                    away = random_unit()
                self.steer_cargo_to(c, lys.pos + norm(away) * (lys.radius * 0.12), dt, strength=2.4, max_speed=2.8)
        for p in self.free_particles():
            lys = self.nearest_lysosome(p.pos)
            if lys:
                self.steer_particle_to(p, lys.pos, dt, strength=1.4, max_speed=1.9)

    def execute_careful(self, dt):
        active = self.active_cargos()
        if not active:
            return
        target = min(active, key=lambda c: mag(c.pos - self.nearest_lysosome(c.pos).pos))
        lys = self.nearest_lysosome(target.pos)
        self.steer_cargo_to(target, lys.pos, dt, strength=1.6, max_speed=1.55)
        for c in active:
            if c is not target:
                c.vel *= 0.982

    def execute_orbit(self, dt):
        active = self.active_cargos()
        for i, c in enumerate(active):
            lys = self.sim.lysosomes[i % len(self.sim.lysosomes)]
            if not c.ai_attached or c.orbit_target is not lys:
                c.attach_orbit(lys)
            c.orbit_phase += dt * (0.55 + 0.08 * i)
            radius = lys.radius + c.radius + 1.25 + 0.22 * (i % 3)
            target = lys.pos + vector(math.cos(c.orbit_phase) * radius, 0.45 * math.sin(c.orbit_phase * 1.7 + i), math.sin(c.orbit_phase) * radius)
            self.steer_cargo_to(c, target, dt, strength=2.7, max_speed=2.25)

    def execute_dip_and_pull(self, dt):
        for i, c in enumerate(self.active_cargos()):
            lys = self.nearest_lysosome(c.pos)
            direction = c.pos - lys.pos
            if mag(direction) < 0.001:
                direction = random_unit()
            r = lys.radius + c.radius + 0.25 + 0.8 * (0.5 + 0.5 * math.sin(self.mode_time * 1.35 + i))
            self.steer_cargo_to(c, lys.pos + norm(direction) * r, dt, strength=2.0, max_speed=2.0)
            if random.random() < 0.0018 and mag(c.pos - lys.pos) < lys.radius + c.radius + 0.55:
                self.steer_cargo_to(c, lys.pos, dt, strength=5.0, max_speed=3.1)

    def execute_spill_and_mix(self, dt):
        active = self.active_cargos()
        self.action_cooldown -= dt
        if active and self.action_cooldown <= 0:
            candidate = random.choice(active)
            candidate.spill() if random.random() < 0.55 else candidate.mark()
            self.action_cooldown = randf(1.8, 3.8)
        for p in self.free_particles():
            lys = self.nearest_lysosome(p.pos)
            if lys:
                swirl = cross(vector(0, 1, 0), p.pos - lys.pos)
                if mag(swirl) > 0.001:
                    p.vel += norm(swirl) * 0.55 * dt
                self.steer_particle_to(p, lys.pos, dt, strength=0.9, max_speed=1.8)

    def execute_mark_and_sort(self, dt):
        active = sorted(self.active_cargos(), key=lambda c: c.hue)
        self.action_cooldown -= dt
        if active and self.action_cooldown <= 0:
            random.choice(active).mark()
            self.action_cooldown = randf(1.0, 2.0)
        for i, c in enumerate(active):
            lys = self.sim.lysosomes[i % len(self.sim.lysosomes)]
            lane = lys.radius + c.radius + 1.7 + (i // len(self.sim.lysosomes)) * 0.42
            angle = i * 2.399963 + self.mode_time * 0.18
            target = lys.pos + vector(math.cos(angle) * lane, 1.0 + 0.18 * i, math.sin(angle) * lane)
            self.steer_cargo_to(c, target, dt, strength=1.8, max_speed=1.7)

    def execute_chaotic_stir(self, dt):
        for c in self.active_cargos():
            center_push = -norm(c.pos) * 0.25 if mag(c.pos) > 0.1 else random_unit()
            c.apply_force(random_unit() * 3.4 + center_push, dt)
            c.spin += randf(-4, 4) * dt
            if random.random() < 0.0025:
                c.mark()
            if random.random() < 0.0012:
                c.spill()
        for p in self.free_particles():
            p.vel += random_unit() * 1.8 * dt

    def execute_artistic_spiral(self, dt):
        active = self.active_cargos()
        for i, c in enumerate(active):
            angle = self.mode_time * 0.38 + i * 1.618
            radius = 2.2 + 0.34 * i
            target = vector(math.cos(angle) * radius, math.sin(angle * 0.7) * 1.4, math.sin(angle) * radius)
            self.steer_cargo_to(c, target, dt, strength=2.1, max_speed=2.0)
            if random.random() < 0.002:
                c.mark()
        for i, p in enumerate(self.free_particles()):
            lys = self.sim.lysosomes[i % len(self.sim.lysosomes)]
            angle = self.mode_time + i
            self.steer_particle_to(p, lys.pos + vector(math.cos(angle), math.sin(angle * 0.3), math.sin(angle)) * (lys.radius * 0.55), dt, strength=0.9, max_speed=1.3)

    def reset_if_complete_or_stagnant(self, dt):
        sig = self.simulation_signature()
        if self.last_signature is None:
            self.last_signature = sig
        if sig == self.last_signature:
            self.stagnation_time += dt
        else:
            self.stagnation_time = max(0, self.stagnation_time - dt * 0.7)
            self.last_signature = sig
        summary = self.state_summary()
        complete = summary["active_cargos"] == 0 and summary["free_particles"] == 0 and summary["degrading_particles"] == 0
        empty_or_stable = summary["total_alive_particles"] == 0 or (summary["active_cargos"] == 0 and summary["degrading_particles"] == 0)
        self.completion_time = self.completion_time + dt if complete or empty_or_stable else 0.0
        if self.completion_time > self.loop_delay:
            self.rounds_started_by_ai += 1
            self.sim.reset(reason="AI loop: completed degradation")
            self.last_signature = None
            self.completion_time = 0.0
            self.stagnation_time = 0.0
            self.choose_new_mode("play")
        elif self.stagnation_time > 11.0:
            if self.mode not in ["CHAOTIC_STIR", "SPILL_AND_MIX", "HERD_TO_ACID"]:
                self.choose_new_mode("stagnation")
            elif self.stagnation_time > 18.0:
                self.rounds_started_by_ai += 1
                self.sim.reset(reason="AI loop: stagnation reset")
                self.last_signature = None
                self.completion_time = 0.0
                self.stagnation_time = 0.0
                self.choose_new_mode("play")

    def update(self, dt):
        if not self.enabled or self.paused:
            return
        if self.sim.time < self.sim.manual_override_until:
            return
        self.mode_time += dt
        self.reset_if_complete_or_stagnant(dt)
        if self.mode_time > self.next_switch:
            self.choose_new_mode("time")
        if self.mode == "EXPLORE":
            self.execute_explore(dt)
        elif self.mode == "HERD_TO_ACID":
            self.execute_herd(dt)
        elif self.mode == "CAREFUL_ONE_BY_ONE":
            self.execute_careful(dt)
        elif self.mode == "ORBIT_RITUAL":
            self.execute_orbit(dt)
        elif self.mode == "DIP_AND_PULL":
            self.execute_dip_and_pull(dt)
        elif self.mode == "SPILL_AND_MIX":
            self.execute_spill_and_mix(dt)
        elif self.mode == "MARK_AND_SORT":
            self.execute_mark_and_sort(dt)
        elif self.mode == "CHAOTIC_STIR":
            self.execute_chaotic_stir(dt)
        elif self.mode == "ARTISTIC_SPIRAL":
            self.execute_artistic_spiral(dt)


class Simulation:
    def __init__(self):
        self.bounds = 7.2
        self.time = 0.0
        self.round_number = 0
        self.paused = False
        self.manual_override_until = -1
        self.dynamic_visuals = []
        self.lysosomes = []
        self.cargos = []
        self.particles = []
        self.effects = []
        self.ai = None
        self.selected_index = 0
        self.last_reset_reason = "initial"
        self.world_box = box(pos=vector(0, 0, 0), size=vector(self.bounds * 2, self.bounds * 2, self.bounds * 2), color=vector(0.55, 0.76, 0.92), opacity=0.035, shininess=0)
        self.status = label(pos=vector(0, self.bounds + 1.75, 0), text="", height=11, color=vector(0.12, 0.17, 0.23), box=False, opacity=0)
        self.selection_marker = sphere(pos=vector(0, 0, 0), radius=0.8, color=color.white, opacity=0.16, emissive=True, visible=False)
        self.reset(reason="initial setup")

    def hide_dynamic_visuals(self):
        for v in self.dynamic_visuals:
            hide_obj(v)
        self.dynamic_visuals = []

    def reset(self, reason="manual reset"):
        self.hide_dynamic_visuals()
        self.round_number += 1
        self.time = 0.0
        self.manual_override_until = -1
        self.last_reset_reason = reason
        self.lysosomes = []
        self.cargos = []
        self.particles = []
        self.effects = []
        self.selected_index = 0
        self.selection_marker.visible = False
        for pos, rad, name, hue in [
            (vector(-3.6, -0.6, -2.4), 1.18, "Lysosome A", 0.82),
            (vector(3.5, 0.4, -1.2), 1.34, "Lysosome B", 0.76),
            (vector(0.1, 1.0, 3.2), 1.08, "Lysosome C", 0.88),
        ]:
            self.lysosomes.append(Lysosome(self, pos, rad, name, hue))
        cargo_count = random.randint(8, 11)
        for i in range(cargo_count):
            for _ in range(200):
                p = vector(randf(-5.8, 5.8), randf(-4.6, 4.6), randf(-5.8, 5.8))
                if all(mag(p - l.pos) > l.radius + 1.9 for l in self.lysosomes):
                    break
            self.cargos.append(CargoVesicle(self, p, randf(0.42, 0.62), (i / max(1, cargo_count) + randf(-0.04, 0.04)) % 1.0, f"cargo {i + 1}"))
        burst = sphere(pos=vector(0, 0, 0), radius=0.25, color=vector(0.75, 0.93, 1.0), opacity=0.24, emissive=True)
        self.effects.append(TransientEffect(self, burst, ttl=1.1, expand=2.8, fade=True))

    def active_cargos(self):
        return [c for c in self.cargos if c.active]

    def selected_cargo(self):
        active = self.active_cargos()
        if not active:
            return None
        self.selected_index %= len(active)
        return active[self.selected_index]

    def select_next(self):
        active = self.active_cargos()
        if active:
            self.selected_index = (self.selected_index + 1) % len(active)

    def manual_override(self, seconds=4.0):
        self.manual_override_until = self.time + seconds

    def nearest_lysosome(self, pos):
        return min(self.lysosomes, key=lambda l: mag(l.pos - pos))

    def force_fuse_selected(self):
        c = self.selected_cargo()
        if c:
            c.fuse_with(self.nearest_lysosome(c.pos))

    def update_selection_marker(self):
        c = self.selected_cargo()
        if c and c.active:
            self.selection_marker.visible = True
            self.selection_marker.pos = c.pos
            self.selection_marker.radius = c.radius * 1.55 + 0.04 * math.sin(self.time * 7)
            self.selection_marker.color = mix_color(c.base_color, color.white, 0.65)
        else:
            self.selection_marker.visible = False

    def update_status(self):
        active = len([c for c in self.cargos if c.active])
        fused = len([c for c in self.cargos if c.fused])
        spilled = len([c for c in self.cargos if c.spilled])
        free = len([p for p in self.particles if not p.dead and p.state == "free"])
        degrading = len([p for p in self.particles if not p.dead and p.state == "degrading"])
        gone = len([p for p in self.particles if p.dead])
        total = len(self.particles)
        ai_text = "AI: unavailable"
        if self.ai:
            ai_text = f"AI: {'ON' if self.ai.enabled else 'OFF'}{' / paused' if self.ai.paused else ''} | mode: {self.ai.mode} | stagnant: {self.ai.stagnation_time:.1f}s"
        manual = f" | HUMAN OVERRIDE {self.manual_override_until - self.time:.1f}s" if self.time < self.manual_override_until else ""
        self.status.text = (
            f"Round {self.round_number} | {ai_text}{manual}\n"
            f"active vesicles: {active} | fused: {fused} | spilled: {spilled} | free particles: {free} | degrading: {degrading} | disappeared: {gone}/{total}\n"
            "Controls: SPACE pause, I/A AI, R reset, TAB select, WASD/arrows/QE move, O orbit, X spill, F fuse, M mark, C mode, P pause AI\n"
            f"CSV: {os.path.basename(CSV_OUTPUT_PATH)} | Last reset: {self.last_reset_reason}"
        )

    def update(self, dt):
        if self.paused:
            self.update_status()
            return
        self.time += dt
        if self.ai:
            self.ai.update(dt)
        for lys in self.lysosomes:
            lys.update(dt)
        for c in list(self.cargos):
            c.update(dt)
        for p in list(self.particles):
            p.update(dt)
        self.particles = [p for p in self.particles if not (p.dead and p.visual.visible is False)]
        self.effects = [e for e in self.effects if e.update(dt)]
        if int(self.time * 2) != int((self.time - dt) * 2):
            self.dynamic_visuals = [v for v in self.dynamic_visuals if getattr(v, "visible", True)]
        self.update_selection_marker()
        self.update_status()

# ------------------------------------------------------------
# CSV snapshot helpers
# ------------------------------------------------------------

def csv_scene_state(sim):
    active = [c for c in sim.cargos if c.active]
    alive_particles = [p for p in sim.particles if not p.dead]
    in_cargo = [p for p in alive_particles if p.state == "in_cargo"]
    free = [p for p in alive_particles if p.state == "free"]
    degrading = [p for p in alive_particles if p.state == "degrading"]
    dead = [p for p in sim.particles if p.dead]
    avg_speed = sum(mag(c.vel) for c in active) / max(1, len(active))
    selected = sim.selected_cargo()
    gaps = []
    for c in active:
        lys = sim.nearest_lysosome(c.pos)
        gaps.append(max(0.0, mag(c.pos - lys.pos) - lys.radius - c.radius))
    ai = sim.ai
    return {
        "round_number": sim.round_number,
        "paused": sim.paused,
        "last_reset_reason": sim.last_reset_reason,
        "ai_enabled": ai.enabled if ai else "",
        "ai_paused": ai.paused if ai else "",
        "ai_mode": ai.mode if ai else "",
        "ai_previous_mode": ai.previous_mode if ai else "",
        "ai_mode_time": ai.mode_time if ai else "",
        "ai_stagnation_time": ai.stagnation_time if ai else "",
        "ai_completion_time": ai.completion_time if ai else "",
        "manual_override_remaining": max(0.0, sim.manual_override_until - sim.time),
        "selected_index": sim.selected_index,
        "selected_cargo": selected.name if selected else "",
        "lysosome_count": len(sim.lysosomes),
        "cargo_count": len(sim.cargos),
        "active_cargo_count": len(active),
        "fused_cargo_count": len([c for c in sim.cargos if c.fused]),
        "spilled_cargo_count": len([c for c in sim.cargos if c.spilled]),
        "particle_count": len(sim.particles),
        "in_cargo_particle_count": len(in_cargo),
        "free_particle_count": len(free),
        "degrading_particle_count": len(degrading),
        "dead_particle_count": len(dead),
        "effect_count": len(sim.effects),
        "dynamic_visual_count": len(sim.dynamic_visuals),
        "digest_total": sum(l.digest_count for l in sim.lysosomes),
        "avg_cargo_speed": avg_speed,
        "nearest_fusion_gap": min(gaps) if gaps else "",
    }


def csv_base_row(sim, csv_elapsed_seconds, frame, row_type, object_id="", object_kind=""):
    row = {
        "csv_run_id": CSV_RUN_ID,
        "csv_elapsed_seconds": round(csv_elapsed_seconds, 4),
        "simulation_time": round(sim.time, 4),
        "frame": frame,
        "row_type": row_type,
        "object_id": object_id,
        "object_kind": object_kind,
    }
    row.update(csv_scene_state(sim))
    return row


def write_csv_snapshot(sim, csv_elapsed_seconds, frame):
    _csv_writer.writerow(csv_base_row(sim, csv_elapsed_seconds, frame, "summary", "lysosome_fusion", "summary"))
    for i, lys in enumerate(sim.lysosomes):
        row = csv_base_row(sim, csv_elapsed_seconds, frame, "lysosome", f"lysosome_{i}", "lysosome")
        row.update({"name": lys.name, "radius": lys.radius, "lysosome_digest_count": lys.digest_count, "lysosome_glow_timer": lys.glow_timer})
        row.update(vdict(lys.pos, ""))
        _csv_writer.writerow(row)
    for i, cargo in enumerate(sim.cargos):
        row = csv_base_row(sim, csv_elapsed_seconds, frame, "cargo", f"cargo_{i}", "cargo_vesicle")
        row.update({
            "name": cargo.name,
            "radius": cargo.radius,
            "base_radius": cargo.radius,
            "age": cargo.age,
            "hue": cargo.hue,
            "spin": cargo.spin,
            "cargo_active": cargo.active,
            "cargo_fused": cargo.fused,
            "cargo_spilled": cargo.spilled,
            "cargo_marked": cargo.marked,
            "cargo_ai_attached": cargo.ai_attached,
            "target_name": cargo.orbit_target.name if cargo.orbit_target else "",
            "cargo_particle_count": len(cargo.particles),
            "cargo_alive_particle_count": len(cargo.alive_particles()),
            "orbit_phase": cargo.orbit_phase,
        })
        row.update(vdict(cargo.pos, ""))
        row.update(vdict(cargo.vel, "v"))
        _csv_writer.writerow(row)
    for i, particle in enumerate(sim.particles):
        row = csv_base_row(sim, csv_elapsed_seconds, frame, "particle", f"particle_{i}", "cargo_particle")
        row.update({
            "kind": "cargo_particle",
            "state": particle.state,
            "particle_state": particle.state,
            "particle_dead": particle.dead,
            "radius": particle.radius,
            "particle_radius0": particle.radius0,
            "age": particle.age,
            "target_name": particle.cargo.name if particle.cargo else "",
            "lysosome_name": particle.lysosome.name if particle.lysosome else "",
            "opacity": getattr(particle.visual, "opacity", ""),
        })
        row.update(vdict(particle.pos, ""))
        row.update(vdict(particle.vel, "v"))
        _csv_writer.writerow(row)
    for i, effect in enumerate(sim.effects):
        row = csv_base_row(sim, csv_elapsed_seconds, frame, "effect", f"effect_{i}", "transient_effect")
        row.update({"state": "active", "life": effect.life, "ttl": effect.ttl, "radius": getattr(effect.visual, "radius", ""), "opacity": getattr(effect.visual, "opacity", "")})
        if hasattr(effect.visual, "pos"):
            row.update(vdict(effect.visual.pos, ""))
        _csv_writer.writerow(row)
    _csv_file.flush()

# ------------------------------------------------------------
# Keyboard and run loop
# ------------------------------------------------------------

sim = Simulation()
sim.ai = AIController(sim)


def keydown(evt):
    key = evt.key
    c = sim.selected_cargo()
    move_force = 4.8
    if key == " ":
        sim.paused = not sim.paused
    elif key in ["A", "a", "i", "I"]:
        sim.ai.enabled = not sim.ai.enabled
    elif key in ["p", "P"]:
        sim.ai.paused = not sim.ai.paused
    elif key in ["r", "R"]:
        sim.reset(reason="manual reset")
        if sim.ai:
            sim.ai.last_signature = None
            sim.ai.stagnation_time = 0
            sim.ai.completion_time = 0
    elif key == "tab":
        sim.select_next()
    elif key in ["c", "C"]:
        if sim.ai:
            sim.ai.choose_new_mode("play")
    elif key in ["m", "M"]:
        if c:
            c.mark()
            sim.manual_override()
    elif key in ["x", "X"]:
        if c:
            c.spill()
            sim.manual_override()
    elif key in ["f", "F"]:
        sim.force_fuse_selected()
        sim.manual_override()
    elif key in ["o", "O"]:
        if c:
            c.detach_orbit() if c.ai_attached else c.attach_orbit(sim.nearest_lysosome(c.pos))
            sim.manual_override()
    elif c:
        direction = vector(0, 0, 0)
        if key in ["left", "a"]:
            direction += vector(-1, 0, 0)
        if key in ["right", "d"]:
            direction += vector(1, 0, 0)
        if key in ["up", "w"]:
            direction += vector(0, 0, -1)
        if key in ["down", "s"]:
            direction += vector(0, 0, 1)
        if key in ["q", "Q"]:
            direction += vector(0, -1, 0)
        if key in ["e", "E"]:
            direction += vector(0, 1, 0)
        if mag(direction) > 0:
            c.detach_orbit()
            c.vel += norm(direction) * move_force * 0.12
            c.spin += randf(-1, 1)
            sim.manual_override()

scene.bind("keydown", keydown)

csv_elapsed_seconds = 0.0
csv_sample_timer = CSV_SAMPLE_INTERVAL
csv_frame = 0

try:
    while csv_elapsed_seconds < CSV_RUN_SECONDS:
        rate(60)
        csv_frame += 1
        csv_elapsed_seconds += DT
        csv_sample_timer += DT
        sim.update(DT)
        if csv_sample_timer >= CSV_SAMPLE_INTERVAL:
            csv_sample_timer = 0.0
            write_csv_snapshot(sim, csv_elapsed_seconds, csv_frame)
    write_csv_snapshot(sim, csv_elapsed_seconds, csv_frame)
    sim.status.text = f"CSV recording complete: {CSV_RUN_SECONDS:0.0f}s saved to {os.path.basename(CSV_OUTPUT_PATH)}"
finally:
    _csv_file.flush()
    _csv_file.close()
