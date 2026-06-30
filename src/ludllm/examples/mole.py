"""The canonical example: a mole inside a Vienna station.

Ships in the package so `ludllm demo` works offline with no keys. The scripted
author returns canned per-stage JSON, standing in for a real generator, so the
whole pipeline runs deterministically. Tests reuse this too.
"""

from __future__ import annotations

import json

from ludllm.models.base import (
    TASK_CAST,
    TASK_NORMALIZE,
    TASK_OUTLINE,
    TASK_STRUCTURE,
    TASK_WORLD,
)
from ludllm.models.mock import ScriptedAuthorModel
from ludllm.state.schema import BookState, CreativeBrief

PREMISE = "A mole inside a Vienna station."

_NORMALIZE = {
    "elements": [
        {"kind": "premise", "text": PREMISE, "provenance": "user_seed"},
        {"kind": "character", "text": "Marek, a case officer.", "provenance": "user_seed"},
        {"kind": "character", "text": "Vesna, an asset.", "provenance": "user_seed"},
    ]
}

# Stage 1: the world and the secrets. No characters here (they are the cast stage).
_WORLD = {
    "world": {
        "premise": "A mole hunt in a Vienna station.",
        "setting": "Cold-war Vienna.",
        "rules": ["Tradecraft is realistic."],
        "factions": ["The station", "The opposing service"],
        "tradecraft": ["Dead drops", "Brush passes"],
        "plot_mechanism": "An asset feeds the station false intel while secretly reporting to the other side; the operation's weakness is a verification step nobody re-checks.",
        "themes": ["Loyalty", "Betrayal"],
        "real_anchors": [
            {"incident": "the 1963 defection of Kim Philby to Moscow", "era": "1963",
             "relevance": "the institutional template for the buried traitor"},
            {"incident": "the 1985 Aldrich Ames betrayal", "era": "1985",
             "relevance": "the cost of intelligence no one wants to question"},
            {"incident": "the 1961 construction of the Berlin Wall", "era": "1961",
             "relevance": "the divided geography the station operates across"},
        ],
        "real_organizations": ["CIA", "KGB", "BND"],
        "invented_units": [
            {"name": "the Vienna Liaison Desk", "parent_org": "CIA",
             "justification": "no real desk of this exact remit existed at the station"}
        ],
        "eras": [
            {
                "id": "e_vienna",
                "label": "Vienna station, 1985",
                "year_start": 1985,
                "year_end": None,
                "place": "Vienna",
                "capability_baseline": [
                    "Field comms are dead drops, brush passes, phone boxes, telex, and shortwave numbers stations; no mobile phones.",
                    "No DNA profiling in casework; identity is verified by documents, tradecraft, and tells.",
                    "The KGB, the CIA, and the BND are all operational; the Berlin Wall still stands.",
                ],
            }
        ],
    },
    "facts": [
        {
            "id": "f_mole",
            "text": "Vesna is a double agent inside the station.",
            "tier": "hidden",
            "era_id": "e_vienna",
            "reveal": {"order": 1},
        },
        {
            "id": "f_station",
            "text": "The Vienna station exists and runs the operation.",
            "tier": "public",
            "era_id": "e_vienna",
        },
    ],
    "threads": [{"id": "t_molehunt", "name": "The mole hunt", "description": "Finding the leak."}],
}

# Stage 2: the cast, built against the Stage 1 facts.
_CAST = {
    "characters": [
        {
            "id": "c_marek",
            "name": "Marek",
            "provenance": "user_seed",
            "role": "protagonist, case officer",
            "backstory": "A careful officer who trusts his assets.",
            "worldview": "Loyalty is earned and kept.",
            "initial_beliefs": [
                {
                    "fact_id": "f_mole",
                    "kind": "falsely_believes",
                    "false_value": "Vesna is a loyal asset.",
                }
            ],
        },
        {
            "id": "c_vesna",
            "name": "Vesna",
            "provenance": "user_seed",
            "role": "asset, secret mole",
            "backstory": "Recruited under duress by the opposing service.",
            "worldview": "Survival first.",
            "initial_beliefs": [{"fact_id": "f_mole", "kind": "knows"}],
        },
    ]
}

_STRUCTURE = {
    "narrative": {
        "mode": "linear",
        "pov_strategy": "single",
        "pov_count": 1,
        "rationale": "A single POV locked to Marek maximizes the reader-vs-protagonist gap.",
    },
    "tropes": [
        {"name": "The mole", "how_used": "A trusted asset is the traitor.", "subverted": False},
        {"name": "The intelligence that is too good", "how_used": "The station's appetite is the vulnerability.", "subverted": True},
    ],
    "acts": [
        {"id": "a1", "n": 1, "name": "Setup", "summary": "Marek trusts Vesna."},
        {"id": "a2", "n": 2, "name": "Rising", "summary": "Doubts surface."},
        {"id": "a3", "n": 3, "name": "Crisis", "summary": "The betrayal lands."},
        {"id": "a4", "n": 4, "name": "Resolution", "summary": "The reckoning."},
    ],
    "reveal_bindings": [{"fact_id": "f_mole", "act_anchor": "a3", "order": 1}],
}

_OUTLINE = {
    "chapters": [
        {"n": 1, "act_id": "a1", "era_id": "e_vienna", "story_time": "spring 1985",
         "pov": "c_marek", "present": ["c_marek", "c_vesna"],
         "threads": ["t_molehunt"], "beat": "Marek trusts Vesna with the operation.",
         "intent": "Establish the trust that will break.",
         "hook": "An intercept arrives that should not exist."},
        {"n": 6, "act_id": "a2", "era_id": "e_vienna", "story_time": "summer 1985",
         "pov": "c_marek", "present": ["c_marek"],
         "threads": ["t_molehunt"], "beat": "The reader sees Vesna signal her handler.",
         "intent": "Reader learns the truth before Marek.", "reader_reveals": ["f_mole"],
         "hook": "Marek signs off on the next drop, blind."},
        {"n": 9, "act_id": "a3", "era_id": "e_vienna", "story_time": "autumn 1985",
         "pov": "c_marek", "present": ["c_marek", "c_vesna"],
         "threads": ["t_molehunt"], "beat": "Marek discovers the betrayal.",
         "intent": "Marek learns what the reader already knows.",
         "character_reveals": ["f_mole"],
         "hook": "He has to decide what to do with what he now knows."},
    ],
    "reveal_bindings": [
        {"fact_id": "f_mole", "reader_reveal_chapter": 6, "character_reveal_chapter": 9}
    ],
}


def scripted_author() -> ScriptedAuthorModel:
    return ScriptedAuthorModel(
        responses={
            TASK_NORMALIZE: json.dumps(_NORMALIZE),
            TASK_WORLD: json.dumps(_WORLD),
            TASK_CAST: json.dumps(_CAST),
            TASK_STRUCTURE: json.dumps(_STRUCTURE),
            TASK_OUTLINE: json.dumps(_OUTLINE),
        }
    )


def seed_state() -> BookState:
    """A fresh project state seeded only with the premise; the setup stages fill
    in the rest."""
    return BookState(brief=CreativeBrief(raw_input=PREMISE))
