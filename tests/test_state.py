"""Smoke tests for the state schema: round-trip + the no-leak traversal.

The no-leak tests are the important ones. They assert the data behind the
triple-layer scoped context is correct BEFORE any model is wired in: the mole
fact must be forbidden to the drafter from Marek's POV until the scheduled
reveal, and allowed after.
"""

from __future__ import annotations

import pytest

from ludllm.state.schema import Belief, BeliefUpdate, KnowledgeKind
from ludllm.state.store import load_state, save_state
from tests.fixtures.tiny_state import tiny_state


def test_round_trip(tmp_path):
    state = tiny_state()
    path = tmp_path / "book_state.json"
    save_state(state, path)
    loaded = load_state(path)
    assert loaded.model_dump() == state.model_dump()


def test_reader_learns_on_schedule():
    state = tiny_state()
    # reader_reveal_chapter is 6, so the reader does not know at ch 6, knows at ch 7.
    known_at_6 = {f.id for f in state.reader_known_facts(chapter=6)}
    known_at_7 = {f.id for f in state.reader_known_facts(chapter=7)}
    assert "f_mole" not in known_at_6
    assert "f_mole" in known_at_7
    # public facts are always reader-known
    assert "f_station" in known_at_6


def test_marek_falsely_believes_then_unaware_of_truth():
    state = tiny_state()
    # Marek does not KNOW the mole fact early (he falsely believes otherwise).
    known = {f.id for f in state.character_known_facts("c_marek", chapter=1)}
    assert "f_mole" not in known
    beliefs = state.effective_beliefs("c_marek", chapter=1)
    assert beliefs["f_mole"].kind == KnowledgeKind.falsely_believes


def test_vesna_knows_from_the_start():
    state = tiny_state()
    assert "c_vesna" in state.who_knows("f_mole", chapter=1)
    assert "c_marek" not in state.who_knows("f_mole", chapter=1)


def test_drafter_is_denied_the_mole_fact_before_reveal():
    state = tiny_state()
    # From Marek's POV at ch 3, the mole fact is neither his knowledge nor the
    # reader's: it MUST be forbidden to the drafter.
    forbidden = {f.id for f in state.forbidden_for_drafter("c_marek", chapter=3)}
    assert "f_mole" in forbidden
    assert "f_station" not in forbidden  # public, always allowed


def test_drafter_allowed_the_fact_after_character_learns_it():
    state = tiny_state()
    # The loop's extract step records that Marek learned the truth in chapter 9.
    state.running.belief_updates.append(
        BeliefUpdate(chapter=9, character_id="c_marek", fact_id="f_mole",
                     kind=KnowledgeKind.knows)
    )
    forbidden = {f.id for f in state.forbidden_for_drafter("c_marek", chapter=10)}
    assert "f_mole" not in forbidden
    # and he now counts as knowing it
    assert "c_marek" in state.who_knows("f_mole", chapter=10)


def test_public_fact_cannot_carry_reveal():
    from ludllm.state.schema import Fact, RevealPlan, SecrecyTier

    with pytest.raises(ValueError):
        Fact(id="x", text="t", tier=SecrecyTier.public, reveal=RevealPlan())


def test_false_belief_requires_value():
    with pytest.raises(ValueError):
        Belief(fact_id="f", kind=KnowledgeKind.falsely_believes)
