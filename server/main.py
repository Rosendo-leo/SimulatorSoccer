"""FastAPI server: robot CRUD + WebSocket simulation stream."""
from __future__ import annotations
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

ROBOTS_DIR = Path(__file__).parent.parent / "robots"

# ── Sim state ─────────────────────────────────────────────────────────────────

_engine   = None
_clients: set[WebSocket] = set()
_speed    = 1.0


def _build_engine(blue: str = "striker_v3", yellow: str = "goalkeeper_v2"):
    from sim.engine import SimEngine
    from sim.config_loader import load_robot_config
    from examples.attacker_strategy import strategy as attacker
    from examples.defender_strategy  import strategy as defender

    engine = SimEngine(seed=42)
    for fname, team, strat in [
        (f"{blue}.yaml",   "blue",   attacker),
        (f"{yellow}.yaml", "yellow", defender),
    ]:
        path = ROBOTS_DIR / fname
        if path.exists():
            engine.add_robot(load_robot_config(path), team, strategy_fn=strat)
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
    global _engine
    from sim.engine import PHYSICS_DT
    while True:
        try:
            if _engine is not None and not _engine.paused:
                state = _engine.step()
                if _clients:
                    msg  = json.dumps(_slim(state))
                    dead: set[WebSocket] = set()
                    for ws in list(_clients):
                        try:
                            await ws.send_text(msg)
                        except Exception:
                            dead.add(ws)
                    _clients.difference_update(dead)
            await asyncio.sleep(PHYSICS_DT / _speed)
        except asyncio.CancelledError:
            return
        except Exception:
            await asyncio.sleep(0.1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    _engine = _build_engine()
    task    = asyncio.create_task(_sim_loop())
    yield
    task.cancel()


app = FastAPI(title="RCJ Soccer Simulator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/sim")
async def ws_sim(ws: WebSocket):
    global _engine, _speed
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
            elif cmd == "restart":
                _engine = _build_engine(
                    msg.get("blue",   "striker_v3"),
                    msg.get("yellow", "goalkeeper_v2"),
                )
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
