"""The scoped-context assembler: the triple-layer no-leak enforcement, realized.

This is the crown jewel. It turns `BookState` + (chapter) into the drafter's
prompt, fed ONLY the facts the drafter is allowed to see. As a belt-and-braces
check it asserts that no forbidden fact text made it into the prompt, so a leak
is impossible at generation time rather than merely caught afterward.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ludllm.pipeline.guards import find_leaks
from ludllm.prompts import DRAFTER_SYSTEM
from ludllm.state.schema import BookState, Fact
from ludllm.util.blocks import make_block


class LeakError(RuntimeError):
    """Raised if a forbidden fact reaches the drafter's prompt. Should never fire;
    it is the assertion that the scoping is actually doing its job."""


@dataclass
class DrafterContext:
    chapter: int
    pov: str | None
    system: str
    prompt: str
    allowed_fact_ids: list[str] = field(default_factory=list)
    forbidden_fact_ids: list[str] = field(default_factory=list)


def _facts_block(facts: list[Fact]) -> str:
    if not facts:
        return "(none)"
    return "\n".join(f"- {f.id}: {f.text}" for f in facts)


def _era_block(state: BookState, beat) -> str:
    """The period contract for this chapter: year, place, story time, and the
    capability baseline the drafter must write inside. Empty for a book with no
    eras. This is anachronism prevention at generation time, the time analogue of
    feeding the drafter only its allowed facts."""
    era = state.era(beat.era_id)
    if era is None and len(state.authored.world.eras) == 1:
        era = state.authored.world.eras[0]  # single-era book: chapters need not name it
    if era is None:
        return ""
    if era.year_end and era.year_end != era.year_start:
        yr = f"{era.year_start}-{era.year_end}"
    else:
        yr = str(era.year_start) if era.year_start is not None else "?"
    lines = [f"{era.label or era.id} ({yr})"]
    if era.place:
        lines.append(f"place: {era.place}")
    if beat.story_time:
        lines.append(f"story time: {beat.story_time}")
    if era.capability_baseline:
        lines.append("period baseline (write strictly within this):")
        lines += [f"- {b}" for b in era.capability_baseline]
    return make_block("ERA", "\n".join(lines))


def build_drafter_context(state: BookState, chapter: int) -> DrafterContext:
    beat = state.chapter_beat(chapter)
    pov = beat.pov
    allowed = state.drafter_allowed_facts(pov, chapter) if pov else state.reader_known_facts(chapter)
    forbidden = state.forbidden_for_drafter(pov, chapter) if pov else []

    prev_summary = ""
    prev = next((c for c in state.running.chapters if c.n == chapter - 1), None)
    if prev:
        prev_summary = prev.rolling_summary

    blocks = [
        make_block("CHAPTER", chapter),
        make_block("POV", pov or "(omniscient)"),
        _era_block(state, beat),
        make_block("BEAT", beat.beat or beat.intent),
        make_block("INTENT", beat.intent),
        make_block("ROLLING_SUMMARY", state.running.rolling_summary or "(start of book)"),
        make_block("PREVIOUS_CHAPTER_SUMMARY", prev_summary or "(none)"),
        make_block("ALLOWED_FACTS", _facts_block(allowed)),
    ]
    # Length target: the drafter is otherwise given no word goal, so chapters come
    # in short and the book lands well under the genre target. Feed the per-chapter
    # target as a soft goal with explicit anti-padding guidance.
    target = getattr(state.genre, "words_per_chapter", 0) or 0
    if target:
        lo, hi = int(target * 0.85), int(target * 1.2)
        blocks.append(
            make_block(
                "TARGET_LENGTH",
                f"Aim for a substantial chapter of about {target} words (roughly "
                f"{lo}-{hi}). Develop the beat fully through scene, sensory texture, "
                f"dialogue, and interiority; do not rush it or compress it into "
                f"summary. Do not pad to reach the count - every paragraph must earn "
                f"its place, and a genuinely brief beat may run shorter. Momentum and "
                f"quality over hitting the number exactly."
            )
        )
    prompt = "\n".join(b for b in blocks if b)

    # Belt and braces: a forbidden fact must never appear in the prompt.
    leaked = find_leaks(prompt, forbidden)
    if leaked:
        raise LeakError(
            f"forbidden facts {leaked} reached the drafter prompt for chapter {chapter}"
        )

    return DrafterContext(
        chapter=chapter,
        pov=pov,
        system=DRAFTER_SYSTEM,
        prompt=prompt,
        allowed_fact_ids=[f.id for f in allowed],
        forbidden_fact_ids=[f.id for f in forbidden],
    )
