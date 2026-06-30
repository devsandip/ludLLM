"""Extract: read the accepted chapter and write back what it established.

Appends belief updates (the POV now knows the facts revealed to them) to the
running state and returns established facts + a summary. This is what keeps the
ledger and belief states LIVE during writing.
"""

from __future__ import annotations

from ludllm.models.base import TASK_EXTRACT, ModelBundle
from ludllm.prompts import EXTRACT_SYSTEM
from ludllm.state.schema import BeliefUpdate, BookState, KnowledgeKind
from ludllm.util.blocks import make_block
from ludllm.util.jsonio import loads_lenient


def extract(state: BookState, n: int, prose: str, models: ModelBundle) -> dict:
    beat = state.chapter_beat(n)
    prompt = "\n".join(
        [
            make_block("CHAPTER", n),
            make_block("POV", beat.pov or ""),
            make_block("PLANNED_CHARACTER_REVEALS", ",".join(beat.character_reveals)),
            make_block("INTENT", beat.intent),
            make_block("BEAT", beat.beat),
            make_block("PROSE", prose),
        ]
    )
    raw = models.extractor.generate(system=EXTRACT_SYSTEM, prompt=prompt, task=TASK_EXTRACT)
    try:
        data = loads_lenient(raw)
        if not isinstance(data, dict):
            raise ValueError("extract did not return a JSON object")
    except ValueError:
        # Fall back to the authored plan: a misformatted extract must not crash a run.
        data = {"learned_fact_ids": list(beat.character_reveals)}

    learned = data.get("learned_fact_ids", [])
    if beat.pov:
        for fid in learned:
            state.running.belief_updates.append(
                BeliefUpdate(chapter=n, character_id=beat.pov, fact_id=fid, kind=KnowledgeKind.knows)
            )
    return {
        "established_fact_ids": data.get("established_fact_ids", learned),
        "summary": data.get("summary") or beat.intent or beat.beat,
    }
