"""The drafter sub-steps: write a chapter, and revise it against critique flags.

Both feed the scoped context from `context.py`, so the no-leak guarantee holds on
the first draft and on every revision.
"""

from __future__ import annotations

from ludllm.models.base import TASK_DRAFT, TASK_REVISE, ModelBundle
from ludllm.pipeline.writer.context import build_drafter_context
from ludllm.state.schema import BookState
from ludllm.util.blocks import make_block


def draft(state: BookState, n: int, models: ModelBundle) -> str:
    ctx = build_drafter_context(state, n)  # raises LeakError if scoping failed
    return models.drafter.generate(system=ctx.system, prompt=ctx.prompt, task=TASK_DRAFT)


def revise(state: BookState, n: int, prose: str, flags: list[str], models: ModelBundle) -> str:
    ctx = build_drafter_context(state, n)
    prompt = "\n".join(
        [ctx.prompt, make_block("PRIOR_DRAFT", prose), make_block("FLAGS", "; ".join(flags))]
    )
    return models.drafter.generate(system=ctx.system, prompt=prompt, task=TASK_REVISE)
