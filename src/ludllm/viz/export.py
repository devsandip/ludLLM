"""state_to_graph: the versioned graph contract the renderers consume.

Lives in core (stdlib + Pydantic only, no UI deps) so the JSON shape is versioned
with the schema and the boundary semantics are fixed once, here. Renderers
(Cytoscape.js, D3) live in the bolt-on UI and never re-derive epistemic logic.

The graph at a given chapter is the knowledge graph AT THAT MOMENT: character and
fact nodes, with one edge per character's effective belief about each fact
(knows / does_not_know / falsely_believes). Drag the chapter and the edges
restyle; that is the information-asymmetry view the system exists to control.

Boundary semantics come straight from the BookState helpers (reader knowledge
uses strict `< chapter`; in-chapter reveals use `== chapter`), never re-derived.
"""

from __future__ import annotations

from ludllm.state.schema import BookState, KnowledgeKind

GRAPH_SCHEMA_VERSION = 2


def state_to_graph(state: BookState, chapter: int) -> dict:
    reader_known_ids = {f.id for f in state.reader_known_facts(chapter)}
    fact_ids = {f.id for f in state.authored.facts}

    nodes: list[dict] = []
    for c in state.authored.characters:
        nodes.append(
            {"id": c.id, "type": "character", "label": c.name, "role": c.role, "born": c.born}
        )
    for f in state.authored.facts:
        nodes.append(
            {
                "id": f.id,
                "type": "fact",
                "label": f.text,
                "tier": f.tier.value,
                "era_id": f.era_id,
                "reader_known": f.id in reader_known_ids,
                "reader_reveal_chapter": f.reveal.reader_reveal_chapter if f.reveal else None,
                "character_reveal_chapter": (
                    f.reveal.character_reveal_chapter if f.reveal else None
                ),
            }
        )

    edges: list[dict] = []
    for c in state.authored.characters:
        for fid, belief in state.effective_beliefs(c.id, chapter).items():
            if fid not in fact_ids:
                # Orphan: a belief about a fact that no longer exists. Skip, do
                # not crash, so a mid-edit state still renders.
                continue
            edge = {"source": c.id, "target": fid, "kind": belief.kind.value}
            if belief.kind == KnowledgeKind.falsely_believes:
                edge["false_value"] = belief.false_value
            edges.append(edge)

    # Story-time context for the snapshot, so a renderer can show which era/year
    # the chapter sits in (a braided timeline) rather than only a print index.
    # Resolved (not the raw beat) so era_id and era_year agree past the outline.
    snap_era = state.era(state._resolve_era_id(chapter))
    return {
        "graph_schema_version": GRAPH_SCHEMA_VERSION,
        "chapter": chapter,
        "era_id": snap_era.id if snap_era else None,
        "era_year": state._chapter_era_year(chapter),
        "eras": [
            {"id": e.id, "label": e.label, "year_start": e.year_start, "year_end": e.year_end}
            for e in state.authored.world.eras
        ],
        "nodes": nodes,
        "edges": edges,
    }
