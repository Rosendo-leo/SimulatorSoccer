"""FastAPI server: robot CRUD + WebSocket simulation stream."""
from __future__ import annotations
import asyncio
import importlib
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from server.paths import (
    ROBOTS_DIR, EXAMPLES_DIR, BRIDGE_DIR, RECORDINGS_DIR, SCENARIOS_DIR,
)

# Só módulos destes pacotes podem ser importados via WebSocket/REST
_STRATEGY_PREFIXES = ("examples.", "bridge.")

DEFAULT_MATCH = {
    "blue":            ["striker_v3"],
    "yellow":          ["goalkeeper_v2"],
    "blue_strategy":   "examples.attacker_strategy",
    "yellow_strategy": "examples.defender_strategy",
}

# ── Sim state ─────────────────────────────────────────────────────────────────

_engine    = None
_match     = dict(DEFAULT_MATCH)   # config usada no último (re)start
_clients: set[WebSocket] = set()
_speed     = 1.0
_recording: str | None = None      # nome da gravação ativa (sem extensão)


def list_strategies() -> list[str]:
    """Módulos de estratégia disponíveis (examples/*.py + bridge compilado)."""
    found = []
    for p in sorted(EXAMPLES_DIR.glob("*_strategy.py")):
        found.append(f"examples.{p.stem}")
    for p in sorted(BRIDGE_DIR.glob("cpp_*")):
        if p.suffix in (".pyd", ".so"):
            found.append(f"bridge.{p.name.split('.')[0]}")
    return found


def _load_strategy(module_name: str):
    if not module_name.startswith(_STRATEGY_PREFIXES):
        raise ValueError(f"Strategy module not allowed: {module_name!r}")
    mod = importlib.import_module(module_name)
    fn  = getattr(mod, "strategy", None)
    if fn is None:
        raise ValueError(f"{module_name} has no strategy() function")
    return fn


def _build_engine(match: dict):
    from sim.engine import SimEngine
    from sim.config_loader import load_robot_config

    strats = {
        "blue":   _load_strategy(match.get("blue_strategy")
                                 or DEFAULT_MATCH["blue_strategy"]),
        "yellow": _load_strategy(match.get("yellow_strategy")
                                 or DEFAULT_MATCH["yellow_strategy"]),
    }

    engine = SimEngine(seed=42)
    for team in ("blue", "yellow"):
        names = match.get(team) or DEFAULT_MATCH[team]
        if isinstance(names, str):
            names = [names]
        for name in names[:2]:      # máx. 2 robôs por time (2v2)
            path = ROBOTS_DIR / f"{name}.yaml"
            if path.exists():
                engine.add_robot(load_robot_config(path), team,
                                 strategy_fn=strats[team])
    return engine


def _slim(state: dict) -> dict:
    """Strip percepts — large arrays not needed by the viewer."""
    slim = dict(state)
    slim["robots"] = [
        {k: v for k, v in r.items() if k != "percepts"}
        for r in state["robots"]
    ]
    return slim


async def _sim_loop():
    """Loop de tempo real com catch-up.

    No Windows o asyncio.sleep tem resolução ~15 ms, então dormir PHYSICS_DT
    (16.7 ms) por step rende ~42 ticks/s. Em vez disso, acumulamos o tempo
    decorrido (escalado pela velocidade) e damos quantos steps forem devidos
    por iteração — o tick rate médio fica em 60/s independente do timer.
    """
    global _engine
    from sim.engine import PHYSICS_DT
    MAX_STEPS_PER_ITER = 8          # evita espiral de atraso após stalls
    acc  = 0.0
    prev = time.perf_counter()
    while True:
        try:
            now  = time.perf_counter()
            acc += (now - prev) * _speed
            prev = now
            if _engine is not None and not _engine.paused:
                steps = min(int(acc / PHYSICS_DT), MAX_STEPS_PER_ITER)
                acc  -= steps * PHYSICS_DT
                acc   = min(acc, PHYSICS_DT * MAX_STEPS_PER_ITER)
                state = None
                for _ in range(steps):
                    state = _engine.step()
                if state is not None and _clients:
                    msg  = json.dumps(_slim(state))
                    dead: set[WebSocket] = set()
                    for ws in list(_clients):
                        try:
                            await ws.send_text(msg)
                        except Exception:
                            dead.add(ws)
                    _clients.difference_update(dead)
            else:
                acc = 0.0
            await asyncio.sleep(PHYSICS_DT)
        except asyncio.CancelledError:
            return
        except Exception:
            await asyncio.sleep(0.1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    _engine = _build_engine(_match)
    task    = asyncio.create_task(_sim_loop())
    yield
    task.cancel()


app = FastAPI(title="RCJ Soccer Simulator API", lifespan=lifespan)

# Origens extras (produção) via env var, separadas por vírgula:
#   CORS_ORIGINS=https://meu-sim.vercel.app,https://meudominio.com
_cors_origins = [
    "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000",
    # Webview do app desktop (Tauri)
    "http://tauri.localhost", "https://tauri.localhost", "tauri://localhost",
] + [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket ─────────────────────────────────────────────────────────────────

async def _broadcast_state() -> None:
    """Envia o estado atual a todos os clientes (útil com o sim pausado)."""
    if _engine is None or not _clients:
        return
    msg  = json.dumps(_slim(_engine.get_state()))
    dead: set[WebSocket] = set()
    for ws in list(_clients):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


def _scenario_path(name: str) -> Path:
    if not name or "/" in name or "\\" in name or ".." in name:
        raise HTTPException(400, "Invalid scenario name")
    return SCENARIOS_DIR / f"{name}.json"


def _capture_scenario() -> dict:
    state = _engine.get_state()
    return {
        "ball":   {"x": state["ball"]["x"], "y": state["ball"]["y"]},
        "robots": [
            {"id": r["id"], "x": r["x"], "y": r["y"], "heading": r["heading"]}
            for r in state["robots"]
        ],
    }


def _apply_scenario(data: dict) -> None:
    _engine.set_ball_pose(data["ball"]["x"], data["ball"]["y"])
    for r in data.get("robots", []):
        try:
            _engine.set_robot_pose(r["id"], r["x"], r["y"], r.get("heading"))
        except KeyError:
            pass    # cenário salvo com outro line-up — ignora ids ausentes


def _stop_recording_if_active() -> str | None:
    """Fecha a gravação corrente (se houver) e devolve o nome dela."""
    global _recording
    name, _recording = _recording, None
    if name and _engine:
        _engine.stop_recording()
    return name


@app.websocket("/ws/sim")
async def ws_sim(ws: WebSocket):
    global _engine, _speed, _match, _recording
    await ws.accept()
    _clients.add(ws)
    if _engine:
        try:
            await ws.send_text(json.dumps(_slim(_engine.get_state())))
        except Exception:
            pass
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            cmd = msg.get("cmd")
            if   cmd == "pause"  and _engine: _engine.paused = True
            elif cmd == "resume" and _engine: _engine.paused = False
            elif cmd == "reset"  and _engine: _engine._kickoff_reset()
            elif cmd == "speed":
                _speed = max(0.25, min(8.0, float(msg.get("value", 1.0))))
            elif cmd == "place" and _engine:
                try:
                    obj = msg.get("object", "ball")
                    x, y = float(msg["x"]), float(msg["y"])
                    if obj == "ball":
                        _engine.set_ball_pose(x, y)
                    else:
                        h = msg.get("heading")
                        _engine.set_robot_pose(obj, x, y,
                                               float(h) if h is not None else None)
                    await _broadcast_state()
                except (KeyError, ValueError, TypeError) as exc:
                    await ws.send_text(json.dumps(
                        {"event": "error", "detail": str(exc)}))
            elif cmd == "scenario_save" and _engine:
                try:
                    path = _scenario_path(msg.get("name", ""))
                    SCENARIOS_DIR.mkdir(exist_ok=True)
                    path.write_text(json.dumps(_capture_scenario(), indent=2),
                                    encoding="utf-8")
                    await ws.send_text(json.dumps(
                        {"event": "scenario_saved", "name": path.stem}))
                except HTTPException as exc:
                    await ws.send_text(json.dumps(
                        {"event": "error", "detail": exc.detail}))
            elif cmd == "scenario_load" and _engine:
                try:
                    path = _scenario_path(msg.get("name", ""))
                    if not path.exists():
                        raise HTTPException(404, f"Scenario not found: {msg.get('name')}")
                    _apply_scenario(json.loads(path.read_text(encoding="utf-8")))
                    await _broadcast_state()
                    await ws.send_text(json.dumps(
                        {"event": "scenario_loaded", "name": path.stem}))
                except HTTPException as exc:
                    await ws.send_text(json.dumps(
                        {"event": "error", "detail": exc.detail}))
            elif cmd == "record_start" and _engine:
                if _recording is None:
                    _recording = time.strftime("match_%Y%m%d_%H%M%S")
                    _engine.start_recording(RECORDINGS_DIR / f"{_recording}.jsonl")
                await ws.send_text(json.dumps(
                    {"event": "recording_started", "name": _recording}))
            elif cmd == "record_stop":
                name = _stop_recording_if_active()
                await ws.send_text(json.dumps(
                    {"event": "recording_stopped", "name": name}))
            elif cmd == "restart":
                _stop_recording_if_active()
                new_match = {
                    k: msg[k] for k in
                    ("blue", "yellow", "blue_strategy", "yellow_strategy")
                    if msg.get(k)
                }
                try:
                    _engine = _build_engine({**DEFAULT_MATCH, **new_match})
                    _match  = {**DEFAULT_MATCH, **new_match}
                    await ws.send_text(json.dumps(
                        {"event": "restarted", "match": _match}))
                except Exception as exc:
                    await ws.send_text(json.dumps(
                        {"event": "error", "detail": str(exc)}))
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)


# ── REST ──────────────────────────────────────────────────────────────────────

@app.get("/api/sim/state")
def get_state() -> dict:
    if not _engine:
        raise HTTPException(503, "Sim not running")
    return _slim(_engine.get_state())


@app.get("/api/robots")
def list_robots() -> list[str]:
    return sorted(p.stem for p in ROBOTS_DIR.glob("*.yaml"))


@app.get("/api/strategies")
def get_strategies() -> list[str]:
    return list_strategies()


@app.get("/api/match")
def get_match() -> dict:
    return dict(_match)


@app.get("/api/scenarios")
def list_scenarios() -> list[str]:
    if not SCENARIOS_DIR.exists():
        return []
    return sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))


@app.delete("/api/scenarios/{name}")
def delete_scenario(name: str) -> dict:
    path = _scenario_path(name)
    if not path.exists():
        raise HTTPException(404, f"Scenario '{name}' not found")
    path.unlink()
    return {"deleted": name}


@app.get("/api/recordings")
def list_recordings() -> list[dict]:
    if not RECORDINGS_DIR.exists():
        return []
    out = []
    for p in sorted(RECORDINGS_DIR.glob("*.jsonl"), reverse=True):
        if p.stem == _recording:
            continue    # gravação em andamento — arquivo ainda aberto
        out.append({
            "name":     p.stem,
            "size_kb":  round(p.stat().st_size / 1024, 1),
            "mtime":    p.stat().st_mtime,
        })
    return out


@app.get("/api/recordings/{name}")
def get_recording(name: str) -> dict:
    from sim.recorder import load_replay
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(400, "Invalid recording name")
    path = RECORDINGS_DIR / f"{name}.jsonl"
    if not path.exists():
        raise HTTPException(404, f"Recording '{name}' not found")
    frames = [_slim(f) for f in load_replay(path)]
    return {"name": name, "frames": frames}


@app.delete("/api/recordings/{name}")
def delete_recording(name: str) -> dict:
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(400, "Invalid recording name")
    path = RECORDINGS_DIR / f"{name}.jsonl"
    if not path.exists():
        raise HTTPException(404, f"Recording '{name}' not found")
    path.unlink()
    return {"deleted": name}


@app.get("/api/robots/{name}")
def get_robot(name: str) -> dict:
    path = ROBOTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(404, f"Robot '{name}' not found")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@app.post("/api/robots/{name}", status_code=201)
def save_robot(name: str, body: dict[str, Any]) -> dict:
    ROBOTS_DIR.mkdir(exist_ok=True)
    path = ROBOTS_DIR / f"{name}.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(body, f, default_flow_style=False,
                  allow_unicode=True, sort_keys=False)
    return {"saved": name}


@app.delete("/api/robots/{name}")
def delete_robot(name: str) -> dict:
    path = ROBOTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(404, f"Robot '{name}' not found")
    path.unlink()
    return {"deleted": name}
