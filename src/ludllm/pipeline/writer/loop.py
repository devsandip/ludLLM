"""Stage 5 orchestration: draft -> critique -> revise (until gate) -> extract.

Ordering note: the primer sketches draft -> extract -> critique -> revise. We run
extract on the ACCEPTED prose instead, so we do not write established facts back
to state from a draft we are about to throw away. The gate is per chapter; the
loop's goal is never "finish the book."

Model-agnostic. With `MockModel`s it runs deterministically and free; swap in
Claude/Gemini/GPT adapters with no change here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ludllm.eval import critique_chapter
from ludllm.models.base import ModelBundle
from ludllm.pipeline.guards import find_leaks
from ludllm.pipeline.writer.critique import critique
from ludllm.pipeline.writer.draft import draft, revise
from ludllm.pipeline.writer.extract import extract
from ludllm.reference.anachronisms import scan_anachronisms
from ludllm.state.schema import BookState, ChapterState, ChapterStatus


@dataclass
class LoopConfig:
    max_revise: int = 2
    output_dir: str | None = None  # if set, accepted prose is written here
    advisory: bool = True          # run the per-chapter advisory note on accepted prose


@dataclass
class ChapterRunResult:
    chapter: int
    accepted: bool
    prose: str
    flags: list[str] = field(default_factory=list)
    leaks: list[str] = field(default_factory=list)
    anachronisms: list[str] = field(default_factory=list)
    revise_iterations: int = 0
    chapter_state: ChapterState | None = None


def _chapter_state(state: BookState, n: int) -> ChapterState:
    cs = next((c for c in state.running.chapters if c.n == n), None)
    if cs is None:
        cs = ChapterState(n=n)
        state.running.chapters.append(cs)
    return cs


def run_chapter(
    state: BookState, n: int, models: ModelBundle, config: LoopConfig | None = None
) -> ChapterRunResult:
    config = config or LoopConfig()
    models.assert_cross_family_critique()

    prose = draft(state, n, models)

    accepted = False
    flags: list[str] = []
    iterations = 0
    for attempt in range(config.max_revise + 1):
        flags = critique(state, n, prose, models)
        if not flags:
            accepted = True
            break
        if attempt == config.max_revise:
            break
        prose = revise(state, n, prose, flags, models)
        iterations += 1

    beat = state.chapter_beat(n)
    forbidden = state.forbidden_for_drafter(beat.pov, n) if beat.pov else []
    leaks = find_leaks(prose, forbidden)

    # Period backstop: scan the prose for terms that do not belong to the chapter's
    # era (advisory, like the leak list; the human gate and the period critic decide).
    era = state.chapter_era(n)
    anachronisms = scan_anachronisms(prose, era.year_start if era else None)

    cs = _chapter_state(state, n)
    cs.word_count = len(prose.split())
    cs.revise_iterations = iterations
    cs.critique_flags = flags
    cs.anachronism_flags = anachronisms

    if accepted:
        result = extract(state, n, prose, models)
        cs.established_fact_ids = result["established_fact_ids"]
        cs.rolling_summary = result["summary"]
        state.running.rolling_summary = (
            f"{state.running.rolling_summary}\nCh{n}: {result['summary']}".strip()
        )
        cs.status = ChapterStatus.accepted
        # Advisory coverage note on the finished prose (voice / momentum / realism).
        # The blocking critic above is the convergence driver; this is for the showrunner.
        if config.advisory:
            state.reviews[f"chapter_{n}"] = critique_chapter(state, n, prose, models)
    else:
        cs.status = ChapterStatus.critiqued

    if config.output_dir and accepted:
        out = Path(config.output_dir) / f"chapter_{n:03d}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(prose, encoding="utf-8")
        cs.draft_path = str(out)

    return ChapterRunResult(
        chapter=n,
        accepted=accepted,
        prose=prose,
        flags=flags,
        leaks=leaks,
        anachronisms=anachronisms,
        revise_iterations=iterations,
        chapter_state=cs,
    )
