"""Engine-first proof: the chapter loop runs deterministically over the fixture,
the information asymmetry holds end to end, and the leak guard catches a spill.
"""

from __future__ import annotations

import pytest

from ludllm.models.base import ModelBundle
from ludllm.models.mock import LeakyMockModel, MockModel
from ludllm.pipeline.writer import LoopConfig, build_drafter_context, run_chapter
from ludllm.state.schema import KnowledgeKind
from tests.fixtures.tiny_state import tiny_state

MOLE_TEXT = "Vesna is an ISI double agent inside the station."


def mock_bundle(drafter=None) -> ModelBundle:
    return ModelBundle(
        drafter=drafter or MockModel(),
        extractor=MockModel(name="extractor"),
        critic=MockModel(name="critic"),
    )


# --------------------------------------------------------------------------- #
# Scoped context
# --------------------------------------------------------------------------- #

def test_drafter_prompt_excludes_the_forbidden_fact_at_ch1():
    state = tiny_state()
    ctx = build_drafter_context(state, 1)
    assert "f_mole" in ctx.forbidden_fact_ids
    assert "f_mole" not in ctx.allowed_fact_ids
    assert MOLE_TEXT.lower() not in ctx.prompt.lower()
    assert "f_station" in ctx.allowed_fact_ids  # public fact is allowed


def test_reveal_chapter_allows_the_fact_being_revealed():
    state = tiny_state()
    # ch9 is Marek's character-reveal of the mole: the drafter MUST get it.
    ctx = build_drafter_context(state, 9)
    assert "f_mole" in ctx.allowed_fact_ids
    assert "f_mole" not in ctx.forbidden_fact_ids


# --------------------------------------------------------------------------- #
# The loop
# --------------------------------------------------------------------------- #

def test_happy_path_chapter_accepts_without_leak():
    state = tiny_state()
    result = run_chapter(state, 1, mock_bundle())
    assert result.accepted
    assert result.leaks == []
    assert result.prose
    assert MOLE_TEXT.lower() not in result.prose.lower()
    assert result.chapter_state.status.value == "accepted"


def test_reveal_chapter_updates_belief_state_end_to_end():
    state = tiny_state()
    # Before: Marek does not know the mole fact.
    assert "c_marek" not in state.who_knows("f_mole", chapter=10)

    result = run_chapter(state, 9, mock_bundle())
    assert result.accepted

    # Extract wrote the belief update back; now Marek knows it from ch10 on,
    # and the drafter is no longer denied it. This ties the loop to the schema.
    beliefs = state.effective_beliefs("c_marek", chapter=10)
    assert beliefs["f_mole"].kind == KnowledgeKind.knows
    assert "c_marek" in state.who_knows("f_mole", chapter=10)
    forbidden_ids = {f.id for f in state.forbidden_for_drafter("c_marek", chapter=10)}
    assert "f_mole" not in forbidden_ids


def test_leak_guard_catches_a_spill_and_blocks_acceptance():
    state = tiny_state()
    leaky = LeakyMockModel(leak_text=MOLE_TEXT)
    result = run_chapter(state, 1, mock_bundle(drafter=leaky), LoopConfig(max_revise=2))
    assert not result.accepted
    assert "f_mole" in result.leaks
    assert any("LEAK" in f for f in result.flags)
    assert result.chapter_state.status.value == "critiqued"
    assert result.revise_iterations == 2  # it tried to fix and could not


def test_no_belief_update_when_chapter_rejected():
    state = tiny_state()
    leaky = LeakyMockModel(leak_text=MOLE_TEXT)
    run_chapter(state, 1, mock_bundle(drafter=leaky))
    # A rejected chapter must not mutate running belief state.
    assert state.running.belief_updates == []


# --------------------------------------------------------------------------- #
# Cross-family critique discipline
# --------------------------------------------------------------------------- #

def test_same_family_critic_is_rejected():
    bundle = ModelBundle(
        drafter=MockModel(family="anthropic"),
        extractor=MockModel(family="anthropic"),
        critic=MockModel(family="anthropic"),
    )
    with pytest.raises(ValueError):
        bundle.assert_cross_family_critique()


def test_cross_family_critic_is_accepted():
    bundle = ModelBundle(
        drafter=MockModel(family="anthropic"),
        extractor=MockModel(family="anthropic"),
        critic=MockModel(family="google"),
    )
    bundle.assert_cross_family_critique()  # does not raise
