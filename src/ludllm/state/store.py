"""Load and save the book state. One recoverable JSON file, atomic writes.

Atomicity matters: a write interrupted mid-flush must not corrupt the single
source of truth. We write to a temp file in the same directory and os.replace
onto the target, which is atomic on POSIX.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ludllm.state.schema import BookState


def load_state(path: str | Path) -> BookState:
    path = Path(path)
    return BookState.model_validate_json(path.read_text(encoding="utf-8"))


def save_state(state: BookState, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = state.model_dump_json(indent=2)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
