"""The graph exporter reflects the knowledge state at a given chapter and moves
the information asymmetry as the chapter advances.
"""

from __future__ import annotations

from ludllm.state.schema import Belief, BeliefUpdate, KnowledgeKind
from ludllm.viz.export import state_to_graph
from tests.fixtures.tiny_state import tiny_state


def _edge(graph, source, target):
    return next((e for e in graph["edges"] if e["source"] == source and e["target"] == target), None)


def _node(graph, node_id):
    return next((n for n in graph["nodes"] if n["id"] == node_id), None)


def test_graph_has_character_and_fact_nodes():
    g = state_to_graph(tiny_state(), chapter=1)
    assert _node(g, "c_marek")["type"] == "character"
    fact = _node(g, "f_mole")
    assert fact["type"] == "fact" and fact["tier"] == "hidden"
    assert g["graph_schema_version"] == 2


def test_asymmetry_at_chapter_1():
    g = state_to_graph(tiny_state(), chapter=1)
    # Marek falsely believes; Vesna knows; reader does not know yet.
    marek = _edge(g, "c_marek", "f_mole")
    assert marek["kind"] == "falsely_believes"
    assert marek["false_value"] == "Vesna is a loyal asset."
    assert _edge(g, "c_vesna", "f_mole")["kind"] == "knows"
    assert _node(g, "f_mole")["reader_known"] is False
    assert _node(g, "f_station")["reader_known"] is True  # public


def test_slider_moves_the_asymmetry():
    state = tiny_state()
    # Reader learns at ch6 (so known from ch7), Marek learns at ch9.
    assert _node(state_to_graph(state, 6), "f_mole")["reader_known"] is False
    assert _node(state_to_graph(state, 7), "f_mole")["reader_known"] is True

    # After extract records Marek's discovery, his edge flips to knows by ch10.
    state.running.belief_updates.append(
        BeliefUpdate(chapter=9, character_id="c_marek", fact_id="f_mole", kind=KnowledgeKind.knows)
    )
    assert _edge(state_to_graph(state, 10), "c_marek", "f_mole")["kind"] == "knows"


def test_orphan_belief_is_skipped_not_crashed():
    state = tiny_state()
    marek = state.character("c_marek")
    marek.initial_beliefs.append(Belief(fact_id="f_ghost", kind=KnowledgeKind.knows))
    g = state_to_graph(state, chapter=1)  # must not raise
    assert _edge(g, "c_marek", "f_ghost") is None
