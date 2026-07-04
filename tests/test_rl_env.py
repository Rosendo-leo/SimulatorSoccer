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


# ── Upgrades: referee no reward, domain randomization, sensores novos ────────

def test_domain_rand_varies_mass_and_noise():
    e = SoccerEnv(seed=3, domain_rand=True)
    base_mass = e._base_mass
    masses, noises = set(), set()
    for _ in range(5):
        e.reset()
        masses.add(round(e._agent.robot.body.mass, 5))
        noises.add(round(e._agent.robot.config.sensors.ir_ring.noise_std, 5))
    assert len(masses) > 1 and len(noises) > 1
    assert all(0.8 * base_mass <= m <= 1.2 * base_mass for m in masses)


def test_domain_rand_off_keeps_mass():
    e = SoccerEnv(seed=3, domain_rand=False)
    m0 = e._agent.robot.body.mass
    e.reset()
    assert e._agent.robot.body.mass == m0


def test_violation_penalizes_reward(tmp_path):
    # Agente parado com a bola colada → holding → reward negativo no tick
    e = SoccerEnv(seed=5, randomize=False, opponent_config=None)
    e.reset()
    e.engine.set_robot_pose("blue_1", 0.3, 0.3, 0.0)
    e.engine.set_ball_pose(0.455, 0.3)
    from sim.referee import HOLDING_TICKS
    total_before = sum(e.engine.violation_counts.values())
    rewards = []
    for _ in range(HOLDING_TICKS // e.frame_skip + 20):
        _, r, term, trunc, _ = e.step(np.zeros(4))
        rewards.append(r)
        if term or trunc:
            break
    assert sum(e.engine.violation_counts.values()) > total_before
    from rl.env import VIOLATION_REWARD
    assert min(rewards) <= VIOLATION_REWARD + 0.5   # tick da violação punido


def test_percepts_obs_includes_new_sensors():
    # example.yaml tem ball_velocity + opponent_lidar → obs maior
    e_full = SoccerEnv(agent_config="robots/example.yaml",
                       obs_mode="percepts", seed=1)
    e_base = SoccerEnv(agent_config="robots/striker_v3.yaml",
                       obs_mode="percepts", seed=1)
    # 2 floats de ball_velocity + 5 do lidar do example.yaml
    assert (e_full.observation_space.shape[0]
            >= e_base.observation_space.shape[0] + 7)


def test_camera_obs_mode():
    e = SoccerEnv(agent_config="robots/example.yaml", obs_mode="camera",
                  seed=1, randomize=False)
    assert e.observation_space.dtype == np.uint8
    obs, _ = e.reset()
    assert obs.shape == e.observation_space.shape          # (H, W, 3)
    assert obs.shape[2] == 3
    obs, r, term, trunc, info = e.step(np.zeros(4))
    assert obs.dtype == np.uint8


def test_camera_obs_requires_camera_block():
    with pytest.raises(ValueError, match="sensors.camera"):
        SoccerEnv(agent_config="robots/striker_v3.yaml", obs_mode="camera",
                  seed=1)
