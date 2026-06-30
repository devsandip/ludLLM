"""End-to-end on mocks: premise -> all setup stages -> chapter loop.

This is the capstone proof that the control plane (generators + gates) and the
data plane (state + no-leak) compose. The reveal authored in Stage 1 is bound to
an act in Stage 2 and to chapters in Stage 3, and the Stage 4 loop then respects
and updates it. No API calls, fully deterministic.
"""

from __future__ import annotations

from ludllm.models.base import ModelBundle
from ludllm.models.mock import MockModel
from ludllm.pipeline.writer import run_chapter
from ludllm.pipeline.stages import SETUP_STAGES, run_stage
from ludllm.state.schema import BookState, CreativeBrief, KnowledgeKind, SecrecyTier
from ludllm.examples.mole import scripted_author


def _bundle() -> ModelBundle:
    return ModelBundle(
        drafter=MockModel(family="anthropic"),
        extractor=MockModel(family="anthropic"),
        critic=MockModel(family="google"),  # different family: cross-family critique
        author=scripted_author(),
    )


def test_full_setup_then_chapter_loop():
    state = BookState(brief=CreativeBrief(raw_input="A mole inside a Vienna station."))
    bundle = _bundle()

    # Run all setup stages, gates-off (auto-advance), as in a tuning run.
    for stage in SETUP_STAGES:
        result = run_stage(state, stage, bundle)
        assert result.frozen, f"stage {stage} did not freeze"
    assert state.meta.frozen_stages == SETUP_STAGES

    # The reveal was authored once and bound progressively across the stages.
    mole = state.fact("f_mole")
    assert mole.tier == SecrecyTier.hidden
    assert mole.reveal.act_anchor == "a3"                # bound in Stage 2
    assert mole.reveal.reader_reveal_chapter == 6        # bound in Stage 3
    assert mole.reveal.character_reveal_chapter == 9     # bound in Stage 3

    # Before the reveal, the secret is denied to the drafter from Marek's POV.
    assert "f_mole" in {f.id for f in state.forbidden_for_drafter("c_marek", 1)}

    # Run the protagonist's reveal chapter through the Stage 4 loop.
    run = run_chapter(state, 9, bundle)
    assert run.accepted
    assert run.leaks == []

    # The loop wrote the belief update back: Marek now knows it from ch10 on.
    assert state.effective_beliefs("c_marek", 10)["f_mole"].kind == KnowledgeKind.knows
    assert "c_marek" in state.who_knows("f_mole", 10)
