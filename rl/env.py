"""Ambiente Gymnasium single-agent sobre o SimEngine.

O agente controla o robô azul (ataca o gol amarelo em +X); o adversário roda
uma estratégia scriptada (examples.*). Sem renderização — headless por design;
para assistir a uma política treinada, use o viewer normal com um adapter.

Observação (`obs_mode`):
  "vector"   — estado global normalizado (14 floats, ground truth). Aprende
               rápido; bom para prototipagem de reward/currículo.
  "percepts" — apenas o que a HAL fornece (IR ring + bússola sin/cos +
               ultrassom + line sensors + odometria). Realista (sim2real);
               tamanho depende do YAML do robô.
  "camera"   — frame RGB (H, W, 3) uint8 da câmera simulada (exige bloco
               sensors.camera no YAML do agente; use CnnPolicy no SB3).

Ação: Box(-1, 1, (4,)) → [vx, vy, omega, kick]
  vx/vy escalados por body.max_speed (frame local: vx=frente, vy=esquerda),
  omega escalado por MAX_OMEGA, kick dispara quando > 0.5.
"""
from __future__ import annotations
import importlib
import math
from pathlib import Path

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from sim.engine import SimEngine, PHYSICS_DT
from sim.field import HALF_L, HALF_W
from sim.hal_sim import MAX_BALL_SPEED

_ROOT = Path(__file__).parent.parent

MAX_OMEGA = 6.0          # rad/s no comando de rotação (|a[2]| = 1)
KICK_THRESHOLD = 0.5

# Pesos de reward shaping
W_BALL_TO_GOAL  = 3.0    # bola avançando na direção do gol adversário
W_ROBOT_TO_BALL = 1.0    # robô se aproximando da bola
STEP_PENALTY    = 0.002  # incentivo a resolver rápido
GOAL_REWARD     = 10.0
PENALTY_REWARD  = -5.0   # robô penalizado (saiu do campo)
VIOLATION_REWARD = -2.0  # violação do árbitro atribuída ao agente
                         # (holding / multiple_defense / pushing — Rules 2026)


def _load_strategy(module_name: str):
    return importlib.import_module(module_name).strategy


class SoccerEnv(gym.Env):
    metadata = {"render_modes": [], "render_fps": int(1 / PHYSICS_DT)}

    def __init__(
        self,
        agent_config: str = "robots/striker_v3.yaml",
        opponent_config: str | None = "robots/goalkeeper_v2.yaml",
        opponent_strategy: str = "examples.defender_strategy",
        obs_mode: str = "vector",
        frame_skip: int = 4,
        max_steps: int = 1800,        # 1800 decisões × 4 frames = 2 min de jogo
        randomize: bool = True,
        domain_rand: bool = False,    # randomiza massa/ruído por episódio
        seed: int | None = None,
    ) -> None:
        if obs_mode not in ("vector", "percepts", "camera"):
            raise ValueError(
                f"obs_mode must be 'vector', 'percepts' or 'camera', "
                f"got {obs_mode!r}")
        self._agent_config    = str(_ROOT / agent_config)
        self._opponent_config = str(_ROOT / opponent_config) if opponent_config else None
        # opponent_strategy: módulo ("examples.x") OU callable strategy(hal)
        # OU factory sem argumentos que devolve uma strategy (self-play)
        self._opponent_fn = (opponent_strategy if callable(opponent_strategy)
                             else _load_strategy(opponent_strategy))
        self.obs_mode    = obs_mode
        self.frame_skip  = frame_skip
        self.max_steps   = max_steps
        self.randomize   = randomize
        self.domain_rand = domain_rand

        self._build(seed)

        self.action_space = spaces.Box(-1.0, 1.0, shape=(4,), dtype=np.float32)
        obs = self._observe()
        if obs_mode == "camera":
            self.observation_space = spaces.Box(
                0, 255, shape=obs.shape, dtype=np.uint8)
        else:
            self.observation_space = spaces.Box(
                -np.inf, np.inf, shape=obs.shape, dtype=np.float32)

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _build(self, seed: int | None) -> None:
        self.engine = SimEngine(seed=seed)
        _, self._hal = self.engine.add_robot(
            self._agent_config, "blue", strategy_fn=None)
        self._agent = self.engine.entries[0]
        if self._opponent_config:
            self.engine.add_robot(
                self._opponent_config, "yellow", strategy_fn=self._opponent_fn)
        self._steps = 0
        self._hal._refresh_percepts()

        if self.obs_mode == "camera" and \
                self._agent.robot.config.sensors.camera is None:
            raise ValueError(
                "obs_mode='camera' exige um bloco sensors.camera no YAML "
                f"do agente ({self._agent_config})")

        # Baselines para domain randomization (restaurados a cada episódio)
        cfg = self._agent.robot.config
        self._base_mass  = cfg.body.mass
        self._base_noise = {
            name: getattr(cfg.sensors, name).noise_std
            for name in ("ir_ring", "compass", "ultrasound",
                         "ball_velocity", "opponent_lidar")
            if getattr(cfg.sensors, name, None) is not None
        }

    def _apply_domain_rand(self) -> None:
        """Varia massa (±20%) e ruído dos sensores (×0.5–2) por episódio —
        mesma lógica da augmentation do XLC, aplicada à física (sim2real)."""
        rng = self.np_random
        cfg = self._agent.robot.config
        self._agent.robot.body.mass = self._base_mass * rng.uniform(0.8, 1.2)
        for name, base in self._base_noise.items():
            getattr(cfg.sensors, name).noise_std = base * rng.uniform(0.5, 2.0)

    # ── Observation ───────────────────────────────────────────────────────────

    def _observe(self) -> np.ndarray:
        if self.obs_mode == "camera":
            return self._hal.read_camera_frame()
        if self.obs_mode == "percepts":
            p = self._hal
            heading = p.read_compass()
            px, py  = p.read_position()
            parts = [
                p.read_ir(),
                [math.sin(heading), math.cos(heading)],
                p.read_ultrasound(),
                [1.0 if v else 0.0 for v in p.read_line_sensors()],
                [px / HALF_L, py / HALF_W],
            ]
            # Sensores opcionais (B5/B2) entram na obs se estiverem no YAML
            try:
                bvx, bvy = p.read_ball_velocity()
                parts.append([bvx / MAX_BALL_SPEED, bvy / MAX_BALL_SPEED])
            except NotImplementedError:
                pass
            try:
                lidar = p.read_opponent_lidar()
                rng_max = self._agent.robot.config.sensors.opponent_lidar.range
                parts.append([d / rng_max for d in lidar])
            except NotImplementedError:
                pass
            return np.concatenate(parts, dtype=np.float32)

        rb    = self._agent.robot.body
        ball  = self.engine.ball.body
        h     = rb.angle
        rel_x = ball.position.x - rb.position.x
        rel_y = ball.position.y - rb.position.y
        # Bola no frame local do robô
        cos_h, sin_h = math.cos(h), math.sin(h)
        loc_x =  cos_h * rel_x + sin_h * rel_y
        loc_y = -sin_h * rel_x + cos_h * rel_y
        max_v = self._agent.robot.config.body.max_speed
        return np.array([
            rb.position.x / HALF_L,
            rb.position.y / HALF_W,
            math.sin(h), math.cos(h),
            rb.velocity.x / max_v, rb.velocity.y / max_v,
            ball.position.x / HALF_L,
            ball.position.y / HALF_W,
            ball.velocity.x / MAX_BALL_SPEED,
            ball.velocity.y / MAX_BALL_SPEED,
            loc_x / (2 * HALF_L), loc_y / (2 * HALF_L),
            self._ball_dist_to_goal() / (2 * HALF_L),
            self._robot_dist_to_ball() / (2 * HALF_L),
        ], dtype=np.float32)

    def _ball_dist_to_goal(self) -> float:
        bx, by = self.engine.ball.body.position
        return math.hypot(HALF_L - bx, by)        # gol amarelo em (+HALF_L, 0)

    def _robot_dist_to_ball(self) -> float:
        rx, ry = self._agent.robot.body.position
        bx, by = self.engine.ball.body.position
        return math.hypot(bx - rx, by - ry)

    # ── Gym API ───────────────────────────────────────────────────────────────

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is not None:
            self._build(seed)     # engine novo → percept noise reproduzível
        else:
            self.engine._kickoff_reset()
            self._steps = 0

        if self.randomize:
            rng = self.np_random
            self.engine.set_ball_pose(rng.uniform(-0.8, 0.8),
                                      rng.uniform(-0.6, 0.6))
            self.engine.set_robot_pose(
                self._agent.robot_id,
                rng.uniform(-HALF_L + 0.15, -0.1),
                rng.uniform(-HALF_W + 0.15, HALF_W - 0.15),
                rng.uniform(-math.pi, math.pi),
            )

        if self.domain_rand:
            self._apply_domain_rand()

        self._hal._refresh_percepts()
        return self._observe(), {}

    def step(self, action):
        a = np.clip(np.asarray(action, dtype=np.float64), -1.0, 1.0)
        max_v = self._agent.robot.config.body.max_speed
        self._hal.set_velocity(a[0] * max_v, a[1] * max_v, a[2] * MAX_OMEGA)
        if a[3] > KICK_THRESHOLD:
            self._hal.kick()

        prev_bg = self._ball_dist_to_goal()
        prev_rb = self._robot_dist_to_ball()
        prev_violations = sum(self.engine.violation_counts.values())

        terminated = False
        reward     = -STEP_PENALTY
        for _ in range(self.frame_skip):
            state = self.engine.step()
            if state["state"] == "goal_blue":
                reward    += GOAL_REWARD
                terminated = True
                break
            if state["state"] == "goal_yellow":
                reward    -= GOAL_REWARD
                terminated = True
                break

        if not terminated:
            reward += W_BALL_TO_GOAL  * (prev_bg - self._ball_dist_to_goal())
            reward += W_ROBOT_TO_BALL * (prev_rb - self._robot_dist_to_ball())
            if self._agent.penalized:
                reward    += PENALTY_REWARD
                terminated = True

        # Violações do árbitro (Rules 2026) atribuídas ao agente
        if sum(self.engine.violation_counts.values()) > prev_violations:
            v = self.engine.last_violation
            if v and (v["robot_id"] == self._agent.robot_id
                      or (v["kind"] == "pushing"
                          and self._agent.robot_id in v["detail"])):
                reward += VIOLATION_REWARD

        self._steps += 1
        truncated = not terminated and self._steps >= self.max_steps

        obs  = self._observe()
        info = {"score": dict(self.engine.score), "sim_state": self.engine.state}
        return obs, float(reward), terminated, truncated, info
