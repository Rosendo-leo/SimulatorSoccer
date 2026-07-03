"""Treina um atacante com PPO (Stable-Baselines3) no SoccerEnv.

Uso:
    python -m rl.train                                   # 200k steps, defaults
    python -m rl.train --timesteps 1000000 --n-envs 8
    python -m rl.train --obs-mode percepts --save models/ppo_percepts

Depois de treinar, avalia por 10 episódios e salva em models/<nome>.zip.
"""
from __future__ import annotations
import argparse
import time
from pathlib import Path

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.monitor import Monitor
except ImportError as exc:                             # pragma: no cover
    raise SystemExit(
        "stable-baselines3 não instalado. Rode:\n"
        "  .venv\\Scripts\\python.exe -m pip install stable-baselines3"
    ) from exc

from rl.env import SoccerEnv

_ROOT = Path(__file__).parent.parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--timesteps", type=int, default=200_000)
    p.add_argument("--n-envs",    type=int, default=4)
    p.add_argument("--seed",      type=int, default=0)
    p.add_argument("--obs-mode",  choices=("vector", "percepts"), default="vector")
    p.add_argument("--opponent",  default="examples.defender_strategy",
                   help="módulo da estratégia adversária")
    p.add_argument("--frame-skip", type=int, default=4)
    p.add_argument("--domain-rand", action="store_true",
                   help="randomiza massa/ruído por episódio (sim2real)")
    p.add_argument("--save", default="models/ppo_striker",
                   help="caminho do modelo (sem .zip)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    def make_env():
        return Monitor(SoccerEnv(
            obs_mode=args.obs_mode,
            opponent_strategy=args.opponent,
            frame_skip=args.frame_skip,
            domain_rand=args.domain_rand,
        ))

    vec = make_vec_env(make_env, n_envs=args.n_envs, seed=args.seed)
    model = PPO("MlpPolicy", vec, verbose=1, seed=args.seed)

    t0 = time.perf_counter()
    model.learn(total_timesteps=args.timesteps, progress_bar=False)
    print(f"\nTreino: {args.timesteps} steps em {time.perf_counter() - t0:.0f}s")

    save_path = _ROOT / args.save
    save_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(save_path)
    print(f"Modelo salvo em {save_path}.zip")

    # ── Avaliação rápida ──────────────────────────────────────────────────────
    env = SoccerEnv(obs_mode=args.obs_mode,
                    opponent_strategy=args.opponent,
                    frame_skip=args.frame_skip, seed=args.seed + 1000)
    goals = conceded = 0
    returns = []
    for ep in range(10):
        obs, _ = env.reset()
        done, total = False, 0.0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, r, term, trunc, info = env.step(action)
            total += r
            done = term or trunc
        returns.append(total)
        if info["sim_state"] == "goal_blue":
            goals += 1
        elif info["sim_state"] == "goal_yellow":
            conceded += 1
    print(f"Avaliação (10 eps): retorno médio {sum(returns)/len(returns):+.2f}, "
          f"gols {goals}, sofridos {conceded}")


if __name__ == "__main__":
    main()
