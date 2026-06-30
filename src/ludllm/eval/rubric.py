"""The critique rubric: which dimensions are scored at which stage, what each
dimension means, and how a panel of dimension scores becomes a verdict.

Dimensions are a PER-STAGE rubric, not a flat universal list: "is it dragging?"
is meaningless for a cast list and decisive for an outline. Each stage gets the
4-5 dimensions that actually apply to it. The catalogue here is reference data,
like the trope catalogue - the panel engine in critique.py consumes it.
"""

from __future__ import annotations

import json

from ludllm.state.schema import BookState, DimensionScore

# Stage keys (string literals on purpose, to avoid importing the pipeline here).
WORLD = "world"
CAST = "cast"
STRUCTURE = "structure"
OUTLINE = "outline"
PROSE = "prose"

# Dimension -> what the critic is judging. Tuned for a candid coverage read.
DIMENSIONS: dict[str, str] = {
    "plausibility": (
        "Tradecraft, institutions, human behavior, and geography hold up to a reader who "
        "knows the real world. Nothing is hand-waved or movie-logic."
    ),
    "grounding": (
        "Internally consistent (matches the fact ledger and the belief states) AND externally "
        "accurate (real organizations and the anchored real incidents are used correctly), and it "
        "does not trample anything the writer locked."
    ),
    "momentum": (
        "Tension is shaped and escalating; every unit turns and earns its place; nothing sags, "
        "stalls, or repeats. Is it boring or dragging?"
    ),
    "originality": (
        "Not derivative. Cliches are examined or subverted rather than used straight. It takes a "
        "real swing instead of playing it safe toward competent-but-forgettable."
    ),
    "character": (
        "Wants, competences, and wounds are specific and real; the antagonist is sympathetic with a "
        "layered motive, not cartoon villainy; belief states are load-bearing, not decoration."
    ),
    "coherence": (
        "The plot mechanism actually works and has a real, exploitable vulnerability; no "
        "contradictions; the information asymmetry is logically sound end to end."
    ),
    "reveal_craft": (
        "The gap between what the reader knows and what the protagonist knows is genuinely "
        "engineered and exploited; clues are planted before payoffs so reveals feel earned."
    ),
    "stakes_theme": (
        "The cost matters and escalates, and there is something underneath the mechanism worth "
        "saying - a theme the story is actually about."
    ),
    "voice_fit": (
        "Sits in the le Carre / Forsyth register: interiority and restraint, procedural authority, "
        "subtext over statement, and none of the machine tells."
    ),
    "period_authenticity": (
        "Everything is consistent with the era(s) and their anchored years: technology, tradecraft, "
        "communications, forensics, weapons, slang, brands, and geopolitics all fit the period, and "
        "places carry their period names. Flag anything that could not exist yet (a capability, a "
        "country, a device ahead of its time) or that is no longer current by then; in a braided "
        "timeline, check each scene against its OWN era, not the latest one."
    ),
}

# Stage -> the dimensions scored for it.
STAGE_RUBRICS: dict[str, list[str]] = {
    WORLD: ["plausibility", "grounding", "coherence", "originality", "stakes_theme", "period_authenticity"],
    CAST: ["character", "plausibility", "grounding", "originality", "coherence"],
    STRUCTURE: ["momentum", "reveal_craft", "coherence", "originality", "stakes_theme"],
    OUTLINE: ["momentum", "reveal_craft", "coherence", "grounding", "period_authenticity"],
    PROSE: ["voice_fit", "momentum", "plausibility", "period_authenticity"],
}

SCALE = (
    "Score 1-5: 1 broken, 2 weak, 3 competent, 4 strong, 5 exceptional. Be candid - you are "
    "advising a human showrunner, not gatekeeping, so do not inflate. Cite the specific element "
    "or line that earned the score, and give one concrete, actionable fix."
)


def has_rubric(stage: str) -> bool:
    return stage in STAGE_RUBRICS


def derive_verdict(scores: list[DimensionScore]) -> tuple[str, str]:
    """Verdict from the panel, derived deterministically from the LOWEST dimension
    (no composite average - that hides the weak spot). Returns (verdict, top_fix)."""
    if not scores:
        return "ship", ""
    lowest = min(scores, key=lambda s: s.score)
    if lowest.score <= 1:
        verdict = "regenerate"
    elif lowest.score == 2:
        verdict = "tighten"
    else:
        verdict = "ship"
    return verdict, lowest.fix


def grounding_context(state: BookState) -> str:
    """The shared context every critic gets, so any dimension can check grounding
    and period accuracy: the fact ledger, the real organizations, the anchored
    real incidents, and the eras with their capability baselines."""
    w = state.authored.world
    return json.dumps(
        {
            "facts": [{"id": f.id, "text": f.text, "tier": f.tier.value} for f in state.authored.facts],
            "real_organizations": w.real_organizations,
            "real_anchors": [a.model_dump() for a in w.real_anchors],
            "eras": [
                {"id": e.id, "label": e.label, "year_start": e.year_start,
                 "year_end": e.year_end, "capability_baseline": e.capability_baseline}
                for e in w.eras
            ],
        }
    )


def stage_content(state: BookState, stage: str) -> str:
    """A clean serialization of what is under review for a stage (no rendered
    banners, to avoid the critic reading a prior critique of itself)."""
    a = state.authored
    if stage == WORLD:
        return json.dumps({"world": a.world.model_dump(), "facts": [f.model_dump() for f in a.facts],
                           "threads": [t.model_dump() for t in a.threads]})
    if stage == CAST:
        return json.dumps({"characters": [c.model_dump() for c in a.characters]})
    if stage == STRUCTURE:
        return json.dumps({
            "narrative": a.narrative.model_dump(),
            "acts": [act.model_dump() for act in a.acts],
            "tropes": [t.model_dump() for t in a.tropes],
            "reveal_act_bindings": [
                {"fact_id": f.id, "act_anchor": f.reveal.act_anchor, "order": f.reveal.order}
                for f in a.facts if f.reveal and f.reveal.act_anchor
            ],
        })
    if stage == OUTLINE:
        return json.dumps({"chapters": [cb.model_dump() for cb in a.chapter_outline]})
    return "{}"
