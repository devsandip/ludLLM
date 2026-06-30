"""Stage 5, the writer: the per-chapter loop and its sub-steps.

Each sub-step is its own module so the parts most likely to grow (critique,
draft) have room to. The public surface is re-exported here, so callers do
`from ludllm.pipeline.writer import run_chapter` regardless of internal layout.
"""

from ludllm.pipeline.writer.context import (
    DrafterContext,
    LeakError,
    build_drafter_context,
)
from ludllm.pipeline.writer.critique import critique
from ludllm.pipeline.writer.draft import draft, revise
from ludllm.pipeline.writer.extract import extract
from ludllm.pipeline.writer.loop import ChapterRunResult, LoopConfig, run_chapter

__all__ = [
    "build_drafter_context",
    "DrafterContext",
    "LeakError",
    "draft",
    "revise",
    "critique",
    "extract",
    "run_chapter",
    "LoopConfig",
    "ChapterRunResult",
]
