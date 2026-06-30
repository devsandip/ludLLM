"""A tiny hand-authored book state for engine-first testing.

A minimal mole structure: one secret (Vesna is the mole), planted as `hidden`,
scheduled so the READER learns at chapter 6 and the PROTAGONIST (Marek) learns
at chapter 9. Until then Marek falsely believes Vesna is loyal. This is the
ground-truth structure the no-leak engine must respect.
"""

from __future__ import annotations

from ludllm.state.schema import (
    Act,
    Authored,
    Belief,
    BookState,
    Character,
    ChapterBeat,
    CreativeBrief,
    Fact,
    GenreProfile,
    KnowledgeKind,
    Provenance,
    RevealPlan,
    SecrecyTier,
    Thread,
    World,
)


def tiny_state() -> BookState:
    facts = [
        Fact(
            id="f_mole",
            text="Vesna is an ISI double agent inside the station.",
            tier=SecrecyTier.hidden,
            reveal=RevealPlan(order=1, reader_reveal_chapter=6, character_reveal_chapter=9),
        ),
        Fact(
            id="f_station",
            text="The Vienna station exists and runs the operation.",
            tier=SecrecyTier.public,
        ),
    ]

    characters = [
        Character(
            id="c_marek",
            name="Marek",
            provenance=Provenance.user_seed,
            role="protagonist, case officer",
            # Marek falsely believes Vesna is loyal until he learns the truth.
            initial_beliefs=[
                Belief(
                    fact_id="f_mole",
                    kind=KnowledgeKind.falsely_believes,
                    false_value="Vesna is a loyal asset.",
                ),
            ],
        ),
        Character(
            id="c_vesna",
            name="Vesna",
            provenance=Provenance.user_seed,
            role="asset, secret mole",
            # Vesna knows what she is from the start.
            initial_beliefs=[Belief(fact_id="f_mole", kind=KnowledgeKind.knows)],
        ),
    ]

    return BookState(
        genre=GenreProfile(target_words=30_000, words_per_chapter=3_000, default_acts=4),
        brief=CreativeBrief(raw_input="A mole inside a Vienna station."),
        authored=Authored(
            world=World(premise="A mole hunt in a Vienna station.", plot_mechanism="..."),
            characters=characters,
            facts=facts,
            threads=[Thread(id="t_molehunt", name="The mole hunt")],
            acts=[Act(id="a1", n=1, name="Setup")],
            chapter_outline=[
                ChapterBeat(n=1, pov="c_marek", present=["c_marek", "c_vesna"],
                            beat="Marek trusts Vesna with the operation."),
                ChapterBeat(n=6, pov="c_marek", reader_reveals=["f_mole"],
                            beat="The reader sees Vesna signal her handler."),
                ChapterBeat(n=9, pov="c_marek", character_reveals=["f_mole"],
                            beat="Marek discovers the betrayal."),
            ],
        ),
    )
