"""Tests do server FastAPI: montagem de partida, whitelist e serialização."""
import pytest

pytest.importorskip("fastapi")

from server.main import (  # noqa: E402
    DEFAULT_MATCH, _build_engine, _load_strategy, list_strategies,
)


def test_list_strategies_includes_examples():
    found = list_strategies()
    assert "examples.attacker_strategy" in found
    assert "examples.defender_strategy" in found


def test_load_strategy_returns_callable():
    fn = _load_strategy("examples.attacker_strategy")
    assert callable(fn)


def test_load_strategy_rejects_module_outside_whitelist():
    with pytest.raises(ValueError, match="not allowed"):
        _load_strategy("os.path")


def test_load_strategy_rejects_module_without_strategy_fn():
    with pytest.raises(ValueError, match="no strategy"):
        _load_strategy("examples.__init__")


def test_build_engine_default_match():
    engine = _build_engine(DEFAULT_MATCH)
    state = engine.get_state()
    teams = [r["team"] for r in state["robots"]]
    assert teams == ["blue", "yellow"]


def test_build_engine_2v2():
    match = {
        "blue":   ["striker_v3", "goalkeeper_v2"],
        "yellow": ["striker_omni", "goalkeeper_diff"],
        "blue_strategy":   "examples.attacker_strategy",
        "yellow_strategy": "examples.defender_strategy",
    }
    engine = _build_engine(match)
    ids = [r["id"] for r in engine.get_state()["robots"]]
    assert ids == ["blue_1", "blue_2", "yellow_1", "yellow_2"]


def test_build_engine_caps_at_two_robots_per_team():
    match = dict(DEFAULT_MATCH, blue=["striker_v3"] * 3)
    engine = _build_engine(match)
    blue = [r for r in engine.get_state()["robots"] if r["team"] == "blue"]
    assert len(blue) == 2


def test_state_includes_name_and_radius():
    engine = _build_engine(DEFAULT_MATCH)
    robot = engine.get_state()["robots"][0]
    assert robot["name"]
    assert 0 < robot["radius"] <= 0.16


def test_engine_set_ball_pose_clamps_and_zeroes_velocity():
    engine = _build_engine(DEFAULT_MATCH)
    engine.set_ball_pose(99.0, -99.0)
    bx, by = engine.ball.body.position
    assert abs(bx) < 1.22 and abs(by) < 0.92
    assert engine.ball.body.velocity.length == 0


def test_engine_set_robot_pose_clears_penalty():
    engine = _build_engine(DEFAULT_MATCH)
    entry = engine.entries[0]
    engine._penalize(entry)
    assert entry.penalized
    engine.set_robot_pose(entry.robot_id, 0.5, 0.2, 1.0)
    assert not entry.penalized
    x, y = entry.robot.body.position
    assert (x, y) == (0.5, 0.2)
    assert entry.robot.body.angle == 1.0


def test_engine_set_robot_pose_unknown_id():
    engine = _build_engine(DEFAULT_MATCH)
    with pytest.raises(KeyError):
        engine.set_robot_pose("purple_9", 0, 0)


def test_scenario_roundtrip(tmp_path, monkeypatch):
    import json
    import server.main as srv
    monkeypatch.setattr(srv, "SCENARIOS_DIR", tmp_path)
    monkeypatch.setattr(srv, "_engine", _build_engine(DEFAULT_MATCH))

    srv._engine.set_ball_pose(0.3, -0.2)
    data = srv._capture_scenario()
    assert data["ball"] == {"x": 0.3, "y": -0.2}
    (tmp_path / "test.json").write_text(json.dumps(data), encoding="utf-8")

    srv._engine.set_ball_pose(0.0, 0.0)
    srv._apply_scenario(data)
    bx, by = srv._engine.ball.body.position
    assert (round(bx, 4), round(by, 4)) == (0.3, -0.2)

    assert srv.list_scenarios() == ["test"]
    assert srv.delete_scenario("test") == {"deleted": "test"}
    assert srv.list_scenarios() == []


def test_scenario_name_rejects_path_traversal():
    from fastapi import HTTPException
    from server.main import _scenario_path
    for bad in ("../x", "a/b", "a\\b", ""):
        with pytest.raises(HTTPException):
            _scenario_path(bad)


def test_recording_name_rejects_path_traversal():
    from fastapi import HTTPException
    from server.main import get_recording
    for bad in ("../secrets", "a/b", "a\\b"):
        with pytest.raises(HTTPException) as exc:
            get_recording(bad)
        assert exc.value.status_code == 400


def test_recording_roundtrip(tmp_path, monkeypatch):
    import server.main as srv
    monkeypatch.setattr(srv, "RECORDINGS_DIR", tmp_path)

    engine = _build_engine(DEFAULT_MATCH)
    engine.start_recording(tmp_path / "test_match.jsonl")
    for _ in range(10):
        engine.step()
    engine.stop_recording()

    names = [r["name"] for r in srv.list_recordings()]
    assert "test_match" in names

    data = srv.get_recording("test_match")
    assert len(data["frames"]) == 10
    assert "percepts" not in data["frames"][0]["robots"][0]

    assert srv.delete_recording("test_match") == {"deleted": "test_match"}
    assert srv.list_recordings() == []


def test_ws_camera_frame():
    """PiP: robô sem câmera devolve png=null; robô inexistente também."""
    from fastapi.testclient import TestClient
    from server.main import app
    with TestClient(app) as client, \
            client.websocket_connect("/ws/sim") as ws:
        ws.receive_json()                       # estado inicial
        ws.send_json({"cmd": "camera_frame", "robot": "blue_1"})
        while True:
            msg = ws.receive_json()
            if msg.get("event") == "camera_frame":
                break
        assert msg["robot"] == "blue_1"
        assert msg["png"] is None               # striker_v3 não tem câmera
