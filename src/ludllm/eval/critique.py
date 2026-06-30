"""The dimensional critique panel.

For a stage, one cross-family critic call per rubric dimension produces a
{score, evidence, fix}; the panel aggregates them into a StageCritique with a
verdict derived from the lowest dimension. This is advisory - it informs the
human gate. The auto-revise and blocking behaviors live one layer up, in
authoring/run.py, which decides what to do with the verdict.

The critic MUST be a different model family from the author (cross-family
critique is the quality unlock); the bundle's critic is used.
"""

from __future__ import annotations

from ludllm.eval.rubric import (
    DIMENSIONS,
    SCALE,
    STAGE_RUBRICS,
    derive_verdict,
    grounding_context,
    stage_content,
)
from ludllm.models.base import TASK_STAGE_CRITIQUE, ModelBundle
from ludllm.prompts import STAGE_CRITIC_SYSTEM
from ludllm.state.schema import CritiqueMode, DimensionScore, StageCritique
from ludllm.util.blocks import make_block
from ludllm.util.jsonio import loads_lenient


def _score_one(dimension: str, content: str, grounding: str, label: str, critic) -> DimensionScore:
    prompt = "\n".join(
        [
            make_block("DIMENSION", dimension),
            make_block("WHAT_TO_JUDGE", DIMENSIONS[dimension]),
            make_block("SCALE", SCALE),
            make_block("UNDER_REVIEW", f"This is the {label} of a spy novel.\n{content}"),
            make_block("GROUNDING", grounding),
        ]
    )
    raw = critic.generate(system=STAGE_CRITIC_SYSTEM, prompt=prompt, task=TASK_STAGE_CRITIQUE)
    data = loads_lenient(raw)
    score = int(data.get("score", 3))
    score = max(1, min(5, score))  # clamp to the scale
    return DimensionScore(
        dimension=dimension,
        score=score,
        evidence=str(data.get("evidence", "")),
        fix=str(data.get("fix", "")),
    )


def _panel(dims: list[str], content: str, grounding: str, label: str, critic) -> list[DimensionScore]:
    return [_score_one(d, content, grounding, label, critic) for d in dims]


def _assert_cross_family(models: ModelBundle) -> None:
    """The panel critic must not share a family with the author it is grading."""
    if models.critic.family == models.author_model.family and models.critic.family != "mock":
        raise ValueError(
            "critique panel critic shares a family with the author; cross-family "
            "critique is the point. Use a different provider for the critic."
        )


def critique_stage(
    state, stage: str, models: ModelBundle, *, mode: CritiqueMode = CritiqueMode.advisory_only
) -> StageCritique:
    """Run the per-dimension panel on a setup stage's output. Cross-family critic."""
    _assert_cross_family(models)
    dims = STAGE_RUBRICS[stage]
    scores = _panel(dims, stage_content(state, stage), grounding_context(state), stage, models.critic)
    verdict, top_fix = derive_verdict(scores)
    return StageCritique(stage=stage, mode=mode, scores=scores, verdict=verdict, top_fix=top_fix)


def critique_chapter(state, n: int, prose: str, models: ModelBundle) -> StageCritique:
    """The advisory per-chapter note (Q4): voice / momentum / plausibility /
    period on the finished prose. Advisory only - the writer's blocking critic
    stays the convergence driver; this is a coverage note for the showrunner.

    The chapter's OWN era and baseline are prepended so the period critic judges
    the scene against its period, not the latest one (the braided-timeline case)."""
    dims = STAGE_RUBRICS["prose"]
    content = prose
    era = state.chapter_era(n)
    if era:
        baseline = "; ".join(era.capability_baseline) or "(none stated)"
        yr = era.year_start if era.year_start is not None else "?"
        content = (
            f"This chapter is set in era '{era.id}' ({era.label or yr}). "
            f"Capability baseline for the period: {baseline}.\n\n{prose}"
        )
    scores = _panel(dims, content, grounding_context(state), f"chapter {n}", models.critic)
    verdict, top_fix = derive_verdict(scores)
    return StageCritique(
        stage=f"chapter_{n}", mode=CritiqueMode.advisory_only,
        scores=scores, verdict=verdict, top_fix=top_fix,
    )


def critique_notes(crit: StageCritique) -> str:
    """Turn a critique into revision notes to feed a regenerate (auto-revise)."""
    weak = [s for s in crit.scores if s.score < 3]
    lines = ["Address these points from the editorial review, while keeping the story's voice:"]
    for s in weak:
        lines.append(f"- {s.dimension} (scored {s.score}/5): {s.evidence} Fix: {s.fix}")
    if crit.top_fix:
        lines.append(f"Highest priority: {crit.top_fix}")
    return "\n".join(lines)
