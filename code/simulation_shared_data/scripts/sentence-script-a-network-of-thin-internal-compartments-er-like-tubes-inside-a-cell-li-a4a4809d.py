from vpython import *
import random as pyrandom
import math

# ============================================================
# Calcium Wave Signaling in a Cell - VPython simulation
# Updated: replaces VPython torus(...) with ring(...) for environments where torus is unavailable.
# Includes an automatic expressive AI controller + human control
# ============================================================

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="3D Calcium Wave Signaling in a Cell",
    width=1200,
    height=760,
    background=vector(0.96, 0.985, 1.0),
)
scene.range = 6.5
scene.forward = vector(-0.65, -0.28, -0.70)
scene.up = vector(0, 1, 0)
scene.autoscale = False

scene.caption = """
Controls:
  Space = pause/resume      I = toggle AI      R = reset round
  WASD = move cursor        Q/E = down/up      J = trigger calcium release
  K = spill free calcium    P = boost nearby pumps
  M = mark current site     1-7 = force AI behavior mode
Human movement temporarily overrides AI motion.
"""

pyrandom.seed(7)

# -----------------------------
# Constants
# -----------------------------
CELL_R = 4.25
NUCLEUS_R = 0.95
ER_TUBE_RADIUS = 0.055
PARTICLE_R = 0.043
MAX_PARTICLES = 260
MAX_MARKS = 280

CA_DIFFUSION = 0.78
CA_DECAY = 0.16
CA_MAX_VIS = 1.35

DT = 0.016
SIM_SPEED = 1.0

# -----------------------------
# Utility functions
# -----------------------------
def clamp(x, a, b):
    return max(a, min(b, x))

def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)

def safe_norm(v):
    m = mag(v)
    if m < 1e-9:
        return vector(1, 0, 0)
    return v / m

def mix(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return a * (1.0 - t) + b * t

def random_unit():
    z = pyrandom.uniform(-1.0, 1.0)
    th = pyrandom.uniform(0, 2 * math.pi)
    r = math.sqrt(max(0.0, 1.0 - z * z))
    return vector(r * math.cos(th), r * math.sin(th), z)

def random_inside_cell(radius=CELL_R * 0.88):
    while True:
        p = vector(
            pyrandom.uniform(-radius, radius),
            pyrandom.uniform(-radius, radius),
            pyrandom.uniform(-radius, radius),
        )
        if mag(p) < radius and mag(p) > NUCLEUS_R * 1.15:
            return p

def point_segment_closest(p, a, b):
    ab = b - a
    denom = dot(ab, ab)
    if denom < 1e-9:
        return a, 0.0
    t = clamp(dot(p - a, ab) / denom, 0.0, 1.0)
    return a + ab * t, t

def calcium_color(x):
    """
    Low calcium: pale cyan/blue.
    Medium: green/yellow.
    High: orange/white.
    """
    x = clamp(x, 0.0, 1.0)
    c0 = vector(0.25, 0.78, 1.00)
    c1 = vector(0.18, 1.00, 0.68)
    c2 = vector(1.00, 0.92, 0.15)
    c3 = vector(1.00, 0.42, 0.08)
    c4 = vector(1.00, 1.00, 0.92)

    if x < 0.33:
        return mix(c0, c1, x / 0.33)
    elif x < 0.66:
        return mix(c1, c2, (x - 0.33) / 0.33)
    elif x < 0.90:
        return mix(c2, c3, (x - 0.66) / 0.24)
    else:
        return mix(c3, c4, (x - 0.90) / 0.10)

def mode_color(mode):
    colors = {
        "SCOUT": vector(0.20, 0.75, 1.00),
        "SEED_WAVE": vector(1.00, 0.85, 0.10),
        "ORBIT": vector(0.70, 0.50, 1.00),
        "PUMP_SWEEP": vector(0.30, 1.00, 0.68),
        "CHAOS": vector(1.00, 0.35, 0.16),
        "ARTIST": vector(1.00, 0.38, 0.90),
        "CAREFUL": vector(0.55, 0.95, 1.00),
        "RESETTING": vector(0.80, 0.80, 0.80),
    }
    return colors.get(mode, vector(1, 1, 1))

# -----------------------------
# Visual marker
# -----------------------------
class FadingMarker:
    def __init__(self):
        self.obj = sphere(
            pos=vector(0, 0, 0),
            radius=0.045,
            color=vector(1, 1, 1),
            opacity=0.0,
            emissive=True,
            visible=False,
        )
        self.age = 0.0
        self.life = 1.0
        self.active = False

    def activate(self, pos, col, radius=0.045, life=6.0, opacity=0.55):
        self.obj.pos = pos
        self.obj.color = col
        self.obj.radius = radius
        self.obj.opacity = opacity
        self.obj.visible = True
        self.age = 0.0
        self.life = life
        self.active = True

    def update(self, dt):
        if not self.active:
            return
        self.age += dt
        f = 1.0 - self.age / self.life
        if f <= 0:
            self.active = False
            self.obj.visible = False
            return
        self.obj.opacity = 0.58 * f
        self.obj.radius *= (1.0 + 0.12 * dt)

# -----------------------------
# Pump object
# -----------------------------
class CalciumPump:
    def __init__(self, pos, axis, node_a, node_b):
        self.pos = pos
        self.axis = safe_norm(axis)
        self.node_a = node_a
        self.node_b = node_b
        self.absorb_radius = 0.30
        self.boost = 0.0
        self.glow = 0.0
        self.absorbed = 0

        self.body = ring(
            pos=self.pos,
            axis=self.axis,
            radius=0.105,
            thickness=0.018,
            color=vector(0.28, 0.50, 1.00),
            opacity=0.72,
        )
        self.core = sphere(
            pos=self.pos,
            radius=0.043,
            color=vector(0.40, 0.85, 1.00),
            opacity=0.75,
            emissive=True,
        )

    def update(self, dt):
        self.boost = max(0.0, self.boost - 0.65 * dt)
        self.glow = max(0.0, self.glow - 1.8 * dt)
        g = clamp(self.glow + 0.7 * self.boost, 0.0, 1.0)
        self.body.color = mix(vector(0.25, 0.45, 0.95), vector(1.00, 0.36, 0.90), g)
        self.core.color = mix(vector(0.38, 0.82, 1.00), vector(1.00, 0.94, 0.22), g)
        self.core.radius = 0.043 * (1.0 + 1.0 * g)
        self.absorb_radius = 0.30 + 0.28 * self.boost

# -----------------------------
# Calcium particle
# -----------------------------
class CalciumParticle:
    def __init__(self):
        self.obj = sphere(
            pos=vector(0, 0, 0),
            radius=PARTICLE_R,
            color=vector(1.0, 0.92, 0.10),
            opacity=0.0,
            emissive=True,
            visible=False,
        )
        self.active = False
        self.vel = vector(0, 0, 0)
        self.age = 0.0
        self.life = 7.0

    def activate(self, pos, vel, life=7.0):
        self.obj.pos = pos
        self.vel = vel
        self.age = 0.0
        self.life = life
        self.active = True
        self.obj.visible = True
        self.obj.opacity = 0.92
        self.obj.radius = PARTICLE_R * pyrandom.uniform(0.75, 1.35)
        self.obj.color = vector(1.0, pyrandom.uniform(0.72, 1.0), 0.08)

    def deactivate(self):
        self.active = False
        self.obj.visible = False
        self.obj.opacity = 0.0

    def update(self, sim, dt):
        if not self.active:
            return

        self.age += dt
        if self.age > self.life:
            self.deactivate()
            return

        # Pump attraction and absorption
        for pump in sim.pumps:
            dvec = pump.pos - self.obj.pos
            d = mag(dvec)
            if pump.boost > 0.02 and d < pump.absorb_radius * 2.2:
                self.vel += safe_norm(dvec) * (5.0 * pump.boost * dt)
            if d < pump.absorb_radius:
                pump.glow = 1.0
                pump.absorbed += 1
                sim.total_reabsorbed += 1
                self.deactivate()
                return

        # Mix with local flow from ER wavefront
        near_node = sim.nearest_node(self.obj.pos)
        if near_node is not None and sim.node_ca[near_node] > 0.15:
            self.vel += safe_norm(self.obj.pos - sim.nodes[near_node]) * sim.node_ca[near_node] * 0.55 * dt

        self.obj.pos += self.vel * dt

        # Soft drag
        self.vel *= (1.0 - 0.045 * dt)

        # Bounce at outer cell membrane
        r = mag(self.obj.pos)
        wall = CELL_R - self.obj.radius
        if r > wall:
            n = safe_norm(self.obj.pos)
            self.obj.pos = n * wall
            self.vel = self.vel - 2.0 * dot(self.vel, n) * n
            self.vel *= 0.86
            sim.boundary_flash = 1.0

        # Bounce/collide against ER-like tubes
        for edge_index, (i, j) in enumerate(sim.edges):
            a = sim.nodes[i]
            b = sim.nodes[j]
            closest, t = point_segment_closest(self.obj.pos, a, b)
            dvec = self.obj.pos - closest
            d = mag(dvec)
            threshold = ER_TUBE_RADIUS + self.obj.radius * 0.85
            if d < threshold:
                n = safe_norm(dvec)
                self.obj.pos = closest + n * threshold
                self.vel = self.vel - 2.0 * dot(self.vel, n) * n
                self.vel += random_unit() * 0.04
                self.vel *= 0.93
                sim.edge_collision_flash[edge_index] = 1.0
                break

        # Color/opacity indicates age and concentration mixing
        f = 1.0 - self.age / self.life
        local = 0.0
        nidx = sim.nearest_node(self.obj.pos)
        if nidx is not None:
            local = sim.node_ca[nidx] / CA_MAX_VIS
        self.obj.color = mix(vector(0.32, 0.82, 1.0), vector(1.0, 0.86, 0.08), clamp(0.45 + local, 0, 1))
        self.obj.opacity = clamp(0.18 + 0.80 * f, 0.05, 0.95)

# -----------------------------
# Expressive AI controller
# -----------------------------
class CalciumWaveAI:
    MODES = ["SCOUT", "SEED_WAVE", "ORBIT", "PUMP_SWEEP", "CHAOS", "ARTIST", "CAREFUL"]

    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.mode = "SCOUT"
        self.previous_mode = None
        self.mode_timer = 0.0
        self.mode_duration = 5.0
        self.override_timer = 0.0

        self.target = vector(0, 0, 0)
        self.target_node = 0
        self.target_edge = 0
        self.target_pump = 0

        self.release_timer = 0.0
        self.mark_timer = 0.0
        self.spill_timer = 0.0
        self.wrap_timer = 0.0

        self.sample_timer = 0.0
        self.history = []
        self.stagnant_timer = 0.0
        self.reset_timer = 0.0

        self.orbit_axis = safe_norm(vector(0.3, 1.0, 0.2))
        self.orbit_phase = 0.0

    def state(self):
        active = self.sim.active_particle_count()
        avg_ca = self.sim.average_calcium()
        max_ca = max(self.sim.node_ca) if self.sim.node_ca else 0.0
        min_node = min(range(len(self.sim.nodes)), key=lambda i: self.sim.node_ca[i])
        max_node = max(range(len(self.sim.nodes)), key=lambda i: self.sim.node_ca[i])
        return {
            "time": self.sim.t,
            "round_time": self.sim.round_time,
            "active_particles": active,
            "avg_ca": avg_ca,
            "max_ca": max_ca,
            "quietest_node": min_node,
            "hottest_node": max_node,
            "total_reabsorbed": self.sim.total_reabsorbed,
            "cursor": self.sim.cursor.pos,
        }

    def force_mode(self, mode):
        if mode in self.MODES or mode == "RESETTING":
            self.previous_mode = self.mode
            self.mode = mode
            self.mode_timer = 0.0
            self.mode_duration = pyrandom.uniform(4.0, 8.5)
            self.pick_new_targets()

    def choose_next_mode(self):
        s = self.state()
        options = list(self.MODES)

        if self.previous_mode in options and len(options) > 1:
            options.remove(self.previous_mode)

        # State-reactive weighting
        weighted = []
        for m in options:
            w = 1
            if s["active_particles"] < 15 and s["avg_ca"] < 0.10:
                if m in ["SEED_WAVE", "CHAOS", "ARTIST"]:
                    w += 4
            if s["active_particles"] > 130 or s["avg_ca"] > 0.45:
                if m in ["PUMP_SWEEP", "CAREFUL", "ORBIT"]:
                    w += 5
            if self.stagnant_timer > 2.0:
                if m in ["CHAOS", "ARTIST", "SEED_WAVE"]:
                    w += 6
            if self.sim.round_time > 35:
                if m in ["PUMP_SWEEP", "ORBIT"]:
                    w += 3
            weighted += [m] * w

        new_mode = pyrandom.choice(weighted)
        self.previous_mode = self.mode
        self.mode = new_mode
        self.mode_timer = 0.0
        self.mode_duration = pyrandom.uniform(4.0, 9.0)
        self.pick_new_targets()

    def pick_new_targets(self):
        s = self.state()
        if self.mode in ["SEED_WAVE", "CAREFUL"]:
            self.target_node = s["quietest_node"]
        elif self.mode == "PUMP_SWEEP" and self.sim.pumps:
            self.target_pump = pyrandom.randrange(len(self.sim.pumps))
        elif self.mode == "ARTIST":
            self.target_edge = pyrandom.randrange(len(self.sim.edges))
            a, b = self.sim.edges[self.target_edge]
            self.target_node = a
        else:
            self.target_node = pyrandom.randrange(len(self.sim.nodes))

        self.target = self.sim.nodes[self.target_node]

    def detect_stagnation_or_completion(self, dt):
        self.sample_timer += dt
        if self.sample_timer >= 0.75:
            self.sample_timer = 0.0
            s = self.state()
            self.history.append((self.sim.t, s["avg_ca"], s["active_particles"], s["max_ca"]))
            if len(self.history) > 12:
                self.history.pop(0)

            if len(self.history) >= 8:
                avg_vals = [h[1] for h in self.history]
                act_vals = [h[2] for h in self.history]
                max_vals = [h[3] for h in self.history]
                low_empty = max(act_vals) < 8 and max(avg_vals) < 0.055
                barely_changing = (max(avg_vals) - min(avg_vals) < 0.012 and
                                   max(act_vals) - min(act_vals) < 5 and
                                   max(max_vals) < 0.16)
                if low_empty or barely_changing:
                    self.stagnant_timer += 0.75
                else:
                    self.stagnant_timer = max(0.0, self.stagnant_timer - 1.0)

        complete = (
            self.sim.round_time > 62.0 or
            self.sim.total_reabsorbed > 520 or
            self.stagnant_timer > 8.5
        )

        if complete and self.mode != "RESETTING":
            self.force_mode("RESETTING")
            self.reset_timer = 2.4

    def update(self, dt):
        if not self.enabled:
            return

        self.detect_stagnation_or_completion(dt)

        if self.override_timer > 0.0:
            self.override_timer -= dt
            return

        self.mode_timer += dt
        self.release_timer -= dt
        self.mark_timer -= dt
        self.spill_timer -= dt
        self.wrap_timer -= dt

        if self.mode == "RESETTING":
            self.reset_timer -= dt
            self.sim.cursor.color = mode_color("RESETTING")
            self.sim.move_cursor_toward(vector(0, 0, 0), dt, speed=2.0)
            if self.reset_timer <= 0:
                self.sim.reset_round(auto_started=True)
                self.stagnant_timer = 0.0
                self.history.clear()
                self.force_mode("SEED_WAVE")
            return

        if self.mode_timer > self.mode_duration:
            self.choose_next_mode()

        if self.mode == "SCOUT":
            self.behavior_scout(dt)
        elif self.mode == "SEED_WAVE":
            self.behavior_seed_wave(dt)
        elif self.mode == "ORBIT":
            self.behavior_orbit(dt)
        elif self.mode == "PUMP_SWEEP":
            self.behavior_pump_sweep(dt)
        elif self.mode == "CHAOS":
            self.behavior_chaos(dt)
        elif self.mode == "ARTIST":
            self.behavior_artist(dt)
        elif self.mode == "CAREFUL":
            self.behavior_careful(dt)

        self.sim.cursor.color = mode_color(self.mode)
        self.sim.cursor_halo.color = mode_color(self.mode)

    def behavior_scout(self, dt):
        if mag(self.sim.cursor.pos - self.target) < 0.25 or self.mark_timer <= 0:
            self.target_node = pyrandom.randrange(len(self.sim.nodes))
            self.target = self.sim.nodes[self.target_node] + random_unit() * 0.20
            self.mark_timer = pyrandom.uniform(0.8, 1.4)
            self.sim.add_marker(self.target, mode_color("SCOUT"), radius=0.035, life=4.0, opacity=0.38)
        self.sim.move_cursor_toward(self.target, dt, speed=1.65)

    def behavior_seed_wave(self, dt):
        s = self.state()
        self.target_node = s["quietest_node"]
        self.target = self.sim.nodes[self.target_node]
        self.sim.move_cursor_toward(self.target, dt, speed=2.35)
        if mag(self.sim.cursor.pos - self.target) < 0.45 and self.release_timer <= 0:
            self.sim.trigger_release_at_node(self.target_node, strength=1.0, count=22, source="AI seed")
            self.sim.add_marker(self.target, mode_color("SEED_WAVE"), radius=0.08, life=6.5, opacity=0.70)
            self.release_timer = pyrandom.uniform(0.48, 0.82)

    def behavior_orbit(self, dt):
        self.orbit_phase += dt * 1.05
        rad = 2.85 + 0.33 * math.sin(self.orbit_phase * 1.7)
        z = 1.15 * math.sin(self.orbit_phase * 0.73)
        self.target = vector(rad * math.cos(self.orbit_phase), z, rad * math.sin(self.orbit_phase))
        self.sim.move_cursor_toward(self.target, dt, speed=2.55)

        if self.release_timer <= 0:
            n = self.sim.nearest_node(self.sim.cursor.pos)
            if n is not None:
                self.sim.trigger_release_at_node(n, strength=0.48, count=9, source="AI orbit")
            self.release_timer = pyrandom.uniform(1.0, 1.8)

        if self.mark_timer <= 0:
            self.sim.add_marker(self.sim.cursor.pos, mode_color("ORBIT"), radius=0.04, life=5.0, opacity=0.45)
            self.mark_timer = 0.26

    def behavior_pump_sweep(self, dt):
        if not self.sim.pumps:
            return
        pump = self.sim.pumps[self.target_pump % len(self.sim.pumps)]
        self.target = pump.pos
        self.sim.move_cursor_toward(self.target, dt, speed=2.9)

        if mag(self.sim.cursor.pos - pump.pos) < 0.35:
            pump.boost = 1.0
            pump.glow = max(pump.glow, 0.55)
            if self.mark_timer <= 0:
                self.sim.add_marker(pump.pos + random_unit() * 0.05, mode_color("PUMP_SWEEP"),
                                    radius=0.05, life=3.8, opacity=0.62)
                self.mark_timer = 0.18
            if self.mode_timer > 1.2:
                self.target_pump = (self.target_pump + pyrandom.randint(1, 3)) % len(self.sim.pumps)
                self.mode_timer = 0.0

    def behavior_chaos(self, dt):
        wobble = vector(
            math.sin(self.sim.t * 2.7),
            math.sin(self.sim.t * 3.1 + 1.2),
            math.cos(self.sim.t * 2.1),
        )
        if mag(self.sim.cursor.pos - self.target) < 0.5 or self.spill_timer <= 0:
            self.target = random_inside_cell(CELL_R * 0.86)
            self.spill_timer = pyrandom.uniform(0.32, 0.75)

        self.sim.move_cursor_toward(self.target + wobble * 0.18, dt, speed=3.7)

        if self.release_timer <= 0:
            if pyrandom.random() < 0.55:
                self.sim.spill_particles(self.sim.cursor.pos, count=pyrandom.randint(10, 20), intensity=1.2)
            else:
                n = self.sim.nearest_node(self.sim.cursor.pos)
                if n is not None:
                    self.sim.trigger_release_at_node(n, strength=0.75, count=16, source="AI chaos")
            self.release_timer = pyrandom.uniform(0.20, 0.45)

    def behavior_artist(self, dt):
        if not self.sim.edges:
            return
        i, j = self.sim.edges[self.target_edge % len(self.sim.edges)]
        a = self.sim.nodes[i]
        b = self.sim.nodes[j]
        edge = b - a
        phase = (self.mode_timer * 0.18) % 1.0
        center = a + edge * phase

        direction = safe_norm(edge)
        side = safe_norm(cross(direction, vector(0, 1, 0)))
        if mag(side) < 0.2:
            side = safe_norm(cross(direction, vector(1, 0, 0)))
        up2 = safe_norm(cross(direction, side))
        angle = self.mode_timer * 7.5
        wrap_pos = center + (math.cos(angle) * side + math.sin(angle) * up2) * 0.23

        self.sim.move_cursor_toward(wrap_pos, dt, speed=2.7)

        if self.wrap_timer <= 0:
            self.sim.add_marker(wrap_pos, mode_color("ARTIST"), radius=0.038, life=8.5, opacity=0.62)
            self.wrap_timer = 0.08

        if self.release_timer <= 0:
            node = i if phase < 0.5 else j
            self.sim.trigger_release_at_node(node, strength=0.32, count=5, source="AI artist")
            self.release_timer = 0.75

        if self.mode_timer > self.mode_duration * 0.75:
            self.target_edge = pyrandom.randrange(len(self.sim.edges))

    def behavior_careful(self, dt):
        s = self.state()
        self.target_node = s["quietest_node"]
        quiet = self.sim.nodes[self.target_node]
        offset = safe_norm(quiet) * 0.16
        self.sim.move_cursor_toward(quiet + offset, dt, speed=1.15)

        if s["active_particles"] < 75 and s["avg_ca"] < 0.32 and self.release_timer <= 0:
            self.sim.trigger_release_at_node(self.target_node, strength=0.36, count=7, source="AI careful")
            self.sim.add_marker(quiet, mode_color("CAREFUL"), radius=0.052, life=5.5, opacity=0.48)
            self.release_timer = pyrandom.uniform(1.8, 2.9)

# -----------------------------
# Main simulation
# -----------------------------
class CalciumWaveSimulation:
    def __init__(self):
        self.t = 0.0
        self.round_time = 0.0
        self.round_number = 0
        self.paused = False

        self.nodes = []
        self.edges = []
        self.edge_cylinders = []
        self.edge_collision_flash = []
        self.node_objs = []
        self.node_ca = []
        self.neighbor_edges = []
        self.pumps = []
        self.particles = []
        self.markers = []

        self.total_reabsorbed = 0
        self.total_released = 0
        self.boundary_flash = 0.0

        self.keys_down = set()

        self.build_static_scene()
        self.build_er_network()
        self.build_particles()
        self.build_markers()
        self.build_colorbar()
        self.build_graph()

        self.cursor = sphere(
            pos=self.nodes[0] if self.nodes else vector(0, 0, 0),
            radius=0.145,
            color=vector(0.2, 0.75, 1.0),
            opacity=0.9,
            emissive=True,
        )
        self.cursor_halo = ring(
            pos=self.cursor.pos,
            axis=vector(0, 1, 0),
            radius=0.24,
            thickness=0.010,
            color=vector(0.2, 0.75, 1.0),
            opacity=0.35,
        )

        self.mode_label = label(
            pos=vector(-5.4, 4.8, 0),
            text="",
            height=15,
            color=vector(0.10, 0.18, 0.28),
            box=False,
            opacity=0,
        )
        self.stats_label = label(
            pos=vector(-5.4, 4.45, 0),
            text="",
            height=11,
            color=vector(0.12, 0.18, 0.22),
            box=False,
            opacity=0,
        )

        self.ai = CalciumWaveAI(self)

        scene.bind("keydown", self.on_keydown)
        scene.bind("keyup", self.on_keyup)

        self.reset_round(auto_started=False)

    def build_static_scene(self):
        self.cell = sphere(
            pos=vector(0, 0, 0),
            radius=CELL_R,
            color=vector(0.62, 0.86, 1.0),
            opacity=0.085,
            shininess=0.35,
        )
        self.cell_shell = sphere(
            pos=vector(0, 0, 0),
            radius=CELL_R * 1.002,
            color=vector(0.45, 0.68, 0.95),
            opacity=0.045,
        )
        self.nucleus = sphere(
            pos=vector(0, 0, 0),
            radius=NUCLEUS_R,
            color=vector(0.72, 0.60, 1.0),
            opacity=0.16,
            shininess=0.3,
        )
        self.nucleus_label = label(
            pos=vector(0, -1.25, 0),
            text="nucleus",
            height=9,
            color=vector(0.42, 0.34, 0.62),
            box=False,
            opacity=0,
        )

    def build_er_network(self):
        self.nodes = []
        self.edges = []

        # Three irregular ER-like loops wrapping around the nucleus
        layer_specs = [
            (2.08, 1.55, -1.13, 0.0),
            (2.55, 1.85, 0.08, 0.46),
            (2.15, 1.46, 1.25, 0.91),
        ]
        ring_count = 9
        for layer, (rx, rz, y, phase) in enumerate(layer_specs):
            for k in range(ring_count):
                th = 2 * math.pi * k / ring_count + phase
                wob = 0.16 * math.sin(3 * th + layer)
                p = vector(
                    (rx + wob) * math.cos(th),
                    y + 0.25 * math.sin(2 * th + layer),
                    (rz + wob) * math.sin(th),
                )
                p += random_unit() * 0.075
                self.nodes.append(p)

        # Several branching interior ER tubules
        extra = [
            vector(-0.45, -1.75, 1.55),
            vector(0.68, -1.62, -1.65),
            vector(1.68, 0.55, 1.55),
            vector(-1.72, 0.72, -1.38),
            vector(0.35, 1.92, 0.95),
            vector(-0.88, 1.68, -1.35),
        ]
        for p in extra:
            self.nodes.append(p)

        def add_edge(a, b):
            if a == b:
                return
            e = tuple(sorted((a, b)))
            if e not in self.edges:
                self.edges.append(e)

        # Ring edges
        for layer in range(3):
            base = layer * ring_count
            for k in range(ring_count):
                add_edge(base + k, base + ((k + 1) % ring_count))

        # Vertical/cross links between rings
        for k in range(ring_count):
            add_edge(k, ring_count + ((k + 1) % ring_count))
            add_edge(ring_count + k, 2 * ring_count + ((k + 2) % ring_count))

        # Extra branches connect to nearest ring nodes and to each other
        for idx in range(3 * ring_count, len(self.nodes)):
            nearest = sorted(range(3 * ring_count), key=lambda i: mag(self.nodes[i] - self.nodes[idx]))[:2]
            for n in nearest:
                add_edge(idx, n)
        add_edge(27, 28)
        add_edge(29, 30)
        add_edge(31, 32)
        add_edge(27, 31)
        add_edge(28, 32)

        self.node_ca = [0.0 for _ in self.nodes]
        self.neighbor_edges = [[] for _ in self.nodes]

        for idx, (i, j) in enumerate(self.edges):
            a = self.nodes[i]
            b = self.nodes[j]
            cyl = cylinder(
                pos=a,
                axis=b - a,
                radius=ER_TUBE_RADIUS,
                color=vector(0.46, 0.82, 0.92),
                opacity=0.42,
                shininess=0.25,
            )
            self.edge_cylinders.append(cyl)
            self.edge_collision_flash.append(0.0)
            self.neighbor_edges[i].append((j, idx))
            self.neighbor_edges[j].append((i, idx))

        for p in self.nodes:
            s = sphere(
                pos=p,
                radius=0.075,
                color=vector(0.50, 0.95, 1.0),
                opacity=0.32,
                emissive=True,
            )
            self.node_objs.append(s)

        # Pumps attached to selected ER tubes
        pump_edges = list(range(0, len(self.edges), 4))
        pyrandom.shuffle(pump_edges)
        pump_edges = pump_edges[:13]
        for eidx in pump_edges:
            i, j = self.edges[eidx]
            a = self.nodes[i]
            b = self.nodes[j]
            f = pyrandom.uniform(0.25, 0.75)
            pos = a * (1.0 - f) + b * f
            self.pumps.append(CalciumPump(pos, b - a, i, j))

    def build_particles(self):
        for _ in range(MAX_PARTICLES):
            self.particles.append(CalciumParticle())

    def build_markers(self):
        for _ in range(MAX_MARKS):
            self.markers.append(FadingMarker())

    def build_colorbar(self):
        self.colorbar_boxes = []
        n = 18
        y0 = -2.15
        dy = 0.235
        for i in range(n):
            val = i / (n - 1)
            b = box(
                pos=vector(5.55, y0 + i * dy, 0),
                size=vector(0.18, dy * 0.88, 0.18),
                color=calcium_color(val),
                opacity=0.92,
                emissive=True,
            )
            self.colorbar_boxes.append(b)
        self.colorbar_marker = box(
            pos=vector(5.82, y0, 0),
            size=vector(0.28, 0.045, 0.20),
            color=vector(0.08, 0.08, 0.10),
            opacity=0.9,
        )
        self.colorbar_label = label(
            pos=vector(5.53, y0 + n * dy + 0.18, 0),
            text="local Ca²⁺",
            height=11,
            color=vector(0.10, 0.16, 0.22),
            box=False,
            opacity=0,
        )
        self.colorbar_low = label(
            pos=vector(5.98, y0 - 0.05, 0),
            text="low",
            height=8,
            color=vector(0.10, 0.16, 0.22),
            box=False,
            opacity=0,
        )
        self.colorbar_high = label(
            pos=vector(6.02, y0 + (n - 1) * dy, 0),
            text="high",
            height=8,
            color=vector(0.10, 0.16, 0.22),
            box=False,
            opacity=0,
        )

    def build_graph(self):
        self.g = graph(
            title="Calcium concentration over time",
            xtitle="time",
            ytitle="Ca²⁺ / particles",
            width=560,
            height=230,
            fast=False,
            background=color.white,
            foreground=vector(0.08, 0.12, 0.16),
        )
        self.ca_curve = gcurve(graph=self.g, color=vector(1.0, 0.56, 0.04), label="mean ER Ca²⁺")
        self.particle_curve = gcurve(graph=self.g, color=vector(0.05, 0.55, 1.0), label="free particles / 260")
        self.absorb_curve = gcurve(graph=self.g, color=vector(0.75, 0.20, 0.95), label="pump uptake / 520")
        self.graph_timer = 0.0

    def reset_round(self, auto_started=True):
        self.round_number += 1
        self.round_time = 0.0
        self.total_reabsorbed = 0
        self.total_released = 0
        self.boundary_flash = 0.0

        for i in range(len(self.node_ca)):
            self.node_ca[i] = 0.0

        for p in self.particles:
            p.deactivate()

        for pump in self.pumps:
            pump.boost = 0.0
            pump.glow = 0.0
            pump.absorbed = 0

        for m in self.markers:
            m.active = False
            m.obj.visible = False

        if self.nodes:
            start = pyrandom.randrange(len(self.nodes))
            self.cursor.pos = self.nodes[start] + random_unit() * 0.18
            self.cursor_halo.pos = self.cursor.pos
            if auto_started:
                self.trigger_release_at_node(start, strength=0.90, count=20, source="reset seed")
                self.add_marker(self.nodes[start], vector(1.0, 0.85, 0.10), radius=0.09, life=7.0, opacity=0.70)

        for idx in range(len(self.edge_collision_flash)):
            self.edge_collision_flash[idx] = 0.0

    def nearest_node(self, pos):
        if not self.nodes:
            return None
        best = 0
        best_d = 1e9
        for i, p in enumerate(self.nodes):
            d = mag2(pos - p)
            if d < best_d:
                best_d = d
                best = i
        return best

    def add_marker(self, pos, col, radius=0.045, life=6.0, opacity=0.55):
        inactive = None
        oldest = None
        oldest_age = -1
        for m in self.markers:
            if not m.active:
                inactive = m
                break
            if m.age > oldest_age:
                oldest_age = m.age
                oldest = m
        m = inactive if inactive is not None else oldest
        if m is not None:
            m.activate(pos, col, radius=radius, life=life, opacity=opacity)

    def active_particle_count(self):
        return sum(1 for p in self.particles if p.active)

    def average_calcium(self):
        if not self.node_ca:
            return 0.0
        return sum(self.node_ca) / len(self.node_ca)

    def spill_particles(self, pos, count=15, intensity=1.0):
        spawned = 0
        for p in self.particles:
            if not p.active:
                direction = random_unit()
                vel = direction * pyrandom.uniform(0.75, 2.35) * intensity
                p.activate(pos + direction * pyrandom.uniform(0.02, 0.20), vel, life=pyrandom.uniform(4.5, 8.5))
                spawned += 1
                self.total_released += 1
                if spawned >= count:
                    break

    def trigger_release_at_node(self, node_idx, strength=1.0, count=18, source="release"):
        if node_idx is None:
            return
        node_idx = int(clamp(node_idx, 0, len(self.nodes) - 1))
        p0 = self.nodes[node_idx]
        self.node_ca[node_idx] = clamp(self.node_ca[node_idx] + 0.75 * strength, 0.0, CA_MAX_VIS * 1.35)

        # Transfer into neighbors for traveling wave kickoff
        for nb, _ in self.neighbor_edges[node_idx]:
            self.node_ca[nb] = clamp(self.node_ca[nb] + 0.22 * strength, 0.0, CA_MAX_VIS)

        self.spill_particles(p0, count=count, intensity=1.0 + 0.3 * strength)

    def trigger_release_at_cursor(self, strength=0.8, count=16):
        n = self.nearest_node(self.cursor.pos)
        if n is not None:
            self.trigger_release_at_node(n, strength=strength, count=count, source="cursor")
            self.add_marker(self.nodes[n], vector(1.0, 0.82, 0.12), radius=0.075, life=5.5, opacity=0.65)

    def boost_nearby_pumps(self):
        for pump in self.pumps:
            if mag(pump.pos - self.cursor.pos) < 0.9:
                pump.boost = 1.0
                pump.glow = max(pump.glow, 0.8)
                self.add_marker(pump.pos, vector(1.0, 0.32, 0.90), radius=0.055, life=3.2, opacity=0.60)

    def move_cursor_toward(self, target, dt, speed=2.0):
        if mag(target) > CELL_R * 0.94:
            target = safe_norm(target) * CELL_R * 0.94
        self.cursor.pos = self.cursor.pos + (target - self.cursor.pos) * clamp(speed * dt, 0.0, 1.0)
        if mag(self.cursor.pos) > CELL_R * 0.94:
            self.cursor.pos = safe_norm(self.cursor.pos) * CELL_R * 0.94

    def update_cursor_halo(self, dt):
        self.cursor_halo.pos = self.cursor.pos
        self.cursor_halo.axis = safe_norm(vector(math.sin(self.t * 0.8), 1.0, math.cos(self.t * 0.8)))
        pulse = 0.5 + 0.5 * math.sin(self.t * 5.0)
        self.cursor_halo.radius = 0.22 + 0.045 * pulse
        self.cursor_halo.opacity = 0.25 + 0.14 * pulse

    def update_human_control(self, dt):
        if not self.keys_down:
            return

        move = vector(0, 0, 0)
        if "w" in self.keys_down:
            move += vector(0, 1, 0)
        if "s" in self.keys_down:
            move += vector(0, -1, 0)
        if "a" in self.keys_down:
            move += vector(-1, 0, 0)
        if "d" in self.keys_down:
            move += vector(1, 0, 0)
        if "q" in self.keys_down:
            move += vector(0, 0, -1)
        if "e" in self.keys_down:
            move += vector(0, 0, 1)

        if mag(move) > 0:
            self.cursor.pos += safe_norm(move) * 2.65 * dt
            if mag(self.cursor.pos) > CELL_R * 0.93:
                self.cursor.pos = safe_norm(self.cursor.pos) * CELL_R * 0.93
            self.ai.override_timer = 2.5

    def update_calcium_network(self, dt):
        old = list(self.node_ca)
        delta = [0.0 for _ in self.node_ca]

        for i, j in self.edges:
            flux = CA_DIFFUSION * (old[j] - old[i])
            delta[i] += flux
            delta[j] -= flux

        # Pump-mediated ER reuptake sinks local cytosolic signal at neighboring nodes
        pump_sink = [0.0 for _ in self.node_ca]
        for pump in self.pumps:
            sink = 0.10 + 0.40 * pump.boost + 0.25 * pump.glow
            pump_sink[pump.node_a] += sink
            pump_sink[pump.node_b] += sink

        for i in range(len(self.node_ca)):
            self.node_ca[i] += delta[i] * dt
            self.node_ca[i] -= (CA_DECAY + pump_sink[i]) * self.node_ca[i] * dt
            self.node_ca[i] = clamp(self.node_ca[i], 0.0, CA_MAX_VIS * 1.45)

        # Free particles passing near junctions contribute a tiny local concentration mark
        for p in self.particles:
            if not p.active:
                continue
            n = self.nearest_node(p.obj.pos)
            if n is not None:
                d = mag(p.obj.pos - self.nodes[n])
                if d < 0.42:
                    self.node_ca[n] = clamp(self.node_ca[n] + 0.012 * (1.0 - d / 0.42), 0.0, CA_MAX_VIS * 1.45)

    def update_visuals(self, dt):
        avg = self.average_calcium()
        self.boundary_flash = max(0.0, self.boundary_flash - 1.7 * dt)
        self.cell.opacity = 0.075 + 0.055 * self.boundary_flash + 0.035 * clamp(avg / CA_MAX_VIS, 0, 1)
        self.cell.color = mix(vector(0.62, 0.86, 1.0), vector(1.0, 0.78, 0.18), clamp(avg / CA_MAX_VIS, 0, 1) * 0.75)

        for idx, cyl in enumerate(self.edge_cylinders):
            i, j = self.edges[idx]
            ca = 0.5 * (self.node_ca[i] + self.node_ca[j])
            v = clamp(ca / CA_MAX_VIS, 0.0, 1.0)
            flash = self.edge_collision_flash[idx]
            self.edge_collision_flash[idx] = max(0.0, flash - 2.5 * dt)
            cyl.color = mix(calcium_color(v), vector(1.0, 1.0, 1.0), 0.45 * flash)
            cyl.opacity = 0.34 + 0.55 * smoothstep(v) + 0.10 * flash
            cyl.radius = ER_TUBE_RADIUS * (1.0 + 0.85 * smoothstep(v) + 0.45 * flash)

        for i, obj in enumerate(self.node_objs):
            v = clamp(self.node_ca[i] / CA_MAX_VIS, 0.0, 1.0)
            obj.color = calcium_color(v)
            obj.opacity = 0.25 + 0.65 * smoothstep(v)
            obj.radius = 0.070 + 0.095 * smoothstep(v)

        # Colorbar marker follows average calcium
        y0 = -2.15
        dy = 0.235
        n = len(self.colorbar_boxes)
        y = y0 + clamp(avg / CA_MAX_VIS, 0.0, 1.0) * (n - 1) * dy
        self.colorbar_marker.pos.y = y
        self.colorbar_marker.color = calcium_color(clamp(avg / CA_MAX_VIS, 0.0, 1.0))

        self.update_cursor_halo(dt)

        ai_status = "ON" if self.ai.enabled else "OFF"
        paused_status = " PAUSED" if self.paused else ""
        self.mode_label.text = f"AI {ai_status}: {self.ai.mode}   Round {self.round_number}{paused_status}"
        self.mode_label.color = mode_color(self.ai.mode)
        self.stats_label.text = (
            f"particles {self.active_particle_count():3d}/{MAX_PARTICLES}   "
            f"mean Ca²⁺ {avg:.3f}   "
            f"uptake {self.total_reabsorbed}"
        )

    def update_graph(self, dt):
        self.graph_timer += dt
        if self.graph_timer >= 0.18:
            self.graph_timer = 0.0
            self.ca_curve.plot(self.t, self.average_calcium())
            self.particle_curve.plot(self.t, self.active_particle_count() / MAX_PARTICLES)
            self.absorb_curve.plot(self.t, min(1.0, self.total_reabsorbed / 520.0))

    def on_keydown(self, evt):
        k = evt.key.lower()

        if k in ["w", "a", "s", "d", "q", "e"]:
            self.keys_down.add(k)
            self.ai.override_timer = 3.0
            return

        if k == " ":
            self.paused = not self.paused
        elif k == "i":
            self.ai.enabled = not self.ai.enabled
        elif k == "r":
            self.reset_round(auto_started=True)
            self.ai.history.clear()
            self.ai.stagnant_timer = 0.0
        elif k == "j":
            self.trigger_release_at_cursor(strength=1.0, count=24)
            self.ai.override_timer = 2.5
        elif k == "k":
            self.spill_particles(self.cursor.pos, count=28, intensity=1.35)
            self.add_marker(self.cursor.pos, vector(1.0, 0.45, 0.12), radius=0.10, life=4.5, opacity=0.68)
            self.ai.override_timer = 2.5
        elif k == "p":
            self.boost_nearby_pumps()
            self.ai.override_timer = 2.5
        elif k == "m":
            self.add_marker(self.cursor.pos, vector(0.95, 0.28, 1.0), radius=0.07, life=8.0, opacity=0.65)
            self.ai.override_timer = 2.0
        elif k in ["1", "2", "3", "4", "5", "6", "7"]:
            idx = int(k) - 1
            if 0 <= idx < len(self.ai.MODES):
                self.ai.enabled = True
                self.ai.force_mode(self.ai.MODES[idx])

    def on_keyup(self, evt):
        k = evt.key.lower()
        if k in self.keys_down:
            self.keys_down.remove(k)

    def step(self, dt):
        if self.paused:
            self.update_visuals(dt)
            return

        self.t += dt
        self.round_time += dt

        self.update_human_control(dt)
        self.ai.update(dt)

        self.update_calcium_network(dt)

        for pump in self.pumps:
            pump.update(dt)

        for p in self.particles:
            p.update(self, dt)

        for m in self.markers:
            m.update(dt)

        self.update_visuals(dt)
        self.update_graph(dt)

# -----------------------------
# Run
# -----------------------------
sim = CalciumWaveSimulation()

while True:
    rate(60)
    sim.step(DT * SIM_SPEED)
