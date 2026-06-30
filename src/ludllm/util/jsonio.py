"""Tolerant JSON parsing for real model output.

Frontier models often wrap JSON in ```json fences or add a line of prose. This
strips that and extracts the outermost JSON value, so the structured-output
steps survive normal model formatting without forcing provider-specific
structured-output APIs into the model-agnostic pipeline.
"""

from __future__ import annotations

import json
import re


def loads_lenient(text: str) -> object:
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\n", "", s)
        s = re.sub(r"\n```\s*$", "", s).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", s, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        raise
