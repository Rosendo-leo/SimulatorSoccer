"""Ambiente PettingZoo (ParallelEnv) 2v2 para self-play.

Os 4 robôs são controlados por políticas externas (sem estratégias scriptadas).
Com `mirror=True` (padrão), as observações e ações do time amarelo são
espelhadas no eixo Y — do ponto de vista de cada agente, o gol a atacar fica
sempre em +X. Isso permite treinar UMA política compartilhada pelos dois times
(self-play simétrico).

Espelhamento (reflexão x → -x):
  obs   : x, vx trocam de sinal; heading θ → π−θ (sin mantém, cos inverte)
  ação  : frame local do robô muda de mão → vy → −vy, omega → −omega
"""
from __future__ import annotations
import functools
import math
from pathlib import Path

import numpy as np
from gymnasium import spaces
from pettingzoo import ParallelEnv

from sim.engine import SimEngine
from sim.field import HALF_L, HALF_W
from sim.hal_sim import MAX_BALL_SPEED
from rl.env import MAX_OMEGA, KICK_THRESHOLD, W_BALL_TO_GOAL, STEP_PENALTY, GOAL_REWARD

_ROOT = Path(__file__).parent.parent

W_TEAM_TO_BALL = 0.5     # agente mais próximo da bola se aproximando dela


class SoccerParallelEnv(ParallelEnv):
    metadata = {"name": "rcj_soccer_2v2_v0", "render_modes": []}

    def __init__(
        self,
        blue_configs:   tuple[str, str] = ("robots/striker_v3.yaml",
                                           "robots/goalkeeper_v2.yaml"),
        yellow_configs: tuple[str, str] = ("robots/striker_v3.yaml",
                                           "robots/goalkeeper_v2.yaml"),
        mirror: bool = True,
        frame_skip: int = 4,
        max_steps: int = 1800,
        randomize: bool = True,
        seed: int | None = None,
    ) -> None:
        self._blue_configs   = [str(_ROOT / c) for c in blue_configs]
        self._yellow_configs = [str(_ROOT / c) for c in yellow_configs]
        self.mirror     = mirror
        self.frame_skip = frame_skip
        self.max_steps  = max_steps
        self.randomize  = randomize

        self.possible_agents = ["blue_1", "blue_2", "yellow_1", "yellow_2"]
        self.agents: list[str] = []
        self._rng = np.random.default_rng(seed)
        self._build(seed)

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _build(self, seed: int | None) -> None:
        self.engine = SimEngine(seed=seed)
        for cfg in self._blue_configs:
            self.engine.add_robot(cfg, "blue", strategy_fn=None)
        for cfg in self._yellow_configs:
            self.engine.add_robot(cfg, "yellow", strategy_fn=None)
        self._entries = {e.robot_id: e for e in self.engine.entries}
        self._steps = 0

    # ── Spaces ────────────────────────────────────────────────────────────────

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent):
        return spaces.Box(-np.inf, np.inf, shape=(14,), dtype=np.float32)

    @functools.lru_cache(maxsize=None)
    def action_space(self, agent):
        return spaces.Box(-1.0, 1.0, shape=(4,), dtype=np.float32)

    # ── Observation ───────────────────────────────────────────────────────────

    def _observe(self, agent: str) -> np.ndarray:
        entry  = self._entries[agent]
        rb     = entry.robot.body
        ball   = self.engine.ball.body
        flip   = -1.0 if (self.mirror and entry.team == "yellow") else 1.0

        rx, ry   = flip * rb.position.x,  rb.position.y
        rvx, rvy = flip * rb.velocity.x,  rb.velocity.y
        bx, by   = flip * ball.position.x, ball.position.y
        bvx, bvy = flip * ball.velocity.x, ball.velocity.y
        h = rb.angle if flip > 0 else math.pi - rb.angle

        rel_x, rel_y = bx - rx, by - ry
        cos_h, sin_h = math.cos(h), math.sin(h)
        loc_x =  cos_h * rel_x + sin_h * rel_y
        loc_y = -sin_h * rel_x + cos_h * rel_y
        max_v = entry.robot.config.body.max_speed

        return np.array([
            rx / HALF_L, ry / HALF_W,
            math.sin(h), math.cos(h),
            rvx / max_v, rvy / max_v,
            bx / HALF_L, by / HALF_W,
            bvx / MAX_BALL_SPEED, bvy / MAX_BALL_SPEED,
            loc_x / (2 * HALF_L), loc_y / (2 * HALF_L),
            math.hypot(HALF_L - bx, by) / (2 * HALF_L),   # bola → gol a atacar
            math.hypot(rel_x, rel_y)    / (2 * HALF_L),   # robô → bola
        ], dtype=np.float32)

    def _ball_progress(self, team: str) -> float:
        """Distância da bola ao gol que o time ataca (menor = melhor)."""
        bx, by = self.engine.ball.body.position
        gx = HALF_L if team == "blue" else -HALF_L
        return math.hypot(gx - bx, by)

    def _team_dist_to_ball(self, team: str) -> float:
        bx, by = self.engine.ball.body.position
        return min(
            math.hypot(bx - e.robot.body.position.x,
                       by - e.robot.body.position.y)
            for e in self.engine.entries if e.team == team
        )

    # ── PettingZoo API ────────────────────────────────────────────────────────

    def reset(self, seed: int | None = None, options: dict | None = None):
        if seed is not None:
            self._rng = np.random.default_rng(seed)
            self._build(seed)
        else:
            self.engine._kickoff_reset()
            self._steps = 0

        if self.randomize:
            self.engine.set_ball_pose(self._rng.uniform(-0.6, 0.6),
                                      self._rng.uniform(-0.5, 0.5))

        self.agents = list(self.possible_agents)
        for e in self.engine.entries:
            e.hal._refresh_percepts()
        obs   = {a: self._observe(a) for a in self.agents}
        infos = {a: {} for a in self.agents}
        return obs, infos

    def step(self, actions: dict):
        for agent, action in actions.items():
            entry = self._entries[agent]
            a = np.clip(np.asarray(action, dtype=np.float64), -1.0, 1.0)
            flip = -1.0 if (self.mirror and entry.team == "yellow") else 1.0
            max_v = entry.robot.config.body.max_speed
            entry.hal.set_velocity(a[0] * max_v,
                                   flip * a[1] * max_v,
                                   flip * a[2] * MAX_OMEGA)
            if a[3] > KICK_THRESHOLD:
                entry.hal.kick()

        prev_prog = {t: self._ball_progress(t)     for t in ("blue", "yellow")}
        prev_ball = {t: self._team_dist_to_ball(t) for t in ("blue", "yellow")}

        goal_team = None
        for _ in range(self.frame_skip):
            state = self.engine.step()
            if state["state"] == "goal_blue":
                goal_team = "blue"
                break
            if state["state"] == "goal_yellow":
                goal_team = "yellow"
                break

        rewards = {}
        for agent in self.agents:
            team = self._entries[agent].team
            r = -STEP_PENALTY
            if goal_team is not None:
                r += GOAL_REWARD if team == goal_team else -GOAL_REWARD
            else:
                r += W_BALL_TO_GOAL * (prev_prog[team] - self._ball_progress(team))
                r += W_TEAM_TO_BALL * (prev_ball[team] - self._team_dist_to_ball(team))
            rewards[agent] = float(r)

        self._steps += 1
        terminated = goal_team is not None
        truncated  = not terminated and self._steps >= self.max_steps

        terminations = {a: terminated for a in self.agents}
        truncations  = {a: truncated  for a in self.agents}
        obs   = {a: self._observe(a) for a in self.agents}
        infos = {a: {"score": dict(self.engine.score)} for a in self.agents}

        if terminated or truncated:
            self.agents = []
        return obs, rewards, terminations, truncations, infos
