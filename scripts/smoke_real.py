"""Tiny real-model validation on the bundled mole example.

Setup runs on the free scripted author (deterministic), so this isolates the
real-model integration: Opus drafts, Haiku extracts, Gemini critiques. Proves the
keys work, real prose flows through the no-leak scoped context, and the belief
state updates after the scheduled reveal. Costs a few cents.

    uv run python scripts/smoke_real.py
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from ludllm.models.base import ModelBundle  # noqa: E402
from ludllm.models.mock import MockModel  # noqa: E402
from ludllm.models.providers import AnthropicModel, GeminiModel  # noqa: E402
from ludllm.examples.mole import scripted_author, seed_state  # noqa: E402
from ludllm.pipeline.writer import LoopConfig, run_chapter  # noqa: E402
from ludllm.pipeline.stages import SETUP_STAGES, run_stage  # noqa: E402
from ludllm.state.schema import KnowledgeKind  # noqa: E402
from ludllm.state.store import save_state  # noqa: E402


def main() -> None:
    # 1. Build a valid mole state with the free scripted setup.
    state = seed_state()
    setup = ModelBundle(
        drafter=MockModel(), extractor=MockModel(), critic=MockModel(family="google"),
        author=scripted_author(),
    )
    for stage in SETUP_STAGES:
        run_stage(state, stage, setup)
    print("setup complete:", state.meta.frozen_stages)

    # 2. Real models for the chapter loop.
    real = ModelBundle(
        drafter=AnthropicModel("claude-opus-4-8", name="drafter", max_tokens=3500),
        extractor=AnthropicModel("claude-haiku-4-5", name="extractor", max_tokens=1500),
        critic=GeminiModel(name="critic"),
        author=AnthropicModel("claude-opus-4-8", name="author"),
    )
    real.assert_cross_family_critique()

    out = Path("runs/smoke")
    for n in (1, 9):
        res = run_chapter(state, n, real, LoopConfig(max_revise=1, output_dir=str(out / "chapters")))
        print(f"\n===== Chapter {n} =====")
        print(f"accepted={res.accepted}  leaks={res.leaks}  revises={res.revise_iterations}")
        print(f"critic flags: {res.flags}")
        print("prose (first 500 chars):")
        print(res.prose[:500])

    # 3. The reveal must have propagated: Marek knows the mole from ch10 on.
    belief = state.effective_beliefs("c_marek", 10).get("f_mole")
    print("\n===== asymmetry check =====")
    print("Marek knows the mole at ch10:", bool(belief) and belief.kind == KnowledgeKind.knows)
    print("Who knows the mole at ch10:", state.who_knows("f_mole", 10))

    save_state(state, out / "book_state.json")
    print(f"\nstate written to {out}/book_state.json")


if __name__ == "__main__":
    main()
