"""Entry point: python -m sim [options]"""
from __future__ import annotations
import argparse
import importlib
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m sim",
        description="RCJ Soccer Simulator — Phase 1",
    )
    parser.add_argument(
        "--blue", default="robots/example.yaml",
        metavar="YAML", help="Blue robot config (default: robots/example.yaml)",
    )
    parser.add_argument(
        "--yellow", default=None,
        metavar="YAML", help="Yellow robot config (optional, enables 1v1)",
    )
    parser.add_argument(
        "--strategy", default="examples.simple_strategy",
        metavar="MODULE", help="Decision module exposing strategy(hal)",
    )
    parser.add_argument(
        "--steps", type=int, default=None,
        help="Max steps before exiting (default: unlimited)",
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run without pygame window",
    )
    parser.add_argument(
        "--record", metavar="FILE", default=None,
        help="Save replay to this JSON-Lines file",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="RNG seed for reproducible noise",
    )
    args = parser.parse_args()

    # Resolve strategy
    try:
        mod = importlib.import_module(args.strategy)
        strategy_fn = mod.strategy
    except (ImportError, AttributeError) as exc:
        sys.exit(f"Cannot load strategy '{args.strategy}': {exc}")

    from sim.engine import SimEngine

    engine = SimEngine(seed=args.seed)
    engine.add_robot(args.blue, team="blue", strategy_fn=strategy_fn)
    if args.yellow:
        engine.add_robot(args.yellow, team="yellow", strategy_fn=strategy_fn)

    if args.record:
        engine.start_recording(args.record)

    if args.headless:
        n = args.steps or 3600
        print(f"Running {n} steps headless …")
        engine.run_headless(n)
        state = engine.get_state()
        print(f"Done — tick {state['tick']}, score {state['score']}")
    else:
        from viewer.pygame_viewer import PygameViewer
        viewer = PygameViewer()
        viewer.run(engine, max_steps=args.steps)

    if args.record:
        engine.stop_recording()


if __name__ == "__main__":
    main()
