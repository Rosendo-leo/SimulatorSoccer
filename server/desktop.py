"""Entry point do sidecar desktop (compilado com PyInstaller).

Roda o mesmo FastAPI app do deploy web, mas só em loopback e com os
diretórios graváveis na pasta de dados do usuário (ver server/paths.py).
O shell Tauri inicia este processo e o encerra ao fechar a janela.
"""
from __future__ import annotations

import os

import uvicorn

from server.paths import ensure_data_dirs


def main() -> None:
    ensure_data_dirs()
    port = int(os.environ.get("RCJ_SERVER_PORT", "8765"))
    from server.main import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
