"""The dimensional critique panel: per-stage scoring, verdict derivation, and the
three modes (advisory_only / auto_revise / blocking). All offline on mocks.
"""

from __future__ import annotations

from ludllm.authoring.project import create_project
from ludllm.authoring.run import run_stage
from ludllm.eval import critique_stage
from ludllm.eval.rubric import STAGE_RUBRICS
from ludllm.examples.mole import scripted_author, seed_state
from ludllm.models.base import ModelBundle
from ludllm.models.mock import MockModel
from ludllm.pipeline.stages import SETUP_STAGES
from ludllm.pipeline.stages import run_stage as pipeline_run_stage
from ludllm.pipeline.writer import LoopConfig, run_chapter
from ludllm.state.schema import CritiqueMode


def _bundle(score: int = 4) -> ModelBundle:
    return ModelBundle(
        drafter=MockModel(),
        extractor=MockModel(),
        critic=MockModel(family="google", critique_score=score),
        author=scripted_author(),
    )


def _state_through(stage: str, score: int = 4):
    """A state with the setup pipeline run up to and including `stage`."""
    state = seed_state()
    bundle = _bundle(score)
    for s in SETUP_STAGES:
        pipeline_run_stage(state, s, bundle)
        if s == stage:
            break
    return state, bundle


def test_panel_scores_every_rubric_dimension():
    state, bundle = _state_through("structure")
    crit = critique_stage(state, "structure", bundle)
    scored = {s.dimension for s in crit.scores}
    assert scored == set(STAGE_RUBRICS["structure"])
    assert crit.verdict == "ship"  # mock scores 4


def test_low_scores_derive_regenerate_verdict():
    state, bundle = _state_through("world", score=1)
    crit = critique_stage(state, "world", bundle)
    assert crit.verdict == "regenerate"
    assert crit.min_score == 1
    assert crit.top_fix  # the weakest dimension's fix is surfaced


def test_advisory_only_neither_revises_nor_blocks(tmp_path):
    project = create_project(tmp_path, "A mole inside a Vienna station.")
    run_stage(project, "normalize", _bundle(1))
    run = run_stage(project, "world", _bundle(1), critique_mode=CritiqueMode.advisory_only)
    assert run.critique.verdict == "regenerate"
    assert not run.critique.revised
    assert not run.blocked
    # Advisory does not change the freeze: the stage still advanced.
    assert "world" in project.load().meta.frozen_stages


def test_blocking_holds_the_freeze(tmp_path):
    project = create_project(tmp_path, "A mole inside a Vienna station.")
    run_stage(project, "normalize", _bundle(1))
    run = run_stage(project, "world", _bundle(1), critique_mode=CritiqueMode.blocking)
    assert run.blocked
    assert "world" not in project.load().meta.frozen_stages


def test_auto_revise_regenerates_once_then_advances(tmp_path):
    project = create_project(tmp_path, "A mole inside a Vienna station.")
    run_stage(project, "normalize", _bundle(1))
    run = run_stage(project, "world", _bundle(1), critique_mode=CritiqueMode.auto_revise)
    assert run.critique.revised  # it regenerated once addressing the critique
    assert "world" in project.load().meta.frozen_stages  # best-effort one pass, then advance


def test_no_critique_flag_skips_the_panel(tmp_path):
    project = create_project(tmp_path, "A mole inside a Vienna station.")
    run_stage(project, "normalize", _bundle(1))
    run = run_stage(project, "world", _bundle(1), critique=False)
    assert run.critique is None
    assert "world" not in project.load().reviews


def test_scorecard_renders_into_stage_markdown(tmp_path):
    project = create_project(tmp_path, "A mole inside a Vienna station.")
    for stage in ("normalize", "world", "cast", "structure"):
        run_stage(project, stage, _bundle(4))
    assert "Critique panel" in (project.root / "03_structure" / "structure.md").read_text()


def test_chapter_advisory_note_is_recorded():
    state, bundle = _state_through("outline")
    run = run_chapter(state, 9, bundle, LoopConfig())
    assert run.accepted
    assert "chapter_9" in state.reviews
    assert state.reviews["chapter_9"].scores
