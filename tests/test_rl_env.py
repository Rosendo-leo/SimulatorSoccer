"""Tests dos ambientes RL (Gymnasium + PettingZoo)."""
import numpy as np
import pytest

gym = pytest.importorskip("gymnasium")

from rl.env import SoccerEnv  # noqa: E402
from sim.field import HALF_L  # noqa: E402


@pytest.fixture
def env():
    e = SoccerEnv(seed=7)
    yield e


def test_reset_returns_obs_matching_space(env):
    obs, info = env.reset(seed=7)
    assert obs.shape == env.observation_space.shape
    assert obs.dtype == np.float32
    assert np.all(np.isfinite(obs))
    assert info == {}


def test_step_returns_five_tuple(env):
    env.reset(seed=7)
    obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
    assert obs.shape == env.observation_space.shape
    assert isinstance(reward, float)
    assert isinstance(terminated, bool) and isinstance(truncated, bool)
    assert "score" in info


def test_random_rollout_stays_finite(env):
    env.reset(seed=3)
    for _ in range(50):
        obs, reward, term, trunc, _ = env.step(env.action_space.sample())
        assert np.all(np.isfinite(obs))
        assert np.isfinite(reward)
        if term or trunc:
            env.reset()


def test_goal_gives_positive_reward_and_terminates():
    env = SoccerEnv(seed=1, randomize=False)
    env.reset(seed=1)
    # Bola dentro do gol amarelo → próximo step detecta gol do azul
    env.engine.set_ball_pose(HALF_L + 0.03, 0.0)
    obs, reward, terminated, truncated, info = env.step(np.zeros(4))
    assert terminated
    assert reward > 5.0
    assert info["score"]["blue"] == 1


def test_seed_reproducibility():
    e1, e2 = SoccerEnv(seed=42), SoccerEnv(seed=42)
    o1, _ = e1.reset(seed=42)
    o2, _ = e2.reset(seed=42)
    np.testing.assert_allclose(o1, o2)
    a = np.array([0.5, -0.2, 0.1, 0.0], dtype=np.float32)
    for _ in range(20):
        o1 = e1.step(a)[0]
        o2 = e2.step(a)[0]
    np.testing.assert_allclose(o1, o2)


def test_percepts_obs_mode():
    env = SoccerEnv(obs_mode="percepts", seed=5)
    obs, _ = env.reset(seed=5)
    # ir(16) + compass sin/cos(2) + us(4) + lines(4) + pos(2) p/ striker_v3
    assert obs.shape == env.observation_space.shape
    assert obs.shape[0] >= 16
    env.step(env.action_space.sample())


def test_truncation_at_max_steps():
    env = SoccerEnv(seed=9, max_steps=5, randomize=False)
    env.reset(seed=9)
    # Ação nula: sem gol; deve truncar no 5º step
    for i in range(5):
        _, _, term, trunc, _ = env.step(np.zeros(4))
        if term:
            pytest.skip("goal happened unexpectedly")
    assert trunc


# ── PettingZoo 2v2 ────────────────────────────────────────────────────────────

pz = pytest.importorskip("pettingzoo")


def test_pettingzoo_parallel_api():
    from pettingzoo.test import parallel_api_test
    from rl.soccer_pz import SoccerParallelEnv
    parallel_api_test(SoccerParallelEnv(seed=0), num_cycles=30)


def test_pettingzoo_mirror_symmetry():
    """Com mirror, azul e amarelo no kickoff veem observações ~idênticas."""
    from rl.soccer_pz import SoccerParallelEnv
    env = SoccerParallelEnv(seed=0, randomize=False, mirror=True)
    obs, _ = env.reset(seed=0)
    np.testing.assert_allclose(obs["blue_1"], obs["yellow_1"], atol=1e-6)
    np.testing.assert_allclose(obs["blue_2"], obs["yellow_2"], atol=1e-6)


def test_pettingzoo_goal_rewards_are_opposed():
    from rl.soccer_pz import SoccerParallelEnv
    env = SoccerParallelEnv(seed=0, randomize=False)
    env.reset(seed=0)
    env.engine.set_ball_pose(HALF_L + 0.03, 0.0)   # gol do azul
    zero = {a: np.zeros(4, dtype=np.float32) for a in env.agents}
    _, rewards, terms, _, _ = env.step(zero)
    assert all(terms.values())
    assert rewards["blue_1"] > 5.0 and rewards["blue_2"] > 5.0
    assert rewards["yellow_1"] < -5.0 and rewards["yellow_2"] < -5.0
