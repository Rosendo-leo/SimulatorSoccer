"""Records simulation frames to a JSON Lines file for replay."""
from __future__ import annotations
import json
import gzip
from pathlib import Path
from typing import IO


class Recorder:
    def __init__(self, path: str | Path, compress: bool = False) -> None:
        self._path = Path(path)
        self._compress = compress
        self._file: IO | None = None
        self._count = 0

    def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._compress:
            self._file = gzip.open(self._path.with_suffix(".jsonl.gz"), "wt", encoding="utf-8")
        else:
            self._file = open(self._path, "w", encoding="utf-8")
        self._count = 0

    def record(self, frame: dict) -> None:
        if self._file is None:
            raise RuntimeError("Call open() before record()")
        self._file.write(json.dumps(frame, separators=(",", ":")) + "\n")
        self._count += 1

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None

    def __enter__(self) -> "Recorder":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    @property
    def frame_count(self) -> int:
        return self._count


def load_replay(path: str | Path) -> list[dict]:
    p = Path(path)
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
