"""
Geometry Spider v3 - Spatial Explorer
A VPython simulation of a spider that plays with geometry.

This version keeps the smooth polygon behavior from v2 and increases spatial exploration:
- the spider chooses frontier goals across the full plane instead of lingering near the center
- recent visited regions are tracked so repeated local loops are discouraged
- web-heavy areas gently repel the spider, pushing it toward open space
- boundary contact turns into wide inward arcs instead of wall-following
- polygon centers are more widely distributed while still avoiding clutter

Scene:
- A spider lives at the center of a light plane.
- It spins geometric web pieces: triangles, squares, pentagons, hexagons, spirals, and radial spokes.
- Each new thread changes a visible stability score.
- The spider tries to build a mathematical web with symmetry and few collisions.

Controls:
- W/A/S/D : move spider on the plane
- Space   : spin one geometry piece now
- M       : switch autonomous mode
- R       : reset web
- P       : pause/resume
- C       : clear text/event trail
- H       : show/hide controls
- Arrow keys : pan camera target
- J/L     : rotate camera left/right
- I/K     : rotate camera up/down
- + / -   : zoom camera

Run:
    python geometry_spider_v3_spatial_explorer.py
"""

from vpython import *
import random
import math
import time

# -----------------------------
# Scene setup
# -----------------------------
scene.title = "Geometry Spider v3 - spatial explorer organism"
scene.width = 1200
scene.height = 760
scene.background = vector(0.94, 0.97, 1.0)
scene.forward = vector(-0.45, -0.45, -0.78)
scene.center = vector(0, 0, 0)
scene.range = 18

WORLD_LIMIT = 14.0
SPIDER_Z = 0.35
THREAD_Z = 0.07
DT = 1.0 / 60.0

# Soft colors
COLOR_PLANE = vector(0.86, 0.90, 0.86)
COLOR_GRID = vector(0.73, 0.78, 0.74)
COLOR_THREAD = vector(0.25, 0.34, 0.42)
COLOR_THREAD_NEW = vector(0.1, 0.45, 0.75)
COLOR_BAD = vector(0.9, 0.35, 0.25)
COLOR_GOOD = vector(0.2, 0.65, 0.42)
COLOR_SPIDER = vector(0.12, 0.13, 0.16)
COLOR_LEG = vector(0.18, 0.18, 0.20)
COLOR_GLOW = vector(0.45, 0.72, 1.0)

# Floor
floor = box(pos=vector(0, 0, -0.04), size=vector(WORLD_LIMIT * 2.2, WORLD_LIMIT * 2.2, 0.05), color=COLOR_PLANE)

# Grid lines
for i in range(-int(WORLD_LIMIT), int(WORLD_LIMIT) + 1):
    curve(pos=[vector(i, -WORLD_LIMIT, 0.0), vector(i, WORLD_LIMIT, 0.0)], color=COLOR_GRID, radius=0.008)
    curve(pos=[vector(-WORLD_LIMIT, i, 0.0), vector(WORLD_LIMIT, i, 0.0)], color=COLOR_GRID, radius=0.008)

# Boundary ring made from four lines
boundary_lines = [
    curve(pos=[vector(-WORLD_LIMIT, -WORLD_LIMIT, 0.03), vector(WORLD_LIMIT, -WORLD_LIMIT, 0.03)], color=vector(0.55, 0.60, 0.58), radius=0.025),
    curve(pos=[vector(WORLD_LIMIT, -WORLD_LIMIT, 0.03), vector(WORLD_LIMIT, WORLD_LIMIT, 0.03)], color=vector(0.55, 0.60, 0.58), radius=0.025),
    curve(pos=[vector(WORLD_LIMIT, WORLD_LIMIT, 0.03), vector(-WORLD_LIMIT, WORLD_LIMIT, 0.03)], color=vector(0.55, 0.60, 0.58), radius=0.025),
    curve(pos=[vector(-WORLD_LIMIT, WORLD_LIMIT, 0.03), vector(-WORLD_LIMIT, -WORLD_LIMIT, 0.03)], color=vector(0.55, 0.60, 0.58), radius=0.025),
]

# -----------------------------
# Utility math
# -----------------------------
def clamp(value, low, high):
    return max(low, min(high, value))


def mag2(v):
    return v.x * v.x + v.y * v.y + v.z * v.z


def flat(v):
    return vector(v.x, v.y, 0)


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-6:
        return fallback
    return norm(v)


def rotate_xy(v, angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return vector(v.x * c - v.y * s, v.x * s + v.y * c, v.z)


def lerp_vec(a, b, t):
    return a * (1 - t) + b * t


def dist_point_segment_2d(p, a, b):
    ap = flat(p - a)
    ab = flat(b - a)
    denom = mag2(ab)
    if denom < 1e-8:
        return mag(ap)
    t = clamp((ap.x * ab.x + ap.y * ab.y) / denom, 0, 1)
    closest = flat(a) + ab * t
    return mag(flat(p) - closest)


def ccw(a, b, c):
    return (c.y - a.y) * (b.x - a.x) > (b.y - a.y) * (c.x - a.x)


def segments_intersect_2d(a, b, c, d):
    # Ignore nearly shared endpoints so connected web pieces do not count as collisions.
    if mag(flat(a - c)) < 0.18 or mag(flat(a - d)) < 0.18 or mag(flat(b - c)) < 0.18 or mag(flat(b - d)) < 0.18:
        return False
    return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)


def point_on_circle(center, radius, angle, z=THREAD_Z):
    return vector(center.x + radius * math.cos(angle), center.y + radius * math.sin(angle), z)


def cell_key(pos, size=3.0):
    return (int(math.floor((pos.x + WORLD_LIMIT) / size)), int(math.floor((pos.y + WORLD_LIMIT) / size)))


def inside_safe_world(pos, margin=1.4):
    return -WORLD_LIMIT + margin <= pos.x <= WORLD_LIMIT - margin and -WORLD_LIMIT + margin <= pos.y <= WORLD_LIMIT - margin

# -----------------------------
# State containers
# -----------------------------
class WebSegment:
    def __init__(self, a, b, color=COLOR_THREAD, radius=0.025, label_text=""):
        self.a = vector(a.x, a.y, THREAD_Z)
        self.b = vector(b.x, b.y, THREAD_Z)
        self.obj = curve(pos=[self.a, self.b], color=color, radius=radius)
        self.age = 0.0
        self.good = True
        self.label_text = label_text

    def set_color(self, c):
        self.obj.color = c

    def fade_toward_old(self):
        self.age += DT
        if self.age > 1.5 and self.good:
            t = clamp((self.age - 1.5) / 4.0, 0, 1)
            self.obj.color = lerp_vec(COLOR_THREAD_NEW, COLOR_THREAD, t)

    def hide(self):
        self.obj.visible = False


class FloatingNote:
    def __init__(self, text, pos, color=vector(0.1, 0.25, 0.35)):
        self.age = 0.0
        self.obj = label(pos=pos, text=text, height=11, box=False, opacity=0, color=color)

    def update(self):
        self.age += DT
        self.obj.pos.z += 0.012
        if self.age > 2.3:
            self.obj.visible = False
            return False
        return True


class GeometrySpider:
    def __init__(self):
        self.pos = vector(0, 0, SPIDER_Z)
        self.vel = vector(0, 0, 0)
        self.heading = random.uniform(0, math.tau)
        self.mode = "wander"
        self.paused = False
        self.show_controls = True
        self.spin_timer = 0.8
        self.symmetry_order = 6
        self.web_segments = []
        self.notes = []
        self.event_log = []
        self.stability = 50.0
        self.collisions = 0
        self.pieces_built = 0
        self.last_shape = "none"
        self.polygon_centers = []
        self.polygon_cooldown = 1.0
        self.last_polygon_sides = 6
        self.clean_polygon_mode = True
        self.goal = vector(0, 0, SPIDER_Z)
        self.goal_timer = 0.0
        self.goal_kind = "center birth"
        self.autonomous_spin = True

        # Spatial exploration memory. The spider marks broad grid cells as visited
        # and gives priority to unvisited/open regions when choosing new goals.
        self.visited_cells = set()
        self.visit_trail = []
        self.recent_positions = []
        self.last_explore_choice = vector(0, 0, SPIDER_Z)
        self.explore_impulse_timer = 0.0
        self.edge_escape_timer = 0.0
        self.local_loop_timer = 0.0
        self.frontier_goal_interval = 0.0
        self.controls = {
            "w": False, "a": False, "s": False, "d": False,
            "left": False, "right": False, "up": False, "down": False,
            "j": False, "l": False, "i": False, "k": False,
            "+": False, "-": False, "=": False,
        }

        # Body parts
        self.body = sphere(pos=self.pos, radius=0.45, color=COLOR_SPIDER, shininess=0.25)
        self.head = sphere(pos=self.pos + vector(0.42, 0, 0.08), radius=0.27, color=vector(0.08, 0.09, 0.11), shininess=0.2)
        self.glow = sphere(pos=self.pos + vector(0, 0, -0.02), radius=0.62, color=COLOR_GLOW, opacity=0.18)
        self.legs = []
        for side in [-1, 1]:
            for k in range(4):
                offset = -0.32 + k * 0.22
                leg = curve(pos=[self.pos, self.pos + vector(offset, side * 0.9, -0.05)], color=COLOR_LEG, radius=0.035)
                self.legs.append((side, offset, leg))

        self.status = label(pos=vector(-15.3, 15.2, 0.5), text="", align="left", height=13, box=False, opacity=0, color=vector(0.05, 0.09, 0.12))
        self.help_label = label(pos=vector(0, -16.2, 0.6), text="", height=11, box=False, opacity=0, color=vector(0.08, 0.12, 0.16))
        self.goal_marker = sphere(pos=self.goal, radius=0.18, color=vector(1.0, 0.75, 0.1), emissive=True, opacity=0.75)

    # -----------------------------
    # Input
    # -----------------------------
    def keydown(self, evt):
        key = evt.key.lower()
        if key in self.controls:
            self.controls[key] = True
        elif key == " ":
            self.spin_geometry(force=True)
        elif key == "m":
            self.cycle_mode()
        elif key == "r":
            self.reset_web()
        elif key == "p":
            self.paused = not self.paused
        elif key == "c":
            self.clear_notes()
        elif key == "h":
            self.show_controls = not self.show_controls

    def keyup(self, evt):
        key = evt.key.lower()
        if key in self.controls:
            self.controls[key] = False

    def cycle_mode(self):
        modes = ["wander", "symmetry", "polygon", "spiral", "repair"]
        idx = modes.index(self.mode) if self.mode in modes else 0
        self.mode = modes[(idx + 1) % len(modes)]
        self.add_note("mode: " + self.mode, self.pos + vector(0, 0, 1.0), vector(0.1, 0.25, 0.7))

    # -----------------------------
    # Web construction
    # -----------------------------
    def add_note(self, text, pos, color=vector(0.1, 0.25, 0.35)):
        self.notes.append(FloatingNote(text, pos, color))
        self.event_log.append(text)
        self.event_log = self.event_log[-5:]

    def clear_notes(self):
        for n in self.notes:
            n.obj.visible = False
        self.notes = []
        self.event_log = []

    def reset_web(self):
        for seg in self.web_segments:
            seg.hide()
        self.web_segments = []
        self.clear_notes()
        self.stability = 50.0
        self.collisions = 0
        self.pieces_built = 0
        self.last_shape = "none"
        self.polygon_centers = []
        self.polygon_cooldown = 1.0
        self.last_polygon_sides = 6
        self.visited_cells = set()
        self.visit_trail = []
        self.recent_positions = []
        self.goal_kind = "reset frontier"
        self.choose_frontier_goal(force_far=True)
        self.add_note("web reset", vector(0, 0, 1.0), vector(0.1, 0.35, 0.55))

    def score_segment(self, a, b):
        crossings = 0
        for seg in self.web_segments:
            if segments_intersect_2d(a, b, seg.a, seg.b):
                crossings += 1
        length = mag(flat(b - a))
        center_pull = max(0, 1.0 - mag(flat((a + b) * 0.5)) / WORLD_LIMIT)
        length_bonus = 0.8 if 1.0 < length < 7.0 else -0.5
        return crossings, center_pull + length_bonus

    def add_segment(self, a, b, label_text=""):
        a = vector(clamp(a.x, -WORLD_LIMIT + 0.5, WORLD_LIMIT - 0.5), clamp(a.y, -WORLD_LIMIT + 0.5, WORLD_LIMIT - 0.5), THREAD_Z)
        b = vector(clamp(b.x, -WORLD_LIMIT + 0.5, WORLD_LIMIT - 0.5), clamp(b.y, -WORLD_LIMIT + 0.5, WORLD_LIMIT - 0.5), THREAD_Z)
        crossings, bonus = self.score_segment(a, b)
        color = COLOR_THREAD_NEW if crossings == 0 else COLOR_BAD
        seg = WebSegment(a, b, color=color, radius=0.026, label_text=label_text)
        if crossings > 0:
            seg.good = False
            self.collisions += crossings
            self.stability -= 1.8 * crossings
        else:
            self.stability += 0.55 + bonus * 0.18
        self.stability = clamp(self.stability, 0, 100)
        self.web_segments.append(seg)
        return seg, crossings

    def polygon_space_is_clear(self, center, radius):
        # Keep polygon centers separated so outlines do not pile up into clutter.
        for old_center, old_radius in self.polygon_centers[-18:]:
            if mag(flat(center - old_center)) < radius + old_radius + 1.25:
                return False
        return True

    def choose_clean_polygon_center(self, radius):
        # Try several calm candidate locations near the spider. If none are clean,
        # choose an open spot nearer the middle instead of stacking on the current web.
        for _ in range(24):
            # Use wider candidate distances so polygon drawing follows the spider's
            # exploration instead of piling up near the current web knot.
            angle = self.heading + random.uniform(-2.2, 2.2)
            distance = random.uniform(3.0, 8.0)
            center = self.pos + vector(math.cos(angle) * distance, math.sin(angle) * distance, 0)
            center.x = clamp(center.x, -WORLD_LIMIT + radius + 0.8, WORLD_LIMIT - radius - 0.8)
            center.y = clamp(center.y, -WORLD_LIMIT + radius + 0.8, WORLD_LIMIT - radius - 0.8)
            center.z = THREAD_Z
            if self.polygon_space_is_clear(center, radius):
                return center
        angle = random.uniform(0, math.tau)
        distance = random.uniform(1.0, 7.0)
        return vector(math.cos(angle) * distance, math.sin(angle) * distance, THREAD_Z)

    def build_polygon(self, sides=None, radius=None, center=None, rotation=None):
        # Simpler polygon behavior: fewer side counts, moderate radius, clear spacing,
        # and one clean outline per polygon. This keeps the geometry readable.
        if self.polygon_cooldown > 0:
            return
        if sides is None:
            choices = [3, 4, 5, 6]
            # Avoid repeating the exact same side count too often.
            choices = [n for n in choices if n != self.last_polygon_sides] or choices
            sides = random.choice(choices)
        if radius is None:
            radius = random.uniform(1.15, 2.15)
        if center is None:
            center = self.choose_clean_polygon_center(radius)
        if rotation is None:
            # Mild snapping produces smoother visual rhythm than fully random rotation.
            rotation_snap = math.pi / max(3, sides)
            rotation = round(self.heading / rotation_snap) * rotation_snap

        if not self.polygon_space_is_clear(center, radius) and len(self.polygon_centers) > 0:
            self.add_note("skipped crowded polygon", self.pos + vector(0, 0, 0.9), vector(0.35, 0.35, 0.25))
            self.polygon_cooldown = random.uniform(0.7, 1.3)
            return

        vertices = []
        for i in range(sides):
            angle = rotation + math.tau * i / sides
            vertices.append(point_on_circle(center, radius, angle))

        crossings = 0
        created = []
        for i in range(sides):
            seg, c = self.add_segment(vertices[i], vertices[(i + 1) % sides], f"clean {sides}-gon")
            seg.obj.radius = 0.022
            created.append(seg)
            crossings += c

        # A tiny center dot makes each polygon read as one object without adding clutter.
        dot = sphere(pos=vector(center.x, center.y, THREAD_Z + 0.02), radius=0.07, color=COLOR_THREAD_NEW, opacity=0.55)
        dot.clear_age = 0.0
        self.polygon_centers.append((vector(center.x, center.y, THREAD_Z), radius))
        self.polygon_centers = self.polygon_centers[-22:]
        self.last_polygon_sides = sides
        self.last_shape = f"clean {sides}-gon"
        self.pieces_built += 1
        self.symmetry_order = sides
        self.polygon_cooldown = random.uniform(1.6, 2.8)
        if crossings == 0:
            self.add_note(f"clean {sides}-gon", center + vector(0, 0, 0.7), COLOR_GOOD)
        else:
            # Bad outlines are softened instead of left as bright red tangles.
            for seg in created:
                if not seg.good:
                    seg.obj.radius = 0.012
            self.add_note(f"softened {sides}-gon", center + vector(0, 0, 0.7), COLOR_BAD)

    def build_radial_symmetry(self):
        order = random.choice([4, 5, 6, 8, 10])
        radius = random.uniform(2.8, 6.5)
        center = self.pos
        base = self.heading + random.uniform(-0.25, 0.25)
        crossings = 0
        for i in range(order):
            end = point_on_circle(center, radius, base + math.tau * i / order)
            _, c = self.add_segment(center, end, f"radial {order}")
            crossings += c
        self.last_shape = f"radial {order}"
        self.pieces_built += 1
        self.symmetry_order = order
        if crossings == 0:
            self.stability += 2.0
            self.add_note(f"symmetry x{order}", center + vector(0, 0, 1.0), COLOR_GOOD)
        else:
            self.add_note(f"broken symmetry x{order}", center + vector(0, 0, 1.0), COLOR_BAD)

    def build_spiral(self):
        turns = random.uniform(1.2, 2.5)
        steps = 18
        spacing = random.uniform(0.11, 0.22)
        center = self.pos
        pts = []
        start = self.heading
        for i in range(steps):
            t = i / (steps - 1)
            angle = start + turns * math.tau * t
            radius = 0.3 + spacing * i * 2.4
            pts.append(point_on_circle(center, radius, angle))
        crossings = 0
        for i in range(len(pts) - 1):
            _, c = self.add_segment(pts[i], pts[i + 1], "spiral")
            crossings += c
        self.last_shape = "spiral"
        self.pieces_built += 1
        if crossings == 0:
            self.stability += 1.3
            self.add_note("clean spiral", center + vector(0, 0, 0.9), COLOR_GOOD)
        else:
            self.add_note("tangled spiral", center + vector(0, 0, 0.9), COLOR_BAD)

    def build_bridge(self):
        # Connect near existing thread endpoints, creating a web-like network.
        if len(self.web_segments) < 2:
            self.build_radial_symmetry()
            return
        endpoints = []
        for seg in random.sample(self.web_segments, min(len(self.web_segments), 16)):
            endpoints.append(seg.a)
            endpoints.append(seg.b)
        a = min(endpoints, key=lambda p: mag(flat(p - self.pos)))
        candidates = sorted(endpoints, key=lambda p: abs(mag(flat(p - a)) - random.uniform(2.0, 5.0)))
        b = candidates[min(3, len(candidates) - 1)]
        _, crossings = self.add_segment(a, b, "bridge")
        self.last_shape = "bridge"
        self.pieces_built += 1
        if crossings == 0:
            self.add_note("bridge", (a + b) * 0.5 + vector(0, 0, 0.65), COLOR_GOOD)
        else:
            self.add_note("snagged bridge", (a + b) * 0.5 + vector(0, 0, 0.65), COLOR_BAD)

    def repair_tangle(self):
        # Mark a bad/tangled segment as faded and reward the spider for pruning.
        bad_segments = [seg for seg in self.web_segments if not seg.good and seg.obj.visible]
        if not bad_segments:
            self.build_bridge()
            return
        seg = random.choice(bad_segments)
        seg.obj.radius = 0.01
        seg.obj.color = vector(0.72, 0.74, 0.72)
        seg.good = True
        self.stability = clamp(self.stability + 2.5, 0, 100)
        self.last_shape = "repair"
        self.pieces_built += 1
        self.add_note("pruned crossing", (seg.a + seg.b) * 0.5 + vector(0, 0, 0.8), vector(0.3, 0.45, 0.2))

    def spin_geometry(self, force=False):
        if not force and not self.autonomous_spin:
            return
        if self.mode == "symmetry":
            choice = random.choices(["radial", "polygon", "spiral", "bridge"], [5, 2, 1, 2])[0]
        elif self.mode == "polygon":
            # Polygon mode now strongly prefers clean individual polygons and
            # avoids stacking bridges/spirals over them.
            choice = random.choices(["polygon", "radial", "bridge", "spiral"], [8, 1, 1, 0])[0]
        elif self.mode == "spiral":
            choice = random.choices(["spiral", "polygon", "radial", "bridge"], [6, 1, 1, 2])[0]
        elif self.mode == "repair":
            choice = random.choices(["repair", "bridge", "polygon"], [6, 3, 1])[0]
        else:
            choice = random.choices(["polygon", "radial", "spiral", "bridge"], [3, 2, 1, 2])[0]

        if choice == "polygon":
            self.build_polygon()
        elif choice == "radial":
            self.build_radial_symmetry()
        elif choice == "spiral":
            self.build_spiral()
        elif choice == "repair":
            self.repair_tangle()
        else:
            self.build_bridge()

    # -----------------------------
    # Motion
    # -----------------------------
    def update_exploration_memory(self):
        key = cell_key(self.pos)
        self.visited_cells.add(key)
        if not self.visit_trail or mag(flat(self.pos - self.visit_trail[-1])) > 1.1:
            self.visit_trail.append(vector(self.pos.x, self.pos.y, SPIDER_Z))
            self.visit_trail = self.visit_trail[-90:]
        self.recent_positions.append(vector(self.pos.x, self.pos.y, SPIDER_Z))
        self.recent_positions = self.recent_positions[-150:]

    def web_density_near(self, p, radius=2.8):
        density = 0.0
        sample = self.web_segments[-90:]
        for seg in sample:
            d = dist_point_segment_2d(p, seg.a, seg.b)
            if d < radius:
                density += (radius - d) / radius
        for center, pradius in self.polygon_centers[-18:]:
            d = mag(flat(p - center))
            if d < pradius + 1.8:
                density += 1.2 * (pradius + 1.8 - d) / (pradius + 1.8)
        return density

    def recent_visit_pressure(self, p):
        pressure = 0.0
        for old in self.visit_trail[-45:]:
            d = mag(flat(p - old))
            if d < 4.2:
                pressure += (4.2 - d) / 4.2
        return pressure

    def exploration_score(self, p, force_far=False):
        if not inside_safe_world(p, margin=1.5):
            return -999.0
        key = cell_key(p)
        unvisited_bonus = 7.0 if key not in self.visited_cells else -1.5
        distance_bonus = clamp(mag(flat(p - self.pos)) / WORLD_LIMIT, 0, 1) * (4.5 if force_far else 2.5)
        recent_penalty = self.recent_visit_pressure(p) * 1.5
        web_penalty = self.web_density_near(p) * 1.1
        edge_penalty = 0.0
        edge_dist = WORLD_LIMIT - max(abs(p.x), abs(p.y))
        if edge_dist < 2.0:
            edge_penalty = (2.0 - edge_dist) * 1.4
        # Prefer broad coverage over returning to the exact center.
        center_penalty = max(0.0, 4.0 - mag(flat(p))) * 0.25
        return unvisited_bonus + distance_bonus - recent_penalty - web_penalty - edge_penalty - center_penalty

    def choose_frontier_goal(self, force_far=False):
        best = None
        best_score = -9999.0
        # Mix global candidates with heading-biased candidates so movement is wide
        # but still looks continuous and organic.
        for _ in range(36):
            if random.random() < 0.55:
                x = random.uniform(-WORLD_LIMIT + 1.8, WORLD_LIMIT - 1.8)
                y = random.uniform(-WORLD_LIMIT + 1.8, WORLD_LIMIT - 1.8)
                candidate = vector(x, y, SPIDER_Z)
            else:
                angle = self.heading + random.uniform(-2.7, 2.7)
                distance = random.uniform(5.5 if force_far else 3.5, 11.5)
                candidate = self.pos + vector(math.cos(angle) * distance, math.sin(angle) * distance, 0)
                candidate.x = clamp(candidate.x, -WORLD_LIMIT + 1.8, WORLD_LIMIT - 1.8)
                candidate.y = clamp(candidate.y, -WORLD_LIMIT + 1.8, WORLD_LIMIT - 1.8)
                candidate.z = SPIDER_Z
            score = self.exploration_score(candidate, force_far=force_far)
            if score > best_score:
                best = candidate
                best_score = score
        self.goal = best if best is not None else vector(random.uniform(-9, 9), random.uniform(-9, 9), SPIDER_Z)
        self.goal_timer = random.uniform(2.4, 5.4)
        self.goal_kind = "frontier"
        self.last_explore_choice = vector(self.goal.x, self.goal.y, SPIDER_Z)
        self.goal_marker.pos = self.goal
        return self.goal

    def choose_goal(self):
        # In every mode, periodically choose a frontier goal so the spider covers
        # more of the plane before returning to local geometry work.
        self.frontier_goal_interval -= DT
        if self.frontier_goal_interval <= 0 or random.random() < 0.34:
            self.frontier_goal_interval = random.uniform(1.8, 4.2)
            self.choose_frontier_goal(force_far=random.random() < 0.55)
            return

        if self.mode == "symmetry":
            # Visit wider points on an invisible symmetry ring instead of staying
            # around the origin.
            center = self.choose_frontier_goal(force_far=False)
            angle = random.randrange(max(3, self.symmetry_order)) * math.tau / max(3, self.symmetry_order) + random.uniform(-0.35, 0.35)
            radius = random.uniform(1.5, 4.5)
            self.goal = center + vector(radius * math.cos(angle), radius * math.sin(angle), 0)
            self.goal_kind = "symmetry roam"
        elif self.mode == "polygon":
            # Polygon mode gets broad roaming goals; drawing remains clean because
            # build_polygon still checks spacing before creating outlines.
            self.choose_frontier_goal(force_far=True)
            self.goal_kind = "polygon frontier"
            return
        elif self.mode == "spiral":
            self.heading += random.uniform(0.75, 1.25)
            radius = random.uniform(3.0, 7.5)
            self.goal = self.pos + vector(radius * math.cos(self.heading), radius * math.sin(self.heading), 0)
            self.goal_kind = "spiral roam"
        elif self.mode == "repair" and self.web_segments and random.random() < 0.45:
            # Repair still visits existing web, but less often than before.
            seg = random.choice(self.web_segments[-80:])
            self.goal = (seg.a + seg.b) * 0.5 + vector(0, 0, SPIDER_Z)
            self.goal_kind = "repair visit"
        else:
            self.choose_frontier_goal(force_far=random.random() < 0.5)
            return

        self.goal.x = clamp(self.goal.x, -WORLD_LIMIT + 1.5, WORLD_LIMIT - 1.5)
        self.goal.y = clamp(self.goal.y, -WORLD_LIMIT + 1.5, WORLD_LIMIT - 1.5)
        self.goal.z = SPIDER_Z
        self.goal_timer = random.uniform(2.0, 4.6)
        self.goal_marker.pos = self.goal

    def movement_force(self):
        force = vector(0, 0, 0)

        # Manual controls
        manual = vector(0, 0, 0)
        if self.controls["w"]:
            manual.y += 1
        if self.controls["s"]:
            manual.y -= 1
        if self.controls["a"]:
            manual.x -= 1
        if self.controls["d"]:
            manual.x += 1
        if mag(manual) > 0:
            force += safe_norm(manual) * 8.5

        # Autonomous goal seeking
        if mag(manual) < 0.1:
            self.goal_timer -= DT
            if self.goal_timer <= 0 or mag(flat(self.goal - self.pos)) < 0.7:
                self.choose_goal()
            to_goal = flat(self.goal - self.pos)
            force += safe_norm(to_goal, vector(math.cos(self.heading), math.sin(self.heading), 0)) * 4.2
            # Curved exploration component so motion feels like an organism tracing math, not a cursor.
            tangent = rotate_xy(safe_norm(to_goal, vector(1, 0, 0)), math.pi / 2)
            force += tangent * math.sin(time.time() * 1.8 + self.pieces_built * 0.4) * 2.2

            # Nudge away from nearby existing web so the spider does not keep
            # orbiting the same constructed geometry.
            web_push = vector(0, 0, 0)
            for seg in self.web_segments[-70:]:
                mid = (seg.a + seg.b) * 0.5
                away = flat(self.pos - mid)
                d = mag(away)
                if 0.05 < d < 2.6:
                    web_push += norm(away) * (2.6 - d) / 2.6
            if mag(web_push) > 0:
                force += safe_norm(web_push) * clamp(mag(web_push), 0.0, 3.0) * 1.15

            # Very recent trail avoidance prevents local circular loops.
            trail_push = vector(0, 0, 0)
            for old in self.visit_trail[-28:]:
                away = flat(self.pos - old)
                d = mag(away)
                if 0.2 < d < 1.8:
                    trail_push += norm(away) * (1.8 - d)
            if mag(trail_push) > 0:
                force += safe_norm(trail_push) * 1.6

        # Soft wall avoidance. Near edges, redirect inward at an angle and choose
        # a new frontier instead of sliding along the boundary.
        margin = 3.2
        edge_hit = False
        if self.pos.x > WORLD_LIMIT - margin:
            force.x -= (self.pos.x - (WORLD_LIMIT - margin)) * 3.8
            edge_hit = True
        if self.pos.x < -WORLD_LIMIT + margin:
            force.x += ((-WORLD_LIMIT + margin) - self.pos.x) * 3.8
            edge_hit = True
        if self.pos.y > WORLD_LIMIT - margin:
            force.y -= (self.pos.y - (WORLD_LIMIT - margin)) * 3.8
            edge_hit = True
        if self.pos.y < -WORLD_LIMIT + margin:
            force.y += ((-WORLD_LIMIT + margin) - self.pos.y) * 3.8
            edge_hit = True
        if edge_hit and self.edge_escape_timer <= 0:
            self.edge_escape_timer = random.uniform(1.1, 2.0)
            self.choose_frontier_goal(force_far=True)
        if self.edge_escape_timer > 0:
            inward = safe_norm(vector(0, 0, 0) - flat(self.pos), vector(-math.cos(self.heading), -math.sin(self.heading), 0))
            arc = rotate_xy(inward, random.choice([-1, 1]) * 0.7)
            force += arc * 4.5

        return force

    def update_motion(self):
        self.update_exploration_memory()
        self.edge_escape_timer = max(0.0, self.edge_escape_timer - DT)
        self.explore_impulse_timer = max(0.0, self.explore_impulse_timer - DT)

        # Detect lingering loops: if recent movement has stayed within a small
        # region, force a far frontier goal and give the spider an outward impulse.
        if len(self.recent_positions) >= 120:
            recent = self.recent_positions[-120:]
            xs = [p.x for p in recent]
            ys = [p.y for p in recent]
            spread = max(max(xs) - min(xs), max(ys) - min(ys))
            if spread < 3.0:
                self.local_loop_timer += DT
            else:
                self.local_loop_timer = max(0.0, self.local_loop_timer - DT * 2.0)
            if self.local_loop_timer > 1.2:
                self.choose_frontier_goal(force_far=True)
                self.explore_impulse_timer = 1.3
                self.local_loop_timer = 0.0
                self.add_note("wide scout", self.pos + vector(0, 0, 1.0), vector(0.15, 0.35, 0.75))

        force = self.movement_force()
        if self.explore_impulse_timer > 0:
            force += safe_norm(flat(self.goal - self.pos), vector(math.cos(self.heading), math.sin(self.heading), 0)) * 3.5

        self.vel += force * DT
        self.vel *= 0.925
        max_speed = 4.9
        if mag(self.vel) > max_speed:
            self.vel = norm(self.vel) * max_speed
        self.pos += self.vel * DT
        self.pos.x = clamp(self.pos.x, -WORLD_LIMIT + 0.55, WORLD_LIMIT - 0.55)
        self.pos.y = clamp(self.pos.y, -WORLD_LIMIT + 0.55, WORLD_LIMIT - 0.55)
        self.pos.z = SPIDER_Z
        if mag(flat(self.vel)) > 0.05:
            self.heading = math.atan2(self.vel.y, self.vel.x)

    def update_body(self):
        pulse = 1.0 + 0.04 * math.sin(time.time() * 5.0)
        self.body.pos = self.pos
        self.body.radius = 0.45 * pulse
        head_offset = rotate_xy(vector(0.42, 0, 0.08), self.heading)
        self.head.pos = self.pos + head_offset
        self.glow.pos = self.pos + vector(0, 0, -0.08)
        self.glow.radius = 0.58 + 0.04 * math.sin(time.time() * 4.0)
        self.goal_marker.visible = True

        for idx, (side, offset, leg) in enumerate(self.legs):
            base_local = vector(offset, side * 0.22, -0.02)
            foot_local = vector(offset + 0.12 * math.sin(time.time() * 5 + idx), side * (0.85 + 0.10 * math.sin(time.time() * 4 + idx)), -0.08)
            base = self.pos + rotate_xy(base_local, self.heading)
            mid = self.pos + rotate_xy(vector(offset * 1.1, side * 0.55, 0.03), self.heading)
            foot = self.pos + rotate_xy(foot_local, self.heading)
            leg.clear()
            leg.append(base)
            leg.append(mid)
            leg.append(foot)

    def update_camera_controls(self):
        pan_speed = 0.16
        if self.controls["left"]:
            scene.center.x -= pan_speed
        if self.controls["right"]:
            scene.center.x += pan_speed
        if self.controls["up"]:
            scene.center.y += pan_speed
        if self.controls["down"]:
            scene.center.y -= pan_speed
        if self.controls["j"]:
            scene.forward = rotate(scene.forward, angle=0.025, axis=vector(0, 0, 1))
        if self.controls["l"]:
            scene.forward = rotate(scene.forward, angle=-0.025, axis=vector(0, 0, 1))
        if self.controls["i"]:
            scene.forward = rotate(scene.forward, angle=0.018, axis=vector(1, 0, 0))
        if self.controls["k"]:
            scene.forward = rotate(scene.forward, angle=-0.018, axis=vector(1, 0, 0))
        if self.controls["+"] or self.controls["="]:
            scene.range = max(6, scene.range * 0.985)
        if self.controls["-"]:
            scene.range = min(28, scene.range * 1.015)

    def update_web(self):
        self.polygon_cooldown = max(0.0, self.polygon_cooldown - DT)
        for seg in self.web_segments:
            seg.fade_toward_old()
            # Tangled segments fade and thin quickly so clutter does not dominate.
            if not seg.good and seg.age > 1.0:
                seg.obj.radius = max(0.008, seg.obj.radius * 0.985)
                seg.obj.color = lerp_vec(seg.obj.color, vector(0.72, 0.74, 0.72), 0.03)
        if len(self.web_segments) > 240:
            # Keep the drawing simpler by removing older visible segments sooner.
            for seg in self.web_segments[:36]:
                seg.hide()
            self.web_segments = self.web_segments[36:]

    def update_notes(self):
        self.notes = [n for n in self.notes if n.update()]

    def update_status(self):
        event_text = " | ".join(self.event_log[-3:]) if self.event_log else "no web events yet"
        self.status.text = (
            f"Geometry Spider\n"
            f"mode: {self.mode}\n"
            f"stability: {self.stability:05.1f} / 100\n"
            f"pieces built: {self.pieces_built}\n"
            f"crossings: {self.collisions}\n"
            f"last shape: {self.last_shape}\n"
            f"polygon cooldown: {self.polygon_cooldown:03.1f}s\n"
            f"goal: ({self.goal.x:04.1f}, {self.goal.y:04.1f}) {self.goal_kind}\n"
            f"visited cells: {len(self.visited_cells)} | loop timer: {self.local_loop_timer:03.1f}s\n"
            f"events: {event_text}"
        )
        if self.show_controls:
            self.help_label.text = (
                "WASD move | Space spin geometry | M mode | R reset | P pause | C clear notes | H hide controls | "
                "arrows pan | J/L rotate | I/K tilt | +/- zoom"
            )
        else:
            self.help_label.text = ""

    def update(self):
        self.update_camera_controls()
        if self.paused:
            self.update_status()
            return
        self.update_motion()
        self.update_body()
        self.spin_timer -= DT
        if self.spin_timer <= 0:
            # Lower stability means the spider spins more often, attempting repair or new structure.
            interval = random.uniform(1.0, 1.8) if self.stability < 35 else random.uniform(1.8, 3.3)
            self.spin_timer = interval
            self.spin_geometry(force=False)
        self.update_web()
        self.update_notes()
        self.update_status()


spider = GeometrySpider()
spider.choose_goal()
scene.bind("keydown", spider.keydown)
scene.bind("keyup", spider.keyup)

# Initial web seed
spider.build_radial_symmetry()
spider.polygon_cooldown = 0.0
spider.build_polygon(sides=6, radius=2.0, center=vector(0, 0, THREAD_Z), rotation=0)
spider.add_note("born at center", vector(0, 0, 1.2), vector(0.1, 0.25, 0.5))

while True:
    rate(60)
    spider.update()
