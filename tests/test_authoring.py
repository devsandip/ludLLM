"""The file-based authoring workflow: naming, scaffolding, rendering, checks,
and the stage runner. All offline on the scripted mole author."""

from __future__ import annotations

from datetime import date

from ludllm.authoring import render as R
from ludllm.authoring.checks import check_state
from ludllm.authoring.project import create_project, next_auto_name, slugify
from ludllm.authoring.run import run_stage
from ludllm.examples.mole import scripted_author, seed_state
from ludllm.models.base import ModelBundle
from ludllm.models.mock import MockModel
from ludllm.pipeline.stages import SETUP_STAGES
from ludllm.pipeline.stages import run_stage as pipeline_run_stage
from ludllm.state.schema import Belief, Fact, KnowledgeKind, SecrecyTier


def _bundle() -> ModelBundle:
    return ModelBundle(
        drafter=MockModel(), extractor=MockModel(),
        critic=MockModel(family="google"), author=scripted_author(),
    )


def _mole_state():
    state = seed_state()
    bundle = _bundle()
    for stage in SETUP_STAGES:
        pipeline_run_stage(state, stage, bundle)
    return state


def test_slugify():
    assert slugify("Cold Channel") == "cold-channel"
    assert slugify("  A/B: C!! ") == "a-b-c"
    assert slugify("") == "untitled"


def test_next_auto_name_increments(tmp_path):
    d = date(2026, 6, 20)
    assert next_auto_name(tmp_path, d) == "book_000_20_06_26"
    (tmp_path / "book_000_20_06_26").mkdir()
    (tmp_path / "book_003_01_01_26").mkdir()
    assert next_auto_name(tmp_path, d) == "book_004_20_06_26"


def test_create_project_scaffolds(tmp_path):
    project = create_project(tmp_path, "A mole.", name="Cold Channel")
    assert project.root.name == "cold-channel"
    assert project.state_path.exists()
    assert (project.root / "01_world").is_dir()
    assert (project.root / "02_cast").is_dir()
    assert (project.root / "05_manuscript").is_dir()
    assert project.load().brief.raw_input == "A mole."


def test_render_and_checks_clean():
    state = _mole_state()
    assert "Marek" in R.render_cast(state)
    assert "falsely_believes" in R.render_cast(state)
    assert "f_mole" in R.render_ledger(state)
    assert "asymmetry" in R.render_outline(state).lower()
    assert "No structural issues found." in R.render_outline(state)
    assert check_state(state) == []


def test_checks_detect_orphan_belief():
    state = _mole_state()
    state.authored.characters[0].initial_beliefs.append(
        Belief(fact_id="f_ghost", kind=KnowledgeKind.knows)
    )
    assert any("f_ghost" in i for i in check_state(state))


def test_checks_flag_uncorrected_false_belief():
    state = _mole_state()  # outline exists, so the coupling check is active
    # A hidden secret nobody ever corrects + a character who falsely believes it.
    state.authored.facts.append(
        Fact(id="f_loose", text="A secret never put right.", tier=SecrecyTier.hidden)
    )
    state.authored.characters[0].initial_beliefs.append(
        Belief(fact_id="f_loose", kind=KnowledgeKind.falsely_believes, false_value="a wrong thing")
    )
    assert any("f_loose" in i and "loose thread" in i for i in check_state(state))


def test_checks_flag_false_belief_about_public_fact():
    state = _mole_state()
    state.authored.facts.append(Fact(id="f_open", text="Common knowledge.", tier=SecrecyTier.public))
    state.authored.characters[0].initial_beliefs.append(
        Belief(fact_id="f_open", kind=KnowledgeKind.falsely_believes, false_value="a wrong thing")
    )
    assert any("f_open" in i and "public" in i for i in check_state(state))


def test_run_stage_renders_and_force_regenerates(tmp_path):
    project = create_project(tmp_path, "A mole in Vienna.")
    bundle = _bundle()

    run = run_stage(project, "normalize", bundle)
    assert run.ran
    assert (project.root / "00_brief" / "brief.md").exists()

    # Already done -> skipped without force.
    assert not run_stage(project, "normalize", bundle).ran
    # Force re-runs.
    assert run_stage(project, "normalize", bundle, force=True).ran
