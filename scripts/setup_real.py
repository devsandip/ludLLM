"""Validate the setup generators on real Opus, using a DISPOSABLE synthetic
premise (not the real book). Confirms the model emits schema-valid output across
normalize / world / cast / structure / outline, then writes one chapter end to end.

    uv run python scripts/setup_real.py
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from ludllm.models.base import ModelBundle  # noqa: E402
from ludllm.models.providers import AnthropicModel, GeminiModel  # noqa: E402
from ludllm.pipeline.writer import LoopConfig, run_chapter  # noqa: E402
from ludllm.pipeline.stages import SETUP_STAGES, run_stage  # noqa: E402
from ludllm.state.schema import BookState, CreativeBrief, GenreProfile  # noqa: E402
from ludllm.state.store import save_state  # noqa: E402

# Disposable test premise. NOT the real book.
PREMISE = (
    "Maya Rao, a young R&AW field officer, runs a defector exfiltration out of "
    "Istanbul. Her Delhi handler, Colonel Anjali Sen, is secretly an ISI asset "
    "feeding the operation to the other side. The reader should come to suspect "
    "Anjali around the midpoint; Maya should only learn the betrayal near the climax."
)


def main() -> None:
    state = BookState(
        genre=GenreProfile(target_words=12000, words_per_chapter=3000, default_acts=4),
        brief=CreativeBrief(raw_input=PREMISE),
    )
    bundle = ModelBundle(
        drafter=AnthropicModel("claude-opus-4-8", name="drafter", max_tokens=3500),
        extractor=AnthropicModel("claude-haiku-4-5", name="extractor", max_tokens=1500),
        critic=GeminiModel(name="critic"),
        author=AnthropicModel("claude-opus-4-8", name="author", max_tokens=6000),
    )

    for stage in SETUP_STAGES:
        run_stage(state, stage, bundle)
        print(f"[stage ok] {stage}")

    a = state.authored
    print("\n===== WORLD =====")
    print(a.world.premise, "|", a.world.setting)
    print("plot_mechanism:", a.world.plot_mechanism)
    print("\n===== CAST =====")
    for c in a.characters:
        beliefs = ", ".join(
            f"{b.kind.value}:{b.fact_id}" + (f"({b.false_value})" if b.false_value else "")
            for b in c.initial_beliefs
        )
        print(f"  {c.id} {c.name} [{c.role}] -> {beliefs or '(none)'}")
    print("\n===== LEDGER =====")
    for f in a.facts:
        r = f.reveal
        sched = (
            f" reader@{r.reader_reveal_chapter} char@{r.character_reveal_chapter} act={r.act_anchor}"
            if r else ""
        )
        print(f"  [{f.tier.value:>14}] {f.id}: {f.text}{sched}")
    print("\n===== ACTS =====")
    for act in a.acts:
        print(f"  {act.id} (n{act.n}) {act.name}: {act.summary[:80]}")
    print("\n===== OUTLINE =====")
    for cb in a.chapter_outline:
        print(f"  ch{cb.n} act={cb.act_id} pov={cb.pov} reveals(reader={cb.reader_reveals} "
              f"char={cb.character_reveals}): {cb.beat[:70]}")

    print("\n===== writing chapter 1 on Opus =====")
    res = run_chapter(state, 1, bundle, LoopConfig(max_revise=1, output_dir="runs/setup/chapters"))
    print(f"accepted={res.accepted} leaks={res.leaks} flags={res.flags}")
    print(res.prose[:500])

    save_state(state, Path("runs/setup/book_state.json"))
    print("\nstate written to runs/setup/book_state.json")


if __name__ == "__main__":
    main()
