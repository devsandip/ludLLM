"""The studio data builder freezes the engine's knowledge graph into a render-only
blob, and build_viz writes a self-contained folder. No keys, no network.
"""

from __future__ import annotations

import json

from ludllm.authoring.project import create_project
from ludllm.authoring.run import pending_finishing_stages, run_stage
from ludllm.pipeline.stages import (
    FINISHING_STAGES,
    RUNNABLE_STAGES,
    SETUP_STAGES,
    STAGE_DOSSIER,
    STAGE_VIZ,
)
from ludllm.viz.studio import build_studio_data, build_viz
from tests.fixtures.tiny_state import tiny_state


def test_studio_data_excludes_public_and_disambiguates():
    data = build_studio_data(tiny_state())
    # public facts are not secrets
    assert [f["id"] for f in data["facts"]] == ["f_mole"]
    assert data["facts"][0]["tier"] == "hidden"
    # every character gets a unique initials token
    inis = [c["ini"] for c in data["chars"]]
    assert len(inis) == len(set(inis))
    # transitions encode belief by chapter; Vesna knows the mole from the start
    assert data["trans"]["f_mole"]["c_vesna"][0][1] == 1


def test_studio_data_handles_no_eras():
    data = build_studio_data(tiny_state())
    assert data["eras"] == []
    assert data["span"] >= 1
    assert len(data["story_order"]) == data["span"]


def test_build_viz_writes_self_contained_folder(tmp_path):
    (tmp_path / "book_state.json").write_text(tiny_state().model_dump_json(), encoding="utf-8")
    studio = build_viz(tmp_path)
    assert studio.exists() and studio.name == "studio.html"
    html = studio.read_text()
    assert html.startswith("<!DOCTYPE html>")
    assert "const DATA =" in html
    # data.json is the same blob, parseable
    blob = json.loads((tmp_path / "viz" / "data.json").read_text())
    assert blob["title"] == tiny_state().meta.title
    # no dossier assets present -> no dossier pages, graceful
    assert not list((tmp_path / "viz").glob("dossier_*.html"))


def test_viz_is_an_offspine_finishing_stage(tmp_path):
    """viz is a runnable stage but off the authoring spine: model-free, freezes
    once, always rebuilds. Off-spine but mandatory, and a FINISHING stage (run last,
    after the writer)."""
    assert STAGE_VIZ in RUNNABLE_STAGES
    assert STAGE_VIZ not in SETUP_STAGES   # not a model-driven setup generator
    assert STAGE_VIZ in FINISHING_STAGES   # mandatory, run after the manuscript

    proj = create_project(tmp_path, "a premise", name="vizstage")
    proj.save(tiny_state())

    # models=None: the viz stage authors no state and needs no bundle.
    run = run_stage(proj, STAGE_VIZ, None)
    assert run.ran
    studio = proj.root / "viz" / "studio.html"
    assert studio.exists()
    assert run.rendered == [str(studio)]
    assert proj.load().meta.frozen_stages == [STAGE_VIZ]

    # Re-running rebuilds (a view never goes stale) without duplicating the freeze.
    run2 = run_stage(proj, STAGE_VIZ, None)
    assert run2.ran
    assert proj.load().meta.frozen_stages.count(STAGE_VIZ) == 1


def test_finishing_stages_pending_until_dossier_and_viz_run(tmp_path):
    """dossier and viz are the mandatory finishing stages: pending after the setup
    spine, cleared once both have run (after the manuscript)."""
    proj = create_project(tmp_path, "a premise", name="vizgate")
    state = tiny_state()
    # Setup spine done; finishing stages have not run yet.
    state.meta.frozen_stages = list(SETUP_STAGES)
    proj.save(state)
    assert set(pending_finishing_stages(proj)) == {STAGE_DOSSIER, STAGE_VIZ}

    # Run viz (model-free); dossier still pending.
    run_stage(proj, STAGE_VIZ, None)
    assert pending_finishing_stages(proj) == [STAGE_DOSSIER]

    # Mark dossier done -> nothing pending, the book is finished.
    s = proj.load()
    s.meta.frozen_stages.append(STAGE_DOSSIER)
    proj.save(s)
    assert pending_finishing_stages(proj) == []
