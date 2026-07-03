"""Testes de ball_velocity (B5) e opponent_lidar (B2)."""
import math

import pytest

from sim.config_loader import ConfigError, load_robot_config
from sim.engine import SimEngine


def _yaml(tmp_path, sensors):
    p = tmp_path / "r.yaml"
    p.write_text(f"""
robot:
  name: T
  body: {{ radius: 0.10 }}
  sensors:
{sensors}
""")
    return str(p)


BOTH = """
    ball_velocity: { noise_std: 0.0 }
    opponent_lidar: { directions: [0], range: 1.0, noise_std: 0.0 }
"""


# ── Config ────────────────────────────────────────────────────────────────────

def test_sensors_parsed(tmp_path):
    cfg = load_robot_config(_yaml(tmp_path, BOTH))
    assert cfg.sensors.ball_velocity.noise_std == 0.0
    assert cfg.sensors.opponent_lidar.directions == [0]


def test_lidar_defaults(tmp_path):
    cfg = load_robot_config(_yaml(tmp_path, "    opponent_lidar: {}"))
    assert cfg.sensors.opponent_lidar.directions == [-40, -20, 0, 20, 40]
    assert cfg.sensors.opponent_lidar.range == 1.0


def test_lidar_empty_directions_rejected(tmp_path):
    with pytest.raises(ConfigError, match="opponent_lidar.directions"):
        load_robot_config(_yaml(
            tmp_path, "    opponent_lidar: { directions: [] }"))


def test_ball_velocity_negative_noise_rejected(tmp_path):
    with pytest.raises(ConfigError, match="ball_velocity.noise_std"):
        load_robot_config(_yaml(
            tmp_path, "    ball_velocity: { noise_std: -1 }"))


# ── HAL sem os sensores configurados ─────────────────────────────────────────

def test_hal_raises_without_sensor():
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot("robots/striker_v3.yaml", team="blue")
    engine.step()
    with pytest.raises(NotImplementedError):
        hal.read_ball_velocity()
    with pytest.raises(NotImplementedError):
        hal.read_opponent_lidar()


# ── Leituras ──────────────────────────────────────────────────────────────────

def test_ball_velocity_reads_true_velocity(tmp_path):
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot(_yaml(tmp_path, BOTH), team="blue")
    engine.ball.body.velocity = (1.2, -0.7)
    hal._refresh_percepts()
    vx, vy = hal.read_ball_velocity()
    # damping ainda não foi aplicado — leitura sem ruído é exata
    assert vx == pytest.approx(1.2, abs=1e-6)
    assert vy == pytest.approx(-0.7, abs=1e-6)


def test_ball_velocity_noise(tmp_path):
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot(_yaml(tmp_path, """
    ball_velocity: { noise_std: 0.2 }
"""), team="blue")
    engine.ball.body.velocity = (0.0, 0.0)
    samples = []
    for _ in range(50):
        hal._refresh_percepts()
        samples.append(hal.read_ball_velocity()[0])
    assert any(abs(s) > 1e-6 for s in samples)      # ruído presente
    assert abs(sum(samples) / len(samples)) < 0.15  # média ~0


def test_lidar_detects_robot_ahead(tmp_path):
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot(_yaml(tmp_path, BOTH), team="blue")
    engine.add_robot("robots/striker_v3.yaml", team="yellow")
    engine.set_robot_pose("blue_1", 0.0, 0.0, 0.0)     # olhando +X
    engine.set_robot_pose("yellow_1", 0.5, 0.0)        # 50 cm à frente
    hal._refresh_percepts()
    dist = hal.read_opponent_lidar()[0]
    # distância do início do raio (borda do robô) até a borda do oponente:
    # 0.5 − 0.10 (raio próprio) − 0.015 (offset) − 0.11 (raio oponente) ≈ 0.275
    assert dist == pytest.approx(0.275, abs=0.03)


def test_lidar_ignores_ball_and_walls(tmp_path):
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot(_yaml(tmp_path, BOTH), team="blue")
    engine.set_robot_pose("blue_1", 0.6, 0.0, 0.0)   # bola (0,0) atrás; parede à frente
    engine.set_ball_pose(0.8, 0.0)                   # bola diretamente à frente
    hal._refresh_percepts()
    # nada de robô à frente → range cheio, mesmo com bola e parede no caminho
    assert hal.read_opponent_lidar()[0] == pytest.approx(1.0, abs=1e-6)


def test_lidar_detects_teammate_too(tmp_path):
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot(_yaml(tmp_path, BOTH), team="blue")
    engine.add_robot("robots/striker_v3.yaml", team="blue")
    engine.set_robot_pose("blue_1", 0.0, 0.0, 0.0)
    engine.set_robot_pose("blue_2", 0.4, 0.0)
    hal._refresh_percepts()
    assert hal.read_opponent_lidar()[0] < 0.25


def test_percepts_serialized_in_state(tmp_path):
    engine = SimEngine(seed=0, referee=False)
    engine.add_robot(_yaml(tmp_path, BOTH), team="blue")
    engine.step()
    p = engine.get_state()["robots"][0]["percepts"]
    assert "ball_velocity" in p and "opponent_lidar" in p
