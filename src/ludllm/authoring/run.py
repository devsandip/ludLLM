"""Run one setup stage for a novel project: execute it, run the dimensional
critique panel, act on its verdict per the chosen mode, save the canonical JSON,
render the markdown for review, and stop. The human is the gate: you review the
markdown (now with a critique scorecard on top), push edits through any channel,
then run the next stage when ready.

Re-running a stage with force=True regenerates it AND invalidates every
downstream stage (so edits ripple forward instead of leaving stale artifacts).

Critique modes (default auto_revise):
- advisory_only: critique, render, stop. The scorecard informs your review.
- auto_revise: if the verdict is not 'ship', regenerate the stage with the
  critique as notes and re-critique, up to critique.auto_revise_passes times,
  before you see it.
- blocking: a 'regenerate' verdict unfreezes the stage so it does not advance
  until you resolve it.

The critique mode, whether the panel runs, and the auto_revise pass count are
read from the project's params (params.toml, see ludllm.params) when the caller
does not pass them explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass

from ludllm.authoring.project import NovelProject
from ludllm.authoring.render import render_all, render_stage
from ludllm.eval import critique_notes, critique_stage, has_rubric
from ludllm.models.base import ModelBundle
from ludllm.params import load_params
from ludllm.pipeline.dossier import build_dossier_artifacts
from ludllm.pipeline.stages import SETUP_STAGES, STAGE_DOSSIER
from ludllm.pipeline.stages import run_stage as pipeline_run_stage
from ludllm.state.schema import CritiqueMode, StageCritique


@dataclass
class StageRun:
    stage: str
    ran: bool
    rendered: list[str]
    critique: StageCritique | None = None
    blocked: bool = False  # blocking mode: a 'regenerate' verdict held the freeze


def _invalidate_from(state, stage: str) -> None:
    """Unfreeze this stage and everything downstream so they can be re-run. For the
    off-spine dossier stage there is no downstream, so just unfreeze it."""
    if stage not in SETUP_STAGES:
        state.meta.frozen_stages = [s for s in state.meta.frozen_stages if s != stage]
        return
    idx = SETUP_STAGES.index(stage)
    downstream = set(SETUP_STAGES[idx:])
    state.meta.frozen_stages = [s for s in state.meta.frozen_stages if s not in downstream]


def run_stage(
    project: NovelProject,
    stage: str,
    models: ModelBundle,
    *,
    force: bool = False,
    notes: str = "",
    critique: bool | None = None,
    critique_mode: CritiqueMode | None = None,
) -> StageRun:
    # Unset args fall back to the project's params (params.toml). An explicit value
    # (e.g. a --critique-mode flag, or a test) always wins.
    params = load_params(project.root)
    if critique is None:
        critique = params.critique.enabled
    if critique_mode is None:
        critique_mode = params.critique.mode
    max_passes = params.critique.auto_revise_passes

    state = project.load()
    if force:
        _invalidate_from(state, stage)

    result = pipeline_run_stage(state, stage, models, notes=notes)  # gated=False: runs + freezes

    crit: StageCritique | None = None
    blocked = False
    if result.ran and critique and has_rubric(stage):
        crit = critique_stage(state, stage, models, mode=critique_mode)

        if critique_mode == CritiqueMode.auto_revise:
            # Regenerate addressing the critique and re-critique, up to max_passes
            # times, stopping as soon as the verdict reaches 'ship'.
            passes = 0
            while crit.verdict != "ship" and passes < max_passes:
                _invalidate_from(state, stage)
                pipeline_run_stage(state, stage, models, notes=critique_notes(crit))
                crit = critique_stage(state, stage, models, mode=critique_mode)
                passes += 1
            crit.revise_passes = passes
            crit.revised = passes > 0
        elif critique_mode == CritiqueMode.blocking and crit.verdict == "regenerate":
            # Hold the freeze: the stage must be resolved before it advances.
            state.meta.frozen_stages = [s for s in state.meta.frozen_stages if s != stage]
            blocked = True

        state.reviews[stage] = crit

    # The dossier stage produces image/PDF artifacts from the generated content
    # (portraits, three-page files, spreads). Do it once, here, so a later
    # re-render does not regenerate images; paths are recorded on the dossiers.
    if result.ran and stage == STAGE_DOSSIER:
        # Persist the (model-generated, expensive) dossier content FIRST, so a
        # failure in the paid/fallible artifact step (image backend, PIL, rsvg)
        # cannot discard it. Artifact paths recorded on the dossiers are saved by
        # the final save below if the step completes.
        project.save(state)
        build_dossier_artifacts(state, project.stage_dir(STAGE_DOSSIER))

    project.save(state)

    rendered: list[str] = []
    if result.ran:
        rendered = render_stage(project, state, stage)
        # Re-render every stage so earlier files that later stages fill in (e.g.
        # the ledger's reveal columns) stay in sync with the canonical JSON.
        render_all(project, state)
    return StageRun(stage=stage, ran=result.ran, rendered=rendered, critique=crit, blocked=blocked)


def critique_only(project: NovelProject, stage: str, models: ModelBundle) -> StageCritique | None:
    """Run (or re-run) the dimensional panel on a stage on demand, advisory only.
    Stores the result and re-renders so the scorecard refreshes. No regeneration."""
    if not has_rubric(stage):
        return None
    state = project.load()
    crit = critique_stage(state, stage, models, mode=CritiqueMode.advisory_only)
    state.reviews[stage] = crit
    project.save(state)
    render_all(project, state)
    return crit


def stale_stages(project: NovelProject) -> list[str]:
    """Setup stages that have run earlier than an unfrozen upstream stage, i.e.
    downstream artifacts that may be stale after an upstream edit+regenerate."""
    state = project.load()
    frozen = set(state.meta.frozen_stages)
    stale = []
    seen_unfrozen = False
    for stage in SETUP_STAGES:
        if stage not in frozen:
            seen_unfrozen = True
        elif seen_unfrozen:
            stale.append(stage)
    return stale
