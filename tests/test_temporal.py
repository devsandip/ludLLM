"""The temporal spine: the anachronism backstop, per-era belief ordering across a
braided timeline (knowledge accrues in STORY time, not reading order), and the
era / age deterministic checks. All offline.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ludllm.authoring import render as R
from ludllm.authoring.checks import check_state
from ludllm.examples.mole import scripted_author, seed_state
from ludllm.models.base import ModelBundle
from ludllm.models.mock import MockModel
from ludllm.pipeline.generators import _clean_character
from ludllm.pipeline.stages import SETUP_STAGES
from ludllm.pipeline.stages import run_stage as pipeline_run_stage
from ludllm.pipeline.writer import LoopConfig, run_chapter
from ludllm.reference.anachronisms import scan_anachronisms
from ludllm.state.schema import (
    Authored,
    Belief,
    BeliefUpdate,
    BookState,
    ChapterBeat,
    Character,
    Era,
    Fact,
    KnowledgeKind,
    NarrativeDesign,
    SecrecyTier,
    World,
)


# --------------------------------------------------------------------------- #
# The anachronism scanner (the deterministic backstop).
# --------------------------------------------------------------------------- #

def test_scan_flags_tech_ahead_of_its_time():
    flags = scan_anachronisms("He used his mobile phone, then ordered DNA testing.", 1975)
    assert any("mobile phone" in f for f in flags)
    assert any("dna testing" in f.lower() for f in flags)


def test_scan_flags_defunct_state_and_old_name_too_late():
    flags = scan_anachronisms("He had served the KGB out of Leningrad.", 2010)
    assert any("kgb" in f.lower() for f in flags)
    assert any("leningrad" in f.lower() for f in flags)


def test_scan_clean_when_period_correct():
    # Dead drop, telephone box, and Leningrad are all right for 1985.
    assert scan_anachronisms("A dead drop behind the telephone box in Leningrad.", 1985) == []


def test_scan_without_a_year_is_a_noop():
    assert scan_anachronisms("smartphones and drone strikes everywhere", None) == []


# --------------------------------------------------------------------------- #
# A braided two-era state, built by hand (no model), to exercise per-era beliefs.
# --------------------------------------------------------------------------- #

def _braided_state() -> BookState:
    world = World(
        premise="A betrayal seeded in 1961 surfaces in 1991.",
        eras=[
            Era(id="e_past", label="Berlin 1961", year_start=1961, place="Berlin",
                capability_baseline=["Dead drops and phone boxes; no mobile phones."]),
            Era(id="e_present", label="Vienna 1991", year_start=1991, place="Vienna",
                capability_baseline=["The USSR is collapsing; the KGB is about to be dissolved."]),
        ],
    )
    facts = [
        Fact(id="f_secret", text="Anna's old chief was the mole.", tier=SecrecyTier.hidden),
        Fact(id="f_other", text="A present-day discovery.", tier=SecrecyTier.hidden),
        Fact(id="f_past", text="A 1961 discovery.", tier=SecrecyTier.hidden),
    ]
    anna = Character(
        id="c_anna", name="Anna", born=1935,
        era_beliefs={
            "e_past": [Belief(fact_id="f_secret", kind=KnowledgeKind.does_not_know)],
            "e_present": [Belief(fact_id="f_secret", kind=KnowledgeKind.knows)],
        },
    )
    outline = [
        # Printed present-first, but story time runs 1961 -> 1991.
        ChapterBeat(n=1, era_id="e_present", story_time="1991", pov="c_anna", present=["c_anna"]),
        ChapterBeat(n=2, era_id="e_past", story_time="1961", pov="c_anna", present=["c_anna"]),
    ]
    state = BookState(
        authored=Authored(
            world=world, facts=facts, characters=[anna],
            narrative=NarrativeDesign(mode="dual_timeline", era_ids=["e_past", "e_present"]),
            chapter_outline=outline,
        )
    )
    state.running.belief_updates = [
        BeliefUpdate(chapter=1, character_id="c_anna", fact_id="f_other", kind=KnowledgeKind.knows),
        BeliefUpdate(chapter=2, character_id="c_anna", fact_id="f_past", kind=KnowledgeKind.knows),
    ]
    return state


def test_per_era_authored_belief_selects_by_era():
    state = _braided_state()
    past = state.effective_beliefs("c_anna", 2)       # the 1961 chapter
    present = state.effective_beliefs("c_anna", 1)     # the 1991 chapter
    # The same person, two eras: she does not know the secret in 1961, knows it in 1991.
    assert past["f_secret"].kind == KnowledgeKind.does_not_know
    assert present["f_secret"].kind == KnowledgeKind.knows


def test_knowledge_does_not_bleed_backward_but_flows_forward_in_story_time():
    state = _braided_state()
    past = state.effective_beliefs("c_anna", 2)       # 1961
    present = state.effective_beliefs("c_anna", 1)     # 1991, printed first

    # A 1991 discovery must NOT leak back into the 1961 chapter.
    assert "f_other" not in past
    # The 1961 discovery DOES flow forward into the later-in-story (earlier-printed)
    # 1991 chapter: knowledge accrues in story time, not reading order.
    assert present["f_past"].kind == KnowledgeKind.knows


def test_single_era_belief_ordering_is_unchanged():
    # With one era, story rank reduces to chapter order: an update at ch5 is visible
    # at ch6 and not at ch4 (the legacy behavior, preserved).
    world = World(premise="x", eras=[Era(id="e1", year_start=1985, capability_baseline=["x"])])
    c = Character(id="c1", name="C")
    f = Fact(id="f1", text="a secret", tier=SecrecyTier.hidden)
    outline = [ChapterBeat(n=n, era_id="e1", pov="c1") for n in (4, 5, 6)]
    state = BookState(authored=Authored(world=world, facts=[f], characters=[c], chapter_outline=outline))
    state.running.belief_updates = [
        BeliefUpdate(chapter=5, character_id="c1", fact_id="f1", kind=KnowledgeKind.knows)
    ]
    assert "f1" not in state.effective_beliefs("c1", 4)
    assert state.effective_beliefs("c1", 6)["f1"].kind == KnowledgeKind.knows


# --------------------------------------------------------------------------- #
# Deterministic era / age checks.
# --------------------------------------------------------------------------- #

def test_checks_flag_missing_era_in_braided_timeline():
    state = _braided_state()
    state.authored.chapter_outline.append(ChapterBeat(n=3, pov="c_anna", present=["c_anna"]))
    assert any("chapter 3" in i and "no era" in i for i in check_state(state))


def test_checks_flag_unknown_fact_era():
    state = _braided_state()
    state.authored.facts.append(
        Fact(id="f_ghosttime", text="...", tier=SecrecyTier.hidden, era_id="e_nope")
    )
    assert any("f_ghosttime" in i and "not a known era" in i for i in check_state(state))


def test_checks_flag_implausible_age():
    state = _braided_state()
    state.character("c_anna").born = 1955  # she would be 6 in the 1961 era
    assert any("c_anna" in i and "is 6" in i for i in check_state(state))


def test_checks_flag_era_without_baseline_or_year():
    state = _braided_state()
    state.authored.world.eras.append(Era(id="e_void"))  # no year, no baseline
    issues = check_state(state)
    assert any("e_void" in i and "anchor year" in i for i in issues)
    assert any("e_void" in i and "capability baseline" in i for i in issues)


def test_checks_flag_single_era_mismatch_with_braided_mode_is_silent():
    # Two eras with a braided mode is fine; no mode-mismatch warning.
    state = _braided_state()
    assert not any("braided timeline expects" in i for i in check_state(state))


# --------------------------------------------------------------------------- #
# Rendering surfaces the eras and the two clocks.
# --------------------------------------------------------------------------- #

def test_render_world_shows_eras():
    out = R.render_world(_braided_state())
    assert "Timeline / eras" in out
    assert "e_past" in out and "Berlin 1961" in out


def test_render_timeline_shows_story_and_reading_order():
    out = R.render_timeline(_braided_state())
    assert "story order" in out.lower()
    assert "reading order" in out.lower()
    assert "e_past" in out and "e_present" in out


# --------------------------------------------------------------------------- #
# The writer loop runs the period scan against the chapter's era.
# --------------------------------------------------------------------------- #

class _AnachronisticDrafter(MockModel):
    """A drafter that slips a period-wrong prop into the prose. DNA profiling did
    not reach casework until 1986, so it is wrong for the 1985 era."""

    def _draft(self, prompt: str, *, revising: bool) -> str:
        return super()._draft(prompt, revising=revising) + "\nHe ordered DNA testing on the cup."


def test_loop_flags_anachronism_against_chapter_era():
    state = seed_state()
    bundle = ModelBundle(
        drafter=_AnachronisticDrafter(), extractor=MockModel(),
        critic=MockModel(family="google"), author=scripted_author(),
    )
    for s in SETUP_STAGES:
        pipeline_run_stage(state, s, bundle)
    # Chapter 1 is set in the 1985 era; DNA testing does not belong there yet.
    run = run_chapter(state, 1, bundle, LoopConfig())
    assert any("dna testing" in f.lower() for f in run.anachronisms)
    assert run.chapter_state.anachronism_flags == run.anachronisms


# --------------------------------------------------------------------------- #
# Fixes from the adversarial review: ordering robustness, validator, checks.
# --------------------------------------------------------------------------- #

def test_world_rejects_unanchored_era_in_braided_timeline():
    # A braided timeline cannot order knowledge without anchored years.
    with pytest.raises(ValidationError):
        World(
            premise="x",
            eras=[
                Era(id="e_a", year_start=1961, capability_baseline=["x"]),
                Era(id="e_b", capability_baseline=["x"]),  # no year_start
            ],
        )


def test_post_outline_query_inherits_nearest_era_base():
    # A query point past the outline must keep the per-era base, not silently drop
    # it (the end-state graph at max(chapter)+1 hit this).
    state = _braided_state()
    state.authored.chapter_outline.append(
        ChapterBeat(n=3, era_id="e_present", story_time="1991", pov="c_anna", present=["c_anna"])
    )
    after = state.effective_beliefs("c_anna", 4)
    assert after["f_secret"].kind == KnowledgeKind.knows  # e_present base carried forward


def test_same_year_parallel_tracks_do_not_bleed_on_print_order():
    world = World(
        premise="x",
        eras=[
            Era(id="e_a", year_start=1991, capability_baseline=["x"]),
            Era(id="e_b", year_start=1991, capability_baseline=["x"]),
        ],
    )
    c = Character(id="c1", name="C")
    f = Fact(id="f_x", text="a thread-b discovery", tier=SecrecyTier.hidden)
    # e_b chapter printed FIRST, e_a chapter SECOND.
    outline = [ChapterBeat(n=1, era_id="e_b", pov="c1"), ChapterBeat(n=2, era_id="e_a", pov="c1")]
    state = BookState(authored=Authored(
        world=world, facts=[f], characters=[c],
        narrative=NarrativeDesign(mode="parallel_tracks", era_ids=["e_a", "e_b"]),
        chapter_outline=outline,
    ))
    state.running.belief_updates = [
        BeliefUpdate(chapter=1, character_id="c1", fact_id="f_x", kind=KnowledgeKind.knows)
    ]
    # The thread-b discovery (printed first) must not bleed into the thread-a chapter
    # just because it was printed earlier: ordering is by era ordinal, not print order.
    assert "f_x" not in state.effective_beliefs("c1", 2)


def test_checks_flag_story_time_outside_era_window():
    state = _braided_state()
    state.authored.chapter_outline[1].story_time = "March 1991"  # ch2 is e_past (1961)
    assert any("chapter 2" in i and "1991" in i and "outside its era" in i for i in check_state(state))


def test_checks_allow_relative_story_time():
    state = _braided_state()
    state.authored.chapter_outline[1].story_time = "+3 days"
    assert not any("outside its era" in i for i in check_state(state))


def test_checks_flag_dead_era_beliefs():
    state = _braided_state()
    state.authored.world.eras.append(Era(id="e_extra", year_start=2001, capability_baseline=["x"]))
    state.character("c_anna").era_beliefs["e_extra"] = [
        Belief(fact_id="f_secret", kind=KnowledgeKind.knows)
    ]
    assert any("c_anna" in i and "e_extra" in i and "dead intent" in i for i in check_state(state))


def test_checks_flag_reveal_chapter_not_in_outline():
    state = _braided_state()
    state.authored.facts[0].reveal.reader_reveal_chapter = 99
    assert any(
        "f_secret" in i and "99" in i and "not a chapter in the outline" in i
        for i in check_state(state)
    )


def test_checks_do_not_flag_never_explicit_false_belief():
    state = _braided_state()
    state.authored.facts.append(
        Fact(id="f_amb", text="an unresolved loyalty", tier=SecrecyTier.never_explicit)
    )
    state.character("c_anna").initial_beliefs.append(
        Belief(fact_id="f_amb", kind=KnowledgeKind.falsely_believes, false_value="he was loyal")
    )
    assert not any("f_amb" in i and "loose thread" in i for i in check_state(state))


def test_clean_character_drops_stray_false_value():
    raw = {
        "id": "c1", "name": "C",
        "initial_beliefs": [
            {"fact_id": "f1", "kind": "knows", "false_value": ""},
            {"fact_id": "f2", "kind": "falsely_believes", "false_value": "a lie"},
        ],
        "era_beliefs": {"e1": [{"fact_id": "f3", "kind": "does_not_know", "false_value": ""}]},
    }
    c = Character.model_validate(_clean_character(raw))  # must not raise
    assert c.initial_beliefs[0].false_value is None
    assert c.initial_beliefs[1].false_value == "a lie"
    assert c.era_beliefs["e1"][0].false_value is None


def test_scan_does_not_flag_google_eyed():
    assert scan_anachronisms("She went all google-eyed at the sight.", 1975) == []


def test_scan_flags_extra_old_name_pairs():
    assert any("burma" in f.lower() for f in scan_anachronisms("He flew into Burma.", 2010))
    assert any("ceylon" in f.lower() for f in scan_anachronisms("Tea grown in Ceylon.", 2000))
    assert any("calcutta" in f.lower() for f in scan_anachronisms("The Calcutta station.", 2010))
