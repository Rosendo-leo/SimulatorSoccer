"""Tests for YAML validation (ConfigError) and 2v2 support."""
import math
import textwrap
import pytest

from sim.config_loader import load_robot_config, ConfigError
from sim.engine import SimEngine, _BLUE_STARTS, _YELLOW_STARTS


# ── Validation ────────────────────────────────────────────────────────────────

def _write_yaml(tmp_path, body: str):
    path = tmp_path / "robot.yaml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_valid_minimal_config(tmp_path):
    path = _write_yaml(tmp_path, """
        robot:
          name: "Minimal"
    """)
    cfg = load_robot_config(path)
    assert cfg.name == "Minimal"


def test_missing_robot_key(tmp_path):
    path = _write_yaml(tmp_path, """
        nome_errado:
          name: "Oops"
    """)
    with pytest.raises(ConfigError, match="'robot:' key missing"):
        load_robot_config(path)


def test_radius_above_rcj_limit(tmp_path):
    path = _write_yaml(tmp_path, """
        robot:
          body: { radius: 0.15 }
    """)
    with pytest.raises(ConfigError, match="body.radius"):
        load_robot_config(path)


def test_negative_mass(tmp_path):
    path = _write_yaml(tmp_path, """
        robot:
          body: { mass: -1.0 }
    """)
    with pytest.raises(ConfigError, match="body.mass"):
        load_robot_config(path)


def test_invalid_shape(tmp_path):
    path = _write_yaml(tmp_path, """
        robot:
          body: { shape: triangle }
    """)
    with pytest.raises(ConfigError, match="body.shape"):
        load_robot_config(path)


def test_invalid_wheel_type(tmp_path):
    path = _write_yaml(tmp_path, """
        robot:
          wheels: { type: tank }
    """)
    with pytest.raises(ConfigError, match="wheels.type"):
        load_robot_config(path)


def test_omni_needs_three_wheels(tmp_path):
    path = _write_yaml(tmp_path, """
        robot:
          wheels: { type: omnidirectional, count: 2, positions: [90, 270] }
    """)
    with pytest.raises(ConfigError, match=">= 3 wheels"):
        load_robot_config(path)


def test_ir_ring_zero_count(tmp_path):
    path = _write_yaml(tmp_path, """
        robot:
          sensors:
            ir_ring: { count: 0 }
    """)
    with pytest.raises(ConfigError, match="ir_ring.count"):
        load_robot_config(path)


def test_negative_noise(tmp_path):
    path = _write_yaml(tmp_path, """
        robot:
          sensors:
            compass: { noise_std: -1.0 }
    """)
    with pytest.raises(ConfigError, match="compass.noise_std"):
        load_robot_config(path)


def test_line_sensor_outside_body(tmp_path):
    path = _write_yaml(tmp_path, """
        robot:
          body: { radius: 0.10 }
          sensors:
            line_sensors:
              positions:
                - [0.20, 0.0]
    """)
    with pytest.raises(ConfigError, match="outside the robot body"):
        load_robot_config(path)


def test_kicker_negative_force(tmp_path):
    path = _write_yaml(tmp_path, """
        robot:
          kicker: { force: -5.0 }
    """)
    with pytest.raises(ConfigError, match="kicker.force"):
        load_robot_config(path)


def test_shipped_robots_all_valid():
    """Every YAML in robots/ must pass validation."""
    from pathlib import Path
    robots_dir = Path(__file__).parent.parent / "robots"
    for path in robots_dir.glob("*.yaml"):
        load_robot_config(path)   # must not raise


# ── 2v2 ───────────────────────────────────────────────────────────────────────

def _make_2v2() -> SimEngine:
    engine = SimEngine(seed=1)
    for team in ("blue", "yellow"):
        for _ in range(2):
            engine.add_robot("robots/example.yaml", team=team)
    return engine


def test_2v2_four_robots():
    engine = _make_2v2()
    state = engine.step()
    assert len(state["robots"]) == 4
    ids = [r["id"] for r in state["robots"]]
    assert ids == ["blue_1", "blue_2", "yellow_1", "yellow_2"]


def test_2v2_distinct_kickoff_positions():
    """Two robots on the same team must not spawn on top of each other."""
    engine = _make_2v2()
    state = engine.get_state()
    for team in ("blue", "yellow"):
        bots = [r for r in state["robots"] if r["team"] == team]
        d = math.hypot(bots[0]["x"] - bots[1]["x"], bots[0]["y"] - bots[1]["y"])
        assert d > 0.25, f"{team} robots spawn {d:.2f} m apart (need > 2 radii)"


def test_2v2_kickoff_reset_restores_slots():
    engine = _make_2v2()
    # Scatter robots, then force a kickoff reset
    for entry in engine._entries:
        entry.robot.body.position = (0.5, 0.5)
    engine._kickoff_reset()
    state = engine.get_state()
    got = {(r["id"]): (r["x"], r["y"]) for r in state["robots"]}
    assert got["blue_1"]   == pytest.approx(_BLUE_STARTS[0][:2])
    assert got["blue_2"]   == pytest.approx(_BLUE_STARTS[1][:2])
    assert got["yellow_1"] == pytest.approx(_YELLOW_STARTS[0][:2])
    assert got["yellow_2"] == pytest.approx(_YELLOW_STARTS[1][:2])


def test_2v2_runs_headless_without_error():
    engine = _make_2v2()
    engine.run_headless(120)
    assert engine.tick == 120


def test_2v2_no_lasting_overlap():
    """After many steps, no two active robots overlap significantly."""
    engine = _make_2v2()
    engine.run_headless(300)
    state = engine.get_state()
    active = [r for r in state["robots"] if not r["penalized"]]
    radius = 0.11
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            d = math.hypot(active[i]["x"] - active[j]["x"],
                           active[i]["y"] - active[j]["y"])
            assert d > radius * 1.2, (
                f"{active[i]['id']} and {active[j]['id']} overlap: {d:.3f} m"
            )
