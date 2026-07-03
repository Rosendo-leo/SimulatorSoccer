"""Testes do dribbler (B3) e do kicker multi-ângulo (B4)."""
import math

import pytest

from sim.config_loader import ConfigError, load_robot_config
from sim.engine import SimEngine


def _yaml(tmp_path, extra):
    p = tmp_path / "r.yaml"
    p.write_text(f"""
robot:
  name: T
  body: {{ radius: 0.10, max_speed: 1.5 }}
{extra}
""")
    return str(p)


# ── Config ────────────────────────────────────────────────────────────────────

def test_dribbler_parsed(tmp_path):
    cfg = load_robot_config(_yaml(tmp_path, """
  dribbler: { position: back, strength: 2.0, capture_radius: 0.06 }
"""))
    assert cfg.dribbler.position == "back"
    assert cfg.dribbler.strength == 2.0


def test_dribbler_bad_position(tmp_path):
    with pytest.raises(ConfigError, match="dribbler.position"):
        load_robot_config(_yaml(tmp_path, "  dribbler: { position: left }"))


def test_kicker_aim_range_validated(tmp_path):
    with pytest.raises(ConfigError, match="aim_range"):
        load_robot_config(_yaml(tmp_path, "  kicker: { aim_range: 400 }"))
    cfg = load_robot_config(_yaml(tmp_path, "  kicker: { aim_range: 360 }"))
    assert cfg.kicker.aim_range == 360


def test_set_dribbler_requires_config(tmp_path):
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot(_yaml(tmp_path, ""), team="blue")
    with pytest.raises(NotImplementedError):
        hal.set_dribbler(True)


# ── Dribbler: física de captura ───────────────────────────────────────────────

def _dribbler_engine(tmp_path, position="front"):
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot(_yaml(tmp_path, f"""
  dribbler: {{ position: {position} }}
"""), team="blue")
    return engine, hal


def test_dribbler_holds_ball_while_strafing(tmp_path):
    engine, hal = _dribbler_engine(tmp_path)
    engine.set_robot_pose("blue_1", 0.0, 0.0, 0.0)
    engine.set_ball_pose(0.147, 0.0)        # na boca (0.10 + 0.043 + 0.004)
    hal.set_dribbler(True)

    def strafe(h):
        h.set_velocity(0.0, 0.5, 0.0)       # anda de lado
    engine.entries[0].strategy = strafe
    for _ in range(90):                     # 1,5 s
        engine.step()
    rx, ry = engine.entries[0].robot.body.position
    bx, by = engine.ball.body.position
    gap = math.hypot(bx - rx, by - ry) - 0.10 - 0.043
    assert gap < 0.05                       # bola continua colada


def test_without_dribbler_ball_is_left_behind(tmp_path):
    engine, hal = _dribbler_engine(tmp_path)
    engine.set_robot_pose("blue_1", 0.0, 0.0, 0.0)
    engine.set_ball_pose(0.147, 0.0)
    # dribbler DESLIGADO — mesmo movimento lateral
    def strafe(h):
        h.set_velocity(0.0, 0.5, 0.0)
    engine.entries[0].strategy = strafe
    for _ in range(90):
        engine.step()
    rx, ry = engine.entries[0].robot.body.position
    bx, by = engine.ball.body.position
    gap = math.hypot(bx - rx, by - ry) - 0.10 - 0.043
    assert gap > 0.10                       # bola ficou para trás


def test_dribbler_exempts_holding(tmp_path):
    from sim.referee import HOLDING_TICKS
    engine2 = SimEngine(seed=0, referee=True)
    _, hal2 = engine2.add_robot(_yaml(tmp_path, """
  dribbler: { position: front }
"""), team="blue")
    engine2.set_robot_pose("blue_1", 0.3, 0.3, 0.0)
    engine2.set_ball_pose(0.447, 0.3)
    hal2.set_dribbler(True)
    for _ in range(HOLDING_TICKS + 60):
        engine2.step()
    assert engine2.violation_counts.get("holding", 0) == 0


def test_holding_still_fires_without_dribbler(tmp_path):
    from sim.referee import HOLDING_TICKS
    engine = SimEngine(seed=0, referee=True)
    engine.add_robot(_yaml(tmp_path, ""), team="blue")
    engine.set_robot_pose("blue_1", 0.3, 0.3, 0.0)
    engine.set_ball_pose(0.44, 0.3)          # encostada, sem dribbler
    for _ in range(HOLDING_TICKS + 60):
        engine.step()
    assert engine.violation_counts.get("holding", 0) >= 1


# ── Kicker multi-ângulo ───────────────────────────────────────────────────────

def _kick_engine(tmp_path, aim_range):
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot(_yaml(tmp_path, f"""
  kicker: {{ force: 5.0, cooldown: 2.0, aim_range: {aim_range} }}
"""), team="blue")
    engine.set_robot_pose("blue_1", 0.0, 0.0, 0.0)
    return engine, hal


def test_kick_straight_by_default(tmp_path):
    engine, hal = _kick_engine(tmp_path, 0)
    engine.set_ball_pose(0.15, 0.0)
    hal._refresh_percepts(); hal.kick(); hal._apply_action(1 / 60)
    vx, vy = engine.ball.body.velocity
    assert vx > 1.0 and abs(vy) < 0.2


def test_kick_angle_clamped_without_aim_range(tmp_path):
    engine, hal = _kick_engine(tmp_path, 0)
    engine.set_ball_pose(0.15, 0.0)
    hal._refresh_percepts(); hal.kick(60); hal._apply_action(1 / 60)
    vx, vy = engine.ball.body.velocity
    # aim_range 0 → ângulo comandado é ignorado, chute sai reto
    assert vx > 1.0 and abs(vy) < 0.2


def test_kick_steered_with_aim_range(tmp_path):
    engine, hal = _kick_engine(tmp_path, 90)
    engine.set_ball_pose(0.15, 0.0)
    hal._refresh_percepts(); hal.kick(45); hal._apply_action(1 / 60)
    vx, vy = engine.ball.body.velocity
    angle = math.degrees(math.atan2(vy, vx))
    assert 30 < angle < 60                   # saiu a ~45°


def test_kick_requires_ball_near_mouth(tmp_path):
    engine, hal = _kick_engine(tmp_path, 0)
    engine.set_ball_pose(-0.15, 0.0)         # bola ATRÁS do robô
    hal._refresh_percepts(); hal.kick(); hal._apply_action(1 / 60)
    vx, vy = engine.ball.body.velocity
    assert math.hypot(vx, vy) < 0.05         # não chutou


def test_back_kick_with_360(tmp_path):
    engine, hal = _kick_engine(tmp_path, 360)
    engine.set_ball_pose(-0.15, 0.0)
    hal._refresh_percepts(); hal.kick(180); hal._apply_action(1 / 60)
    vx, vy = engine.ball.body.velocity
    assert vx < -1.0                          # chute para trás
