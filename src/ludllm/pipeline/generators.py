"""The setup-stage generators. Each is a pure function (state, models) that fills
in a slice of the authored intent. They are model-driven: the value is the
model's output. The scaffolding here is what we test deterministically (prompt
build, JSON parse, schema validation), with a scripted author standing in for a
real generator.

Stage 0  normalize  -> brief.elements (with provenance)
Stage 1  world      -> world (incl. real-world grounding + era timeline), facts (ledger), threads
Stage 2  cast       -> characters with belief states (per-era for a braided timeline)
Stage 3  structure  -> narrative design, acts, tropes, reveal act-anchors
Stage 4  outline     -> chapter_outline (with hooks), reveal chapter binding (reader/character split)

The reveal schedule is authored once as intent in Stage 1 and bound progressively:
Stage 3 sets each reveal's act_anchor, Stage 4 sets its reader/character chapter.
It is never re-invented downstream.
"""

from __future__ import annotations

import json

from ludllm.models.base import (
    TASK_CAST,
    TASK_NORMALIZE,
    TASK_OUTLINE,
    TASK_STRUCTURE,
    TASK_WORLD,
    ModelBundle,
)
from ludllm.prompts import (
    CAST_SYSTEM,
    NORMALIZE_SYSTEM,
    OUTLINE_SYSTEM,
    STRUCTURE_SYSTEM,
    WORLD_SYSTEM,
)
from ludllm.reference.tropes import tropes_digest
from ludllm.state.schema import (
    Act,
    BookState,
    BriefElement,
    Character,
    ChapterBeat,
    Fact,
    NarrativeDesign,
    Thread,
    TropeUse,
    World,
)
from ludllm.util.blocks import make_block
from ludllm.util.jsonio import loads_lenient

# Output-token budgets for the setup generators. The adapter default (8000) is
# sized for a prose chapter or a single critique; the setup stages emit large
# structured JSON and truncate mid-string at that cap on a dense book (a braided
# world bible + tiered ledger, a full cast, the act design, a 40+ chapter
# manifest). Each stage gets headroom proportional to what it emits; outline is
# the largest because it is one beat block per chapter across the whole book.
STAGE_MAX_TOKENS = {
    TASK_WORLD: 16000,
    TASK_CAST: 16000,
    TASK_STRUCTURE: 12000,
    TASK_OUTLINE: 32000,
}


def _with_notes(blocks: list[str], notes: str) -> str:
    """Append a revision-notes block when regenerating with feedback (a human's
    notes, or an auto-revise critique). Empty notes leave the prompt unchanged."""
    if notes:
        blocks = blocks + [make_block("REVISION_NOTES", notes)]
    return "\n".join(blocks)


def _clean_belief(b: dict) -> dict:
    """Drop a stray empty false_value on a non-false belief: the schema rejects
    false_value unless kind == falsely_believes, so a model that mirrors the JSON
    shape too literally (emitting "") would hard-fail the gated cast stage."""
    if b.get("kind") != "falsely_believes" and not b.get("false_value"):
        return {k: v for k, v in b.items() if k != "false_value"}
    return b


def _clean_character(c: dict) -> dict:
    """Normalize belief dicts (initial and per-era) before validation."""
    c = dict(c)
    if isinstance(c.get("initial_beliefs"), list):
        c["initial_beliefs"] = [_clean_belief(b) for b in c["initial_beliefs"]]
    if isinstance(c.get("era_beliefs"), dict):
        c["era_beliefs"] = {
            k: [_clean_belief(b) for b in v] for k, v in c["era_beliefs"].items()
        }
    return c


def normalize(state: BookState, models: ModelBundle, notes: str = "") -> None:
    """Stage 0: lift any input (logline OR a full cast with no plot) to a
    canonical brief, tagging each element's provenance so the writer never
    overwrites something the user locked."""
    prompt = _with_notes([make_block("RAW_INPUT", state.brief.raw_input)], notes)
    raw = models.author_model.generate(
        system=NORMALIZE_SYSTEM,
        prompt=prompt,
        task=TASK_NORMALIZE,
    )
    data = loads_lenient(raw)
    state.brief.elements = [BriefElement.model_validate(e) for e in data.get("elements", [])]


def generate_world(state: BookState, models: ModelBundle, notes: str = "") -> None:
    """Stage 1: the world bible - the worked-out plot mechanism, the tiered secret
    ledger, the real-world grounding (real orgs, 3+ real incidents, any invented
    unit inside a real org), and the threads. The people come next, in the cast
    stage. The reveal schedule is authored as INTENT only here."""
    prompt = _with_notes(
        [
            make_block("GENRE", state.genre.model_dump_json()),
            make_block("BRIEF", json.dumps([e.model_dump() for e in state.brief.elements])),
            make_block("RAW_INPUT", state.brief.raw_input),
        ],
        notes,
    )
    raw = models.author_model.generate(
        system=WORLD_SYSTEM,
        prompt=prompt,
        task=TASK_WORLD,
        max_tokens=STAGE_MAX_TOKENS[TASK_WORLD],
    )
    data = loads_lenient(raw)
    state.authored.world = World.model_validate(data["world"])
    state.authored.facts = [Fact.model_validate(f) for f in data.get("facts", [])]
    state.authored.threads = [Thread.model_validate(t) for t in data.get("threads", [])]


def generate_cast(state: BookState, models: ModelBundle, notes: str = "") -> None:
    """Stage 2: the cast, as its own gated stage. Derives the institutional
    ecosystem the world implies, winnows to a small load-bearing roster, and sets
    each character's belief state against the Stage 1 facts (knows / does_not_know
    / falsely_believes). It is fed the world and the ledger so the asymmetry is
    built on real fact ids."""
    prompt = _with_notes(
        [
            make_block("GENRE", state.genre.model_dump_json()),
            make_block("WORLD", state.authored.world.model_dump_json()),
            make_block(
                "FACTS",
                json.dumps(
                    [{"id": f.id, "text": f.text, "tier": f.tier.value, "era_id": f.era_id}
                     for f in state.authored.facts]
                ),
            ),
            make_block("BRIEF", json.dumps([e.model_dump() for e in state.brief.elements])),
        ],
        notes,
    )
    raw = models.author_model.generate(
        system=CAST_SYSTEM,
        prompt=prompt,
        task=TASK_CAST,
        max_tokens=STAGE_MAX_TOKENS[TASK_CAST],
    )
    data = loads_lenient(raw)
    state.authored.characters = [
        Character.model_validate(_clean_character(c)) for c in data.get("characters", [])
    ]


def generate_structure(state: BookState, models: ModelBundle, notes: str = "") -> None:
    """Stage 3: the narrative design (how it is told - POV strategy + time mode),
    the acts (with a finer beat layer), the tropes deliberately put in play, and
    each reveal's act anchor. The model proposes the act count; a human ratifies it
    at the gate. A curated trope catalogue is injected for principled selection."""
    prompt = _with_notes(
        [
            make_block("GENRE", state.genre.model_dump_json()),
            make_block("WORLD", state.authored.world.model_dump_json()),
            make_block(
                "CHARACTERS",
                json.dumps(
                    [{"id": c.id, "name": c.name, "role": c.role} for c in state.authored.characters]
                ),
            ),
            make_block(
                "FACTS",
                json.dumps(
                    [{"id": f.id, "tier": f.tier.value, "era_id": f.era_id}
                     for f in state.authored.facts]
                ),
            ),
            make_block("TROPES", tropes_digest()),
        ],
        notes,
    )
    raw = models.author_model.generate(
        system=STRUCTURE_SYSTEM,
        prompt=prompt,
        task=TASK_STRUCTURE,
        max_tokens=STAGE_MAX_TOKENS[TASK_STRUCTURE],
    )
    data = loads_lenient(raw)
    if data.get("narrative"):
        state.authored.narrative = NarrativeDesign.model_validate(data["narrative"])
    state.authored.acts = [Act.model_validate(a) for a in data.get("acts", [])]
    state.authored.tropes = [TropeUse.model_validate(t) for t in data.get("tropes", [])]
    for b in data.get("reveal_bindings", []):
        fact = state.fact(b["fact_id"])
        if fact and fact.reveal:
            if b.get("act_anchor") is not None:
                fact.reveal.act_anchor = b["act_anchor"]
            if b.get("order") is not None:
                fact.reveal.order = b["order"]


def generate_outline(state: BookState, models: ModelBundle, notes: str = "") -> None:
    """Stage 4: the chapter manifest, honoring the narrative design. Each chapter
    gets a beat and a hook; each reveal is bound to a chapter, splitting the
    reader-reveal chapter from the character-reveal chapter (the asymmetry)."""
    prompt = _with_notes(
        [
            make_block("TARGET_CHAPTERS", state.genre.estimated_chapters),
            make_block("NARRATIVE", state.authored.narrative.model_dump_json()),
            make_block(
                "ERAS",
                json.dumps(
                    [
                        {"id": e.id, "label": e.label, "year_start": e.year_start,
                         "year_end": e.year_end, "place": e.place,
                         "capability_baseline": e.capability_baseline}
                        for e in state.authored.world.eras
                    ]
                ),
            ),
            make_block("ACTS", json.dumps([a.model_dump() for a in state.authored.acts])),
            make_block(
                "CHARACTERS",
                json.dumps(
                    [{"id": c.id, "name": c.name, "role": c.role} for c in state.authored.characters]
                ),
            ),
            make_block(
                "THREADS",
                json.dumps([{"id": t.id, "name": t.name} for t in state.authored.threads]),
            ),
            make_block(
                "FACTS",
                json.dumps(
                    [
                        {"id": f.id, "tier": f.tier.value, "era_id": f.era_id,
                         "act_anchor": f.reveal.act_anchor if f.reveal else None}
                        for f in state.authored.facts
                    ]
                ),
            ),
        ],
        notes,
    )
    raw = models.author_model.generate(
        system=OUTLINE_SYSTEM,
        prompt=prompt,
        task=TASK_OUTLINE,
        max_tokens=STAGE_MAX_TOKENS[TASK_OUTLINE],
    )
    data = loads_lenient(raw)
    state.authored.chapter_outline = [
        ChapterBeat.model_validate(c) for c in data.get("chapters", [])
    ]
    for b in data.get("reveal_bindings", []):
        fact = state.fact(b["fact_id"])
        if fact and fact.reveal:
            if b.get("reader_reveal_chapter") is not None:
                fact.reveal.reader_reveal_chapter = b["reader_reveal_chapter"]
            if b.get("character_reveal_chapter") is not None:
                fact.reveal.character_reveal_chapter = b["character_reveal_chapter"]
