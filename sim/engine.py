"""Main simulation engine: physics loop, game state, penalty system."""
from __future__ import annotations
import math
import time
from typing import Callable, Optional
import numpy as np
import pymunk

from sim.config_loader import RobotConfig, load_robot_config
from sim.field import (
    build_field, is_blue_goal, is_yellow_goal,
    HALF_L, HALF_W, HALF_TOTAL_L, HALF_TOTAL_W, NEUTRAL_SPOTS,
)
from sim.ball import Ball, BALL_RADIUS
from sim.robot import Robot
from sim.hal_sim import SimHAL
from sim.recorder import Recorder

PHYSICS_DT           = 1 / 60    # fixed timestep (s)
PHYSICS_SUBSTEPS     = 4         # sub-steps per frame (prevents ball tunneling)
GOAL_RESET_TICKS     = 120       # pause after goal (~2 s)
BALL_DAMPING         = 0.992     # speed multiplier per frame (applied once)

# Penalty: triggered when robot crosses the white boundary line
PENALTY_DURATION_S   = 60.0                          # 1 minute
PENALTY_TICKS        = int(PENALTY_DURATION_S / PHYSICS_DT)   # 3 600 ticks
_PENALTY_HOLD        = (0.0, -5.0)                   # parking coords (outside field)
_OOB_MARGIN          = 0.01                          # 1 cm past boundary triggers penalty

# Default kick-off positions — slot 0 = attacker, slot 1 = keeper (2v2)
_BLUE_STARTS   = [(-0.40, 0.0, 0.0),      (-0.90, 0.0, 0.0)]
_YELLOW_STARTS = [( 0.40, 0.0, math.pi),  ( 0.90, 0.0, math.pi)]


class _RobotEntry:
    __slots__ = ("robot", "hal", "strategy", "robot_id", "team",
                 "penalized", "penalty_timer")

    def __init__(self, robot: Robot, hal: SimHAL,
                 strategy, robot_id: str, team: str) -> None:
        self.robot         = robot
        self.hal           = hal
        self.strategy      = strategy
        self.robot_id      = robot_id
        self.team          = team
        self.penalized     = False
        self.penalty_timer = 0


class SimEngine:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = np.random.default_rng(seed)

        self._space = pymunk.Space()
        self._space.gravity = (0, 0)
        self._space.damping = 1.0   # ball damping applied manually

        build_field(self._space)
        self._space.collision_slop = 0.0   # tolera zero penetração nas shapes

        self._ball: Ball = Ball(self._space)
        self._entries: list[_RobotEntry] = []

        self.tick:  int  = 0
        self.score: dict = {"blue": 0, "yellow": 0}
        self.state: str  = "playing"
        self._goal_timer = 0
        self.paused = False

        self._recorder: Optional[Recorder] = None

    @property
    def ball(self) -> Ball:
        return self._ball

    @property
    def entries(self) -> list[_RobotEntry]:
        return self._entries

    # ── Robot management ──────────────────────────────────────────────────────

    def add_robot(
        self,
        config: RobotConfig | str,
        team: str,
        position: tuple[float, float] | None = None,
        heading: float = 0.0,
        strategy_fn: Callable | None = None,
    ) -> tuple[Robot, SimHAL]:
        if isinstance(config, str):
            config = load_robot_config(config)

        if position is None:
            same_team = [e for e in self._entries if e.team == team]
            n = len(same_team)
            starts = _BLUE_STARTS if team == "blue" else _YELLOW_STARTS
            x, y, heading = starts[n % len(starts)]
        else:
            x, y = position

        robot    = Robot(self._space, config, team, x, y, heading)
        hal      = SimHAL(robot, self._ball, self._space, config, self._rng)
        robot_id = f"{team}_{sum(1 for e in self._entries if e.team == team) + 1}"

        entry = _RobotEntry(robot, hal, strategy_fn, robot_id, team)
        self._entries.append(entry)
        return robot, hal

    # ── Direct placement (editor de cenários / RL) ───────────────────────────

    def set_ball_pose(self, x: float, y: float) -> None:
        """Teleporta a bola (velocidade zerada), limitada à área total."""
        x = max(-HALF_TOTAL_L + BALL_RADIUS, min(HALF_TOTAL_L - BALL_RADIUS, x))
        y = max(-HALF_TOTAL_W + BALL_RADIUS, min(HALF_TOTAL_W - BALL_RADIUS, y))
        self._ball.reset(x, y)
        if self.state != "playing":
            self.state = "playing"
            self._goal_timer = 0

    def set_robot_pose(self, robot_id: str, x: float, y: float,
                       heading: float | None = None) -> None:
        """Teleporta um robô (limpa penalidade e zera velocidades)."""
        for entry in self._entries:
            if entry.robot_id == robot_id:
                break
        else:
            raise KeyError(f"Robot {robot_id!r} not found")
        r = entry.robot.config.body.radius
        x = max(-HALF_L + r, min(HALF_L - r, x))
        y = max(-HALF_W + r, min(HALF_W - r, y))
        if heading is None:
            heading = entry.robot.body.angle
        entry.robot.reset(x, y, heading)
        entry.penalized     = False
        entry.penalty_timer = 0

    # ── Recording ─────────────────────────────────────────────────────────────

    def start_recording(self, path: str) -> None:
        self._recorder = Recorder(path)
        self._recorder.open()

    def stop_recording(self) -> None:
        if self._recorder:
            self._recorder.close()
            self._recorder = None

    # ── Game loop ─────────────────────────────────────────────────────────────

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def step(self) -> dict:
        if self.paused:
            return self.get_state()

        if self.state in ("goal_blue", "goal_yellow"):
            self._goal_timer -= 1
            if self._goal_timer <= 0:
                self._kickoff_reset()
            return self.get_state()

        # 1. Percepts + strategy (skip penalized robots)
        for entry in self._entries:
            if entry.penalized:
                continue
            entry.hal._refresh_percepts()
            if entry.strategy is not None:
                entry.strategy(entry.hal)

        # 2. Actuators (skip penalized)
        for entry in self._entries:
            if entry.penalized:
                continue
            entry.hal._apply_action(PHYSICS_DT)

        # 3. Ball damping (once per frame, before substeps)
        vx, vy = self._ball.body.velocity
        self._ball.body.velocity = (vx * BALL_DAMPING, vy * BALL_DAMPING)

        # 4. Physics step — use substeps so fast-moving ball never skips walls
        sub_dt = PHYSICS_DT / PHYSICS_SUBSTEPS
        for _ in range(PHYSICS_SUBSTEPS):
            self._space.step(sub_dt)
        self.tick += 1

        # 5. Goal detection
        bx, by = self._ball.body.position
        if is_blue_goal(bx, by):
            self.score["yellow"] += 1
            self.state = "goal_yellow"
            self._goal_timer = GOAL_RESET_TICKS
        elif is_yellow_goal(bx, by):
            self.score["blue"] += 1
            self.state = "goal_blue"
            self._goal_timer = GOAL_RESET_TICKS

        # 4b. Corrige sobreposição entre robôs.
        # O controle direto de velocity sobrescreve o impulso de colisão do
        # PyMunk no tick seguinte; a correção posicional garante separação real.
        self._resolve_robot_overlaps()

        # 5b. Safety net: ball escaped field (shouldn't happen after substeps+clamp)
        if abs(bx) > HALF_TOTAL_L + 0.3 or abs(by) > HALF_TOTAL_W + 0.3:
            self._ball.reset(0.0, 0.0)

        # 6. Out-of-bounds → penalty
        if self.state == "playing":
            for entry in self._entries:
                if entry.penalized:
                    continue
                px, py = entry.robot.body.position
                if abs(px) > HALF_L + _OOB_MARGIN or abs(py) > HALF_W + _OOB_MARGIN:
                    self._penalize(entry)

        # 7. Penalty countdown
        for entry in self._entries:
            if entry.penalized and entry.penalty_timer > 0:
                entry.penalty_timer -= 1
                if entry.penalty_timer == 0:
                    self._return_from_penalty(entry)

        state = self.get_state()
        if self._recorder:
            self._recorder.record(state)
        return state

    # ── Robot-robot collision correction ─────────────────────────────────────

    def _resolve_robot_overlaps(self) -> None:
        """Push overlapping robot bodies apart.

        PyMunk applies collision impulses, but because we override body.velocity
        at the start of every tick (velocity-control pattern), those impulses are
        discarded on the next step and robots slowly clip through each other.
        We correct positions directly so shapes never stay overlapping.
        """
        active = [e for e in self._entries if not e.penalized]
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                b1 = active[i].robot.body
                b2 = active[j].robot.body
                r1 = active[i].robot.config.body.radius
                r2 = active[j].robot.config.body.radius

                dx = b2.position.x - b1.position.x
                dy = b2.position.y - b1.position.y
                dist_sq = dx * dx + dy * dy
                min_dist = r1 + r2

                if dist_sq < min_dist * min_dist and dist_sq > 1e-9:
                    dist = math.sqrt(dist_sq)
                    nx, ny = dx / dist, dy / dist
                    # Empurra cada robô para fora do overlap + 2 mm de margem
                    push = (min_dist - dist) * 0.5 + 0.002
                    b1.position = (b1.position.x - nx * push,
                                   b1.position.y - ny * push)
                    b2.position = (b2.position.x + nx * push,
                                   b2.position.y + ny * push)
                    # Zera a componente de velocidade de CADA robô na direção
                    # do outro, para que no mesmo tick não voltem a se comprimir
                    v1x, v1y = b1.velocity
                    v2x, v2y = b2.velocity
                    approach1 = v1x * nx + v1y * ny          # v1 em direção a b2
                    approach2 = -(v2x * nx + v2y * ny)       # v2 em direção a b1
                    if approach1 > 0:
                        b1.velocity = (v1x - nx * approach1,
                                       v1y - ny * approach1)
                    if approach2 > 0:
                        b2.velocity = (v2x + nx * approach2,
                                       v2y + ny * approach2)

    # ── Penalty system ────────────────────────────────────────────────────────

    def _penalize(self, entry: _RobotEntry) -> None:
        entry.penalized     = True
        entry.penalty_timer = PENALTY_TICKS
        entry.hal.stop()
        entry.robot.body.position         = _PENALTY_HOLD
        entry.robot.body.velocity         = (0.0, 0.0)
        entry.robot.body.angular_velocity = 0.0

    def _return_from_penalty(self, entry: _RobotEntry) -> None:
        sx, sy   = self._best_neutral_spot(exclude=entry)
        # Robot faces its own goal when returning
        heading  = math.pi if entry.team == "blue" else 0.0
        entry.robot.reset(sx, sy, heading)
        entry.penalized     = False
        entry.penalty_timer = 0

    def _best_neutral_spot(self, exclude: _RobotEntry) -> tuple[float, float]:
        """Neutral spot farthest from the ball, not occupied by an active robot."""
        ball_pos = self._ball.body.position
        occupied = [
            e.robot.body.position
            for e in self._entries
            if not e.penalized and e is not exclude
        ]

        best      = NEUTRAL_SPOTS[0]
        best_dist = -1.0

        for sx, sy in NEUTRAL_SPOTS:
            dist = math.sqrt((sx - ball_pos.x) ** 2 + (sy - ball_pos.y) ** 2)
            taken = any(
                math.sqrt((sx - p.x) ** 2 + (sy - p.y) ** 2) < 0.25
                for p in occupied
            )
            if not taken and dist > best_dist:
                best_dist = dist
                best      = (sx, sy)

        return best

    # ── Reset ─────────────────────────────────────────────────────────────────

    def _kickoff_reset(self) -> None:
        self._ball.reset(0.0, 0.0)
        blue_n = yellow_n = 0
        for entry in self._entries:
            # Clear any active penalty
            entry.penalized     = False
            entry.penalty_timer = 0
            if entry.team == "blue":
                x, y, h = _BLUE_STARTS[blue_n % len(_BLUE_STARTS)]
                blue_n += 1
            else:
                x, y, h = _YELLOW_STARTS[yellow_n % len(_YELLOW_STARTS)]
                yellow_n += 1
            entry.robot.reset(x, y, h)
        self.state = "playing"

    # ── State serialization ───────────────────────────────────────────────────

    def get_state(self) -> dict:
        bx, by   = self._ball.body.position
        bvx, bvy = self._ball.body.velocity
        robots   = []
        for entry in self._entries:
            b   = entry.robot.body
            px, py = b.position
            vx, vy = b.velocity
            cfg_body = entry.robot.config.body
            robots.append({
                "id":      entry.robot_id,
                "team":    entry.team,
                "name":    entry.robot.config.name,
                "radius":  round(cfg_body.radius if cfg_body.shape == "circle"
                                 else math.hypot(cfg_body.width, cfg_body.height) / 2, 4),
                "x":       round(px, 4),
                "y":       round(py, 4),
                "heading": round(b.angle, 4),
                "vx":      round(vx, 4),
                "vy":      round(vy, 4),
                "omega":   round(b.angular_velocity, 4),
                "penalized":        entry.penalized,
                "penalty_remaining": round(entry.penalty_timer * PHYSICS_DT, 1),
                "percepts": entry.hal._percepts,
                "action": {
                    "vx":   entry.hal._cmd_vx,
                    "vy":   entry.hal._cmd_vy,
                    "omega": entry.hal._cmd_omega,
                    "kick": entry.hal._kick_requested,
                },
            })
        return {
            "tick":      self.tick,
            "timestamp": round(self.tick * PHYSICS_DT, 3),
            "ball":  {"x": round(bx, 4), "y": round(by, 4),
                      "vx": round(bvx, 4), "vy": round(bvy, 4)},
            "robots": robots,
            "score":  dict(self.score),
            "state":  self.state,
        }

    def run_headless(self, steps: int, *, real_time: bool = False) -> None:
        for _ in range(steps):
            self.step()
            if real_time:
                time.sleep(PHYSICS_DT)
