"""Diretórios de dados do servidor.

Em desenvolvimento tudo fica na raiz do repositório. No executável desktop
(PyInstaller, sys.frozen) o bundle é somente-leitura, então os diretórios
graváveis (robots/, recordings/, scenarios/) vão para a pasta de dados do
usuário (%APPDATA%/RCJSoccerSim no Windows), seedada com os robôs de exemplo
na primeira execução. Override via env var RCJ_DATA_DIR.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))

if FROZEN:
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    _default_data = Path(os.environ.get("APPDATA", Path.home())) / "RCJSoccerSim"
    DATA_DIR = Path(os.environ.get("RCJ_DATA_DIR") or _default_data)
else:
    BUNDLE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BUNDLE_DIR

ROBOTS_DIR     = DATA_DIR / "robots"
RECORDINGS_DIR = DATA_DIR / "recordings"
SCENARIOS_DIR  = DATA_DIR / "scenarios"
EXAMPLES_DIR   = BUNDLE_DIR / "examples"
BRIDGE_DIR     = BUNDLE_DIR / "bridge"


def ensure_data_dirs() -> None:
    """Cria os diretórios graváveis e seeda robots/ com os YAMLs do bundle."""
    if not FROZEN:
        return
    for d in (ROBOTS_DIR, RECORDINGS_DIR, SCENARIOS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    bundled = BUNDLE_DIR / "robots"
    if bundled.is_dir():
        for src in bundled.glob("*.yaml"):
            dst = ROBOTS_DIR / src.name
            if not dst.exists():
                shutil.copyfile(src, dst)
