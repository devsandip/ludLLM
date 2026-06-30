"""Delimited prompt blocks. The loop writes them; the mock model reads them.

Keeping the format in one place means the deterministic mock and the real
prompt builders cannot drift apart.
"""

from __future__ import annotations

import re


def make_block(name: str, body: object) -> str:
    return f"[{name}]\n{body}\n[/{name}]"


def read_block(text: str, name: str) -> str:
    m = re.search(rf"\[{re.escape(name)}\]\n(.*?)\n\[/{re.escape(name)}\]", text, re.DOTALL)
    return m.group(1).strip() if m else ""
