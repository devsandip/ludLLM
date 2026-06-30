"""The CLI runs offline end to end and produces the expected artifacts."""

from __future__ import annotations

import json

from ludllm.cli import main


def test_demo_produces_artifacts(tmp_path, capsys):
    out = tmp_path / "demo"
    rc = main(["demo", str(out)])
    assert rc == 0
    assert (out / "book_state.json").exists()
    assert (out / "graph.json").exists()
    chapters = list((out / "chapters").glob("chapter_*.md"))
    assert len(chapters) == 3  # the example outlines chapters 1, 6, 9

    graph = json.loads((out / "graph.json").read_text())
    assert any(n["type"] == "character" for n in graph["nodes"])


def test_graph_and_show_on_demo_output(tmp_path, capsys):
    out = tmp_path / "demo"
    main(["demo", str(out)])
    capsys.readouterr()

    assert main(["graph", str(out / "book_state.json"), "-c", "1"]) == 0
    graph = json.loads(capsys.readouterr().out)
    assert graph["chapter"] == 1

    assert main(["show", str(out / "book_state.json")]) == 0
    assert "Ledger:" in capsys.readouterr().out
