from vpython import *
import random
import math
import time

# -----------------------------
# Soft capsule cell simulation
# VPython, self-contained
# -----------------------------

scene.title = "Mechanical Model of a Cell as a Soft Capsule — AI Controlled"
scene.width = 1180
scene.height = 760
scene.background = vector(0.94, 0.97, 1.0)
scene.forward = vector(-0.75, -0.55, -0.35)
scene.up = vector(0, 0, 1)
scene.range = 5.8
scene.center = vector(0, 0, 0.1)

# ---------- Utility ----------

def clamp(x, a, b):
    return max(a, min(b, x))

def safe_norm(v):
    m = mag(v)
    if m < 1e-9:
        return vector(1, 0, 0)
    return v / m

def rand_unit():
    z = random.uniform(-1, 1)
    t = random.uniform(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(t), r * math.sin(t), z)

def smoothstep(a, b, x):
    if x <= a:
        return 0
    if x >= b:
        return 1
    u = (x - a) / (b - a)
    return u * u * (3 - 2 * u)

def fibonacci_sphere(n):
    pts = []
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - (i / float(n - 1)) * 2
        radius = math.sqrt(max(0, 1 - y * y))
        theta = golden * i
        x = math.cos(theta) * radius
        z = math.sin(theta) * radius
        pts.append(vector(x, y, z))
    return pts

def channel_half_width(x):
    narrow = 0.78
    wide = 1.95
    core = 2.15
    mouth = 3.15
    ax = abs(x)
    if ax <= core:
        return narrow
    if ax >= mouth:
        return wide
    u = smoothstep(core, mouth, ax)
    return narrow * (1 - u) + wide * u

def channel_wall_force(pos, vel, bead_radius, stiffness=72.0, damping=5.2):
    """Square narrow channel collision force in y and z."""
    h = channel_half_width(pos.x)
    force = vector(0, 0, 0)

    py = abs(pos.y) + bead_radius - h
    if py > 0:
        s = 1 if pos.y >= 0 else -1
        n = vector(0, -s, 0)
        vn = dot(vel, n)
        force += n * (stiffness * py - damping * min(0, vn))

    pz = abs(pos.z) + bead_radius - h
    if pz > 0:
        s = 1 if pos.z >= 0 else -1
        n = vector(0, 0, -s)
        vn = dot(vel, n)
        force += n * (stiffness * pz - damping * min(0, vn))

    return force

# ---------- Stationary channel ----------

channel_color = vector(0.62, 0.75, 0.92)
channel_edge_color = vector(0.35, 0.48, 0.68)
h0 = 0.78
wall_t = 0.055
channel_len = 4.3

box(pos=vector(0, h0 + wall_t / 2, 0),
    size=vector(channel_len, wall_t, 2 * h0 + 2 * wall_t),
    color=channel_color, opacity=0.23)
box(pos=vector(0, -h0 - wall_t / 2, 0),
    size=vector(channel_len, wall_t, 2 * h0 + 2 * wall_t),
    color=channel_color, opacity=0.23)
box(pos=vector(0, 0, h0 + wall_t / 2),
    size=vector(channel_len, 2 * h0 + 2 * wall_t, wall_t),
    color=channel_color, opacity=0.23)
box(pos=vector(0, 0, -h0 - wall_t / 2),
    size=vector(channel_len, 2 * h0 + 2 * wall_t, wall_t),
    color=channel_color, opacity=0.23)

# mouth outlines / guide rings
for x in [-3.15, -2.15, 2.15, 3.15]:
    hh = channel_half_width(x)
    curve(pos=[vector(x, -hh, -hh), vector(x, hh, -hh), vector(x, hh, hh),
               vector(x, -hh, hh), vector(x, -hh, -hh)],
          radius=0.012, color=channel_edge_color)

axis_line = curve(pos=[vector(-5.6, 0, 0), vector(5.6, 0, 0)],
                  radius=0.006, color=vector(0.72, 0.75, 0.78))

label(pos=vector(0, -1.45, 1.25),
      text="stationary narrow channel", height=13,
      color=vector(0.25, 0.36, 0.55), box=False, opacity=0)

# ---------- Soft membrane capsule ----------

class SoftCapsuleCell:
    def __init__(self, n_beads=88, n_particles=28):
        self.n = n_beads
        self.np = n_particles
        self.R0 = 1.15
        self.bead_radius = 0.062
        self.particle_radius = 0.085

        self.base_dirs = fibonacci_sphere(self.n)
        self.edges = self.make_edges(k=6)
        self.edge_set = set((min(i, j), max(i, j)) for i, j, _ in self.edges)

        self.pos = []
        self.vel = []
        self.p_pos = []
        self.p_vel = []
        self.escaped = []

        self.beads = []
        self.particles = []
        self.springs = []
        self.attachments = []
        self.attachment_curves = []

        self.center_trail = None
        self.dynamic_marks = []
        self.mark_cooldown = 0

        self.pore_open = False
        self.pore_dir = vector(1, 0, 0)
        self.pore_timer = 0
        self.pore_ring = torus(pos=vector(0, 0, 0), axis=vector(1, 0, 0),
                               radius=0.18, thickness=0.024,
                               color=vector(1.0, 0.43, 0.22), opacity=0.9,
                               visible=False)

        self.radial_pulse_strength = 0
        self.mem_color = vector(0.45, 0.72, 1.0)
        self.mem_color2 = vector(0.22, 0.55, 0.92)
        self.attach_color = vector(1.0, 0.78, 0.18)
        self.mark_color = vector(1.0, 0.35, 0.72)

        self.reset(round_id=0)

    def make_edges(self, k=6):
        edges = {}
        for i in range(self.n):
            dists = []
            for j in range(self.n):
                if i == j:
                    continue
                d = mag(self.base_dirs[i] - self.base_dirs[j])
                dists.append((d, j))
            dists.sort()
            for _, j in dists[:k]:
                a, b = min(i, j), max(i, j)
                rest = self.R0 * mag(self.base_dirs[a] - self.base_dirs[b])
                edges[(a, b)] = rest
        return [(a, b, rest) for (a, b), rest in edges.items()]

    def reset(self, round_id=0):
        for obj in self.beads + self.particles + self.springs + self.attachment_curves + self.dynamic_marks:
            obj.visible = False
        if self.center_trail is not None:
            self.center_trail.visible = False

        self.pos = []
        self.vel = []
        self.p_pos = []
        self.p_vel = []
        self.escaped = []
        self.beads = []
        self.particles = []
        self.springs = []
        self.attachments = []
        self.attachment_curves = []
        self.dynamic_marks = []

        start_center = vector(-4.65, random.uniform(-0.04, 0.04), random.uniform(-0.04, 0.04))
        for d in self.base_dirs:
            jitter = rand_unit() * random.uniform(0, 0.035)
            p = start_center + d * self.R0 + jitter
            self.pos.append(p)
            self.vel.append(vector(0, 0, 0))
            self.beads.append(sphere(pos=p, radius=self.bead_radius,
                                     color=self.mem_color, opacity=0.88,
                                     shininess=0.35))

        for a, b, _ in self.edges:
            self.springs.append(curve(pos=[self.pos[a], self.pos[b]],
                                      radius=0.012,
                                      color=vector(0.36, 0.68, 0.96),
                                      opacity=0.34))

        for i in range(self.np):
            d = rand_unit()
            r = self.R0 * 0.68 * (random.random() ** (1 / 3))
            p = start_center + d * r
            self.p_pos.append(p)
            self.p_vel.append(rand_unit() * random.uniform(0.0, 0.16))
            self.escaped.append(False)
            c = vector(0.96, 0.58 + random.random() * 0.24, 0.22)
            self.particles.append(sphere(pos=p, radius=self.particle_radius,
                                         color=c, opacity=0.9,
                                         shininess=0.45,
                                         make_trail=False))

        self.center_trail = curve(pos=[start_center],
                                  radius=0.022,
                                  color=vector(0.22, 0.52, 0.95),
                                  opacity=0.55)

        self.pore_open = False
        self.pore_timer = 0
        self.pore_ring.visible = False
        self.radial_pulse_strength = 0

    def center(self):
        c = vector(0, 0, 0)
        for p in self.pos:
            c += p
        return c / self.n

    def average_radius(self):
        c = self.center()
        return sum(mag(p - c) for p in self.pos) / self.n

    def deformation(self):
        c = self.center()
        radii = [mag(p - c) for p in self.pos]
        avg = sum(radii) / len(radii)
        var = sum((r - avg) ** 2 for r in radii) / len(radii)
        return math.sqrt(var) / max(0.01, avg)

    def kinetic_energy_proxy(self):
        return sum(dot(v, v) for v in self.vel) / self.n

    def local_surface_radius(self, direction):
        c = self.center()
        d = safe_norm(direction)
        best = 0.15
        for p in self.pos:
            proj = dot(p - c, d)
            if proj > best:
                best = proj
        return best + self.bead_radius * 0.4

    def nearest_bead_index(self, point):
        best_i = 0
        best_d = 1e9
        for i, p in enumerate(self.pos):
            d = dot(p - point, p - point)
            if d < best_d:
                best_d = d
                best_i = i
        return best_i

    def front_bead_index(self):
        best_i = 0
        best_x = -1e9
        for i, p in enumerate(self.pos):
            if p.x > best_x:
                best_x = p.x
                best_i = i
        return best_i

    def top_contact_bead_index(self):
        best_i = 0
        best_score = -1e9
        for i, p in enumerate(self.pos):
            h = channel_half_width(p.x)
            score = abs(p.z) - h + 0.2 * p.x
            if score > best_score:
                best_score = score
                best_i = i
        return best_i

    def attach_bead_to_wall(self, idx=None, ttl=2.8):
        if idx is None:
            idx = self.top_contact_bead_index()
        p = self.pos[idx]
        h = channel_half_width(p.x)
        if abs(p.z) >= abs(p.y):
            anchor = vector(p.x, p.y, math.copysign(h - 0.02, p.z))
        else:
            anchor = vector(p.x, math.copysign(h - 0.02, p.y), p.z)
        c = curve(pos=[p, anchor], radius=0.018, color=self.attach_color, opacity=0.75)
        self.attachments.append({"idx": idx, "anchor": anchor, "ttl": ttl, "curve": c})
        self.attachment_curves.append(c)
        self.beads[idx].color = self.attach_color

    def detach_all(self):
        for a in self.attachments:
            a["curve"].visible = False
            self.beads[a["idx"]].color = self.mem_color
        self.attachments = []

    def open_pore(self, direction=None, duration=2.2):
        if direction is None:
            direction = vector(1, 0, 0)
        self.pore_dir = safe_norm(direction)
        self.pore_open = True
        self.pore_timer = duration
        self.pore_ring.visible = True

    def mark_scene(self, txt=False):
        if self.mark_cooldown > 0:
            return
        c = self.center()
        m = sphere(pos=c + vector(0, 0, -1.05),
                   radius=0.045,
                   color=self.mark_color,
                   opacity=0.68)
        self.dynamic_marks.append(m)
        if txt:
            lab = label(pos=c + vector(0, 0, 1.35),
                        text="marked deformation event",
                        height=10, box=False, opacity=0,
                        color=self.mark_color)
            self.dynamic_marks.append(lab)
        for _ in range(4):
            i = random.randrange(self.n)
            self.beads[i].color = self.mark_color
        self.mark_cooldown = 1.0

    def apply_swirl_to_membrane(self, axis=vector(1, 0, 0), strength=0.4, dt=0.01):
        c = self.center()
        ax = safe_norm(axis)
        for i in range(self.n):
            off = self.pos[i] - c
            tang = cross(ax, off)
            if mag(tang) > 1e-6:
                self.vel[i] += safe_norm(tang) * strength * dt

    def mix_internal_particles(self, axis=vector(1, 0, 0), strength=1.0, dt=0.01):
        c = self.center()
        ax = safe_norm(axis)
        for i in range(self.np):
            off = self.p_pos[i] - c
            tang = cross(ax, off)
            if mag(tang) > 1e-6:
                self.p_vel[i] += safe_norm(tang) * strength * dt
            self.p_vel[i] += rand_unit() * 0.05 * strength * dt

    def organize_particles(self, dt=0.01):
        """A constructive action: gently gathers escaped/internal particles toward the cell center line."""
        c = self.center()
        for i in range(self.np):
            target = vector(c.x, 0, 0)
            self.p_vel[i] += (target - self.p_pos[i]) * 0.16 * dt

    def step(self, dt, drive_acc=vector(0, 0, 0), probe_pos=None, probe_radius=0.16):
        c = self.center()
        avg_r = self.average_radius()

        forces = [vector(0, 0, 0) for _ in range(self.n)]

        # Global external drive: represents a flow field or AI/human pushing.
        for i in range(self.n):
            forces[i] += drive_acc

        # Stretch/compress springs between membrane beads.
        ks = 24.0
        kd = 1.25
        for a, b, rest in self.edges:
            d = self.pos[b] - self.pos[a]
            L = mag(d)
            if L < 1e-8:
                continue
            n = d / L
            rel = dot(self.vel[b] - self.vel[a], n)
            f = (ks * (L - rest) + kd * rel) * n
            forces[a] += f
            forces[b] -= f

        # Soft volume / radial relaxation.
        kr = 5.6
        kp = 6.2
        for i in range(self.n):
            off = self.pos[i] - c
            r = mag(off)
            d = safe_norm(off)
            forces[i] += d * (kr * (self.R0 - r))
            forces[i] += d * (kp * (self.R0 - avg_r))
            forces[i] += d * self.radial_pulse_strength

        self.radial_pulse_strength *= max(0, 1 - 4.5 * dt)

        # Bead-bead excluded volume.
        min_d = self.bead_radius * 1.85
        for i in range(self.n):
            for j in range(i + 1, self.n):
                if (i, j) in self.edge_set:
                    continue
                d = self.pos[j] - self.pos[i]
                L = mag(d)
                if 1e-8 < L < min_d:
                    n = d / L
                    f = n * (28.0 * (min_d - L))
                    forces[i] -= f
                    forces[j] += f

        # Channel collision forces.
        for i in range(self.n):
            forces[i] += channel_wall_force(self.pos[i], self.vel[i], self.bead_radius,
                                            stiffness=92.0, damping=7.0)

        # Temporary adhesion/attachment springs to channel walls.
        remaining = []
        for a in self.attachments:
            idx = a["idx"]
            anchor = a["anchor"]
            diff = anchor - self.pos[idx]
            forces[idx] += diff * 42.0 - self.vel[idx] * 2.2
            a["ttl"] -= dt
            a["curve"].modify(0, pos=self.pos[idx])
            a["curve"].modify(1, pos=anchor)
            if a["ttl"] > 0:
                remaining.append(a)
            else:
                a["curve"].visible = False
                self.beads[idx].color = self.mem_color
        self.attachments = remaining

        # Probe collision: an AI-controlled orbiter/dipper can push the membrane.
        if probe_pos is not None:
            min_probe = probe_radius + self.bead_radius
            for i in range(self.n):
                d = self.pos[i] - probe_pos
                L = mag(d)
                if 1e-8 < L < min_probe:
                    n = d / L
                    forces[i] += n * (75.0 * (min_probe - L))

        # Integrate membrane.
        drag = 0.70
        for i in range(self.n):
            self.vel[i] += forces[i] * dt
            self.vel[i] *= max(0, 1 - drag * dt)
            self.pos[i] += self.vel[i] * dt

        # Internal particles: collide, mix, shift, bounce, spill through pore.
        p_forces = [drive_acc * 0.22 + rand_unit() * 0.06 for _ in range(self.np)]

        # Particle-particle collisions.
        min_pp = self.particle_radius * 2.05
        for i in range(self.np):
            for j in range(i + 1, self.np):
                d = self.p_pos[j] - self.p_pos[i]
                L = mag(d)
                if 1e-8 < L < min_pp:
                    n = d / L
                    overlap = min_pp - L
                    impulse = n * overlap * 18.0
                    p_forces[i] -= impulse
                    p_forces[j] += impulse
                    rv = dot(self.p_vel[j] - self.p_vel[i], n)
                    if rv < 0:
                        self.p_vel[i] += n * rv * 0.25
                        self.p_vel[j] -= n * rv * 0.25

        # Particle collision with individual membrane beads transfers a little motion.
        for pi in range(self.np):
            for bi in range(0, self.n, 2):
                d = self.p_pos[pi] - self.pos[bi]
                L = mag(d)
                min_bp = self.particle_radius + self.bead_radius
                if 1e-8 < L < min_bp:
                    n = d / L
                    overlap = min_bp - L
                    p_forces[pi] += n * overlap * 42.0
                    self.vel[bi] -= n * overlap * 0.18

        c = self.center()
        for i in range(self.np):
            p = self.p_pos[i]
            off = p - c
            r = mag(off)
            d = safe_norm(off)
            local_r = self.local_surface_radius(d)

            pore_here = self.pore_open and dot(d, self.pore_dir) > 0.86

            if not self.escaped[i]:
                if pore_here and r > local_r * 0.63:
                    p_forces[i] += d * 8.0
                    if r > local_r + self.particle_radius * 0.5:
                        self.escaped[i] = True
                        self.particles[i].color = vector(1.0, 0.25, 0.18)
                        self.particles[i].make_trail = True
                        self.particles[i].retain = 35
                else:
                    max_inside = local_r - self.particle_radius
                    if r > max_inside:
                        penetration = r - max_inside
                        self.p_pos[i] -= d * penetration
                        vn = dot(self.p_vel[i], d)
                        if vn > 0:
                            self.p_vel[i] -= d * (1.55 * vn)
                        p_forces[i] -= d * penetration * 24.0
            else:
                # Escaped particles bounce on the stationary channel walls.
                p_forces[i] += channel_wall_force(p, self.p_vel[i], self.particle_radius,
                                                  stiffness=58.0, damping=3.5)
                # If they wander back into the capsule while pore is open, recapture.
                if self.pore_open and r < local_r * 0.72:
                    self.escaped[i] = False
                    self.particles[i].color = vector(0.96, 0.72, 0.24)
                    self.particles[i].make_trail = False

            self.p_vel[i] += p_forces[i] * dt
            self.p_vel[i] *= max(0, 1 - 0.45 * dt)
            self.p_pos[i] += self.p_vel[i] * dt

        # Pore timer and visual ring.
        if self.pore_open:
            self.pore_timer -= dt
            pore_center = c + self.pore_dir * (self.local_surface_radius(self.pore_dir) + 0.04)
            self.pore_ring.pos = pore_center
            self.pore_ring.axis = self.pore_dir
            if self.pore_timer <= 0:
                self.pore_open = False
                self.pore_ring.visible = False

        if self.mark_cooldown > 0:
            self.mark_cooldown -= dt

        self.update_visuals()

    def update_visuals(self):
        for i in range(self.n):
            self.beads[i].pos = self.pos[i]

        for k, (a, b, _) in enumerate(self.edges):
            self.springs[k].modify(0, pos=self.pos[a])
            self.springs[k].modify(1, pos=self.pos[b])

        for i in range(self.np):
            self.particles[i].pos = self.p_pos[i]

        if self.center_trail is not None:
            c = self.center()
            if len(self.center_trail._points) < 900:
                self.center_trail.append(pos=c)

    def escaped_count(self):
        return sum(1 for e in self.escaped if e)


# ---------- Expressive AI behavior system ----------

class ExpressiveAIController:
    """
    Rule-based/state-machine AI.
    Reads state:
      center x/y/z, velocity proxy, deformation, escaped particle count,
      kinetic energy, channel location, stagnation/completion flags.
    Takes actions:
      move/drive, rotate/swirl, attach/detach, collide via probe, dip probe,
      orbit/wrap, organize particles, mark events, spill particles via pore,
      pulse capsule, reset/loop rounds.
    """

    MODES = [
        "CAREFUL_PUSH",
        "PULSE",
        "ROTATE",
        "ATTACH_PULL",
        "MIX",
        "SPILL",
        "WRAP_ORBIT",
        "DIP_PROBE",
        "ORGANIZE",
        "MARK_ART",
        "CHAOS",
        "RELAX",
    ]

    def __init__(self, cell):
        self.cell = cell
        self.enabled = True
        self.mode = "CAREFUL_PUSH"
        self.mode_timer = 0
        self.next_switch = 5.0
        self.round_id = 1
        self.override_timer = 0
        self.last_center = cell.center()
        self.progress_samples = []
        self.stagnation_time = 0
        self.completion_hold = 0
        self.loop_pause = 0
        self.time = 0

        self.probe = sphere(pos=vector(-3.8, 1.7, 0.0),
                            radius=0.16,
                            color=vector(0.82, 0.42, 1.0),
                            opacity=0.9,
                            shininess=0.6,
                            make_trail=True,
                            retain=90)
        self.probe.visible = True
        self.probe_theta = 0
        self.probe_radius = 0.16
        self.wrap_trails = []
        self.current_wrap = curve(pos=[],
                                  radius=0.018,
                                  color=vector(0.72, 0.28, 1.0),
                                  opacity=0.45)
        self.wrap_trails.append(self.current_wrap)

        self.action_label = label(pos=vector(-5.25, -2.35, 2.25),
                                  text="",
                                  height=12,
                                  color=vector(0.18, 0.28, 0.38),
                                  box=False,
                                  opacity=0)

    def state(self):
        c = self.cell.center()
        return {
            "center": c,
            "x": c.x,
            "in_channel": abs(c.x) < 2.35,
            "near_mouth": 2.0 < abs(c.x) < 3.35,
            "deformation": self.cell.deformation(),
            "avg_radius": self.cell.average_radius(),
            "kinetic": self.cell.kinetic_energy_proxy(),
            "escaped": self.cell.escaped_count(),
            "pore_open": self.cell.pore_open,
            "attachments": len(self.cell.attachments),
        }

    def choose_mode(self, s, forced=False):
        if self.loop_pause > 0:
            self.mode = "RELAX"
            return

        if s["escaped"] >= max(4, self.cell.np // 3):
            choices = ["ORGANIZE", "MARK_ART", "CAREFUL_PUSH", "WRAP_ORBIT"]
        elif self.stagnation_time > 2.0:
            choices = ["PULSE", "CHAOS", "ATTACH_PULL", "DIP_PROBE", "ROTATE"]
        elif s["in_channel"] and s["deformation"] > 0.16:
            choices = ["CAREFUL_PUSH", "ROTATE", "MIX", "ATTACH_PULL", "WRAP_ORBIT"]
        elif s["x"] < -2.5:
            choices = ["CAREFUL_PUSH", "MIX", "WRAP_ORBIT", "MARK_ART"]
        elif s["x"] > 2.0:
            choices = ["SPILL", "MARK_ART", "ORGANIZE", "RELAX"]
        else:
            choices = self.MODES[:]

        # Avoid doing the same thing forever.
        if len(choices) > 1 and self.mode in choices:
            choices.remove(self.mode)

        self.mode = random.choice(choices)
        self.mode_timer = 0
        self.next_switch = random.uniform(4.0, 8.5)

        if self.mode == "WRAP_ORBIT":
            self.current_wrap = curve(pos=[], radius=0.018,
                                      color=vector(random.uniform(0.45, 0.95), 0.35, 1.0),
                                      opacity=0.42)
            self.wrap_trails.append(self.current_wrap)
        if self.mode == "ATTACH_PULL" and len(self.cell.attachments) == 0:
            self.cell.attach_bead_to_wall(ttl=random.uniform(1.3, 2.7))
        if self.mode == "SPILL":
            c = self.cell.center()
            self.cell.open_pore(direction=vector(1, 0.15 * math.sin(self.time), 0.1),
                                duration=random.uniform(1.4, 2.8))
        if self.mode == "MARK_ART":
            self.cell.mark_scene(txt=True)

    def stagnation_detector(self, dt, s):
        self.progress_samples.append((self.time, s["x"], s["kinetic"]))
        self.progress_samples = [(t, x, k) for (t, x, k) in self.progress_samples
                                 if self.time - t < 5.0]
        if len(self.progress_samples) > 5:
            old_t, old_x, old_k = self.progress_samples[0]
            dx = abs(s["x"] - old_x)
            avg_k = sum(k for _, _, k in self.progress_samples) / len(self.progress_samples)
            if dx < 0.055 and avg_k < 0.12 and self.time > 4.0:
                self.stagnation_time += dt
            else:
                self.stagnation_time = max(0, self.stagnation_time - dt * 0.7)

        complete = s["x"] > 5.05
        emptyish = s["escaped"] > self.cell.np * 0.65
        stable_after_exit = s["x"] > 3.7 and s["kinetic"] < 0.04 and s["deformation"] < 0.08

        if complete or emptyish or stable_after_exit:
            self.completion_hold += dt
        else:
            self.completion_hold = max(0, self.completion_hold - dt)

        halted = self.stagnation_time > 7.0
        done = self.completion_hold > 2.2
        return halted, done

    def reset_round(self):
        self.round_id += 1
        self.cell.reset(round_id=self.round_id)
        self.mode = "CAREFUL_PUSH"
        self.mode_timer = 0
        self.next_switch = 4.0
        self.stagnation_time = 0
        self.completion_hold = 0
        self.loop_pause = 1.0
        self.progress_samples = []
        self.probe_theta = random.uniform(0, 2 * math.pi)
        self.current_wrap = curve(pos=[], radius=0.018,
                                  color=vector(0.72, 0.28, 1.0),
                                  opacity=0.42)
        self.wrap_trails.append(self.current_wrap)
        if len(self.wrap_trails) > 7:
            old = self.wrap_trails.pop(0)
            old.visible = False

    def human_override(self, seconds=1.0):
        self.override_timer = max(self.override_timer, seconds)

    def update_probe(self, dt, s):
        c = s["center"]
        self.probe.visible = True

        if self.mode in ["WRAP_ORBIT", "MIX", "DIP_PROBE", "CHAOS", "MARK_ART"]:
            self.probe_theta += dt * (1.3 + 0.7 * math.sin(self.time * 0.7))
            orbit_r = 1.55
            if self.mode == "DIP_PROBE":
                orbit_r = 1.07 + 0.20 * math.sin(self.time * 4.5)
            if self.mode == "CHAOS":
                orbit_r = 1.2 + 0.45 * math.sin(self.time * 3.7)

            px = c.x + 0.35 * math.sin(self.time * 1.1)
            py = c.y + orbit_r * math.cos(self.probe_theta)
            pz = c.z + orbit_r * math.sin(self.probe_theta)
            self.probe.pos = vector(px, py, pz)

            if self.mode == "WRAP_ORBIT":
                self.current_wrap.append(pos=self.probe.pos)
            elif self.mode == "MARK_ART" and random.random() < 0.025:
                self.current_wrap.append(pos=self.probe.pos)

            return self.probe.pos

        # Park the probe visibly near the scene.
        target = c + vector(-0.7, 1.75, 0.9)
        self.probe.pos += (target - self.probe.pos) * clamp(3 * dt, 0, 1)
        return None

    def update(self, dt, manual_acc=vector(0, 0, 0), paused=False):
        if paused:
            self.action_label.text = "PAUSED   | space resume | i toggle AI | r reset"
            return vector(0, 0, 0), None

        self.time += dt
        self.mode_timer += dt
        if self.override_timer > 0:
            self.override_timer -= dt

        s = self.state()
        halted, done = self.stagnation_detector(dt, s)

        if self.loop_pause > 0:
            self.loop_pause -= dt

        if done or halted:
            self.reset_round()
            s = self.state()

        if self.enabled and self.mode_timer > self.next_switch:
            self.choose_mode(s)

        drive = vector(0, 0, 0)

        if self.enabled and self.override_timer <= 0:
            # Rule-based state machine actions.
            if self.mode == "CAREFUL_PUSH":
                h = channel_half_width(s["x"])
                center_correction = vector(0, -s["center"].y, -s["center"].z) * 0.9
                strength = 1.35
                if s["in_channel"] and s["deformation"] > 0.18:
                    strength = 0.72
                drive = vector(strength, 0, 0) + center_correction

            elif self.mode == "PULSE":
                drive = vector(0.75, 0, 0)
                self.cell.radial_pulse_strength += 0.35 * math.sin(self.time * 8.5) + 0.42
                self.cell.mix_internal_particles(axis=vector(1, 0, 0), strength=0.6, dt=dt)

            elif self.mode == "ROTATE":
                drive = vector(0.82, 0, 0)
                self.cell.apply_swirl_to_membrane(axis=vector(1, 0.15, 0.1),
                                                  strength=2.3, dt=dt)
                self.cell.mix_internal_particles(axis=vector(1, 0, 0),
                                                 strength=1.1, dt=dt)

            elif self.mode == "ATTACH_PULL":
                drive = vector(1.15, 0, 0)
                if len(self.cell.attachments) == 0 and random.random() < 0.018:
                    self.cell.attach_bead_to_wall(ttl=random.uniform(1.0, 2.0))
                if random.random() < 0.004:
                    self.cell.detach_all()

            elif self.mode == "MIX":
                drive = vector(0.65, 0, 0)
                self.cell.mix_internal_particles(axis=vector(1, 0.4, 0.2),
                                                 strength=2.2, dt=dt)
                self.cell.apply_swirl_to_membrane(axis=vector(1, 0, 0),
                                                  strength=0.8, dt=dt)

            elif self.mode == "SPILL":
                drive = vector(0.55, 0, 0)
                if not self.cell.pore_open and random.random() < 0.025:
                    self.cell.open_pore(direction=vector(1, random.uniform(-0.25, 0.25),
                                                         random.uniform(-0.25, 0.25)),
                                        duration=random.uniform(1.2, 2.4))
                self.cell.mix_internal_particles(axis=vector(0.2, 1, 0),
                                                 strength=1.0, dt=dt)

            elif self.mode == "WRAP_ORBIT":
                drive = vector(0.72, 0, 0)
                self.cell.apply_swirl_to_membrane(axis=vector(1, 0, 0.25),
                                                  strength=0.8, dt=dt)

            elif self.mode == "DIP_PROBE":
                drive = vector(0.55, 0, 0)
                self.cell.radial_pulse_strength += 0.12

            elif self.mode == "ORGANIZE":
                drive = vector(0.35, 0, 0)
                self.cell.organize_particles(dt=dt)
                if random.random() < 0.006:
                    self.cell.detach_all()

            elif self.mode == "MARK_ART":
                drive = vector(0.48, 0.08 * math.sin(self.time * 2.1),
                               0.08 * math.cos(self.time * 2.1))
                if random.random() < 0.018:
                    self.cell.mark_scene(txt=False)

            elif self.mode == "CHAOS":
                drive = vector(0.8 + random.uniform(-0.7, 1.0),
                               random.uniform(-0.85, 0.85),
                               random.uniform(-0.85, 0.85))
                self.cell.apply_swirl_to_membrane(axis=rand_unit(),
                                                  strength=3.3, dt=dt)
                self.cell.mix_internal_particles(axis=rand_unit(),
                                                 strength=2.0, dt=dt)
                if random.random() < 0.01:
                    self.cell.attach_bead_to_wall(ttl=random.uniform(0.5, 1.2))
                if random.random() < 0.006:
                    self.cell.open_pore(direction=rand_unit(), duration=1.0)

            elif self.mode == "RELAX":
                drive = vector(0.18, -s["center"].y * 0.3, -s["center"].z * 0.3)

        # Human keyboard acceleration can run simultaneously, or override briefly.
        drive += manual_acc

        probe_pos = self.update_probe(dt, s)

        ai_status = "AI ON" if self.enabled else "AI OFF"
        override = " | human override" if self.override_timer > 0 else ""
        self.action_label.text = (
            f"{ai_status} | mode: {self.mode}{override}\n"
            f"round {self.round_id} | x={s['x']:.2f} | deformation={s['deformation']:.2f} "
            f"| escaped={s['escaped']} | stuck={self.stagnation_time:.1f}\n"
            "keys: arrows/WASD push, i AI, space pause, r reset, p pore, t attach, d detach, m mark"
        )

        return drive, probe_pos


# ---------- Simulation wrapper and controls ----------

cell = SoftCapsuleCell(n_beads=88, n_particles=28)
ai = ExpressiveAIController(cell)

paused = False
manual_acc = vector(0, 0, 0)
manual_decay = 0.90

def keydown(evt):
    global paused, manual_acc

    k = evt.key

    if k in [" ", "space"]:
        paused = not paused

    elif k in ["i", "I"]:
        ai.enabled = not ai.enabled
        ai.human_override(0.5)

    elif k in ["r", "R"]:
        ai.reset_round()

    elif k in ["p", "P"]:
        d = safe_norm(vector(1, random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25)))
        cell.open_pore(direction=d, duration=3.0)
        ai.human_override(1.5)

    elif k in ["t", "T"]:
        cell.attach_bead_to_wall(ttl=3.0)
        ai.human_override(1.5)

    elif k in ["d", "D"]:
        cell.detach_all()
        ai.human_override(1.5)

    elif k in ["m", "M"]:
        cell.mark_scene(txt=True)
        ai.human_override(1.2)

    elif k in ["left", "a", "A"]:
        manual_acc += vector(-1.4, 0, 0)
        ai.human_override(1.0)

    elif k in ["right", "e", "E"]:
        manual_acc += vector(1.7, 0, 0)
        ai.human_override(1.0)

    elif k in ["up", "w", "W"]:
        manual_acc += vector(0, 0, 1.25)
        ai.human_override(1.0)

    elif k in ["down", "s", "S"]:
        manual_acc += vector(0, 0, -1.25)
        ai.human_override(1.0)

    elif k in ["q", "Q"]:
        manual_acc += vector(0, -1.25, 0)
        ai.human_override(1.0)

    elif k in ["z", "Z"]:
        manual_acc += vector(0, 1.25, 0)
        ai.human_override(1.0)

    elif k in ["c", "C"]:
        ai.choose_mode(ai.state(), forced=True)
        ai.human_override(0.4)

scene.bind("keydown", keydown)

# Small legend objects
legend_bg = box(pos=vector(-5.35, 2.25, -1.35),
                size=vector(0.05, 0.05, 0.05),
                color=vector(1, 1, 1),
                opacity=0)

label(pos=vector(-4.95, 2.1, -1.25),
      text="blue beads: elastic membrane\norange particles: shifting interior\npurple orb: AI probe / wrapper\nred particles: spilled through pore",
      height=10,
      color=vector(0.25, 0.32, 0.42),
      box=False,
      opacity=0)

# ---------- Main loop ----------

last = time.time()
dt = 1 / 120
substeps = 2

while True:
    rate(60)

    now = time.time()
    frame_dt = clamp(now - last, 0.001, 0.05)
    last = now

    manual_acc *= manual_decay

    drive, probe_pos = ai.update(frame_dt, manual_acc=manual_acc, paused=paused)

    if not paused:
        small_dt = frame_dt / substeps
        for _ in range(substeps):
            cell.step(small_dt,
                      drive_acc=drive,
                      probe_pos=probe_pos,
                      probe_radius=ai.probe_radius)

    # Gentle camera tracking.
    c = cell.center()
    scene.center = scene.center * 0.96 + vector(clamp(c.x, -2.2, 2.6), 0, 0.15) * 0.04
