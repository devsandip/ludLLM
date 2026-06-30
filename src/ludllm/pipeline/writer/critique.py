"""Critique: cross-family model flags plus the deterministic leak guard."""

from __future__ import annotations

from ludllm.models.base import TASK_CRITIQUE, ModelBundle
from ludllm.pipeline.guards import find_leaks
from ludllm.prompts import CRITIQUE_SYSTEM
from ludllm.state.schema import BookState
from ludllm.util.blocks import make_block
from ludllm.util.jsonio import loads_lenient


def critique(state: BookState, n: int, prose: str, models: ModelBundle) -> list[str]:
    """The leak guard runs regardless of what the critic model says; it is the
    model-independent floor."""
    beat = state.chapter_beat(n)
    forbidden = state.forbidden_for_drafter(beat.pov, n) if beat.pov else []

    prompt = "\n".join(
        [
            make_block("PROSE", prose),
            make_block("FORBIDDEN_FACT_IDS", ",".join(f.id for f in forbidden)),
        ]
    )
    raw = models.critic.generate(system=CRITIQUE_SYSTEM, prompt=prompt, task=TASK_CRITIQUE)
    try:
        parsed = loads_lenient(raw)
        model_flags = list(parsed.get("flags", [])) if isinstance(parsed, dict) else []
    except (ValueError, AttributeError):
        model_flags = []  # a critic that won't return JSON cannot block; the leak guard still runs

    leak_ids = find_leaks(prose, forbidden)
    leak_flags = [f"LEAK: forbidden fact {fid} surfaced in the prose" for fid in leak_ids]
    return model_flags + leak_flags
