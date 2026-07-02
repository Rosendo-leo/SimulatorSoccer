"""Tests for the pybind11 C++ strategy bridge.

Skipped entirely if the extension was not built
(cd bridge && python setup.py build_ext --inplace).
"""
import pytest

cpp_attacker = pytest.importorskip(
    "bridge.cpp_attacker",
    reason="C++ bridge not built — run: cd bridge && python setup.py build_ext --inplace",
)

from sim.engine import SimEngine
from examples.attacker_strategy import strategy as py_attacker
from examples.defender_strategy import strategy as py_defender


def _run_match(blue_strategy, steps: int = 600) -> dict:
    engine = SimEngine(seed=123)
    engine.add_robot("robots/striker_v3.yaml",    "blue",   strategy_fn=blue_strategy)
    engine.add_robot("robots/goalkeeper_v2.yaml", "yellow", strategy_fn=py_defender)
    engine.run_headless(steps)
    return engine.get_state()


def test_cpp_strategy_callable():
    assert callable(cpp_attacker.strategy)


def test_cpp_strategy_drives_robot():
    """C++ attacker must actually move the robot (non-zero displacement)."""
    state = _run_match(cpp_attacker.strategy, steps=300)
    blue  = next(r for r in state["robots"] if r["team"] == "blue")
    start_x, start_y = -0.40, 0.0
    moved = abs(blue["x"] - start_x) + abs(blue["y"] - start_y)
    assert moved > 0.05 or blue["penalized"], "C++ strategy should move the robot"


def test_cpp_matches_python_port():
    """Same seed → C++ and Python attacker produce identical trajectories.

    Both implement the same Decisao::Attacker algorithm; percept noise is
    drawn from the same seeded RNG in the same order, so any divergence
    means the ports disagree.
    """
    state_py  = _run_match(py_attacker)
    state_cpp = _run_match(cpp_attacker.strategy)

    assert state_cpp["score"] == state_py["score"]
    assert state_cpp["ball"]  == state_py["ball"]
    for r_cpp, r_py in zip(state_cpp["robots"], state_py["robots"]):
        assert r_cpp["x"]       == r_py["x"],       f"{r_cpp['id']} x diverged"
        assert r_cpp["y"]       == r_py["y"],       f"{r_cpp['id']} y diverged"
        assert r_cpp["heading"] == r_py["heading"], f"{r_cpp['id']} heading diverged"
