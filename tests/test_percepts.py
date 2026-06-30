"""Unit tests for percept computation.

Each test verifies that a known pose produces the expected sensor output.
noise_std=0 is used throughout to make results deterministic.
"""
import math
import pytest
import numpy as np
import pymunk

from sim.config_loader import (
    IRRingConfig, CompassConfig, UltrasoundConfig, LineSensorsConfig,
)
from sim.percepts import (
    compute_ir_ring, compute_compass, compute_ultrasound, compute_line_sensors,
)
from sim.field import (
    build_field, HALF_L, HALF_W, HALF_G,
    PENALTY_HALF_Y, PENALTY_DEPTH, CENTER_CIRCLE_RADIUS,
)

_RNG = np.random.default_rng(0)


# ── IR ring ──────────────────────────────────────────────────────────────────

def test_ir_ring_ball_forward():
    """Ball directly in front → sector 0 has highest intensity."""
    cfg = IRRingConfig(count=16, range=1.5, noise_std=0.0)
    readings = compute_ir_ring(
        pymunk.Vec2d(0.0, 0.0), 0.0, pymunk.Vec2d(0.5, 0.0), cfg, _RNG)
    assert len(readings) == 16
    assert readings[0] == max(readings), "Sector 0 should be strongest"


def test_ir_ring_ball_left():
    """Ball 90° to the left → sector N/4 strongest."""
    cfg = IRRingConfig(count=16, range=1.5, noise_std=0.0)
    readings = compute_ir_ring(
        pymunk.Vec2d(0.0, 0.0), 0.0, pymunk.Vec2d(0.0, 0.5), cfg, _RNG)
    assert readings[4] == max(readings), "Sector 4 (of 16) = 90° left"


def test_ir_ring_ball_out_of_range():
    """Ball beyond range → all zeros."""
    cfg = IRRingConfig(count=8, range=1.0, noise_std=0.0)
    readings = compute_ir_ring(
        pymunk.Vec2d(0.0, 0.0), 0.0, pymunk.Vec2d(2.0, 0.0), cfg, _RNG)
    assert all(v == 0.0 for v in readings)


def test_ir_ring_intensity_decreases_with_distance():
    cfg = IRRingConfig(count=8, range=2.0, noise_std=0.0)
    near = compute_ir_ring(
        pymunk.Vec2d(0, 0), 0.0, pymunk.Vec2d(0.3, 0.0), cfg, _RNG)
    far  = compute_ir_ring(
        pymunk.Vec2d(0, 0), 0.0, pymunk.Vec2d(1.5, 0.0), cfg, _RNG)
    assert near[0] > far[0]


def test_ir_ring_heading_relative():
    """Sector index shifts correctly when robot is rotated."""
    cfg = IRRingConfig(count=8, range=2.0, noise_std=0.0)
    # Ball in world +X; robot heading = 90° → ball is to the robot's right (sector 6)
    readings = compute_ir_ring(
        pymunk.Vec2d(0, 0), math.pi / 2, pymunk.Vec2d(0.5, 0.0), cfg, _RNG)
    assert readings[6] == max(readings), "Ball at sector 6 (270° right) when heading=90°"


# ── Compass ──────────────────────────────────────────────────────────────────

def test_compass_no_noise():
    cfg = CompassConfig(noise_std=0.0)
    assert compute_compass(1.23, cfg, _RNG) == pytest.approx(1.23)


def test_compass_with_noise():
    rng = np.random.default_rng(42)
    cfg = CompassConfig(noise_std=5.0)
    readings = [compute_compass(0.0, cfg, rng) for _ in range(500)]
    assert abs(np.mean(readings)) < 0.05
    assert np.std(readings) > 0.01


# ── Ultrasound ────────────────────────────────────────────────────────────────

@pytest.fixture()
def field_space():
    space = pymunk.Space()
    space.gravity = (0, 0)
    build_field(space)
    return space


def test_ultrasound_sidewall_hits_wall(field_space):
    """Ray pointing left (+Y) from centre should hit the top side wall."""
    cfg = UltrasoundConfig(count=1, directions=[90], range=3.0, noise_std=0.0)
    readings = compute_ultrasound(
        pymunk.Vec2d(0.0, 0.0), 0.0, 0.11, cfg, field_space, _RNG)
    # Top outer wall at y = HALF_TOTAL_W = 0.91
    # start offset = 0.11 + 0.015 = 0.125; wall inner face ≈ 0.91 - 0.01 = 0.90
    expected = 0.90 - 0.125
    assert readings[0] == pytest.approx(expected, abs=0.05)


def test_ultrasound_range_capped(field_space):
    """All four directions from centre should return less than sensor range."""
    cfg = UltrasoundConfig(count=4, directions=[0, 90, 180, 270], range=3.0, noise_std=0.0)
    readings = compute_ultrasound(
        pymunk.Vec2d(0.0, 0.0), 0.0, 0.11, cfg, field_space, _RNG)
    for r in readings:
        assert r < 3.0, "Should hit a wall before max range"


# ── Line sensors ──────────────────────────────────────────────────────────────

def test_line_sensor_on_right_boundary():
    """Sensor exactly on the right boundary line (x = HALF_L) activates."""
    cfg = LineSensorsConfig(count=1, positions=[(0.0, 0.0)])
    result = compute_line_sensors(pymunk.Vec2d(HALF_L, 0.0), 0.0, cfg)
    assert result[0] is True


def test_line_sensor_on_bottom_boundary():
    """Sensor on the bottom boundary line (y = -HALF_W) activates."""
    cfg = LineSensorsConfig(count=1, positions=[(0.0, 0.0)])
    result = compute_line_sensors(pymunk.Vec2d(0.0, -HALF_W), 0.0, cfg)
    assert result[0] is True


def test_line_sensor_away_from_line():
    """Sensor in open field (no lines nearby) does not activate."""
    cfg = LineSensorsConfig(count=1, positions=[(0.0, 0.0)])
    # (0.3, 0.2): not on boundary (±1.095, ±0.79), not on penalty area
    result = compute_line_sensors(pymunk.Vec2d(0.3, 0.2), 0.0, cfg)
    assert result[0] is False


def test_line_sensor_on_penalty_area_front():
    """Sensor on the front line of the right penalty area activates."""
    cfg = LineSensorsConfig(count=1, positions=[(0.0, 0.0)])
    # Right penalty area front is at x = HALF_L - PENALTY_DEPTH = 0.845, y = 0
    front_x = HALF_L - PENALTY_DEPTH   # 0.845
    result   = compute_line_sensors(pymunk.Vec2d(front_x, 0.0), 0.0, cfg)
    assert result[0] is True


def test_line_sensor_on_penalty_area_side():
    """Sensor on the top side of the left penalty area activates."""
    cfg = LineSensorsConfig(count=1, positions=[(0.0, 0.0)])
    # Left penalty area top side: y = PENALTY_HALF_Y, x between -HALF_L and -(HALF_L-PENALTY_DEPTH+corner)
    side_x = -HALF_L + PENALTY_DEPTH * 0.5   # well within the side segment
    result  = compute_line_sensors(pymunk.Vec2d(side_x, PENALTY_HALF_Y), 0.0, cfg)
    assert result[0] is True


def test_centre_circle_not_white_line():
    """Centre circle is a BLACK guide line — should NOT activate line sensors."""
    cfg = LineSensorsConfig(count=1, positions=[(0.0, 0.0)])
    # Point exactly on the centre circle
    result = compute_line_sensors(
        pymunk.Vec2d(CENTER_CIRCLE_RADIUS, 0.0), 0.0, cfg)
    assert result[0] is False, "Centre circle is black, not white — no sensor activation"
