"""The setup generators produce a state the chapter loop can consume, and the
stage framework freezes approved stages and skips re-running them.
"""

from __future__ import annotations

from ludllm.models.base import ModelBundle
from ludllm.models.mock import MockModel
from ludllm.pipeline.stages import STAGE_CAST, STAGE_NORMALIZE, STAGE_WORLD, run_stage
from ludllm.state.schema import BookState, CreativeBrief, KnowledgeKind, SecrecyTier
from ludllm.examples.mole import scripted_author


def _bundle() -> ModelBundle:
    return ModelBundle(
        drafter=MockModel(),
        extractor=MockModel(),
        critic=MockModel(family="google"),
        author=scripted_author(),
    )


def _fresh_state() -> BookState:
    return BookState(brief=CreativeBrief(raw_input="A mole inside a Vienna station."))


def test_normalize_populates_brief_with_provenance():
    state = _fresh_state()
    run_stage(state, STAGE_NORMALIZE, _bundle())
    kinds = {e.kind for e in state.brief.elements}
    assert "premise" in kinds and "character" in kinds
    assert all(e.provenance for e in state.brief.elements)
    assert STAGE_NORMALIZE in state.meta.frozen_stages


def test_world_generator_builds_world_facts_and_grounding():
    state = _fresh_state()
    run_stage(state, STAGE_NORMALIZE, _bundle())
    run_stage(state, STAGE_WORLD, _bundle())

    mole = state.fact("f_mole")
    assert mole is not None and mole.tier == SecrecyTier.hidden
    assert state.fact("f_station").tier == SecrecyTier.public
    # Real-world grounding is authored at the world stage (Forsyth's technique).
    w = state.authored.world
    assert len(w.real_anchors) >= 3
    assert w.real_organizations
    # The cast is NOT built yet; that is the next stage.
    assert state.authored.characters == []


def test_cast_generator_builds_people_and_belief_states():
    state = _fresh_state()
    for stage in (STAGE_NORMALIZE, STAGE_WORLD, STAGE_CAST):
        run_stage(state, stage, _bundle())

    marek = state.character("c_marek")
    assert marek.initial_beliefs[0].kind == KnowledgeKind.falsely_believes
    assert "c_vesna" in state.who_knows("f_mole", chapter=1)

    # The generated state drives the same no-leak traversal the loop relies on.
    forbidden = {f.id for f in state.forbidden_for_drafter("c_marek", chapter=1)}
    assert "f_mole" in forbidden
    assert "f_station" not in forbidden


def test_frozen_stage_is_not_rerun():
    state = _fresh_state()
    first = run_stage(state, STAGE_NORMALIZE, _bundle())
    assert first.ran and first.frozen
    again = run_stage(state, STAGE_NORMALIZE, _bundle())
    assert not again.ran  # skipped, already frozen
    # idempotent: still exactly one normalize in the frozen list
    assert state.meta.frozen_stages.count(STAGE_NORMALIZE) == 1


def test_gated_stage_freezes_only_on_approval():
    state = _fresh_state()
    rejected = run_stage(state, STAGE_NORMALIZE, _bundle(), gated=True, reviewer=lambda s, st: False)
    assert rejected.ran and not rejected.frozen
    assert STAGE_NORMALIZE not in state.meta.frozen_stages

    approved = run_stage(state, STAGE_NORMALIZE, _bundle(), gated=True, reviewer=lambda s, st: True)
    assert approved.frozen
    assert STAGE_NORMALIZE in state.meta.frozen_stages


def test_gates_off_auto_advances():
    state = _fresh_state()
    result = run_stage(state, STAGE_NORMALIZE, _bundle(), gated=False)
    assert result.approved and result.frozen
