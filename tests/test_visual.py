"""Testes do bloco visual: (malha 3D do viewer) e do endpoint /api/meshes."""
import pytest

from sim.config_loader import ConfigError, load_robot_config


def _write(tmp_path, visual_block):
    p = tmp_path / "r.yaml"
    p.write_text(f"""
robot:
  name: T
  body: {{ radius: 0.10 }}
{visual_block}
""")
    return str(p)


def test_visual_parsed(tmp_path):
    cfg = load_robot_config(_write(tmp_path, """
  visual:
    mesh: striker.glb
    scale: 0.001
    offset: [0, 0.01, 0]
    rotation: [0, 90, 0]
"""))
    assert cfg.visual.mesh == "striker.glb"
    assert cfg.visual.scale == 0.001
    assert cfg.visual.offset == (0, 0.01, 0)
    assert cfg.visual.rotation == (0, 90, 0)


def test_visual_optional(tmp_path):
    cfg = load_robot_config(_write(tmp_path, ""))
    assert cfg.visual is None


def test_visual_rejects_path_traversal(tmp_path):
    with pytest.raises(ConfigError, match="visual.mesh"):
        load_robot_config(_write(tmp_path, """
  visual: { mesh: "../secrets.glb" }
"""))
    with pytest.raises(ConfigError, match="visual.mesh"):
        load_robot_config(_write(tmp_path, """
  visual: { mesh: "meshes/x.glb" }
"""))


def test_visual_requires_glb(tmp_path):
    with pytest.raises(ConfigError, match=r"\.glb"):
        load_robot_config(_write(tmp_path, """
  visual: { mesh: "robot.stl" }
"""))


def test_visual_rejects_bad_scale(tmp_path):
    with pytest.raises(ConfigError, match="visual.scale"):
        load_robot_config(_write(tmp_path, """
  visual: { mesh: "a.glb", scale: 0 }
"""))


def test_state_includes_visual():
    from sim.engine import SimEngine
    engine = SimEngine(seed=1)
    engine.add_robot("robots/example.yaml", team="blue")
    r = engine.get_state()["robots"][0]
    assert r["visual"]["mesh"] == "demo.glb"


def test_state_visual_none_without_block(tmp_path):
    from sim.engine import SimEngine
    engine = SimEngine(seed=1)
    engine.add_robot("robots/striker_v3.yaml", team="blue")
    assert engine.get_state()["robots"][0]["visual"] is None


# ── Endpoint /api/meshes ──────────────────────────────────────────────────────

@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from server.main import app
    with TestClient(app) as c:
        yield c


def test_mesh_endpoint_serves_glb(client):
    resp = client.get("/api/meshes/demo.glb")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "model/gltf-binary"
    assert resp.content[:4] == b"glTF"


def test_mesh_endpoint_404(client):
    assert client.get("/api/meshes/nope.glb").status_code == 404


def test_mesh_endpoint_rejects_traversal(client):
    assert client.get("/api/meshes/..%5Cexample.yaml").status_code == 400
    assert client.get("/api/meshes/x.stl").status_code == 400


def test_mesh_list_endpoint(client):
    lst = client.get("/api/meshes").json()
    assert "demo.glb" in lst


def test_null_blocks_mean_absent(tmp_path):
    # Toggles desligados no Builder exportam `bloco: null` — deve valer ausente
    p = tmp_path / "r.yaml"
    p.write_text("""
robot:
  name: T
  body: { radius: 0.10 }
  kicker: null
  dribbler: null
  visual: null
  sensors:
    ir_ring: null
    ball_velocity: null
""")
    cfg = load_robot_config(str(p))
    assert cfg.kicker is None
    assert cfg.dribbler is None
    assert cfg.visual is None
    assert cfg.sensors.ir_ring is None
    assert cfg.sensors.ball_velocity is None
