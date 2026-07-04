"""Self-play com curriculum de checkpoints (PPO, SB3).

Geração 0 treina contra o defensor scriptado; cada geração seguinte treina
contra um checkpoint SORTEADO do pool das gerações anteriores (evita
overfit ao último adversário — curriculum clássico de self-play).

    python -m rl.selfplay --generations 5 --steps-per-gen 200000

O adversário é a própria política anterior adaptada a `strategy(hal)` via
`PolicyOpponent`: o mundo é ROTACIONADO 180° para o amarelo (rotação
preserva o frame local, então a mesma política que aprendeu a atacar +X
joga dos dois lados sem retreino; ações locais não precisam de espelho).
"""
from __future__ import annotations

import argparse
import math
import random
import time
from pathlib import Path

import numpy as np

from sim.field import HALF_L, HALF_W
from sim.hal_sim import MAX_BALL_SPEED

_ROOT = Path(__file__).parent.parent

MAX_OMEGA      = 6.0     # deve bater com rl.env
KICK_THRESHOLD = 0.5


def _mirrored_vector_obs(hal) -> np.ndarray:
    """Obs 'vector' (14 floats, como SoccerEnv._observe) do ponto de vista
    do robô do HAL, com o mundo rotacionado 180° — o robô 'acha' que ataca
    o gol em +X, seja qual for o time."""
    rb   = hal._robot.body
    ball = hal._ball.body
    # Rotação de 180°: (x, y) → (−x, −y); θ → θ + π
    rx, ry = -rb.position.x, -rb.position.y
    h      = rb.angle + math.pi
    rvx, rvy = -rb.velocity.x, -rb.velocity.y
    bx, by   = -ball.position.x, -ball.position.y
    bvx, bvy = -ball.velocity.x, -ball.velocity.y

    cos_h, sin_h = math.cos(h), math.sin(h)
    rel_x, rel_y = bx - rx, by - ry
    loc_x =  cos_h * rel_x + sin_h * rel_y
    loc_y = -sin_h * rel_x + cos_h * rel_y
    max_v = hal._config.body.max_speed

    ball_to_goal  = math.hypot(HALF_L - bx, by)
    robot_to_ball = math.hypot(rel_x, rel_y)
    return np.array([
        rx / HALF_L, ry / HALF_W,
        math.sin(h), math.cos(h),
        rvx / max_v, rvy / max_v,
        bx / HALF_L, by / HALF_W,
        bvx / MAX_BALL_SPEED, bvy / MAX_BALL_SPEED,
        loc_x / (2 * HALF_L), loc_y / (2 * HALF_L),
        ball_to_goal / (2 * HALF_L),
        robot_to_ball / (2 * HALF_L),
    ], dtype=np.float32)


class PolicyOpponent:
    """Adapta um modelo SB3 (ou qualquer objeto com .predict) a strategy(hal).

    Comandos são no frame LOCAL do robô — invariantes à rotação de 180°,
    então a ação da política sai direto em hal.set_velocity()/kick().
    """

    def __init__(self, model, frame_skip: int = 4) -> None:
        self._model = model
        self._skip = max(1, frame_skip)
        self._count = 0
        self._last = np.zeros(4, dtype=np.float32)

    def __call__(self, hal) -> None:
        if self._count % self._skip == 0:
            obs = _mirrored_vector_obs(hal)
            action, _ = self._model.predict(obs, deterministic=True)
            self._last = np.clip(np.asarray(action, dtype=np.float64), -1, 1)
        self._count += 1
        a = self._last
        max_v = hal._config.body.max_speed
        hal.set_velocity(a[0] * max_v, a[1] * max_v, a[2] * MAX_OMEGA)
        if a[3] > KICK_THRESHOLD:
            hal.kick()


def opponent_strategy_from_checkpoint(path: str | Path, frame_skip: int = 4):
    """Carrega um checkpoint PPO e devolve uma strategy(hal) pronta.

    O modelo é carregado UMA vez; cada chamada devolve o mesmo objeto —
    para VecEnvs use `PolicyOpponent(modelo)` novo por env (estado próprio)."""
    from stable_baselines3 import PPO
    return PolicyOpponent(PPO.load(str(path), device="cpu"),
                          frame_skip=frame_skip)


# ── Loop de treino ────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--generations",   type=int, default=5)
    p.add_argument("--steps-per-gen", type=int, default=200_000)
    p.add_argument("--n-envs",        type=int, default=4)
    p.add_argument("--pool-size",     type=int, default=3,
                   help="sorteia o adversário entre os últimos N checkpoints")
    p.add_argument("--seed",          type=int, default=0)
    p.add_argument("--save-dir",      default="models/selfplay")
    args = p.parse_args()

    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.monitor import Monitor

    from rl.env import SoccerEnv

    save_dir = _ROOT / args.save_dir
    save_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    checkpoints: list[Path] = sorted(save_dir.glob("gen_*.zip"))
    model = None

    start_gen = len(checkpoints)
    for gen in range(start_gen, start_gen + args.generations):
        if checkpoints:
            pool = checkpoints[-args.pool_size:]
            chosen = rng.choice(pool)
            opp_model = PPO.load(str(chosen), device="cpu")
            opp_name  = chosen.stem

            def make_opponent():
                return PolicyOpponent(opp_model)   # estado próprio por env
        else:
            opp_name = "defender_scriptado"

            def make_opponent():
                from examples.defender_strategy import strategy
                return strategy

        def make_env():
            return Monitor(SoccerEnv(opponent_strategy=make_opponent()))

        vec = make_vec_env(make_env, n_envs=args.n_envs,
                           seed=args.seed + gen)
        if model is None and checkpoints:
            model = PPO.load(checkpoints[-1], env=vec, device="cpu")
        elif model is None:
            model = PPO("MlpPolicy", vec, verbose=0, seed=args.seed)
        else:
            model.set_env(vec)

        t0 = time.perf_counter()
        model.learn(total_timesteps=args.steps_per_gen,
                    reset_num_timesteps=False)
        dt = time.perf_counter() - t0

        ckpt = save_dir / f"gen_{gen:02d}"
        model.save(ckpt)
        checkpoints.append(Path(str(ckpt) + ".zip"))
        print(f"[gen {gen}] vs {opp_name}: {args.steps_per_gen} steps "
              f"em {dt:.0f}s → {ckpt}.zip")

        # Avaliação rápida contra o baseline scriptado (progresso absoluto)
        env = SoccerEnv(seed=args.seed + 9000 + gen)
        wins = losses = 0
        for _ in range(6):
            obs, _ = env.reset()
            done = False
            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, _, term, trunc, info = env.step(action)
                done = term or trunc
            if info["sim_state"] == "goal_blue":
                wins += 1
            elif info["sim_state"] == "goal_yellow":
                losses += 1
        print(f"[gen {gen}] vs defender scriptado: {wins}V {losses}D "
              f"{6 - wins - losses}E")


if __name__ == "__main__":
    main()
