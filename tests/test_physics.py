"""Tests for physics simulation: ball, kicker, and engine integration."""
from __future__ import annotations
import math
import numpy as np
import pytest
import pymunk

from sim.engine import SimEngine
from sim.field import (
    build_field, HALF_TOTAL_L, HALF_TOTAL_W, HALF_L, HALF_W, HALF_G,
)
from sim.ball import Ball, BALL_RADIUS
from sim.robot import Robot
from sim.hal_sim import SimHAL, BALL_RADIUS_APPROX
from sim.config_loader import (
    RobotConfig, BodyConfig, WheelsConfig,
    SensorsConfig, KickerConfig, IRRingConfig,
)


def _minimal_config() -> RobotConfig:
    return RobotConfig(
        name="TestBot",
        body=BodyConfig(shape="circle", radius=0.11, mass=1.0, max_speed=2.0),
        wheels=WheelsConfig(type="omnidirectional", count=4,
                            positions=[45, 135, 225, 315]),
        sensors=SensorsConfig(
            ir_ring=IRRingConfig(count=8, range=1.5, noise_std=0.0)
        ),
        kicker=KickerConfig(force=5.0, cooldown=0.5),
    )


# ── Ball ─────────────────────────────────────────────────────────────────────

def test_ball_initial_position():
    space = pymunk.Space()
    space.gravity = (0, 0)
    ball = Ball(space)
    x, y = ball.body.position
    assert x == pytest.approx(0.0)
    assert y == pytest.approx(0.0)


def test_ball_starts_at_rest():
    space = pymunk.Space()
    space.gravity = (0, 0)
    ball = Ball(space)
    vx, vy = ball.body.velocity
    assert vx == pytest.approx(0.0)
    assert vy == pytest.approx(0.0)


def test_ball_reset_clears_state():
    space = pymunk.Space()
    space.gravity = (0, 0)
    ball = Ball(space)
    ball.body.position = (0.5, 0.3)
    ball.body.velocity = (1.0, 2.0)
    ball.reset(0.0, 0.0)
    x, y = ball.body.position
    vx, vy = ball.body.velocity
    assert x == pytest.approx(0.0) and y == pytest.approx(0.0)
    assert vx == pytest.approx(0.0) and vy == pytest.approx(0.0)


def test_ball_bounces_off_side_wall():
    """Ball moving toward top side wall at y=0.5 must reverse vertical velocity."""
    space = pymunk.Space()
    space.gravity = (0, 0)
    build_field(space)
    ball = Ball(space)
    # Place near top outer wall, clear of goal cutout
    ball.body.position = (0.0, HALF_TOTAL_W - 0.05)
    ball.body.velocity = (0.0, 3.0)
    for _ in range(20):
        space.step(1 / 60 / 4)
    _, vy = ball.body.velocity
    assert vy < 0, "Ball should reverse Y-velocity after hitting top outer wall"


def test_ball_bounces_elasticity():
    """Ball loses some speed on bounce (elasticity < 1)."""
    space = pymunk.Space()
    space.gravity = (0, 0)
    build_field(space)
    ball = Ball(space)
    ball.body.position = (0.0, HALF_TOTAL_W - 0.05)
    ball.body.velocity = (0.0, 2.0)
    speed_before = 2.0
    for _ in range(30):
        space.step(1 / 60 / 4)
    _, vy = ball.body.velocity
    assert abs(vy) < speed_before, "Ball should lose speed due to elasticity < 1"


# ── Kicker ────────────────────────────────────────────────────────────────────

def test_kicker_applies_impulse_in_range():
    """Kicker fires when ball is within reach → ball gains forward velocity."""
    space = pymunk.Space()
    space.gravity = (0, 0)
    build_field(space)
    cfg = _minimal_config()
    robot = Robot(space, cfg, "blue", 0.0, 0.0, 0.0)
    ball = Ball(space)
    kick_reach = cfg.body.radius + BALL_RADIUS_APPROX + 0.02
    ball.body.position = (kick_reach - 0.01, 0.0)
    rng = np.random.default_rng(0)
    hal = SimHAL(robot, ball, space, cfg, rng)

    hal.kick()
    hal._apply_action(1 / 60)

    vx, _ = ball.body.velocity
    assert vx > 0.5, "Ball should move forward after a kick"


def test_kicker_no_impulse_out_of_range():
    """Ball too far away → kick has no effect."""
    space = pymunk.Space()
    space.gravity = (0, 0)
    build_field(space)
    cfg = _minimal_config()
    robot = Robot(space, cfg, "blue", 0.0, 0.0, 0.0)
    ball = Ball(space)
    ball.body.position = (0.5, 0.0)  # 0.5 m away, beyond kick reach ~0.173
    rng = np.random.default_rng(0)
    hal = SimHAL(robot, ball, space, cfg, rng)

    hal.kick()
    hal._apply_action(1 / 60)

    vx, vy = ball.body.velocity
    assert abs(vx) < 0.01 and abs(vy) < 0.01


def test_kicker_cooldown_prevents_second_kick():
    """Kick within cooldown window must not move ball."""
    space = pymunk.Space()
    space.gravity = (0, 0)
    build_field(space)
    cfg = _minimal_config()
    robot = Robot(space, cfg, "blue", 0.0, 0.0, 0.0)
    ball = Ball(space)
    kick_reach = cfg.body.radius + BALL_RADIUS_APPROX + 0.02
    ball.body.position = (kick_reach - 0.01, 0.0)
    rng = np.random.default_rng(0)
    hal = SimHAL(robot, ball, space, cfg, rng)

    # First kick — succeeds
    hal.kick()
    hal._apply_action(1 / 60)

    # Reset ball, try second kick immediately (cooldown still active)
    ball.body.position = (kick_reach - 0.01, 0.0)
    ball.body.velocity = (0.0, 0.0)
    hal.kick()
    hal._apply_action(1 / 60)

    vx, vy = ball.body.velocity
    assert abs(vx) < 0.01 and abs(vy) < 0.01, "Second kick within cooldown should do nothing"


def test_kicker_direction_follows_heading():
    """Ball kicked by robot facing +Y should gain positive Y velocity."""
    space = pymunk.Space()
    space.gravity = (0, 0)
    build_field(space)
    cfg = _minimal_config()
    heading = math.pi / 2  # facing up (+Y)
    robot = Robot(space, cfg, "blue", 0.0, 0.0, heading)
    ball = Ball(space)
    kick_reach = cfg.body.radius + BALL_RADIUS_APPROX + 0.02
    # Place ball directly above robot
    ball.body.position = (0.0, kick_reach - 0.01)
    rng = np.random.default_rng(0)
    hal = SimHAL(robot, ball, space, cfg, rng)

    hal.kick()
    hal._apply_action(1 / 60)

    _, vy = ball.body.velocity
    assert vy > 0.5, "Ball should move in heading direction (+Y) after kick"


# ── Engine integration ────────────────────────────────────────────────────────

def test_engine_step_returns_expected_keys():
    engine = SimEngine(seed=42)
    state = engine.step()
    for key in ("tick", "timestamp", "ball", "robots", "score", "state"):
        assert key in state


def test_engine_tick_increments():
    engine = SimEngine(seed=0)
    engine.step()
    engine.step()
    assert engine.tick == 2


def test_engine_score_starts_zero():
    engine = SimEngine(seed=0)
    assert engine.score == {"blue": 0, "yellow": 0}


def test_engine_yellow_goal_increments_blue_score():
    """Ball placed inside yellow goal → blue scores on next step."""
    engine = SimEngine(seed=0)
    engine._ball.body.position = (HALF_L + 0.01, 0.0)
    engine._ball.body.velocity = (0.1, 0.0)
    engine.step()
    assert engine.score["blue"] == 1


def test_engine_blue_goal_increments_yellow_score():
    """Ball placed inside blue goal → yellow scores on next step."""
    engine = SimEngine(seed=0)
    engine._ball.body.position = (-HALF_L - 0.01, 0.0)
    engine._ball.body.velocity = (-0.1, 0.0)
    engine.step()
    assert engine.score["yellow"] == 1


def test_engine_ball_stays_in_bounds_after_many_steps():
    """Ball should stay within outer walls for 300 steps with no robots."""
    engine = SimEngine(seed=7)
    engine._ball.body.velocity = (1.5, 0.8)
    state = {}
    for _ in range(300):
        state = engine.step()
    bx = state["ball"]["x"]
    by = state["ball"]["y"]
    assert abs(bx) <= HALF_TOTAL_L + 0.1
    assert abs(by) <= HALF_TOTAL_W + 0.1


def test_engine_paused_does_not_advance_tick():
    engine = SimEngine(seed=0)
    engine.toggle_pause()
    engine.step()
    engine.step()
    assert engine.tick == 0
