"""Tests for YAML robot config parsing."""
import pytest
from pathlib import Path

from sim.config_loader import load_robot_config, RobotConfig

ROBOTS_DIR = Path(__file__).parent.parent / "robots"


# ── example.yaml ─────────────────────────────────────────────────────────────

def test_load_example_returns_robotconfig():
    config = load_robot_config(ROBOTS_DIR / "example.yaml")
    assert isinstance(config, RobotConfig)


def test_example_name():
    config = load_robot_config(ROBOTS_DIR / "example.yaml")
    assert config.name == "Example Robot"


def test_example_body():
    config = load_robot_config(ROBOTS_DIR / "example.yaml")
    assert config.body.shape == "circle"
    assert config.body.radius == pytest.approx(0.11)
    assert config.body.mass == pytest.approx(1.0)
    assert config.body.max_speed == pytest.approx(1.5)


def test_example_wheels():
    config = load_robot_config(ROBOTS_DIR / "example.yaml")
    assert config.wheels.type == "omnidirectional"
    assert config.wheels.count == 4
    assert len(config.wheels.positions) == 4


def test_example_ir_ring():
    config = load_robot_config(ROBOTS_DIR / "example.yaml")
    assert config.sensors.ir_ring is not None
    assert config.sensors.ir_ring.count == 16
    assert config.sensors.ir_ring.range == pytest.approx(1.5)
    assert config.sensors.ir_ring.noise_std == pytest.approx(0.03)


def test_example_compass():
    config = load_robot_config(ROBOTS_DIR / "example.yaml")
    assert config.sensors.compass is not None
    assert config.sensors.compass.noise_std == pytest.approx(2.0)


def test_example_ultrasound():
    config = load_robot_config(ROBOTS_DIR / "example.yaml")
    us = config.sensors.ultrasound
    assert us is not None
    assert us.count == 4
    assert len(us.directions) == 4
    assert us.range == pytest.approx(2.0)


def test_example_line_sensors():
    config = load_robot_config(ROBOTS_DIR / "example.yaml")
    ls = config.sensors.line_sensors
    assert ls is not None
    assert len(ls.positions) == 4
    for pos in ls.positions:
        assert len(pos) == 2


def test_example_kicker():
    config = load_robot_config(ROBOTS_DIR / "example.yaml")
    assert config.kicker is not None
    assert config.kicker.force == pytest.approx(5.0)
    assert config.kicker.cooldown == pytest.approx(2.0)


# ── Other robot files ─────────────────────────────────────────────────────────

def test_load_striker_v3():
    config = load_robot_config(ROBOTS_DIR / "striker_v3.yaml")
    assert config.name == "Striker v3"
    assert config.body.mass == pytest.approx(1.1)


def test_load_goalkeeper_v2():
    config = load_robot_config(ROBOTS_DIR / "goalkeeper_v2.yaml")
    assert config.name == "Goalkeeper v2"
    assert config.sensors.ir_ring.count == 12


def test_load_striker_omni():
    config = load_robot_config(ROBOTS_DIR / "striker_omni.yaml")
    assert config.name == "Striker Omni"
    assert config.wheels.type == "omnidirectional"
    assert config.body.max_speed == pytest.approx(1.8)


def test_load_goalkeeper_diff():
    config = load_robot_config(ROBOTS_DIR / "goalkeeper_diff.yaml")
    assert config.name == "Goalkeeper Diff"
    assert config.wheels.type == "differential"
    assert config.sensors.line_sensors.count == 6


# ── Error cases ───────────────────────────────────────────────────────────────

def test_missing_file_raises():
    with pytest.raises((FileNotFoundError, OSError)):
        load_robot_config(ROBOTS_DIR / "does_not_exist.yaml")
