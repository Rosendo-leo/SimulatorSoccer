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
        "--blue", nargs="+", default=["robots/example.yaml"],
        metavar="YAML", help="Blue robot config(s) — pass two files for 2v2",
    )
    parser.add_argument(
        "--yellow", nargs="+", default=None,
        metavar="YAML", help="Yellow robot config(s) — pass two files for 2v2",
    )
    parser.add_argument(
        "--strategy", default="examples.simple_strategy",
        metavar="MODULE", help="Decision module exposing strategy(hal)",
    )
    parser.add_argument(
        "--yellow-strategy", default=None,
        metavar="MODULE", help="Strategy for the yellow team (default: same as --strategy)",
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
    parser.add_argument(
        "--kicker-test", action="store_true",
        help="Run the official kicker strength test (Rules 2026 Annex A) "
             "on the first --blue robot and exit",
    )
    parser.add_argument(
        "--no-referee", action="store_true",
        help="Disable the automatic referee (Rules 2026 2.5-2.9)",
    )
    args = parser.parse_args()

    if args.kicker_test:
        from sim.kicker_test import run_kicker_test
        result = run_kicker_test(args.blue[0], seed=args.seed or 0)
        print(result.report())
        sys.exit(0 if result.passed else 1)

    # Resolve strategies
    def load_strategy(module_name: str):
        try:
            return importlib.import_module(module_name).strategy
        except (ImportError, AttributeError) as exc:
            sys.exit(f"Cannot load strategy '{module_name}': {exc}")

    blue_strategy   = load_strategy(args.strategy)
    yellow_strategy = (load_strategy(args.yellow_strategy)
                       if args.yellow_strategy else blue_strategy)

    from sim.engine import SimEngine

    engine = SimEngine(seed=args.seed, referee=not args.no_referee)
    for yaml_path in args.blue:
        engine.add_robot(yaml_path, team="blue", strategy_fn=blue_strategy)
    for yaml_path in (args.yellow or []):
        engine.add_robot(yaml_path, team="yellow", strategy_fn=yellow_strategy)

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
