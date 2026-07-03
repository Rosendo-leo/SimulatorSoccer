# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec do sidecar desktop (server/desktop.py → rcj-server.exe).

Build:  pyinstaller packaging/rcj-server.spec --distpath packaging/dist
Rodar da raiz do repositório. O exe resultante é onefile, escuta em
127.0.0.1:8765 e guarda dados em %APPDATA%/RCJSoccerSim.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).parent  # spec fica em packaging/, raiz é o pai

hiddenimports = (
    collect_submodules("sim")
    + collect_submodules("server")
    + collect_submodules("examples")
)
datas, binaries = [], []
for pkg in ("pymunk", "uvicorn"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# examples/*.py como datas: list_strategies() faz glob desses arquivos
datas += [(str(p), "examples") for p in (ROOT / "examples").glob("*_strategy.py")]
# robots de exemplo — seedam a pasta de dados do usuário na primeira execução
datas += [(str(p), "robots") for p in (ROOT / "robots").glob("*.yaml")]
datas += [(str(p), "robots/meshes")
          for p in (ROOT / "robots" / "meshes").glob("*.glb")]

a = Analysis(
    [str(ROOT / "server" / "desktop.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["pygame", "torch", "matplotlib", "tkinter",
              "gymnasium", "pettingzoo", "stable_baselines3"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="rcj-server",
    debug=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
