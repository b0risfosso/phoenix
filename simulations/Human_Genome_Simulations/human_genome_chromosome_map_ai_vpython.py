"""
Human Genome Chromosome Map — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python human_genome_chromosome_map_ai_vpython.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset simulation / new round
    M       cycle AI behavior mode
    Z       zoom to selected chromosome and show DNA segment
    X       hide zoomed DNA segment
    G       toggle gene-region markers on selected chromosome
    O       organize chromosomes into a genome atlas ring
    D       detach / scatter chromosomes
    C       clear temporary AI marks and particles
    TAB     select next chromosome
    H       print controls
    + / =   increase simulation speed
    - / _   decrease simulation speed

Mouse:
    Click a chromosome to select it.
    Mouse drag/scroll use VPython's default camera controls.

Scene concept:
    A transparent nucleus contains 23 human chromosome pairs. Each chromosome pair floats
    as paired X-shaped bodies with labels and color-coded gene regions. A zoom viewer can
    expand one chromosome into a stylized DNA ladder with highlighted gene blocks. A
    rule-based AI controller reads the state, chooses expressive modes, organizes,
    marks, zooms, rotates, scatters, studies, and loops the scene when it becomes stable.

Notes:
    This is an educational visualization. Chromosome shapes, genes, and DNA segments are
    stylized rather than biologically exact maps.
"""

from vpython import *
import random
import math
import time

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

scene = canvas(
    title="Human Genome Chromosome Map — 23 Pairs in a Transparent Nucleus",
    width=1280,
    height=760,
    background=vector(0.96, 0.98, 1.0),
    center=vector(0, 0, 0),
)
scene.range = 18
scene.forward = vector(-0.5, -0.25, -1)

# VPython uses default mouse orbit and scroll zoom.
scene.caption = """
Controls: A AI | P pause | R reset | M AI mode | TAB select | Z zoom DNA | X hide DNA | G genes | O organize | D scatter | C clear marks | H help
"""

# ---------------------------------------------------------------------------
# Constants and helpers
# ---------------------------------------------------------------------------

CHROMOSOME_COUNT = 23
PAIR_COUNT = 2
TOTAL_CHROMOSOMES = CHROMOSOME_COUNT * PAIR_COUNT

GENE_COLORS = [
    vector(1.00, 0.35, 0.35),  # red
    vector(0.25, 0.55, 1.00),  # blue
    vector(0.20, 0.75, 0.45),  # green
    vector(1.00, 0.72, 0.20),  # amber
    vector(0.78, 0.35, 1.00),  # purple
    vector(0.20, 0.85, 0.85),  # cyan
]

NUCLEUS_RADIUS = 11.5
BASE_SPEED = 1.0

def clamp(value, low, high):
    return max(low, min(high, value))

def rand_vec(radius=1.0):
    return vector(
        random.uniform(-radius, radius),
        random.uniform(-radius, radius),
        random.uniform(-radius, radius),
    )

def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) <= 1e-8:
        return fallback
    return norm(v)

def lerp_vec(a, b, t):
    return a * (1 - t) + b * t

def chromosome_label_name(pair_index, copy_index):
    if pair_index == 22:
        return "X" if copy_index == 0 else "Y"
    return str(pair_index + 1)

def chromosome_length_scale(pair_index):
    # Rough visual ranking: chromosomes 1-5 longer, 21-22 shorter.
    return 1.35 - 0.55 * (pair_index / 22.0)

def chromosome_color(pair_index, copy_index):
    hue_index = pair_index % len(GENE_COLORS)
    base = GENE_COLORS[hue_index]
    tint = 0.15 if copy_index == 0 else 0.0
    return vector(
        clamp(base.x + tint, 0, 1),
        clamp(base.y + tint, 0, 1),
        clamp(base.z + tint, 0, 1),
    )

# ---------------------------------------------------------------------------
# Visual environment
# ---------------------------------------------------------------------------

nucleus = sphere(
    pos=vector(0, 0, 0),
    radius=NUCLEUS_RADIUS,
    color=vector(0.75, 0.88, 1.0),
    opacity=0.12,
    shininess=0.15,
)

nucleus_boundary = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 1, 0),
    radius=NUCLEUS_RADIUS,
    thickness=0.03,
    color=vector(0.45, 0.65, 0.95),
    opacity=0.35,
)
nucleus_boundary_2 = ring(
    pos=vector(0, 0, 0),
    axis=vector(1, 0, 0),
    radius=NUCLEUS_RADIUS,
    thickness=0.03,
    color=vector(0.45, 0.65, 0.95),
    opacity=0.25,
)
nucleus_boundary_3 = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 0, 1),
    radius=NUCLEUS_RADIUS,
    thickness=0.03,
    color=vector(0.45, 0.65, 0.95),
    opacity=0.20,
)

center_label = label(
    pos=vector(0, NUCLEUS_RADIUS + 1.2, 0),
    text="Human genome chromosome map: 23 pairs",
    height=18,
    color=vector(0.1, 0.18, 0.28),
    box=False,
    opacity=0,
)

status_label = label(
    pos=vector(-13.0, -11.7, 0),
    text="Starting simulation...",
    height=12,
    color=vector(0.05, 0.08, 0.12),
    box=False,
    opacity=0,
)

# ---------------------------------------------------------------------------
# Data classes implemented as simple Python classes for VPython compatibility
# ---------------------------------------------------------------------------

class Chromosome:
    def __init__(self, pair_index, copy_index, pos):
        self.pair_index = pair_index
        self.copy_index = copy_index
        self.name = chromosome_label_name(pair_index, copy_index)
        self.base_color = chromosome_color(pair_index, copy_index)
        self.pos = pos
        self.vel = rand_vec(0.04)
        self.angle = random.uniform(0, math.tau)
        self.spin = random.uniform(-0.9, 0.9)
        self.length = chromosome_length_scale(pair_index)
        self.selected = False
        self.gene_markers_visible = True
        self.target_pos = vector(pos.x, pos.y, pos.z)
        self.mode_hint = "float"
        self.energy = random.uniform(0.2, 1.0)
        self.last_pos = vector(pos.x, pos.y, pos.z)

        self.parts = []
        self.gene_markers = []
        self.temp_marks = []
        self.label = None
        self.selection_ring = None
        self.create_visuals()

    def create_visuals(self):
        # X-shaped chromosome: four cylinders from center to arms plus a central centromere.
        arm_len = 1.0 + 1.4 * self.length
        arm_radius = 0.13 + 0.05 * self.length
        spread = 0.45 + 0.25 * self.length

        arm_specs = [
            vector(-spread, arm_len, 0),
            vector(spread, arm_len, 0),
            vector(-spread, -arm_len, 0),
            vector(spread, -arm_len, 0),
        ]
        for end in arm_specs:
            cyl = cylinder(
                pos=self.pos,
                axis=end,
                radius=arm_radius,
                color=self.base_color,
                opacity=0.88,
                shininess=0.2,
            )
            self.parts.append(cyl)

        centromere = sphere(
            pos=self.pos,
            radius=arm_radius * 1.8,
            color=vector(1.0, 0.95, 0.75),
            opacity=0.95,
            shininess=0.3,
        )
        self.parts.append(centromere)

        self.label = label(
            pos=self.pos + vector(0, arm_len + 0.85, 0),
            text=f"Chr {self.name}",
            height=10,
            color=vector(0.08, 0.10, 0.16),
            box=False,
            opacity=0,
        )

        self.selection_ring = ring(
            pos=self.pos,
            axis=vector(0, 0, 1),
            radius=1.35 + 0.5 * self.length,
            thickness=0.035,
            color=vector(1.0, 0.6, 0.05),
            opacity=0.0,
        )

        self.create_gene_markers()

    def create_gene_markers(self):
        # Small color-coded regions on arms. These are stylized "gene regions".
        for i in range(4):
            y = random.choice([-1, 1]) * random.uniform(0.45, 1.75) * self.length
            x = random.choice([-1, 1]) * random.uniform(0.08, 0.35)
            marker = sphere(
                pos=self.pos + vector(x, y, 0.07),
                radius=0.10 + 0.02 * self.length,
                color=GENE_COLORS[(self.pair_index + i) % len(GENE_COLORS)],
                emissive=False,
                opacity=0.95,
            )
            marker.local_offset = vector(x, y, 0.07)
            self.gene_markers.append(marker)

    def all_objects(self):
        return self.parts + self.gene_markers + [self.label, self.selection_ring] + self.temp_marks

    def set_visible(self, visible=True):
        for obj in self.all_objects():
            obj.visible = visible

    def toggle_genes(self):
        self.gene_markers_visible = not self.gene_markers_visible
        for m in self.gene_markers:
            m.visible = self.gene_markers_visible

    def mark(self, color_value=vector(1, 0.25, 0.15), ttl=2.5):
        m = sphere(
            pos=self.pos + rand_vec(0.45),
            radius=0.16,
            color=color_value,
            opacity=0.75,
            emissive=True,
        )
        m.ttl = ttl
        self.temp_marks.append(m)

    def update_temp_marks(self, dt):
        still = []
        for m in self.temp_marks:
            m.ttl -= dt
            m.radius *= 0.992
            m.opacity = max(0.0, min(0.8, m.ttl / 2.5))
            m.pos = m.pos + vector(0, 0.01 * math.sin(time.time() * 4), 0)
            if m.ttl > 0 and m.radius > 0.03:
                still.append(m)
            else:
                m.visible = False
        self.temp_marks = still

    def clear_temp_marks(self):
        for m in self.temp_marks:
            m.visible = False
        self.temp_marks = []

    def update(self, dt, organized=False):
        self.last_pos = vector(self.pos.x, self.pos.y, self.pos.z)

        if organized:
            desired = self.target_pos
            pull = (desired - self.pos) * 0.8
            self.vel = self.vel * 0.92 + pull * dt
        else:
            self.vel += rand_vec(0.018) * dt
            self.vel *= 0.992

        # Keep inside transparent nucleus.
        future = self.pos + self.vel * dt * 7.0
        if mag(future) > NUCLEUS_RADIUS - 1.5:
            inward = -safe_norm(future)
            self.vel = self.vel * 0.45 + inward * 0.15

        self.pos += self.vel * dt * 7.0
        self.angle += self.spin * dt * 0.7

        self.draw()
        self.update_temp_marks(dt)

    def draw(self):
        arm_len = 1.0 + 1.4 * self.length
        arm_radius = 0.13 + 0.05 * self.length
        spread = 0.45 + 0.25 * self.length

        # Rotate local X-shape around Z and add mild wobble.
        ca = math.cos(self.angle)
        sa = math.sin(self.angle)
        wobble = 0.18 * math.sin(time.time() * 0.8 + self.pair_index)

        local_ends = [
            vector(-spread, arm_len, wobble),
            vector(spread, arm_len, -wobble),
            vector(-spread, -arm_len, -wobble),
            vector(spread, -arm_len, wobble),
        ]

        for i, end in enumerate(local_ends):
            rotated = vector(end.x * ca - end.y * sa, end.x * sa + end.y * ca, end.z)
            self.parts[i].pos = self.pos
            self.parts[i].axis = rotated
            self.parts[i].radius = arm_radius

        self.parts[4].pos = self.pos
        self.parts[4].radius = arm_radius * 1.8

        for gm in self.gene_markers:
            offset = gm.local_offset
            rotated = vector(offset.x * ca - offset.y * sa, offset.x * sa + offset.y * ca, offset.z)
            gm.pos = self.pos + rotated
            gm.visible = self.gene_markers_visible

        self.label.pos = self.pos + vector(0, arm_len + 0.85, 0)
        self.selection_ring.pos = self.pos
        self.selection_ring.axis = scene.forward
        self.selection_ring.opacity = 0.85 if self.selected else 0.0
        self.selection_ring.radius = 1.35 + 0.5 * self.length

# ---------------------------------------------------------------------------
# DNA zoom viewer
# ---------------------------------------------------------------------------

class DNAPanel:
    def __init__(self):
        self.visible = False
        self.objects = []
        self.selected_chromosome = None
        self.phase = 0.0

    def clear(self):
        for obj in self.objects:
            obj.visible = False
        self.objects = []
        self.visible = False
        self.selected_chromosome = None

    def show_for(self, chrom):
        self.clear()
        self.visible = True
        self.selected_chromosome = chrom
        base_pos = vector(14, 0, 0)

        panel = box(
            pos=base_pos + vector(0, 0, -0.35),
            size=vector(5.2, 10.5, 0.10),
            color=vector(1, 1, 1),
            opacity=0.55,
        )
        self.objects.append(panel)

        title = label(
            pos=base_pos + vector(0, 5.8, 0),
            text=f"Zoomed DNA segment: Chr {chrom.name}",
            height=13,
            color=vector(0.08, 0.10, 0.16),
            box=False,
            opacity=0,
        )
        self.objects.append(title)

        # DNA ladder: two helix-like bead rails plus connecting rungs.
        steps = 34
        height = 8.4
        radius = 0.9
        previous_a = None
        previous_b = None
        for i in range(steps):
            t = i / (steps - 1)
            y = -height / 2 + height * t
            angle = t * math.tau * 3.4
            a = base_pos + vector(math.cos(angle) * radius, y, math.sin(angle) * 0.25)
            b = base_pos + vector(math.cos(angle + math.pi) * radius, y, math.sin(angle + math.pi) * 0.25)

            bead_a = sphere(pos=a, radius=0.11, color=vector(0.15, 0.45, 1.0), opacity=0.9)
            bead_b = sphere(pos=b, radius=0.11, color=vector(1.0, 0.35, 0.35), opacity=0.9)
            rung = cylinder(pos=a, axis=b - a, radius=0.025, color=vector(0.45, 0.52, 0.60), opacity=0.75)

            self.objects.extend([bead_a, bead_b, rung])

            if previous_a is not None:
                rail_a = cylinder(pos=previous_a, axis=a - previous_a, radius=0.035, color=vector(0.25, 0.55, 1.0), opacity=0.65)
                rail_b = cylinder(pos=previous_b, axis=b - previous_b, radius=0.035, color=vector(1.0, 0.45, 0.45), opacity=0.65)
                self.objects.extend([rail_a, rail_b])

            previous_a = a
            previous_b = b

        # Gene blocks on the zoomed DNA segment.
        for i in range(5):
            y = random.uniform(-3.6, 3.6)
            gene = box(
                pos=base_pos + vector(0, y, 0.45),
                size=vector(2.3, 0.35, 0.18),
                color=GENE_COLORS[(chrom.pair_index + i) % len(GENE_COLORS)],
                opacity=0.82,
            )
            gene_label = label(
                pos=gene.pos + vector(1.65, 0, 0),
                text=f"gene region {i + 1}",
                height=8,
                color=vector(0.08, 0.10, 0.16),
                box=False,
                opacity=0,
            )
            self.objects.extend([gene, gene_label])

        pointer = cylinder(
            pos=chrom.pos,
            axis=(base_pos - chrom.pos) * 0.85,
            radius=0.025,
            color=vector(0.2, 0.35, 0.65),
            opacity=0.35,
        )
        self.objects.append(pointer)

    def update(self, dt):
        if not self.visible:
            return
        self.phase += dt
        for obj in self.objects:
            if hasattr(obj, "emissive"):
                pass
        # Gentle pulse for highlighted gene block boxes.
        for obj in self.objects:
            if isinstance(obj, box) and obj.size.z > 0.12:
                obj.opacity = 0.65 + 0.20 * (0.5 + 0.5 * math.sin(self.phase * 2.0 + obj.pos.y))

# ---------------------------------------------------------------------------
# Genome simulation state
# ---------------------------------------------------------------------------

chromosomes = []
selected_index = 0
dna_panel = DNAPanel()
paused = False
ai_enabled = True
simulation_speed = BASE_SPEED
organized_view = False
round_number = 1
last_motion_score = 999
last_reset_time = time.time()

def generate_chromosome_positions():
    positions = []
    for pair in range(CHROMOSOME_COUNT):
        angle = (pair / CHROMOSOME_COUNT) * math.tau
        ring_radius = 5.5 + 2.6 * math.sin(pair * 1.7)
        base = vector(math.cos(angle) * ring_radius, random.uniform(-4.0, 4.0), math.sin(angle) * ring_radius)
        tangent = vector(-math.sin(angle), 0, math.cos(angle))
        positions.append(base + tangent * 0.45)
        positions.append(base - tangent * 0.45)
    return positions

def create_chromosomes():
    global chromosomes, selected_index
    for ch in chromosomes:
        ch.set_visible(False)
    chromosomes = []
    positions = generate_chromosome_positions()
    k = 0
    for pair in range(CHROMOSOME_COUNT):
        for copy in range(PAIR_COUNT):
            ch = Chromosome(pair, copy, positions[k])
            chromosomes.append(ch)
            k += 1
    selected_index = 0
    select_chromosome(0)

def select_chromosome(index):
    global selected_index
    if not chromosomes:
        return
    for ch in chromosomes:
        ch.selected = False
    selected_index = index % len(chromosomes)
    chromosomes[selected_index].selected = True

def selected_chromosome():
    if not chromosomes:
        return None
    return chromosomes[selected_index]

def organize_genome_ring():
    global organized_view
    organized_view = True
    for pair in range(CHROMOSOME_COUNT):
        angle = (pair / CHROMOSOME_COUNT) * math.tau
        radius = 8.4
        y = -3.4 + (pair % 6) * 1.35
        center = vector(math.cos(angle) * radius, y, math.sin(angle) * radius)
        tangent = vector(-math.sin(angle), 0, math.cos(angle))
        chromosomes[pair * 2].target_pos = center + tangent * 0.38
        chromosomes[pair * 2 + 1].target_pos = center - tangent * 0.38
        chromosomes[pair * 2].mode_hint = "atlas"
        chromosomes[pair * 2 + 1].mode_hint = "atlas"

def scatter_chromosomes():
    global organized_view
    organized_view = False
    for ch in chromosomes:
        ch.vel += rand_vec(0.28)
        ch.spin += random.uniform(-1.5, 1.5)
        ch.mode_hint = "float"

def clear_all_marks():
    for ch in chromosomes:
        ch.clear_temp_marks()

def reset_simulation():
    global round_number, organized_view, last_reset_time
    round_number += 1
    organized_view = False
    dna_panel.clear()
    create_chromosomes()
    last_reset_time = time.time()

# ---------------------------------------------------------------------------
# Expressive rule-based AI controller
# ---------------------------------------------------------------------------

class GenomeAI:
    def __init__(self):
        self.modes = [
            "survey",
            "organize",
            "inspect",
            "mark_gene_regions",
            "pair_dance",
            "scatter",
            "repair_order",
            "ritual_loop",
            "artistic_trace",
        ]
        self.mode_index = 0
        self.mode = self.modes[self.mode_index]
        self.timer = 0.0
        self.mode_duration = 5.0
        self.action_cooldown = 0.0
        self.stable_timer = 0.0
        self.completion_timer = 0.0
        self.last_signature = 0.0
        self.round_timer = 0.0
        self.focus_index = 0
        self.trace_particles = []
        self.loop_after_completion = True

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        self.mode = self.modes[self.mode_index]
        self.timer = 0.0
        self.action_cooldown = 0.0

    def read_state(self):
        if not chromosomes:
            return {
                "motion": 0,
                "selected": None,
                "organized": False,
                "zoom_visible": False,
                "marks": 0,
                "signature": 0,
                "spread": 0,
            }

        avg_motion = sum(mag(ch.pos - ch.last_pos) for ch in chromosomes) / len(chromosomes)
        avg_radius = sum(mag(ch.pos) for ch in chromosomes) / len(chromosomes)
        marks = sum(len(ch.temp_marks) for ch in chromosomes)
        signature = avg_motion * 1000 + avg_radius + marks * 0.1 + (1 if dna_panel.visible else 0)
        return {
            "motion": avg_motion,
            "selected": selected_chromosome(),
            "organized": organized_view,
            "zoom_visible": dna_panel.visible,
            "marks": marks,
            "signature": signature,
            "spread": avg_radius,
        }

    def detect_stagnation_or_completion(self, dt, state):
        global last_motion_score

        signature_delta = abs(state["signature"] - self.last_signature)
        self.last_signature = state["signature"]
        last_motion_score = state["motion"]

        if state["motion"] < 0.0025 and signature_delta < 0.008:
            self.stable_timer += dt
        else:
            self.stable_timer = max(0.0, self.stable_timer - dt * 0.5)

        if state["organized"] and state["zoom_visible"] and state["marks"] > 10:
            self.completion_timer += dt
        else:
            self.completion_timer = max(0.0, self.completion_timer - dt * 0.4)

        return self.stable_timer > 7.0 or self.completion_timer > 8.0

    def choose_mode(self, state):
        # React to state while avoiding one behavior forever.
        if self.timer > self.mode_duration:
            if state["marks"] > 24:
                self.mode = "repair_order"
            elif not state["organized"] and random.random() < 0.45:
                self.mode = "organize"
            elif state["organized"] and not state["zoom_visible"]:
                self.mode = "inspect"
            elif state["zoom_visible"] and state["marks"] < 16:
                self.mode = "mark_gene_regions"
            else:
                self.cycle_mode()
            self.timer = 0.0
            self.mode_duration = random.uniform(4.0, 8.5)

    def act(self, dt, state):
        self.action_cooldown -= dt
        if self.action_cooldown > 0:
            return

        if self.mode == "survey":
            self.focus_index = (self.focus_index + random.randint(1, 5)) % len(chromosomes)
            select_chromosome(self.focus_index)
            ch = selected_chromosome()
            ch.mark(vector(0.2, 0.55, 1.0), ttl=1.8)
            ch.spin += random.uniform(-0.6, 0.6)
            self.action_cooldown = 0.7

        elif self.mode == "organize":
            organize_genome_ring()
            for ch in random.sample(chromosomes, min(4, len(chromosomes))):
                ch.mark(vector(0.2, 0.8, 0.45), ttl=2.2)
            self.action_cooldown = 1.4

        elif self.mode == "inspect":
            ch = selected_chromosome()
            if ch is not None:
                dna_panel.show_for(ch)
                ch.mark(vector(1.0, 0.7, 0.15), ttl=3.0)
            self.action_cooldown = 2.5

        elif self.mode == "mark_gene_regions":
            candidates = random.sample(chromosomes, min(6, len(chromosomes)))
            for i, ch in enumerate(candidates):
                ch.mark(GENE_COLORS[(ch.pair_index + i) % len(GENE_COLORS)], ttl=3.5)
            self.action_cooldown = 1.1

        elif self.mode == "pair_dance":
            pair = random.randint(0, CHROMOSOME_COUNT - 1)
            ch1 = chromosomes[pair * 2]
            ch2 = chromosomes[pair * 2 + 1]
            midpoint = (ch1.pos + ch2.pos) * 0.5
            ch1.vel += safe_norm(ch2.pos - ch1.pos) * 0.08 + rand_vec(0.02)
            ch2.vel += safe_norm(ch1.pos - ch2.pos) * 0.08 + rand_vec(0.02)
            ch1.spin += 1.1
            ch2.spin -= 1.1
            ch1.mark(vector(0.8, 0.3, 1.0), ttl=2.0)
            ch2.mark(vector(0.8, 0.3, 1.0), ttl=2.0)
            self.spawn_trace(midpoint, vector(0.8, 0.3, 1.0))
            self.action_cooldown = 0.8

        elif self.mode == "scatter":
            scatter_chromosomes()
            for ch in random.sample(chromosomes, min(5, len(chromosomes))):
                ch.mark(vector(1.0, 0.25, 0.2), ttl=1.7)
            self.action_cooldown = 2.8

        elif self.mode == "repair_order":
            clear_all_marks()
            organize_genome_ring()
            dna_panel.clear()
            self.action_cooldown = 2.0

        elif self.mode == "ritual_loop":
            # Sequentially visit chromosomes 1 through 23 and their pair copies.
            self.focus_index = (self.focus_index + 1) % len(chromosomes)
            select_chromosome(self.focus_index)
            ch = selected_chromosome()
            if self.focus_index % 4 == 0:
                dna_panel.show_for(ch)
            ch.mark(vector(1.0, 0.85, 0.25), ttl=2.4)
            self.action_cooldown = 0.5

        elif self.mode == "artistic_trace":
            ch = random.choice(chromosomes)
            ch.vel += rand_vec(0.10)
            self.spawn_trace(ch.pos, random.choice(GENE_COLORS))
            ch.mark(random.choice(GENE_COLORS), ttl=2.0)
            self.action_cooldown = 0.35

    def spawn_trace(self, pos, color_value):
        s = sphere(
            pos=pos + rand_vec(0.35),
            radius=0.10,
            color=color_value,
            opacity=0.60,
            emissive=True,
        )
        s.ttl = 3.0
        self.trace_particles.append(s)

    def update_trace_particles(self, dt):
        kept = []
        for p in self.trace_particles:
            p.ttl -= dt
            p.pos += vector(0, 0.015, 0) + rand_vec(0.005)
            p.opacity = max(0, p.ttl / 3.0 * 0.60)
            p.radius *= 0.993
            if p.ttl > 0 and p.radius > 0.025:
                kept.append(p)
            else:
                p.visible = False
        self.trace_particles = kept

    def clear_traces(self):
        for p in self.trace_particles:
            p.visible = False
        self.trace_particles = []

    def update(self, dt):
        self.round_timer += dt
        self.timer += dt
        state = self.read_state()
        complete_or_stagnant = self.detect_stagnation_or_completion(dt, state)

        if complete_or_stagnant and self.loop_after_completion:
            self.stable_timer = 0.0
            self.completion_timer = 0.0
            self.clear_traces()
            reset_simulation()
            self.mode = "survey"
            self.timer = 0.0
            return

        self.choose_mode(state)
        self.act(dt, state)
        self.update_trace_particles(dt)

ai = GenomeAI()

# ---------------------------------------------------------------------------
# Human controls
# ---------------------------------------------------------------------------

def print_controls():
    print(__doc__)

def handle_key(evt):
    global paused, ai_enabled, simulation_speed, organized_view
    key = evt.key.lower()

    if key == "a":
        ai_enabled = not ai_enabled
    elif key == "p":
        paused = not paused
    elif key == "r":
        reset_simulation()
    elif key == "m":
        ai.cycle_mode()
    elif key == "z":
        ch = selected_chromosome()
        if ch:
            dna_panel.show_for(ch)
    elif key == "x":
        dna_panel.clear()
    elif key == "g":
        ch = selected_chromosome()
        if ch:
            ch.toggle_genes()
    elif key == "o":
        organize_genome_ring()
    elif key == "d":
        scatter_chromosomes()
    elif key == "c":
        clear_all_marks()
        ai.clear_traces()
    elif key == "tab":
        select_chromosome(selected_index + 1)
    elif key == "h":
        print_controls()
    elif key in ["+", "="]:
        simulation_speed = clamp(simulation_speed * 1.18, 0.15, 5.0)
    elif key in ["-", "_"]:
        simulation_speed = clamp(simulation_speed / 1.18, 0.15, 5.0)

def handle_click(evt):
    picked = scene.mouse.pick
    if picked is None:
        return

    # Select chromosome if any of its body parts or gene markers was clicked.
    for i, ch in enumerate(chromosomes):
        for obj in ch.parts + ch.gene_markers:
            if picked == obj:
                select_chromosome(i)
                return

scene.bind("keydown", handle_key)
scene.bind("click", handle_click)

# ---------------------------------------------------------------------------
# Main simulation loop
# ---------------------------------------------------------------------------

create_chromosomes()
print_controls()

previous_time = time.time()

while True:
    rate(60)
    now = time.time()
    raw_dt = now - previous_time
    previous_time = now
    dt = clamp(raw_dt, 0.001, 0.04) * simulation_speed

    if not paused:
        for ch in chromosomes:
            ch.update(dt, organized=organized_view)

        # Very light collision avoidance between nearby chromosomes.
        for i in range(len(chromosomes)):
            a = chromosomes[i]
            for j in range(i + 1, len(chromosomes)):
                b = chromosomes[j]
                diff = b.pos - a.pos
                d = mag(diff)
                min_d = 0.95
                if 0 < d < min_d:
                    push = safe_norm(diff) * (min_d - d) * 0.018
                    a.vel -= push
                    b.vel += push

        dna_panel.update(dt)

        if ai_enabled:
            ai.update(dt)

    selected = selected_chromosome()
    selected_text = f"Chr {selected.name}" if selected else "none"
    status_label.text = (
        f"Round {round_number} | AI {'ON' if ai_enabled else 'OFF'} | Mode: {ai.mode} | "
        f"Selected: {selected_text} | DNA zoom {'ON' if dna_panel.visible else 'OFF'} | "
        f"Genome atlas {'ON' if organized_view else 'OFF'} | Speed {simulation_speed:.2f}x | "
        f"motion {last_motion_score:.4f}"
    )
