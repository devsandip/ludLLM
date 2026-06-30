"""The control plane: run a setup stage, optionally behind a human gate, and
freeze it once done. Gates are collapsible (alteration #6): during pipeline
tuning you run gates-off (auto-advance); for the hero run you run gated and a
reviewer approves each artifact before it freezes.

A frozen stage is not re-run. This is what protects approved authored intent
while the Stage 5 extract step keeps mutating the running state underneath it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ludllm.models.base import ModelBundle
from ludllm.pipeline.dossier import generate_dossiers
from ludllm.pipeline.generators import (
    generate_cast,
    generate_outline,
    generate_structure,
    generate_world,
    normalize,
)
from ludllm.state.schema import BookState

STAGE_NORMALIZE = "normalize"
STAGE_WORLD = "world"
STAGE_CAST = "cast"
STAGE_STRUCTURE = "structure"
STAGE_OUTLINE = "outline"
STAGE_DOSSIER = "dossier"
STAGE_VIZ = "viz"

# The setup stages, in order. Cast sits between world and structure: it needs the
# facts (Stage 1) to set belief states, and structure/outline need the people.
# Stage 5 (the chapter loop) is its own engine.
SETUP_STAGES = [STAGE_NORMALIZE, STAGE_WORLD, STAGE_CAST, STAGE_STRUCTURE, STAGE_OUTLINE]

# Off-spine artifact stages. Deliberately NOT in SETUP_STAGES (the linear
# JSON-authoring spine the critique panel and the downstream-invalidation logic
# walk): they produce artifacts from finished state, have no dimensional rubric, and
# are not cascade-invalidated when an upstream stage is regenerated with --force.
# They are FINISHING stages, run after the writer (see FINISHING_STAGES below).
#   dossier -> per-character classified files + PDF/portrait artifacts.
#   viz     -> the interactive story-graph studio (viz/studio.html), a read-only
#              view of the state. It authors no state and needs no models; it is
#              handled in the authoring layer (authoring/run.py), not _REGISTRY.
# RUNNABLE_STAGES is everything you can invoke with `ludllm stage`.
RUNNABLE_STAGES = [*SETUP_STAGES, STAGE_DOSSIER, STAGE_VIZ]

# Off-spine, MANDATORY, and run LAST. dossier and viz are not on the critique/
# invalidation spine, but they are not optional either: a finished book ships with
# its dossiers and its studio. They run AFTER the writer, because the chapter loop
# mutates state as it goes (belief updates from extract, plus any mid-write authored
# edits), so the dossiers and the knowledge-graph studio must be built from the
# FINAL book, not a pre-write snapshot the writing would invalidate. The full-book
# runner runs them once the manuscript is complete; `ludllm status` reports them as
# pending until then. Mandatory means required-to-finish, not auto-run.
FINISHING_STAGES = [STAGE_DOSSIER, STAGE_VIZ]

_REGISTRY: dict[str, Callable[..., None]] = {
    STAGE_NORMALIZE: normalize,
    STAGE_WORLD: generate_world,
    STAGE_CAST: generate_cast,
    STAGE_STRUCTURE: generate_structure,
    STAGE_OUTLINE: generate_outline,
    STAGE_DOSSIER: generate_dossiers,
}

# A reviewer is called at a gate; it returns True to approve (freeze) the stage.
Reviewer = Callable[[BookState, str], bool]


@dataclass
class StageResult:
    stage: str
    ran: bool          # False if skipped because already frozen
    frozen: bool       # True if it is now frozen (approved or gates-off)
    approved: bool      # the reviewer's verdict (True when gates-off)


def run_stage(
    state: BookState,
    stage: str,
    models: ModelBundle,
    *,
    gated: bool = False,
    reviewer: Reviewer | None = None,
    notes: str = "",
) -> StageResult:
    if stage not in _REGISTRY:
        raise ValueError(f"unknown or not-yet-implemented stage: {stage!r}")
    if stage in state.meta.frozen_stages:
        return StageResult(stage=stage, ran=False, frozen=True, approved=True)

    _REGISTRY[stage](state, models, notes=notes)

    if gated:
        approved = reviewer(state, stage) if reviewer else False
    else:
        approved = True  # gates-off: auto-advance

    if approved:
        state.meta.frozen_stages.append(stage)
    return StageResult(stage=stage, ran=True, frozen=approved, approved=approved)


def implemented_stages() -> list[str]:
    return list(_REGISTRY.keys())
