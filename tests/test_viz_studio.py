"""The studio data builder freezes the engine's knowledge graph into a render-only
blob, and build_viz writes a self-contained folder. No keys, no network.
"""

from __future__ import annotations

import json

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
