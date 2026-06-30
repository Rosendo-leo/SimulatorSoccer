"""Compute sensor percepts from simulation state.

All angles in radians. Robot-local frame: 0 = forward (+X when heading=0),
positive = counter-clockwise (left).
"""
from __future__ import annotations
import math
import numpy as np
import pymunk

from sim.config_loader import (
    IRRingConfig,
    CompassConfig,
    UltrasoundConfig,
    LineSensorsConfig,
)
from sim.field import (
    FIELD_LINE_SEGMENTS,
    FIELD_LINE_ARCS,
    LINE_HALF_THICKNESS,
)

CATEGORY_WALL  = 0b001
CATEGORY_ROBOT = 0b010
_ULTRASOUND_QUERY_FILTER = pymunk.ShapeFilter(mask=CATEGORY_WALL | CATEGORY_ROBOT)


# ── IR ring ──────────────────────────────────────────────────────────────────

def compute_ir_ring(
    robot_pos: pymunk.Vec2d,
    heading: float,
    ball_pos: pymunk.Vec2d,
    cfg: IRRingConfig,
    rng: np.random.Generator,
) -> list[float]:
    dx = ball_pos.x - robot_pos.x
    dy = ball_pos.y - robot_pos.y
    dist = math.sqrt(dx * dx + dy * dy)

    readings = [0.0] * cfg.count

    if dist < 0.001 or dist > cfg.range:
        if cfg.noise_std > 0:
            readings = [max(0.0, float(v + rng.normal(0, cfg.noise_std * 0.1)))
                        for v in readings]
        return readings

    angle_world = math.atan2(dy, dx)
    angle_local = (angle_world - heading) % (2 * math.pi)

    sector_width = (2 * math.pi) / cfg.count
    sector = int(angle_local / sector_width) % cfg.count

    intensity = max(0.0, 1.0 - dist / cfg.range)

    prev_s = (sector - 1) % cfg.count
    next_s = (sector + 1) % cfg.count
    readings[sector]  = intensity
    readings[prev_s]  = intensity * 0.2
    readings[next_s]  = intensity * 0.2

    if cfg.noise_std > 0:
        readings = [
            max(0.0, min(1.0, float(v + rng.normal(0, cfg.noise_std))))
            for v in readings
        ]
    return readings


# ── Compass ──────────────────────────────────────────────────────────────────

def compute_compass(heading: float, cfg: CompassConfig, rng: np.random.Generator) -> float:
    noise = rng.normal(0, math.radians(cfg.noise_std)) if cfg.noise_std > 0 else 0.0
    return heading + noise


# ── Ultrasound ───────────────────────────────────────────────────────────────

def compute_ultrasound(
    robot_pos: pymunk.Vec2d,
    heading: float,
    robot_radius: float,
    cfg: UltrasoundConfig,
    space: pymunk.Space,
    rng: np.random.Generator,
) -> list[float]:
    readings = []
    for dir_deg in cfg.directions:
        dir_rad = heading + math.radians(dir_deg)
        cos_d   = math.cos(dir_rad)
        sin_d   = math.sin(dir_rad)

        offset = robot_radius + 0.015
        start  = pymunk.Vec2d(robot_pos.x + cos_d * offset,
                               robot_pos.y + sin_d * offset)
        end    = pymunk.Vec2d(robot_pos.x + cos_d * (offset + cfg.range),
                               robot_pos.y + sin_d * (offset + cfg.range))

        hit = space.segment_query_first(start, end, 0.005, _ULTRASOUND_QUERY_FILTER)
        dist = (hit.alpha * cfg.range) if hit is not None else cfg.range

        if cfg.noise_std > 0:
            dist += float(rng.normal(0, cfg.noise_std))
        readings.append(max(0.0, min(cfg.range, dist)))
    return readings


# ── Line sensors ─────────────────────────────────────────────────────────────

def _point_near_segment(px: float, py: float,
                         x1: float, y1: float, x2: float, y2: float) -> bool:
    dx, dy = x2 - x1, y2 - y1
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-12:
        d = math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
    else:
        t  = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len_sq))
        cx = x1 + t * dx
        cy = y1 + t * dy
        d  = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
    return d < LINE_HALF_THICKNESS


def _point_near_arc(px: float, py: float,
                     cx: float, cy: float, r: float,
                     start_rad: float, end_rad: float) -> bool:
    d = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
    if abs(d - r) >= LINE_HALF_THICKNESS:
        return False
    angle = math.atan2(py - cy, px - cx) % (2 * math.pi)
    eps   = 0.12   # ~7° angular tolerance
    start = start_rad % (2 * math.pi)
    end   = end_rad   % (2 * math.pi)
    if start < end:
        return (start - eps) <= angle <= (end + eps)
    else:   # arc wraps through 0°/360°
        return angle >= (start - eps) or angle <= (end + eps)


def compute_line_sensors(
    robot_pos: pymunk.Vec2d,
    heading: float,
    cfg: LineSensorsConfig,
) -> list[bool]:
    cos_h = math.cos(heading)
    sin_h = math.sin(heading)
    results = []

    for lx, ly in cfg.positions:
        wx = robot_pos.x + cos_h * lx - sin_h * ly
        wy = robot_pos.y + sin_h * lx + cos_h * ly

        on_line = any(
            _point_near_segment(wx, wy, x1, y1, x2, y2)
            for (x1, y1), (x2, y2) in FIELD_LINE_SEGMENTS
        )
        if not on_line:
            on_line = any(_point_near_arc(wx, wy, *arc) for arc in FIELD_LINE_ARCS)

        results.append(on_line)
    return results


# ── Top-level combinator ──────────────────────────────────────────────────────

def compute_all_percepts(
    robot_body: pymunk.Body,
    config,
    ball_body: pymunk.Body,
    space: pymunk.Space,
    rng: np.random.Generator,
) -> dict:
    pos     = robot_body.position
    heading = robot_body.angle
    percepts: dict = {}

    if config.sensors.ir_ring:
        percepts["ir_ring"] = compute_ir_ring(
            pos, heading, ball_body.position, config.sensors.ir_ring, rng
        )
    if config.sensors.compass:
        percepts["compass"] = compute_compass(heading, config.sensors.compass, rng)
    if config.sensors.ultrasound:
        percepts["ultrasound"] = compute_ultrasound(
            pos, heading, config.body.radius, config.sensors.ultrasound, space, rng
        )
    if config.sensors.line_sensors:
        percepts["line_sensors"] = compute_line_sensors(
            pos, heading, config.sensors.line_sensors
        )

    return percepts
