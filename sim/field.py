"""Field geometry: walls, goals, and white line definitions.

All dimensions from official RCJ Junior Soccer rules.
"""
from __future__ import annotations
import math
import pymunk

# ── Playing area (internal carpet) ──────────────────────────────────────────
FIELD_LENGTH = 2.19    # X axis — goal to goal  (219 cm)
FIELD_WIDTH  = 1.58    # Y axis — side to side  (158 cm)

# ── Out-area ─────────────────────────────────────────────────────────────────
OUT_AREA_WIDTH = 0.12  # 12 cm around all sides

# ── Total field (playing area + out-area) ────────────────────────────────────
TOTAL_LENGTH = FIELD_LENGTH + 2 * OUT_AREA_WIDTH   # 2.43 m
TOTAL_WIDTH  = FIELD_WIDTH  + 2 * OUT_AREA_WIDTH   # 1.82 m

# ── Goal ─────────────────────────────────────────────────────────────────────
GOAL_WIDTH = 0.60    # internal Y-axis opening   (60 cm)
GOAL_DEPTH = 0.074   # X-axis depth from posts   (74 mm)

# ── White line thickness ─────────────────────────────────────────────────────
LINE_THICKNESS      = 0.020   # 20 mm
LINE_HALF_THICKNESS = LINE_THICKNESS / 2   # 10 mm — used for sensor detection

# ── Penalty areas ────────────────────────────────────────────────────────────
PENALTY_DEPTH    = 0.25   # into field from boundary (25 cm)
PENALTY_HALF_Y   = 0.40   # half of total width (80 cm → ±40 cm)
PENALTY_CORNER_R = 0.15   # rounded front-corner radius (15 cm)

# ── Center circle (BLACK thin line — referee guide, NOT detected by line sensors)
CENTER_CIRCLE_RADIUS = 0.30   # 60 cm diameter

# ── Derived half-dimensions ──────────────────────────────────────────────────
HALF_L       = FIELD_LENGTH / 2    # 1.095 — playing-area boundary
HALF_W       = FIELD_WIDTH  / 2    # 0.79
HALF_TOTAL_L = TOTAL_LENGTH / 2    # 1.215 — outer wall
HALF_TOTAL_W = TOTAL_WIDTH  / 2    # 0.91
HALF_G       = GOAL_WIDTH   / 2    # 0.30

# Penalty arc geometry (pre-computed)
_PF_X  = HALF_L - PENALTY_DEPTH              # front line X = 0.845
_ARC_X = _PF_X + PENALTY_CORNER_R            # arc centre X = 0.995
_ARC_Y = PENALTY_HALF_Y - PENALTY_CORNER_R   # arc centre Y = 0.25

# ── Neutral spots (5 black 1-cm dots) ───────────────────────────────────────
NEUTRAL_SPOTS: list[tuple[float, float]] = [
    (0.0, 0.0),
    ( HALF_L - 0.45,  PENALTY_HALF_Y),
    ( HALF_L - 0.45, -PENALTY_HALF_Y),
    (-HALF_L + 0.45,  PENALTY_HALF_Y),
    (-HALF_L + 0.45, -PENALTY_HALF_Y),
]

# ── White line segments (for line-sensor detection) ──────────────────────────
# Only the WHITE lines: boundary + penalty areas.
# The centre circle is BLACK and is NOT included here.
FIELD_LINE_SEGMENTS: list[tuple] = [
    # Playing-area boundary rectangle
    ((-HALF_L, -HALF_W), ( HALF_L, -HALF_W)),   # bottom
    (( HALF_L, -HALF_W), ( HALF_L,  HALF_W)),   # right
    (( HALF_L,  HALF_W), (-HALF_L,  HALF_W)),   # top
    ((-HALF_L,  HALF_W), (-HALF_L, -HALF_W)),   # left

    # Right (yellow) penalty area
    (( HALF_L, PENALTY_HALF_Y), (_ARC_X,  PENALTY_HALF_Y)),   # top side
    ((_ARC_X, -PENALTY_HALF_Y), ( HALF_L, -PENALTY_HALF_Y)),  # bottom side
    ((_PF_X,  _ARC_Y), (_PF_X, -_ARC_Y)),                      # front straight

    # Left (blue) penalty area
    ((-HALF_L, PENALTY_HALF_Y), (-_ARC_X,  PENALTY_HALF_Y)),  # top side
    ((-_ARC_X, -PENALTY_HALF_Y), (-HALF_L, -PENALTY_HALF_Y)), # bottom side
    ((-_PF_X,  _ARC_Y), (-_PF_X, -_ARC_Y)),                    # front straight
]

# Penalty-area rounded front corners: (cx, cy, r, start_rad, end_rad)
# Angles follow standard math convention (0 = +X, CCW positive).
FIELD_LINE_ARCS: list[tuple] = [
    # Right penalty area, top-front corner    (90° → 180°)
    ( _ARC_X,  _ARC_Y, PENALTY_CORNER_R,     math.pi / 2,     math.pi),
    # Right penalty area, bottom-front corner (180° → 270°)
    ( _ARC_X, -_ARC_Y, PENALTY_CORNER_R,     math.pi,     3 * math.pi / 2),
    # Left penalty area, top-front corner     (0° → 90°)
    (-_ARC_X,  _ARC_Y, PENALTY_CORNER_R,     0.0,             math.pi / 2),
    # Left penalty area, bottom-front corner  (270° → 360°)
    (-_ARC_X, -_ARC_Y, PENALTY_CORNER_R, 3 * math.pi / 2, 2 * math.pi),
]

# ── PyMunk wall construction ─────────────────────────────────────────────────
WALL_RADIUS      = 0.010
WALL_ELASTICITY  = 0.40
WALL_FRICTION    = 0.50


def _add_seg(space: pymunk.Space, a: tuple, b: tuple) -> pymunk.Segment:
    seg = pymunk.Segment(space.static_body, a, b, WALL_RADIUS)
    seg.elasticity = WALL_ELASTICITY
    seg.friction   = WALL_FRICTION
    seg.filter     = pymunk.ShapeFilter(categories=0b001)
    space.add(seg)
    return seg


def build_field(space: pymunk.Space) -> None:
    """Add all static field boundaries (walls + goals) to the pymunk space."""
    # Outer side walls — full length
    _add_seg(space, (-HALF_TOTAL_L, -HALF_TOTAL_W), ( HALF_TOTAL_L, -HALF_TOTAL_W))
    _add_seg(space, (-HALF_TOTAL_L,  HALF_TOTAL_W), ( HALF_TOTAL_L,  HALF_TOTAL_W))

    # Left outer end wall — goal cutout at |y| < HALF_G
    _add_seg(space, (-HALF_TOTAL_L, -HALF_TOTAL_W), (-HALF_TOTAL_L, -HALF_G))
    _add_seg(space, (-HALF_TOTAL_L,  HALF_G),       (-HALF_TOTAL_L,  HALF_TOTAL_W))

    # Right outer end wall — goal cutout
    _add_seg(space, ( HALF_TOTAL_L, -HALF_TOTAL_W), ( HALF_TOTAL_L, -HALF_G))
    _add_seg(space, ( HALF_TOTAL_L,  HALF_G),       ( HALF_TOTAL_L,  HALF_TOTAL_W))

    # Left goal box (blue) — posts on boundary line (x = -HALF_L)
    _add_seg(space, (-HALF_L,  HALF_G), (-HALF_L - GOAL_DEPTH,  HALF_G))
    _add_seg(space, (-HALF_L - GOAL_DEPTH,  HALF_G), (-HALF_L - GOAL_DEPTH, -HALF_G))
    _add_seg(space, (-HALF_L - GOAL_DEPTH, -HALF_G), (-HALF_L, -HALF_G))

    # Right goal box (yellow) — posts on boundary line (x = +HALF_L)
    _add_seg(space, ( HALF_L,  HALF_G), ( HALF_L + GOAL_DEPTH,  HALF_G))
    _add_seg(space, ( HALF_L + GOAL_DEPTH,  HALF_G), ( HALF_L + GOAL_DEPTH, -HALF_G))
    _add_seg(space, ( HALF_L + GOAL_DEPTH, -HALF_G), ( HALF_L, -HALF_G))


# ── Goal detection ───────────────────────────────────────────────────────────

def is_blue_goal(x: float, y: float) -> bool:
    """Ball has crossed the blue (left) goal line."""
    return x < -HALF_L and abs(y) < HALF_G


def is_yellow_goal(x: float, y: float) -> bool:
    """Ball has crossed the yellow (right) goal line."""
    return x > HALF_L and abs(y) < HALF_G
