from vpython import *
import random
import math
import time
import csv
import os
import json
from datetime import datetime

# Cellular Autophagy: Recycling Damaged Parts
# Self-contained VPython simulation with automatic AI behavior controller.
#
# Controls:
#   SPACE  pause/resume
#   A      toggle AI
#   R      reset / new round
#   M      manually mark a damaged organelle
#   W      manually start wrapping a marked organelle
#   D      detach current autophagosome cargo
#   C      chaos impulse
#   O      toggle AI orbit/play mode
#   S      spill recyclable/enzyme particles
#   Arrow keys / Z / X move active autophagosome manually
#   H      toggle help label

scene.title = "Cellular Autophagy: Recycling Damaged Parts"
scene.width = 1180
scene.height = 760
scene.background = vector(0.93, 0.97, 1.0)
scene.forward = vector(-0.55, -0.35, -0.75)
scene.center = vector(0, 0, 0)
scene.range = 11.5
scene.autoscale = False
scene.userzoom = True
scene.userspin = True
scene.lights = []
distant_light(direction=vector(-0.4, -0.6, -0.5), color=color.white)
distant_light(direction=vector(0.8, 0.2, 0.5), color=vector(0.75, 0.85, 1.0))
local_light(pos=vector(0, 6, 6), color=vector(0.7, 0.9, 1.0))

CELL_RADIUS = 8.0
DT = 1 / 60
TWO_PI = 2 * math.pi

AI_MODES = [
    "SURVEY",
    "MARK",
    "CAREFUL_WRAP",
    "DELIVER",
    "FUSE",
    "ORBIT",
    "RITUAL",
    "CHAOS",
    "ARTISTIC",
    "SPILL",
    "RESET_WAIT",
]


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
    CSV_OUTPUT_PATH = os.path.join(CSV_OUTPUT_DIR, f"{CSV_RUN_ID}-autophagy-state-log.csv")
else:
    fallback_path = os.environ.get("SIM_STATE_CSV_PATH", "").strip()
    if fallback_path:
        CSV_OUTPUT_PATH = fallback_path
        parent = os.path.dirname(os.path.abspath(CSV_OUTPUT_PATH))
        if parent:
            os.makedirs(parent, exist_ok=True)
    else:
        CSV_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autophagy_state_log.csv")

CSV_METADATA_PATH = os.path.splitext(CSV_OUTPUT_PATH)[0] + ".metadata.json"

CSV_FIELDNAMES = [
    "csv_run_id", "csv_elapsed_seconds", "simulation_time", "frame",
    "row_type", "object_id", "object_kind",
    "round_index", "paused", "help_visible",
    "ai_enabled", "ai_mode", "ai_last_mode", "ai_mode_timer", "ai_override_until",
    "ai_stagnant_time", "ai_completion_active", "ai_loop_rounds",
    "active_organelle_count", "free_organelle_count", "marked_organelle_count",
    "wrapped_organelle_count", "dissolving_organelle_count", "recycled_organelle_count",
    "particle_count", "enzyme_particle_count", "recycle_particle_count",
    "autophagosome_state", "autophagosome_active", "autophagosome_target_id",
    "autophagosome_radius", "autophagosome_closure", "autophagosome_fuse_timer",
    "lysosome_orbit_mode",
    "name", "kind", "state", "id", "target_id",
    "x", "y", "z", "vx", "vy", "vz",
    "radius", "damage", "age", "mark_strength", "dissolve_amount",
    "opacity", "life", "captured",
    "center_x", "center_y", "center_z",
    "lysosome_x", "lysosome_y", "lysosome_z", "distance_to_lysosome",
]

_csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
_csv_writer = csv.DictWriter(_csv_file, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
_csv_writer.writeheader()
_csv_file.flush()


def _v_components(v, prefix=""):
    return {
        f"{prefix}x": float(v.x),
        f"{prefix}y": float(v.y),
        f"{prefix}z": float(v.z),
    }


def _csv_scene_state():
    organelles = getattr(sim, "organelles", [])
    particles = getattr(sim, "particles", [])
    autophagosome = getattr(sim, "autophagosome", None)
    lysosome = getattr(sim, "lysosome", None)
    ai = getattr(sim, "ai", None)

    active = [o for o in organelles if o.state != "recycled"]
    free = [o for o in organelles if o.state == "free"]
    marked = [o for o in organelles if o.state == "marked"]
    wrapped = [o for o in organelles if o.state == "wrapped"]
    dissolving = [o for o in organelles if o.state == "dissolving"]
    recycled = [o for o in organelles if o.state == "recycled"]
    enzyme_particles = [p for p in particles if p.kind == "enzyme"]
    recycle_particles = [p for p in particles if p.kind == "recycle"]

    target_id = ""
    if autophagosome is not None and autophagosome.target is not None:
        target_id = autophagosome.target.id

    return {
        "round_index": getattr(sim, "round_index", ""),
        "paused": getattr(sim, "paused", ""),
        "help_visible": getattr(sim, "show_help", ""),
        "ai_enabled": getattr(ai, "enabled", ""),
        "ai_mode": getattr(ai, "mode", ""),
        "ai_last_mode": getattr(ai, "last_mode", ""),
        "ai_mode_timer": getattr(ai, "mode_timer", ""),
        "ai_override_until": getattr(ai, "override_until", ""),
        "ai_stagnant_time": getattr(ai, "stagnant_time", ""),
        "ai_completion_active": getattr(ai, "completion_time", None) is not None if ai is not None else "",
        "ai_loop_rounds": getattr(ai, "loop_rounds", ""),
        "active_organelle_count": len(active),
        "free_organelle_count": len(free),
        "marked_organelle_count": len(marked),
        "wrapped_organelle_count": len(wrapped),
        "dissolving_organelle_count": len(dissolving),
        "recycled_organelle_count": len(recycled),
        "particle_count": len(particles),
        "enzyme_particle_count": len(enzyme_particles),
        "recycle_particle_count": len(recycle_particles),
        "autophagosome_state": getattr(autophagosome, "state", ""),
        "autophagosome_active": getattr(autophagosome, "active", ""),
        "autophagosome_target_id": target_id,
        "autophagosome_radius": getattr(autophagosome, "radius", ""),
        "autophagosome_closure": getattr(autophagosome, "closure", ""),
        "autophagosome_fuse_timer": getattr(autophagosome, "fuse_timer", ""),
        "lysosome_orbit_mode": getattr(lysosome, "mode_orbit", ""),
    }


def _csv_base_row(csv_elapsed_seconds, frame, row_type, object_id="", object_kind=""):
    row = {
        "csv_run_id": CSV_RUN_ID,
        "csv_elapsed_seconds": round(csv_elapsed_seconds, 4),
        "simulation_time": round(getattr(sim, "t", 0.0), 4),
        "frame": frame,
        "row_type": row_type,
        "object_id": object_id,
        "object_kind": object_kind,
    }
    row.update(_csv_scene_state())
    return row


def write_csv_snapshot(csv_elapsed_seconds, frame):
    _csv_writer.writerow(_csv_base_row(csv_elapsed_seconds, frame, "summary", "autophagy", "summary"))

    lysosome = getattr(sim, "lysosome", None)
    if lysosome is not None:
        row = _csv_base_row(csv_elapsed_seconds, frame, "lysosome", "lysosome", "lysosome")
        row.update({
            "name": "lysosome",
            "kind": "recycling_center",
            "state": "orbiting" if lysosome.mode_orbit else "stationary",
            "radius": lysosome.radius,
        })
        row.update(_v_components(lysosome.pos, ""))
        _csv_writer.writerow(row)

    autophagosome = getattr(sim, "autophagosome", None)
    if autophagosome is not None:
        row = _csv_base_row(csv_elapsed_seconds, frame, "autophagosome", "autophagosome", "autophagosome")
        target_id = autophagosome.target.id if autophagosome.target is not None else ""
        row.update({
            "name": "autophagosome",
            "state": autophagosome.state,
            "target_id": target_id,
            "radius": autophagosome.radius,
            "autophagosome_radius": autophagosome.radius,
            "autophagosome_closure": autophagosome.closure,
            "autophagosome_fuse_timer": autophagosome.fuse_timer,
        })
        row.update(_v_components(autophagosome.center, "center_"))
        row.update(_v_components(autophagosome.vel, "v"))
        if lysosome is not None:
            row.update(_v_components(lysosome.pos, "lysosome_"))
            row["distance_to_lysosome"] = mag(autophagosome.center - lysosome.pos)
        _csv_writer.writerow(row)

    for i, organelle in enumerate(getattr(sim, "organelles", [])):
        row = _csv_base_row(csv_elapsed_seconds, frame, "organelle", f"organelle_{organelle.id}", "damaged_organelle")
        row.update({
            "id": organelle.id,
            "kind": "damaged_organelle",
            "state": organelle.state,
            "radius": organelle.radius,
            "damage": organelle.damage,
            "age": organelle.age,
            "mark_strength": organelle.mark_strength,
            "dissolve_amount": organelle.dissolve_amount,
            "opacity": getattr(organelle.body, "opacity", ""),
            "target_id": organelle.attached_to.target.id if getattr(organelle, "attached_to", None) is not None and getattr(organelle.attached_to, "target", None) is not None else "",
        })
        row.update(_v_components(organelle.pos, ""))
        row.update(_v_components(organelle.vel, "v"))
        if lysosome is not None:
            row.update(_v_components(lysosome.pos, "lysosome_"))
            row["distance_to_lysosome"] = mag(organelle.pos - lysosome.pos)
        _csv_writer.writerow(row)

    for i, particle in enumerate(getattr(sim, "particles", [])):
        row = _csv_base_row(csv_elapsed_seconds, frame, "particle", f"particle_{i}", "recycle_particle")
        row.update({
            "kind": particle.kind,
            "state": "captured" if particle.captured else "free",
            "age": particle.age,
            "life": particle.life,
            "captured": particle.captured,
            "radius": getattr(particle.body, "radius", ""),
            "opacity": getattr(particle.body, "opacity", ""),
        })
        row.update(_v_components(particle.pos, ""))
        row.update(_v_components(particle.vel, "v"))
        if lysosome is not None:
            row.update(_v_components(lysosome.pos, "lysosome_"))
            row["distance_to_lysosome"] = mag(particle.pos - lysosome.pos)
        _csv_writer.writerow(row)

    _csv_file.flush()


def write_csv_metadata():
    metadata = {
        "csv_run_id": CSV_RUN_ID,
        "csv_output_path": CSV_OUTPUT_PATH,
        "csv_metadata_path": CSV_METADATA_PATH,
        "simulation_name": "Cellular Autophagy: Recycling Damaged Parts",
        "script_type": "full_vpython_csv_logger",
        "run_seconds": CSV_RUN_SECONDS,
        "sample_hz": CSV_SAMPLE_HZ,
        "sample_interval": CSV_SAMPLE_INTERVAL,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "row_types": ["summary", "lysosome", "autophagosome", "organelle", "particle"],
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


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * clamp(t, 0, 1)


def randf(a, b):
    return random.uniform(a, b)


def rand_vec(scale=1.0):
    while True:
        v = vector(randf(-1, 1), randf(-1, 1), randf(-1, 1))
        if mag(v) > 0.001:
            return norm(v) * scale


def random_point_in_cell(margin=1.0):
    r = randf(0.2, CELL_RADIUS - margin)
    return rand_vec(r)


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-7:
        return fallback
    return v / m


def mix_color(c1, c2, t):
    t = clamp(t, 0, 1)
    return c1 * (1 - t) + c2 * t


def hsvish_damage_color(phase, marked=False):
    red = vector(1.0, 0.16, 0.12)
    orange = vector(1.0, 0.58, 0.12)
    magenta = vector(0.95, 0.18, 0.82)
    yellow = vector(1.0, 0.95, 0.16)
    a = 0.5 + 0.5 * math.sin(phase * 7.0)
    b = 0.5 + 0.5 * math.sin(phase * 11.0 + 1.7)
    base = mix_color(red, orange, a)
    base = mix_color(base, magenta, 0.35 * b)
    if marked:
        base = mix_color(base, yellow, 0.35 + 0.25 * math.sin(phase * 13.0))
    return base


class DamagedOrganelle:
    next_id = 1

    def __init__(self, pos=None):
        self.id = DamagedOrganelle.next_id
        DamagedOrganelle.next_id += 1
        self.pos = pos if pos is not None else random_point_in_cell(1.3)
        self.vel = rand_vec(randf(0.25, 0.75))
        self.radius = randf(0.38, 0.7)
        self.damage = randf(0.55, 1.0)
        self.phase = randf(0, TWO_PI)
        self.state = "free"     # free, marked, wrapped, dissolving, recycled
        self.attached_to = None
        self.age = 0
        self.mark_strength = 0.0
        self.dissolve_amount = 0.0

        self.body = sphere(
            pos=self.pos,
            size=vector(self.radius * 1.55, self.radius * randf(0.95, 1.3), self.radius * randf(0.75, 1.2)),
            color=hsvish_damage_color(self.phase),
            opacity=0.92,
            shininess=0.25,
        )

        self.inner_spots = []
        for _ in range(3):
            spot = sphere(
                pos=self.pos + rand_vec(self.radius * 0.35),
                radius=self.radius * randf(0.08, 0.14),
                color=vector(0.4, 0.05, 0.25),
                opacity=0.8,
                shininess=0.1,
            )
            self.inner_spots.append(spot)

        self.trail = curve(color=vector(1.0, 0.52, 0.82), radius=0.018, retain=36)

        self.marker_rings = [
            ring(pos=self.pos, axis=vector(1, 0, 0), radius=self.radius * 1.05, thickness=0.025,
                 color=vector(1.0, 0.95, 0.05), opacity=0.0),
            ring(pos=self.pos, axis=vector(0, 1, 0), radius=self.radius * 1.15, thickness=0.025,
                 color=vector(0.25, 0.55, 1.0), opacity=0.0),
            ring(pos=self.pos, axis=vector(0, 0, 1), radius=self.radius * 1.25, thickness=0.025,
                 color=vector(1.0, 0.7, 0.2), opacity=0.0),
        ]

    def mark(self):
        if self.state in ["free", "marked"]:
            self.state = "marked"
            self.mark_strength = 1.0

    def unmark(self):
        if self.state == "marked":
            self.state = "free"
            self.mark_strength = 0.0

    def attach(self, shell):
        self.state = "wrapped"
        self.attached_to = shell
        self.vel = vector(0, 0, 0)

    def detach(self):
        if self.state == "wrapped":
            self.state = "marked"
            self.attached_to = None
            self.vel = rand_vec(randf(0.3, 0.8))
            self.body.opacity = 0.85

    def dissolve_step(self, dt):
        self.state = "dissolving"
        self.dissolve_amount += dt * 0.42
        self.body.opacity = clamp(0.95 * (1.0 - self.dissolve_amount), 0.0, 0.95)
        self.body.size *= max(0.985, 1.0 - dt * 0.05)
        for spot in self.inner_spots:
            spot.opacity = self.body.opacity * 0.8
        if self.dissolve_amount >= 1.0:
            self.recycle()

    def recycle(self):
        self.state = "recycled"
        self.body.visible = False
        for spot in self.inner_spots:
            spot.visible = False
        self.trail.visible = False
        for r in self.marker_rings:
            r.visible = False

    def nudge(self, impulse):
        if self.state in ["free", "marked"]:
            self.vel += impulse

    def update(self, dt, sim_time):
        self.age += dt
        if self.state in ["free", "marked"]:
            self.pos += self.vel * dt

            # Soft cytoplasm drag and subtle Brownian jitter
            self.vel *= 0.992
            self.vel += rand_vec(randf(0.0, 0.025)) * dt * 8.0

            # Bounce from the cell boundary
            d = mag(self.pos)
            if d + self.radius > CELL_RADIUS:
                n = safe_norm(self.pos)
                self.pos = n * (CELL_RADIUS - self.radius)
                self.vel = self.vel - 2 * dot(self.vel, n) * n
                self.vel *= 0.78

        elif self.state == "wrapped" and self.attached_to is not None:
            self.pos = self.attached_to.center
            self.vel = vector(0, 0, 0)

        self.body.pos = self.pos
        self.body.color = hsvish_damage_color(self.phase + sim_time, self.state in ["marked", "wrapped"])
        if self.state == "wrapped":
            self.body.opacity = 0.45
        elif self.state in ["free", "marked"]:
            self.body.opacity = 0.9

        self.body.rotate(angle=dt * (0.4 + self.damage), axis=vector(0.3, 1, 0.2))

        for i, spot in enumerate(self.inner_spots):
            orbit = vector(
                math.cos(sim_time * (1.2 + i * 0.5) + i) * self.radius * 0.32,
                math.sin(sim_time * (1.5 + i * 0.3) + i * 2) * self.radius * 0.22,
                math.sin(sim_time * (0.9 + i * 0.4) + i) * self.radius * 0.28,
            )
            spot.pos = self.pos + orbit
            spot.visible = self.body.visible
            spot.opacity = self.body.opacity * 0.75

        if self.state in ["free", "marked"]:
            self.trail.append(pos=self.pos)
        elif self.state == "wrapped":
            self.trail.append(pos=self.pos)

        if self.state in ["marked", "wrapped"]:
            self.mark_strength = clamp(self.mark_strength + dt * 1.8, 0, 1)
        else:
            self.mark_strength = clamp(self.mark_strength - dt * 1.4, 0, 1)

        for i, r in enumerate(self.marker_rings):
            r.pos = self.pos
            r.radius = self.radius * (1.05 + i * 0.12 + 0.08 * math.sin(sim_time * 5 + i))
            r.opacity = 0.62 * self.mark_strength
            r.visible = self.state != "recycled"
            if i == 0:
                r.axis = vector(math.sin(sim_time), math.cos(sim_time), 0.25)
            elif i == 1:
                r.axis = vector(0.25, math.sin(sim_time * 0.9), math.cos(sim_time * 0.9))
            else:
                r.axis = vector(math.cos(sim_time * 1.1), 0.2, math.sin(sim_time * 1.1))

    def destroy(self):
        self.body.visible = False
        for spot in self.inner_spots:
            spot.visible = False
        self.trail.visible = False
        for r in self.marker_rings:
            r.visible = False


class RecycleParticle:
    def __init__(self, pos, vel=None, kind="recycle"):
        self.pos = vector(pos)
        self.vel = vel if vel is not None else rand_vec(randf(0.4, 1.5))
        self.kind = kind
        self.age = 0
        self.life = randf(7, 16)
        if kind == "enzyme":
            col = vector(1.0, 0.72, 0.18)
            rad = randf(0.045, 0.075)
        else:
            col = random.choice([
                vector(0.15, 0.85, 0.45),
                vector(0.1, 0.65, 1.0),
                vector(1.0, 0.85, 0.22),
                vector(0.65, 0.95, 0.45),
            ])
            rad = randf(0.035, 0.085)
        self.body = sphere(pos=self.pos, radius=rad, color=col, opacity=0.9, shininess=0.7)
        self.trail = curve(color=col, radius=rad * 0.18, opacity=0.35, retain=20)
        self.captured = False

    def update(self, dt, lysosome):
        self.age += dt
        to_lyso = lysosome.pos - self.pos
        d = mag(to_lyso)
        if d < lysosome.radius * 1.15:
            self.captured = True

        if self.captured:
            # Mix inside lysosome rather than disappearing immediately
            axis = safe_norm(vector(-to_lyso.y, to_lyso.x, 0.35), rand_vec(1))
            self.vel += axis * dt * 0.7
            self.vel += to_lyso * dt * 0.16
            if d > lysosome.radius * 0.7:
                self.vel += safe_norm(to_lyso) * dt * 0.85
            self.vel *= 0.985
        else:
            self.vel += safe_norm(to_lyso) * dt * 0.45
            self.vel *= 0.992

        self.pos += self.vel * dt

        # Keep inside cell
        if mag(self.pos) > CELL_RADIUS - 0.15:
            n = safe_norm(self.pos)
            self.pos = n * (CELL_RADIUS - 0.15)
            self.vel = self.vel - 2 * dot(self.vel, n) * n
            self.vel *= 0.55

        self.body.pos = self.pos
        self.body.opacity = clamp(1.0 - max(0, self.age - self.life) / 3.0, 0.0, 0.9)
        self.trail.append(pos=self.pos)

    @property
    def dead(self):
        return self.age > self.life + 3.0 or self.body.opacity <= 0.01

    def destroy(self):
        self.body.visible = False
        self.trail.visible = False


class Lysosome:
    def __init__(self, pos=vector(4.8, -1.1, 1.2)):
        self.pos = vector(pos)
        self.radius = 1.18
        self.phase = 0
        self.mode_orbit = False
        self.base_pos = vector(pos)

        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=vector(1.0, 0.64, 0.16),
            opacity=0.46,
            shininess=0.8,
        )
        self.core = sphere(
            pos=self.pos,
            radius=self.radius * 0.68,
            color=vector(1.0, 0.35, 0.12),
            opacity=0.28,
            shininess=0.4,
        )
        self.rim = ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=self.radius * 1.04,
            thickness=0.035,
            color=vector(1.0, 0.85, 0.25),
            opacity=0.65,
        )
        self.label = label(
            pos=self.pos + vector(0, 1.6, 0),
            text="lysosome\nacidic recycling center",
            height=12,
            color=vector(0.65, 0.32, 0.05),
            box=False,
            opacity=0,
        )

        self.enzyme_dots = []
        for i in range(14):
            dot = sphere(
                pos=self.pos + rand_vec(randf(0.15, self.radius * 0.85)),
                radius=randf(0.035, 0.07),
                color=vector(1.0, randf(0.75, 0.95), randf(0.12, 0.28)),
                opacity=0.85,
                shininess=0.5,
            )
            self.enzyme_dots.append(dot)

    def update(self, dt, sim_time):
        self.phase += dt
        if self.mode_orbit:
            self.pos = self.base_pos + vector(
                math.cos(sim_time * 0.22) * 0.5,
                math.sin(sim_time * 0.18) * 0.25,
                math.sin(sim_time * 0.25) * 0.45,
            )
        self.body.pos = self.pos
        self.core.pos = self.pos
        self.rim.pos = self.pos
        self.rim.axis = vector(math.sin(sim_time * 0.7), 1.0, math.cos(sim_time * 0.7))
        self.label.pos = self.pos + vector(0, 1.6, 0)

        pulse = 0.5 + 0.5 * math.sin(sim_time * 2.2)
        self.body.radius = self.radius * (1.0 + 0.025 * pulse)
        self.core.radius = self.radius * (0.64 + 0.025 * math.sin(sim_time * 3.0 + 1.0))

        for i, dot in enumerate(self.enzyme_dots):
            a = sim_time * (0.6 + i * 0.035) + i * 1.7
            b = sim_time * (0.9 + i * 0.025) + i
            rad = self.radius * (0.35 + 0.5 * ((i % 5) / 5.0))
            dot.pos = self.pos + vector(math.cos(a) * rad, math.sin(b) * rad * 0.6, math.sin(a) * rad)
            dot.visible = True

    def destroy(self):
        self.body.visible = False
        self.core.visible = False
        self.rim.visible = False
        self.label.visible = False
        for dot in self.enzyme_dots:
            dot.visible = False


class DoubleMembraneArcSet:
    def __init__(self, color_outer=vector(0.22, 0.74, 1.0), color_inner=vector(0.45, 0.98, 0.95)):
        self.n = 72
        self.curves = []
        self.planes = ["xy", "yz", "xz"]
        for membrane_index in range(2):
            for plane in self.planes:
                c = curve(
                    pos=[vector(0, 0, 0) for _ in range(self.n)],
                    radius=0.032 if membrane_index == 0 else 0.026,
                    color=color_outer if membrane_index == 0 else color_inner,
                    opacity=0.82 if membrane_index == 0 else 0.72,
                )
                self.curves.append((membrane_index, plane, c))
        self.visible = False

    def set_visible(self, visible):
        self.visible = visible
        for _, _, c in self.curves:
            c.visible = visible

    def update(self, center, radius, closure, spin_phase=0.0):
        closure = clamp(closure, 0, 1)
        if not self.visible:
            self.set_visible(True)

        # An open crescent becomes a complete shell as closure -> 1.
        span = lerp(0.78 * math.pi, TWO_PI, closure)
        gap = TWO_PI - span
        start = gap * 0.5
        end = TWO_PI - gap * 0.5
        if closure > 0.985:
            start = 0
            end = TWO_PI

        for membrane_index, plane, c in self.curves:
            rr = radius * (1.0 if membrane_index == 0 else 0.82)
            offset = radius * (0.035 if membrane_index == 0 else -0.035)
            for i in range(self.n):
                u = i / (self.n - 1)
                a = start + (end - start) * u + spin_phase
                wobble = 1.0 + 0.025 * math.sin(5 * a + spin_phase * 2 + membrane_index)
                x = math.cos(a) * rr * wobble
                y = math.sin(a) * rr * wobble
                if plane == "xy":
                    p = center + vector(x, y, offset)
                elif plane == "yz":
                    p = center + vector(offset, x, y)
                else:
                    p = center + vector(x, offset, y)
                c.modify(i, pos=p)
            c.opacity = (0.25 + 0.62 * closure) if membrane_index == 0 else (0.18 + 0.5 * closure)

    def destroy(self):
        for _, _, c in self.curves:
            c.visible = False


class Autophagosome:
    def __init__(self):
        self.center = vector(-2.0, 0, 0)
        self.vel = vector(0, 0, 0)
        self.radius = 0.35
        self.target_radius = 1.1
        self.closure = 0.0
        self.state = "idle"  # idle, growing, wrapping, closed, moving, fusing, dissolving
        self.target = None
        self.spin_phase = 0.0
        self.fuse_timer = 0.0
        self.dissolve_spawn_timer = 0.0
        self.mode_color_phase = 0.0

        self.shell_outer = sphere(
            pos=self.center,
            radius=self.radius,
            color=vector(0.28, 0.78, 1.0),
            opacity=0.0,
            shininess=0.9,
        )
        self.shell_inner = sphere(
            pos=self.center,
            radius=self.radius * 0.82,
            color=vector(0.65, 1.0, 0.93),
            opacity=0.0,
            shininess=0.7,
        )
        self.arcset = DoubleMembraneArcSet()
        self.arcset.set_visible(False)
        self.trail = curve(color=vector(0.3, 0.75, 1.0), radius=0.025, retain=80)
        self.label = label(
            pos=self.center + vector(0, 1.6, 0),
            text="autophagosome\nforming double membrane",
            height=12,
            color=vector(0.06, 0.35, 0.65),
            box=False,
            opacity=0,
            visible=False,
        )

    @property
    def active(self):
        return self.state != "idle"

    def start_wrap(self, target):
        if target is None or target.state not in ["free", "marked"]:
            return False
        self.target = target
        target.mark()
        self.state = "growing"
        self.center = target.pos + rand_vec(randf(1.25, 1.75))
        self.vel = vector(0, 0, 0)
        self.radius = 0.35
        self.target_radius = max(0.95, target.radius * 1.85)
        self.closure = 0.02
        self.fuse_timer = 0.0
        self.dissolve_spawn_timer = 0.0
        self.shell_outer.visible = True
        self.shell_inner.visible = True
        self.label.visible = True
        self.arcset.set_visible(True)
        return True

    def detach_target(self):
        if self.target is not None:
            self.target.detach()
        self.target = None
        self.state = "idle"
        self.closure = 0
        self.radius = 0.3
        self.shell_outer.opacity = 0
        self.shell_inner.opacity = 0
        self.arcset.set_visible(False)
        self.label.visible = False

    def force_move(self, delta):
        if self.active:
            self.center += delta
            if self.target is not None and self.target.state == "wrapped":
                self.target.pos = self.center

    def update_visuals(self, sim_time):
        self.shell_outer.pos = self.center
        self.shell_inner.pos = self.center
        self.shell_outer.radius = self.radius
        self.shell_inner.radius = self.radius * 0.82
        membrane_color = mix_color(vector(0.2, 0.7, 1.0), vector(0.7, 1.0, 0.92), 0.5 + 0.5 * math.sin(sim_time * 1.3))
        self.shell_outer.color = membrane_color
        self.shell_inner.color = vector(0.68, 1.0, 0.96)
        self.shell_outer.opacity = 0.035 + 0.13 * self.closure if self.active else 0.0
        self.shell_inner.opacity = 0.025 + 0.08 * self.closure if self.active else 0.0
        self.arcset.update(self.center, self.radius, self.closure, self.spin_phase)
        self.label.pos = self.center + vector(0, self.radius + 0.65, 0)
        self.trail.append(pos=self.center)

    def update(self, dt, sim_time, lysosome, particles):
        if self.state == "idle":
            self.shell_outer.opacity = 0
            self.shell_inner.opacity = 0
            self.arcset.set_visible(False)
            self.label.visible = False
            return

        self.spin_phase += dt * (0.55 + self.closure * 0.4)
        self.label.visible = True

        if self.target is None or self.target.state == "recycled":
            self.detach_target()
            return

        if self.state == "growing":
            desired = self.target.pos + safe_norm(self.center - self.target.pos) * 0.35
            self.center = self.center + (desired - self.center) * dt * 1.6
            self.radius = lerp(self.radius, self.target_radius * 1.05, dt * 1.3)
            self.closure = lerp(self.closure, 0.42, dt * 0.9)
            if mag(self.center - self.target.pos) < 0.55 and abs(self.radius - self.target_radius) < 0.12:
                self.state = "wrapping"

        elif self.state == "wrapping":
            self.center = self.center + (self.target.pos - self.center) * dt * 3.5
            self.radius = lerp(self.radius, self.target_radius, dt * 2.5)
            self.closure += dt * 0.38
            if self.closure > 0.62:
                self.target.attach(self)
            if self.closure >= 1.0:
                self.closure = 1.0
                self.state = "closed"

        elif self.state == "closed":
            self.target.attach(self)
            self.state = "moving"

        elif self.state == "moving":
            self.target.attach(self)
            destination = lysosome.pos + safe_norm(self.center - lysosome.pos) * (lysosome.radius * 0.65)
            direction = destination - self.center
            self.vel += safe_norm(direction) * dt * 2.2
            self.vel *= 0.965
            if mag(direction) < 0.35:
                self.state = "fusing"
                self.fuse_timer = 0.0
            self.center += self.vel * dt

        elif self.state == "fusing":
            self.fuse_timer += dt
            self.center = self.center + (lysosome.pos - self.center) * dt * 1.0
            self.radius = lerp(self.radius, lysosome.radius * 0.85, dt * 1.2)
            self.closure = 1.0
            self.shell_outer.color = vector(0.85, 1.0, 0.75)
            if self.fuse_timer > 1.15:
                self.state = "dissolving"
                self.dissolve_spawn_timer = 0.0

        elif self.state == "dissolving":
            self.fuse_timer += dt
            self.center = self.center + (lysosome.pos - self.center) * dt * 1.25
            self.closure = clamp(self.closure - dt * 0.18, 0.35, 1.0)
            self.radius = lerp(self.radius, lysosome.radius * 0.35, dt * 0.45)
            self.dissolve_spawn_timer += dt

            if self.target is not None:
                self.target.pos = self.center
                self.target.dissolve_step(dt)

            if self.dissolve_spawn_timer > 0.055:
                self.dissolve_spawn_timer = 0.0
                for _ in range(2):
                    particles.append(RecycleParticle(
                        pos=self.center + rand_vec(randf(0.05, self.radius * 0.6)),
                        vel=rand_vec(randf(0.4, 1.3)) + safe_norm(lysosome.pos - self.center) * 0.45,
                        kind="recycle",
                    ))

            if self.target is None or self.target.state == "recycled":
                self.target = None
                self.state = "idle"
                self.closure = 0
                self.radius = 0.35
                self.shell_outer.opacity = 0
                self.shell_inner.opacity = 0
                self.arcset.set_visible(False)
                self.label.visible = False

        if self.active:
            if mag(self.center) + self.radius > CELL_RADIUS:
                n = safe_norm(self.center)
                self.center = n * (CELL_RADIUS - self.radius)
                self.vel = self.vel - 2 * dot(self.vel, n) * n
                self.vel *= 0.55
            self.update_visuals(sim_time)

    def destroy(self):
        self.shell_outer.visible = False
        self.shell_inner.visible = False
        self.arcset.destroy()
        self.trail.visible = False
        self.label.visible = False


class AIController:
    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.mode = "SURVEY"
        self.mode_timer = 0
        self.last_mode = None
        self.override_until = 0
        self.paused_by_human = False
        self.round_delay = 0
        self.last_signature_time = 0
        self.last_motion_signature = None
        self.stagnant_time = 0
        self.completion_time = None
        self.playfulness = 0.55
        self.carefulness = 0.55
        self.chaos = 0.22
        self.ritual_bias = 0.25
        self.art_bias = 0.25
        self.loop_rounds = True

    def human_override(self, seconds=3.0):
        self.override_until = self.sim.t + seconds

    def read_state(self):
        organelles = [o for o in self.sim.organelles if o.state != "recycled"]
        free = [o for o in organelles if o.state == "free"]
        marked = [o for o in organelles if o.state == "marked"]
        wrapped = [o for o in organelles if o.state == "wrapped"]
        dissolving = [o for o in organelles if o.state == "dissolving"]
        nearest_to_lyso = None
        if organelles:
            nearest_to_lyso = min(organelles, key=lambda o: mag(o.pos - self.sim.lysosome.pos))
        most_damaged = None
        candidates = free + marked
        if candidates:
            most_damaged = max(candidates, key=lambda o: o.damage + (0.25 if o.state == "marked" else 0) - 0.015 * mag(o.pos))
        state = {
            "time": self.sim.t,
            "round": self.sim.round_index,
            "autophagosome_state": self.sim.autophagosome.state,
            "free_count": len(free),
            "marked_count": len(marked),
            "wrapped_count": len(wrapped),
            "dissolving_count": len(dissolving),
            "active_organelle_count": len(organelles),
            "particle_count": len(self.sim.particles),
            "nearest_to_lyso": nearest_to_lyso,
            "most_damaged": most_damaged,
            "completion": len(organelles) == 0 and not self.sim.autophagosome.active,
            "stable_empty": len(organelles) == 0,
            "stagnant_time": self.stagnant_time,
        }
        return state

    def choose_mode(self, state):
        if state["completion"]:
            return "RESET_WAIT"

        shell_state = state["autophagosome_state"]

        if shell_state in ["moving"]:
            if random.random() < 0.2 + self.playfulness * 0.3:
                return "ORBIT"
            return "DELIVER"

        if shell_state in ["fusing", "dissolving"]:
            if random.random() < 0.35:
                return "SPILL"
            return "FUSE"

        if shell_state in ["growing", "wrapping", "closed"]:
            if random.random() < self.carefulness:
                return "CAREFUL_WRAP"
            return "RITUAL"

        if state["marked_count"] > 0:
            if random.random() < 0.75:
                return "CAREFUL_WRAP"
            return random.choice(["RITUAL", "ARTISTIC", "ORBIT"])

        if state["free_count"] > 0:
            r = random.random()
            if r < 0.55:
                return "MARK"
            if r < 0.70:
                return "SURVEY"
            if r < 0.82:
                return "ARTISTIC"
            if r < 0.92:
                return "RITUAL"
            return "CHAOS"

        return "RESET_WAIT"

    def detect_stagnation_or_completion(self, dt):
        if self.sim.t - self.last_signature_time < 1.0:
            return
        self.last_signature_time = self.sim.t

        signature = []
        for o in self.sim.organelles:
            if o.state != "recycled":
                signature.append((o.pos.x, o.pos.y, o.pos.z))
        signature.append((self.sim.autophagosome.center.x, self.sim.autophagosome.center.y, self.sim.autophagosome.center.z))
        signature.append((len(self.sim.particles), 0, 0))

        if self.last_motion_signature is None:
            self.last_motion_signature = signature
            return

        n = min(len(signature), len(self.last_motion_signature))
        movement = 0.0
        for i in range(n):
            a = vector(signature[i][0], signature[i][1], signature[i][2])
            b = vector(self.last_motion_signature[i][0], self.last_motion_signature[i][1], self.last_motion_signature[i][2])
            movement += mag(a - b)
        movement += abs(len(signature) - len(self.last_motion_signature))
        self.last_motion_signature = signature

        if movement < 0.22 and not self.sim.autophagosome.active:
            self.stagnant_time += 1.0
        elif movement < 0.08:
            self.stagnant_time += 0.4
        else:
            self.stagnant_time = max(0.0, self.stagnant_time - 0.8)

    def update(self, dt):
        self.detect_stagnation_or_completion(dt)
        if not self.enabled or self.sim.paused:
            return
        if self.sim.t < self.override_until:
            return

        state = self.read_state()

        if state["completion"]:
            if self.completion_time is None:
                self.completion_time = self.sim.t
            if self.loop_rounds and self.sim.t - self.completion_time > 4.0:
                self.mode = "RESET_WAIT"
                self.sim.reset_round()
                self.completion_time = None
            return
        else:
            self.completion_time = None

        if self.stagnant_time > 9.0:
            self.mode = "RESET_WAIT"
            self.sim.reset_round()
            self.stagnant_time = 0
            return

        self.mode_timer -= dt
        if self.mode_timer <= 0:
            new_mode = self.choose_mode(state)
            if new_mode == self.mode and random.random() < 0.45:
                alternatives = [m for m in AI_MODES if m != self.mode]
                if state["autophagosome_state"] == "idle":
                    alternatives = ["MARK", "SURVEY", "ARTISTIC", "RITUAL", "CHAOS"]
                new_mode = random.choice(alternatives)
            self.last_mode = self.mode
            self.mode = new_mode
            self.mode_timer = randf(1.6, 4.5)

        self.apply_mode(dt, state)

    def apply_mode(self, dt, state):
        sim = self.sim
        shell = sim.autophagosome
        lys = sim.lysosome

        if self.mode == "SURVEY":
            for o in sim.organelles:
                if o.state in ["free", "marked"]:
                    tangent = vector(-o.pos.y, o.pos.x, 0.2 * math.sin(sim.t + o.id))
                    o.nudge(safe_norm(tangent) * dt * 0.25)
            if state["most_damaged"] is not None and random.random() < dt * 0.5:
                state["most_damaged"].mark()

        elif self.mode == "MARK":
            target = state["most_damaged"]
            if target is not None:
                target.mark()
                # Pull a damage marker into attention with a visible nudge/orbit.
                tangent = cross(safe_norm(target.pos, vector(1, 0, 0)), vector(0, 1, 0))
                target.nudge(safe_norm(tangent, rand_vec(1)) * dt * 0.55)

        elif self.mode == "CAREFUL_WRAP":
            if not shell.active:
                target = None
                marked = [o for o in sim.organelles if o.state == "marked"]
                if marked:
                    target = max(marked, key=lambda o: o.damage)
                elif state["most_damaged"] is not None:
                    target = state["most_damaged"]
                    target.mark()
                if target is not None:
                    shell.start_wrap(target)
            elif shell.state in ["growing", "wrapping"]:
                if shell.target is not None:
                    # Keep surrounding cytoplasm calm near a forming autophagosome.
                    for o in sim.organelles:
                        if o is not shell.target and o.state in ["free", "marked"]:
                            away = o.pos - shell.center
                            if mag(away) < shell.radius + 1.0:
                                o.nudge(safe_norm(away) * dt * 0.8)

        elif self.mode == "DELIVER":
            if shell.active and shell.state in ["moving", "closed"]:
                to_lyso = lys.pos - shell.center
                shell.vel += safe_norm(to_lyso) * dt * 0.8
            for p in sim.particles:
                p.vel += safe_norm(lys.pos - p.pos) * dt * 0.08

        elif self.mode == "FUSE":
            if shell.active:
                # Hold fusion zone steady and brighten it by adding enzyme particles.
                if random.random() < dt * 2.0:
                    sim.particles.append(RecycleParticle(lys.pos + rand_vec(lys.radius * 0.8), rand_vec(0.4), "enzyme"))

        elif self.mode == "ORBIT":
            center = shell.center if shell.active else lys.pos
            for o in sim.organelles:
                if o.state in ["free", "marked"]:
                    r = o.pos - center
                    tangent = cross(vector(0, 1, 0), r)
                    if mag(tangent) < 0.05:
                        tangent = cross(vector(1, 0, 0), r)
                    o.nudge(safe_norm(tangent) * dt * (0.7 + self.playfulness))
            if shell.active:
                r = shell.center - lys.pos
                tangent = cross(vector(0, 1, 0), r)
                shell.vel += safe_norm(tangent, rand_vec(1)) * dt * 0.35

        elif self.mode == "RITUAL":
            # Organize damaged organelles in a loose ring, then wrap the brightest/marked one.
            active = [o for o in sim.organelles if o.state in ["free", "marked"]]
            n = max(1, len(active))
            ritual_center = vector(-1.2, 0.15, 0)
            for i, o in enumerate(active):
                a = TWO_PI * i / n + sim.t * 0.18
                desired = ritual_center + vector(math.cos(a) * 3.0, math.sin(a * 0.7) * 0.8, math.sin(a) * 3.0)
                o.nudge((desired - o.pos) * dt * 0.16)
                if i == 0 and random.random() < dt * 0.9:
                    o.mark()
            if not shell.active:
                marked = [o for o in active if o.state == "marked"]
                if marked and random.random() < dt * 1.3:
                    shell.start_wrap(max(marked, key=lambda o: o.damage))

        elif self.mode == "CHAOS":
            if random.random() < dt * 5.0:
                sim.chaos_impulse(intensity=0.75)
            if random.random() < dt * 0.35:
                sim.spill_particles(8)

        elif self.mode == "ARTISTIC":
            # Arrange particles and organelles into a spiral-like composition.
            active = [o for o in sim.organelles if o.state in ["free", "marked"]]
            for i, o in enumerate(active):
                a = 0.65 * i + sim.t * 0.35
                rad = 1.2 + 0.45 * i
                desired = vector(math.cos(a) * rad, math.sin(a * 0.7) * 1.3, math.sin(a) * rad)
                if mag(desired) < CELL_RADIUS - 1:
                    o.nudge((desired - o.pos) * dt * 0.12)
                if random.random() < dt * 0.25:
                    o.mark()
            for i, p in enumerate(sim.particles[:120]):
                a = sim.t * 0.7 + i * 0.31
                desired = lys.pos + vector(math.cos(a) * 1.6, math.sin(a * 1.3) * 0.6, math.sin(a) * 1.6)
                p.vel += (desired - p.pos) * dt * 0.08

        elif self.mode == "SPILL":
            if random.random() < dt * 3.0:
                sim.spill_particles(random.randint(2, 6))

        elif self.mode == "RESET_WAIT":
            if self.loop_rounds:
                sim.reset_round()


class Simulation:
    def __init__(self):
        self.t = 0
        self.round_index = 0
        self.paused = False
        self.show_help = True

        self.cell_shell = sphere(
            pos=vector(0, 0, 0),
            radius=CELL_RADIUS,
            color=vector(0.72, 0.92, 1.0),
            opacity=0.10,
            shininess=0.05,
        )
        self.cell_rings = [
            ring(pos=vector(0, 0, 0), axis=vector(1, 0, 0), radius=CELL_RADIUS, thickness=0.018,
                 color=vector(0.35, 0.65, 0.95), opacity=0.28),
            ring(pos=vector(0, 0, 0), axis=vector(0, 1, 0), radius=CELL_RADIUS, thickness=0.018,
                 color=vector(0.35, 0.65, 0.95), opacity=0.28),
            ring(pos=vector(0, 0, 0), axis=vector(0, 0, 1), radius=CELL_RADIUS, thickness=0.018,
                 color=vector(0.35, 0.65, 0.95), opacity=0.28),
        ]
        self.nucleus = sphere(
            pos=vector(-3.7, 1.2, -1.0),
            radius=1.55,
            color=vector(0.68, 0.78, 1.0),
            opacity=0.18,
            shininess=0.3,
        )
        self.nucleus_label = label(
            pos=self.nucleus.pos + vector(0, 1.85, 0),
            text="stationary nucleus",
            height=11,
            color=vector(0.25, 0.38, 0.72),
            box=False,
            opacity=0,
        )

        self.organelles = []
        self.particles = []
        self.lysosome = Lysosome()
        self.autophagosome = Autophagosome()
        self.ai = AIController(self)

        self.status = label(
            pos=vector(-7.9, 8.7, 0),
            text="",
            height=12,
            color=vector(0.1, 0.25, 0.36),
            align="left",
            box=True,
            border=8,
            opacity=0.16,
            background=vector(1, 1, 1),
        )
        self.help_label = label(
            pos=vector(2.2, 8.7, 0),
            text="",
            height=10,
            color=vector(0.12, 0.20, 0.28),
            align="left",
            box=True,
            border=7,
            opacity=0.12,
            background=vector(1, 1, 1),
        )

        self.reset_round(initial=True)

    def reset_round(self, initial=False):
        if not initial:
            self.round_index += 1

        for o in getattr(self, "organelles", []):
            o.destroy()
        for p in getattr(self, "particles", []):
            p.destroy()
        if hasattr(self, "autophagosome"):
            self.autophagosome.destroy()

        self.organelles = []
        self.particles = []

        count = random.randint(5, 8)
        for _ in range(count):
            self.organelles.append(DamagedOrganelle())

        self.autophagosome = Autophagosome()

        # Some new-round visual burst of recyclable fragments near the lysosome
        for _ in range(10):
            self.particles.append(RecycleParticle(
                self.lysosome.pos + rand_vec(randf(0.1, self.lysosome.radius)),
                rand_vec(randf(0.2, 0.8)),
                "enzyme",
            ))

        self.ai.last_motion_signature = None
        self.ai.stagnant_time = 0
        self.ai.completion_time = None
        self.ai.mode = random.choice(["SURVEY", "MARK", "RITUAL", "ARTISTIC"])
        self.ai.mode_timer = 1.0

    def active_organelles(self):
        return [o for o in self.organelles if o.state != "recycled"]

    def nearest_markable(self):
        candidates = [o for o in self.organelles if o.state in ["free", "marked"]]
        if not candidates:
            return None
        return min(candidates, key=lambda o: mag(o.pos - scene.center))

    def mark_one(self):
        candidates = [o for o in self.organelles if o.state in ["free", "marked"]]
        if not candidates:
            return
        target = max(candidates, key=lambda o: o.damage - 0.02 * mag(o.pos))
        target.mark()

    def start_manual_wrap(self):
        if self.autophagosome.active:
            return
        marked = [o for o in self.organelles if o.state == "marked"]
        target = None
        if marked:
            target = max(marked, key=lambda o: o.damage)
        else:
            target = self.nearest_markable()
            if target:
                target.mark()
        if target:
            self.autophagosome.start_wrap(target)

    def chaos_impulse(self, intensity=1.0):
        for o in self.organelles:
            if o.state in ["free", "marked"]:
                o.nudge(rand_vec(randf(0.25, 1.0) * intensity))
                if random.random() < 0.25:
                    o.mark()
        if self.autophagosome.active:
            self.autophagosome.vel += rand_vec(randf(0.15, 0.55) * intensity)

    def spill_particles(self, count=10):
        for _ in range(count):
            pos = self.lysosome.pos + rand_vec(randf(0.1, self.lysosome.radius * 0.9))
            vel = rand_vec(randf(0.7, 1.9))
            self.particles.append(RecycleParticle(pos, vel, random.choice(["recycle", "enzyme"])))

    def resolve_organelle_collisions(self):
        active = [o for o in self.organelles if o.state in ["free", "marked"]]
        for i in range(len(active)):
            a = active[i]
            for j in range(i + 1, len(active)):
                b = active[j]
                delta = b.pos - a.pos
                d = mag(delta)
                min_d = (a.radius + b.radius) * 0.86
                if 0.001 < d < min_d:
                    n = delta / d
                    overlap = min_d - d
                    a.pos -= n * overlap * 0.5
                    b.pos += n * overlap * 0.5
                    va = dot(a.vel, n)
                    vb = dot(b.vel, n)
                    a.vel += (vb - va) * n * 0.75
                    b.vel += (va - vb) * n * 0.75
                    if random.random() < 0.025:
                        a.mark()
                        b.mark()

    def update_particles(self, dt):
        for p in list(self.particles):
            p.update(dt, self.lysosome)
            if p.dead:
                p.destroy()
                self.particles.remove(p)

        # Soft particle limit
        if len(self.particles) > 220:
            excess = len(self.particles) - 220
            for p in self.particles[:excess]:
                p.destroy()
            self.particles = self.particles[excess:]

    def update_status(self):
        active = len(self.active_organelles())
        marked = len([o for o in self.organelles if o.state == "marked"])
        recycled = len([o for o in self.organelles if o.state == "recycled"])
        ai_state = "ON" if self.ai.enabled else "OFF"
        pause_state = "PAUSED" if self.paused else "RUNNING"
        override = "human override" if self.t < self.ai.override_until else "auto"

        self.status.text = (
            f"Autophagy simulation | round {self.round_index}\n"
            f"{pause_state} | AI {ai_state} | mode: {self.ai.mode} | {override}\n"
            f"organelles active: {active}  marked: {marked}  recycled: {recycled}  particles: {len(self.particles)}\n"
            f"autophagosome: {self.autophagosome.state}"
        )

        if self.show_help:
            self.help_label.visible = True
            self.help_label.text = (
                "Keyboard: SPACE pause | A AI | R reset | H help\n"
                "M mark | W wrap | D detach | C chaos | O orbit lysosome | S spill\n"
                "Arrows/Z/X manually move active autophagosome\n"
                "Visual process: damaged organelles flicker, get marked,\n"
                "double membrane wraps/closes, fuses with lysosome,\n"
                "contents dissolve into recyclable particles."
            )
        else:
            self.help_label.visible = False

    def update(self, dt):
        if self.paused:
            self.update_status()
            return

        self.t += dt
        self.cell_shell.opacity = 0.085 + 0.015 * math.sin(self.t * 0.45)
        self.cell_rings[0].axis = vector(1, 0.05 * math.sin(self.t * 0.2), 0.03 * math.cos(self.t * 0.3))
        self.cell_rings[1].axis = vector(0.03 * math.sin(self.t * 0.25), 1, 0.04 * math.cos(self.t * 0.2))
        self.cell_rings[2].axis = vector(0.04 * math.cos(self.t * 0.3), 0.05 * math.sin(self.t * 0.2), 1)

        self.lysosome.update(dt, self.t)

        for o in self.organelles:
            o.update(dt, self.t)

        self.resolve_organelle_collisions()
        self.autophagosome.update(dt, self.t, self.lysosome, self.particles)
        self.update_particles(dt)

        self.ai.update(dt)
        self.update_status()


sim = Simulation()


def on_keydown(evt):
    key = evt.key

    if key == " ":
        sim.paused = not sim.paused
        return

    if key in ["a", "A"]:
        sim.ai.enabled = not sim.ai.enabled
        return

    if key in ["r", "R"]:
        sim.reset_round()
        sim.ai.human_override(1.0)
        return

    if key in ["h", "H"]:
        sim.show_help = not sim.show_help
        return

    sim.ai.human_override(4.0)

    if key in ["m", "M"]:
        sim.mark_one()
    elif key in ["w", "W"]:
        sim.start_manual_wrap()
    elif key in ["d", "D"]:
        sim.autophagosome.detach_target()
    elif key in ["c", "C"]:
        sim.chaos_impulse(1.3)
    elif key in ["o", "O"]:
        sim.lysosome.mode_orbit = not sim.lysosome.mode_orbit
        sim.ai.mode = "ORBIT"
        sim.ai.mode_timer = 3.5
    elif key in ["s", "S"]:
        sim.spill_particles(18)
    elif key == "left":
        sim.autophagosome.force_move(vector(-0.35, 0, 0))
    elif key == "right":
        sim.autophagosome.force_move(vector(0.35, 0, 0))
    elif key == "up":
        sim.autophagosome.force_move(vector(0, 0.35, 0))
    elif key == "down":
        sim.autophagosome.force_move(vector(0, -0.35, 0))
    elif key in ["z", "Z"]:
        sim.autophagosome.force_move(vector(0, 0, 0.35))
    elif key in ["x", "X"]:
        sim.autophagosome.force_move(vector(0, 0, -0.35))


scene.bind("keydown", on_keydown)

# -----------------------------
# Main loop with CSV logging
# -----------------------------
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
            write_csv_snapshot(csv_elapsed_seconds, csv_frame)

    write_csv_snapshot(csv_elapsed_seconds, csv_frame)
    sim.status.text = f"CSV recording complete: {CSV_RUN_SECONDS:0.0f}s saved to {os.path.basename(CSV_OUTPUT_PATH)}"
finally:
    _csv_file.flush()
    _csv_file.close()
