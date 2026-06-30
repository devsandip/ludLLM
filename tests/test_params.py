"""User-editable pipeline params: layering (default < global < project), the
per-stage relevance map, coercion/validation, the interactive prompt, and that
run_stage honors auto_revise_passes. All offline."""

from __future__ import annotations

import io

import pytest

from ludllm.authoring.interactive import prompt_stage_params
from ludllm.authoring.project import create_project
from ludllm.authoring.run import run_stage
from ludllm.examples.mole import scripted_author
from ludllm.models.base import ModelBundle
from ludllm.models.mock import MockModel
from ludllm.params import (
    GLOBAL_ENV,
    PARAM_SPECS,
    STAGE_PARAMS,
    Params,
    coerce,
    load_params,
    relevant_specs,
    resolve_with_sources,
    set_project_value,
    write_global_template,
    write_project_template,
)
from ludllm.state.schema import CritiqueMode


def _bundle(score: int = 4) -> ModelBundle:
    return ModelBundle(
        drafter=MockModel(),
        extractor=MockModel(),
        critic=MockModel(family="google", critique_score=score),
        author=scripted_author(),
    )


def test_defaults_when_no_files(tmp_path):
    p = load_params(tmp_path)
    assert p.critique.mode == CritiqueMode.auto_revise
    assert p.critique.auto_revise_passes == 1
    assert p.writer.max_revise == 2
    assert p.writer.retries == 3
    assert p.writer.advisory is True


def test_layering_project_overrides_global(tmp_path, monkeypatch):
    gpath = tmp_path / "global.toml"
    gpath.write_text("[writer]\nmax_revise = 5\nretries = 7\n", encoding="utf-8")
    monkeypatch.setenv(GLOBAL_ENV, str(gpath))

    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "params.toml").write_text("[writer]\nmax_revise = 1\n", encoding="utf-8")

    p = load_params(proj)
    assert p.writer.max_revise == 1  # project wins
    assert p.writer.retries == 7     # falls through to global
    assert p.writer.advisory is True  # falls through to package default


def test_every_stage_param_has_a_spec():
    for keys in STAGE_PARAMS.values():
        for key in keys:
            assert key in PARAM_SPECS


def test_relevant_specs_are_scoped_to_the_stage():
    assert {s.key for s in relevant_specs("world")} == set(STAGE_PARAMS["world"])
    assert [s.key for s in relevant_specs("writer")] == STAGE_PARAMS["writer"]
    # normalize/dossier surface nothing
    assert relevant_specs("normalize") == []
    assert relevant_specs("dossier") == []


def test_coerce_validates_types_and_ranges():
    assert coerce(PARAM_SPECS["critique.enabled"], "no") is False
    assert coerce(PARAM_SPECS["writer.max_revise"], "4") == 4
    assert coerce(PARAM_SPECS["critique.mode"], "blocking") == "blocking"
    with pytest.raises(ValueError):
        coerce(PARAM_SPECS["critique.mode"], "nonsense")
    with pytest.raises(ValueError):
        coerce(PARAM_SPECS["writer.max_revise"], "99")  # above max
    with pytest.raises(ValueError):
        coerce(PARAM_SPECS["writer.advisory"], "maybe")


def test_set_project_value_round_trips_and_validates(tmp_path):
    set_project_value(tmp_path, "writer.max_revise", 4)
    set_project_value(tmp_path, "critique.mode", "blocking")
    p = load_params(tmp_path)
    assert p.writer.max_revise == 4
    assert p.critique.mode == CritiqueMode.blocking
    # an out-of-range value is rejected before it is persisted
    with pytest.raises(Exception):
        set_project_value(tmp_path, "critique.auto_revise_passes", 99)
    assert load_params(tmp_path).critique.auto_revise_passes == 1  # unchanged


def test_new_project_seeds_an_inert_template(tmp_path):
    project = create_project(tmp_path, "A mole inside a Vienna station.")
    seeded = project.root / "params.toml"
    assert seeded.exists()
    # The seeded template is all comments: it overrides nothing.
    p = load_params(project.root)
    assert p == Params()


def test_resolve_with_sources_labels_layers(tmp_path):
    set_project_value(tmp_path, "writer.retries", 6)
    rows = {r["key"]: r for r in resolve_with_sources(tmp_path)}
    assert rows["writer.retries"]["source"] == "project"
    assert rows["writer.retries"]["value"] == 6
    assert rows["writer.max_revise"]["source"] == "default"


def test_interactive_prompt_changes_one_value(tmp_path):
    project = create_project(tmp_path, "A mole inside a Vienna station.")
    # Answer order matches relevant_specs("writer"): max_revise, retries, advisory.
    inp = io.StringIO("4\n\nfalse\n")
    out = io.StringIO()
    result = prompt_stage_params(project.root, "writer", inp=inp, out=out)
    assert result.writer.max_revise == 4   # changed
    assert result.writer.retries == 3      # blank kept the default
    assert result.writer.advisory is False  # changed
    # persisted to the per-project file
    assert load_params(project.root).writer.max_revise == 4


def test_interactive_eof_leaves_params_untouched(tmp_path):
    project = create_project(tmp_path, "A mole inside a Vienna station.")
    result = prompt_stage_params(project.root, "world", inp=io.StringIO(""), out=io.StringIO())
    assert result == Params()


def test_auto_revise_passes_zero_scores_but_never_regenerates(tmp_path):
    project = create_project(tmp_path, "A mole inside a Vienna station.")
    set_project_value(project.root, "critique.auto_revise_passes", 0)
    run_stage(project, "normalize", _bundle(1))
    run = run_stage(project, "world", _bundle(1), critique_mode=CritiqueMode.auto_revise)
    assert run.critique.verdict == "regenerate"  # score 1
    assert not run.critique.revised               # passes=0, so no regeneration
    assert run.critique.revise_passes == 0


def test_auto_revise_passes_from_params_drive_the_loop(tmp_path):
    project = create_project(tmp_path, "A mole inside a Vienna station.")
    set_project_value(project.root, "critique.auto_revise_passes", 2)
    run_stage(project, "normalize", _bundle(1))
    # mode unset -> read from params (auto_revise default); score 1 never reaches ship,
    # so it exhausts the 2 allowed passes.
    run = run_stage(project, "world", _bundle(1))
    assert run.critique.revised
    assert run.critique.revise_passes == 2


def test_global_template_is_inert(tmp_path, monkeypatch):
    gpath = tmp_path / "global.toml"
    monkeypatch.setenv(GLOBAL_ENV, str(gpath))
    write_global_template()
    assert gpath.exists()
    assert load_params(None) == Params()  # commented template changes nothing


def test_write_project_template_does_not_clobber(tmp_path):
    set_project_value(tmp_path, "writer.max_revise", 9)
    write_project_template(tmp_path)  # must not overwrite an existing file
    assert load_params(tmp_path).writer.max_revise == 9
