"""Testes do adaptador de self-play (rl/selfplay.py) — sem SB3/torch."""
import math

import numpy as np
import pytest

pytest.importorskip("gymnasium")

from sim.engine import SimEngine                     # noqa: E402
from sim.field import HALF_L                          # noqa: E402
from rl.selfplay import PolicyOpponent, _mirrored_vector_obs  # noqa: E402


class _StubModel:
    """Sempre anda para a frente (frame local) e chuta."""
    def predict(self, obs, deterministic=True):
        return np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32), None


def test_mirrored_obs_rotates_world():
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot("robots/striker_v3.yaml", team="yellow")
    # Amarelo em (0.4, 0) olhando −X (heading π); bola bem à frente dele
    engine.set_robot_pose("yellow_1", 0.4, 0.0, math.pi)
    engine.set_ball_pose(0.2, 0.0)
    obs = _mirrored_vector_obs(hal)

    assert obs[0] == pytest.approx(-0.4 / HALF_L, abs=1e-4)   # x rotacionado
    assert obs[2] == pytest.approx(0.0, abs=1e-4)             # sin(h+π)≈0
    assert obs[3] == pytest.approx(1.0, abs=1e-4)             # cos(h+π)≈1
    assert obs[6] == pytest.approx(-0.2 / HALF_L, abs=1e-4)   # bola rotacionada
    assert obs[10] > 0                                        # bola à FRENTE
    # dist bola→"gol dele" (rotacionado p/ +X): |1.095 − (−0.2)| = 1.295
    assert obs[12] == pytest.approx(1.295 / (2 * HALF_L), abs=1e-3)


def test_policy_opponent_drives_yellow_forward():
    engine = SimEngine(seed=0, referee=False)
    engine.add_robot("robots/striker_v3.yaml", team="blue")
    engine.add_robot("robots/striker_v3.yaml", team="yellow",
                     strategy_fn=PolicyOpponent(_StubModel()))
    x0 = engine.entries[1].robot.body.position.x
    for _ in range(60):
        engine.step()
    x1 = engine.entries[1].robot.body.position.x
    # 'Frente' do amarelo (heading π) é −X no mundo: andou para o gol azul
    assert x1 < x0 - 0.3


def test_soccer_env_accepts_callable_opponent():
    from rl.env import SoccerEnv
    calls = {"n": 0}

    def opponent(hal):
        calls["n"] += 1
        hal.set_velocity(0.0, 0.0, 0.0)

    env = SoccerEnv(opponent_strategy=opponent, seed=1, randomize=False)
    env.reset()
    env.step(np.zeros(4))
    assert calls["n"] > 0
