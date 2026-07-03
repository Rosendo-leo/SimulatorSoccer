"""Testes do árbitro automático (Rules 2026 §2.5–2.9) e perfis de liga."""
import math

import pytest

from sim.config_loader import ConfigError, load_robot_config
from sim.field import HALF_L, PENALTY_DEPTH
from sim.referee import (
    HOLDING_TICKS, LACK_OF_PROGRESS_TICKS,
    Referee, RobotSnapshot, Violation,
    check_multiple_defense, check_pushing, in_penalty_area,
)

BALL_R = 0.0215


def _robot(rid, team, x, y, radius=0.11, vx=0.0, vy=0.0):
    return RobotSnapshot(robot_id=rid, team=team, x=x, y=y,
                         radius=radius, vx=vx, vy=vy)


# ── Geometria ─────────────────────────────────────────────────────────────────

def test_in_penalty_area():
    front = HALF_L - PENALTY_DEPTH
    assert in_penalty_area(-(front + 0.05), 0.0, "blue")
    assert in_penalty_area(front + 0.05, 0.3, "yellow")
    assert not in_penalty_area(0.0, 0.0, "blue")
    assert not in_penalty_area(front + 0.05, 0.5, "yellow")   # |y| > 0.40
    assert not in_penalty_area(-(front + 0.05), 0.0, "yellow")


# ── Pushing ───────────────────────────────────────────────────────────────────

def test_pushing_detected_in_area():
    x = -(HALF_L - 0.10)   # dentro da área azul
    a = _robot("blue_1", "blue", x, 0.0)
    b = _robot("yellow_1", "yellow", x + 0.215, 0.0)   # em contato (2×0.11)
    ball = (x + 0.11 + BALL_R, 0.10)                    # encostada no blue_1
    v = check_pushing([a, b], ball, BALL_R)
    assert v is not None and v.kind == "pushing"


def test_pushing_ignores_contact_outside_areas():
    a = _robot("blue_1", "blue", 0.0, 0.0)
    b = _robot("yellow_1", "yellow", 0.215, 0.0)
    ball = (0.11 + BALL_R, 0.0)
    assert check_pushing([a, b], ball, BALL_R) is None


def test_pushing_requires_ball_contact():
    x = -(HALF_L - 0.10)
    a = _robot("blue_1", "blue", x, 0.0)
    b = _robot("yellow_1", "yellow", x + 0.215, 0.0)
    ball = (0.5, 0.5)   # bola longe
    assert check_pushing([a, b], ball, BALL_R) is None


def test_pushing_ignores_same_team():
    x = -(HALF_L - 0.10)
    a = _robot("blue_1", "blue", x, 0.0)
    b = _robot("blue_2", "blue", x + 0.215, 0.0)
    ball = (x + 0.11 + BALL_R, 0.0)
    assert check_pushing([a, b], ball, BALL_R) is None


# ── Multiple defense ──────────────────────────────────────────────────────────

def test_multiple_defense_moves_farthest_from_ball():
    x = -(HALF_L - 0.10)
    ball = (x, 0.35)
    near = _robot("blue_1", "blue", x, 0.30)
    far  = _robot("blue_2", "blue", x, -0.30)
    v = check_multiple_defense([near, far], ball)
    assert v is not None
    assert v.kind == "multiple_defense"
    assert v.robot_id == "blue_2"


def test_multiple_defense_ignores_opponent_area():
    # dois amarelos na área AZUL não é multiple defense
    x = -(HALF_L - 0.10)
    a = _robot("yellow_1", "yellow", x, 0.30)
    b = _robot("yellow_2", "yellow", x, -0.30)
    assert check_multiple_defense([a, b], (0, 0)) is None


def test_single_defender_ok():
    x = HALF_L - 0.10
    a = _robot("yellow_1", "yellow", x, 0.0)
    assert check_multiple_defense([a], (0, 0)) is None


# ── Lack of progress ──────────────────────────────────────────────────────────

def test_lack_of_progress_triggers_after_threshold():
    ref = Referee()
    ball = (0.5, 0.2)
    violations = []
    for _ in range(LACK_OF_PROGRESS_TICKS + 2):
        violations += ref.step([], ball, (0, 0), BALL_R)
    kinds = [v.kind for v in violations]
    assert "lack_of_progress" in kinds


def test_lack_of_progress_resets_when_ball_moves():
    ref = Referee()
    for i in range(LACK_OF_PROGRESS_TICKS * 2):
        # bola se desloca mais que o eps a cada 100 ticks
        ball = (0.1 * (i // 100), 0.0)
        assert ref.step([], ball, (0, 0), BALL_R) == []


# ── Holding ───────────────────────────────────────────────────────────────────

def test_holding_triggers_when_ball_stuck_to_robot():
    ref = Referee()
    r = _robot("blue_1", "blue", 0.0, 0.0)
    ball = (0.11 + BALL_R + 0.01, 0.0)   # 1 cm do corpo
    violations = []
    for _ in range(HOLDING_TICKS + 2):
        violations += ref.step([r], ball, (0, 0), BALL_R)
    holding = [v for v in violations if v.kind == "holding"]
    assert holding and holding[0].robot_id == "blue_1"


def test_holding_not_triggered_when_ball_moving_fast():
    ref = Referee()
    r = _robot("blue_1", "blue", 0.0, 0.0)
    ball = (0.11 + BALL_R + 0.01, 0.0)
    for _ in range(HOLDING_TICKS * 2):
        vs = ref.step([r], ball, (1.5, 0.0), BALL_R)   # bola rápida rel. robô
        assert all(v.kind != "holding" for v in vs)


# ── Integração com o engine ───────────────────────────────────────────────────

def test_engine_multiple_defense_teleports_robot():
    from sim.engine import SimEngine
    engine = SimEngine(seed=1, referee=True)
    engine.add_robot("robots/example.yaml", team="blue")
    engine.add_robot("robots/example.yaml", team="blue")
    x = -(HALF_L - 0.12)
    engine.set_robot_pose("blue_1", x, 0.25)
    engine.set_robot_pose("blue_2", x, -0.25)
    engine.set_ball_pose(0.5, 0.0)
    engine.step()
    assert engine.last_violation is not None
    assert engine.last_violation["kind"] == "multiple_defense"
    # um dos dois saiu da área
    inside = [
        e for e in engine.entries
        if in_penalty_area(e.robot.body.position.x,
                           e.robot.body.position.y, "blue")
    ]
    assert len(inside) == 1


def test_engine_referee_disabled():
    from sim.engine import SimEngine
    engine = SimEngine(seed=1, referee=False)
    engine.add_robot("robots/example.yaml", team="blue")
    engine.add_robot("robots/example.yaml", team="blue")
    x = -(HALF_L - 0.12)
    engine.set_robot_pose("blue_1", x, 0.25)
    engine.set_robot_pose("blue_2", x, -0.25)
    engine.step()
    assert engine.last_violation is None


def test_engine_mark_damaged():
    from sim.engine import SimEngine
    engine = SimEngine(seed=1)
    engine.add_robot("robots/example.yaml", team="blue")
    engine.mark_damaged("blue_1")
    assert engine.entries[0].penalized
    with pytest.raises(KeyError):
        engine.mark_damaged("yellow_9")


def test_state_serializes_referee():
    from sim.engine import SimEngine
    engine = SimEngine(seed=1)
    state = engine.get_state()
    assert state["referee"] == {"last_violation": None, "counts": {}}


# ── Perfis de liga (A1/A2) ────────────────────────────────────────────────────

def _write_yaml(tmp_path, body_extra="", league=None):
    league_line = f"league: {league}\n  " if league else ""
    text = f"""
robot:
  {league_line}name: T
  body: {{ {body_extra} }}
"""
    p = tmp_path / "r.yaml"
    p.write_text(text)
    return str(p)


def test_league_default_is_infrared(tmp_path):
    cfg = load_robot_config(_write_yaml(tmp_path, "radius: 0.11"))
    assert cfg.league == "infrared"


def test_vision_league_18cm_limit(tmp_path):
    path = _write_yaml(tmp_path, "radius: 0.10", league="vision")
    with pytest.raises(ConfigError, match="vision"):
        load_robot_config(path)


def test_vision_league_accepts_9cm(tmp_path):
    cfg = load_robot_config(_write_yaml(tmp_path, "radius: 0.09",
                                        league="vision"))
    assert cfg.league == "vision"


def test_infrared_mass_limit_1500g(tmp_path):
    path = _write_yaml(tmp_path, "radius: 0.11, mass: 2.0")
    with pytest.raises(ConfigError, match="body.mass"):
        load_robot_config(path)


def test_vision_has_no_mass_limit(tmp_path):
    cfg = load_robot_config(_write_yaml(tmp_path, "radius: 0.09, mass: 5.0",
                                        league="vision"))
    assert cfg.body.mass == 5.0


def test_unknown_league_rejected(tmp_path):
    path = _write_yaml(tmp_path, "radius: 0.09", league="lightweight")
    with pytest.raises(ConfigError, match="league"):
        load_robot_config(path)


# ── Kicker test (A5) ──────────────────────────────────────────────────────────

def test_kicker_test_runs_and_reports():
    from sim.kicker_test import run_kicker_test
    result = run_kicker_test("robots/striker_v3.yaml", seed=0)
    assert result.kicked
    assert result.max_x > 0.0          # bola cruzou o meio-campo
    assert isinstance(result.passed, bool)
    assert "Kicker test" in result.report()
