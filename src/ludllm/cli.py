"""The ludllm CLI.

Offline, no keys:
    ludllm demo  <dir>                 run the bundled example end to end -> dir/
    ludllm graph <state.json> [-c N]   export the story graph at chapter N
    ludllm show  <state.json>          print a summary of a book state

Authoring a real novel (needs `pip install ludllm[models]` + keys in .env):
    ludllm new "<premise>" [--name X]  create a novel project under runs/
    ludllm stage <project> <stage>     run one setup stage (normalize|world|cast|structure|outline)
                                       [--critique-mode advisory_only|auto_revise|blocking]
                                       [-i/--interactive: confirm this stage's params first]
    ludllm critique <project> <stage>  re-run the dimensional critique panel (advisory)
    ludllm render <project>            re-render the review markdown from book_state.json
    ludllm status <project>            show stage progress + review checks + critique verdicts
    ludllm params <project>            show resolved pipeline params and their source layer
    ludllm params --init-global        seed ~/.config/ludllm/params.toml with a template

Pipeline tunables (loop/revision knobs) live in params.toml, editable per project
(<project>/params.toml) or globally (~/.config/ludllm/params.toml). See ludllm.params.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ludllm.authoring.checks import check_state
from ludllm.authoring.interactive import prompt_stage_params
from ludllm.authoring.project import create_project, open_project
from ludllm.authoring.render import render_all
from ludllm.authoring.run import critique_only, pending_finishing_stages
from ludllm.authoring.run import run_stage as author_run_stage
from ludllm.authoring.run import stale_stages
from ludllm.examples.mole import scripted_author, seed_state
from ludllm.models.base import ModelBundle
from ludllm.models.mock import MockModel
from ludllm.params import STAGE_PARAMS, resolve_with_sources, write_global_template
from ludllm.pipeline.stages import RUNNABLE_STAGES, SETUP_STAGES, STAGE_VIZ, run_stage
from ludllm.pipeline.writer import LoopConfig, run_chapter
from ludllm.state.schema import BookState, CritiqueMode, GenreProfile
from ludllm.state.store import load_state, save_state
from ludllm.viz.export import state_to_graph
from ludllm.viz.studio import build_viz


def _print_critique(crit) -> None:
    if crit is None:
        return
    if crit.revised:
        n = getattr(crit, "revise_passes", 0) or 1
        revised = f" (auto-revised x{n})"
    else:
        revised = ""
    print(f"\ncritique verdict: {crit.verdict.upper()}{revised}  "
          f"[lowest {crit.min_score}/5]")
    for s in crit.scores:
        print(f"  {s.dimension:>14}: {s.score}/5  {s.fix}")
    if crit.top_fix:
        print(f"  -> top fix: {crit.top_fix}")


def _mock_bundle() -> ModelBundle:
    return ModelBundle(
        drafter=MockModel(family="anthropic"),
        extractor=MockModel(family="anthropic"),
        critic=MockModel(family="google"),
        author=scripted_author(),
    )


def cmd_demo(args: argparse.Namespace) -> int:
    out = Path(args.dir)
    state = seed_state()
    bundle = _mock_bundle()

    for stage in SETUP_STAGES:
        run_stage(state, stage, bundle)

    chapters = [cb.n for cb in state.authored.chapter_outline]
    cfg = LoopConfig(output_dir=str(out / "chapters"))
    for n in chapters:
        run_chapter(state, n, bundle, cfg)

    save_state(state, out / "book_state.json")
    last = max(chapters) + 1 if chapters else 1
    (out / "graph.json").write_text(
        json.dumps(state_to_graph(state, last), indent=2), encoding="utf-8"
    )

    print(f"Demo written to {out}/")
    print(f"  book_state.json  ({len(state.authored.facts)} facts, "
          f"{len(state.authored.chapter_outline)} chapters outlined)")
    print(f"  chapters/        ({len(chapters)} drafted on mock models)")
    print("  graph.json       (story graph at the end state)")
    print("\nThis ran offline on mock models. No keys, no tokens.")
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    state = load_state(args.state)
    graph = state_to_graph(state, args.chapter)
    text = json.dumps(graph, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Graph at chapter {args.chapter} written to {args.output}")
    else:
        print(text)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    state: BookState = load_state(args.state)
    print(f"Title: {state.meta.title}")
    print(f"Frozen stages: {', '.join(state.meta.frozen_stages) or '(none)'}")
    print(f"Characters: {', '.join(c.name for c in state.authored.characters) or '(none)'}")
    print(f"Acts: {len(state.authored.acts)}   "
          f"Chapters outlined: {len(state.authored.chapter_outline)}   "
          f"Chapters drafted: {sum(1 for c in state.running.chapters)}")
    print("Ledger:")
    for f in state.authored.facts:
        print(f"  [{f.tier.value:>14}] {f.id}: {f.text}")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    genre = GenreProfile(target_words=args.words) if args.words else None
    project = create_project(args.runs, args.premise, name=args.name, genre=genre)
    render_all(project)
    print(f"Created {project.root}/")
    print(f"  book_state.json   (premise seeded; {project.load().genre.estimated_chapters} "
          "chapters estimated)")
    print(f"\nNext: ludllm stage {project.root} normalize")
    return 0


def _real_bundle():
    from dotenv import load_dotenv

    load_dotenv()
    from ludllm.models.providers import default_bundle

    return default_bundle()


def cmd_stage(args: argparse.Namespace) -> int:
    if args.stage not in RUNNABLE_STAGES:
        print(f"unknown stage '{args.stage}'. choose: {', '.join(RUNNABLE_STAGES)}")
        return 2
    project = open_project(args.project)
    if args.interactive:
        prompt_stage_params(project.root, args.stage)
    # Unset flags (None) fall through to the project's params.toml; an explicit flag wins.
    critique = False if args.no_critique else None
    critique_mode = CritiqueMode(args.critique_mode) if args.critique_mode else None
    # viz is a model-free view producer; do not build (or require keys for) a bundle.
    bundle = None if args.stage == STAGE_VIZ else _real_bundle()
    run = author_run_stage(
        project, args.stage, bundle,
        force=args.force,
        critique=critique,
        critique_mode=critique_mode,
    )
    if not run.ran:
        print(f"stage '{args.stage}' already done (use --force to regenerate)")
        return 0
    print(f"stage '{args.stage}' done. review:")
    for p in run.rendered:
        print(f"  {p}")
    _print_critique(run.critique)
    if run.blocked:
        print("\nBLOCKED: the critique returned 'regenerate'; this stage is not frozen. "
              "Resolve it (edit or `stage --force`) before advancing.")
    stale = stale_stages(project)
    if stale:
        print(f"\nNote: downstream stages may be stale after this: {', '.join(stale)}")
        print("Regenerate them with --force when ready.")
    return 0


def cmd_critique(args: argparse.Namespace) -> int:
    if args.stage not in SETUP_STAGES:
        print(f"unknown stage '{args.stage}'. choose: {', '.join(SETUP_STAGES)}")
        return 2
    project = open_project(args.project)
    crit = critique_only(project, args.stage, _real_bundle())
    if crit is None:
        print(f"stage '{args.stage}' has no critique rubric")
        return 0
    print(f"critique for stage '{args.stage}' (advisory, re-rendered):")
    _print_critique(crit)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    project = open_project(args.project)
    written = render_all(project)
    print(f"re-rendered {len(written)} file(s) from book_state.json")
    return 0


def cmd_viz(args: argparse.Namespace) -> int:
    project = Path(args.project)
    if not (project / "book_state.json").exists():
        print(f"no book_state.json under {project}")
        return 2
    studio = build_viz(project, open_browser=args.open)
    print(f"story studio written to {studio.parent}/")
    print(f"  open: {studio}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    project = open_project(args.project)
    state = project.load()
    print(f"Project: {project.name}")
    print(f"Stages run: {', '.join(state.meta.frozen_stages) or '(none)'}")
    stale = stale_stages(project)
    if stale:
        print(f"Possibly stale: {', '.join(stale)}")
    # Finishing stages (dossier, viz) are off-spine, mandatory, and run LAST, after
    # the manuscript, so they reflect the final book.
    pending = pending_finishing_stages(project)
    if pending:
        print(f"Finishing stages (run after the manuscript): pending -> {', '.join(pending)}")
    else:
        print("Finishing stages: done (dossiers + studio built)")
    issues = check_state(state)
    if issues:
        print(f"\nReview checks ({len(issues)}):")
        for i in issues:
            print(f"  - {i}")
    else:
        print("Review checks: clean")
    if state.reviews:
        print("\nCritique verdicts:")
        for key, crit in state.reviews.items():
            mark = f"{crit.verdict}{' (revised)' if crit.revised else ''}"
            print(f"  {key:>12}: {mark}  [lowest {crit.min_score}/5]")
    return 0


def cmd_params(args: argparse.Namespace) -> int:
    if args.init_global:
        path = write_global_template(overwrite=args.force)
        print(f"global params template at {path}")
        print("Edit it to set cross-book defaults; per-project params.toml overrides it.")
        return 0
    if not args.project:
        print("usage: ludllm params <project>   (or: ludllm params --init-global)")
        return 2
    project = open_project(args.project)
    rows = resolve_with_sources(project.root)
    print(f"Resolved parameters for {project.name} (project > global > default):\n")
    by_stage: dict[str, list[str]] = {}
    for r in rows:
        tag = "" if r["source"] == "default" else f"  <- {r['source']}"
        print(f"  {r['key']:>28} = {str(r['value']):<14}{tag}")
        for stage, keys in STAGE_PARAMS.items():
            if r["key"] in keys:
                by_stage.setdefault(stage, []).append(r["key"])
    print("\nAsked at the start of each stage (only its own params):")
    for stage in ("world", "cast", "structure", "outline", "writer"):
        print(f"  {stage:>10}: {', '.join(by_stage.get(stage, [])) or '(none)'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ludllm", description="Agentic novel pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_demo = sub.add_parser("demo", help="run the bundled example end to end (offline)")
    p_demo.add_argument("dir", help="output directory")
    p_demo.set_defaults(func=cmd_demo)

    p_graph = sub.add_parser("graph", help="export the story graph from a state file")
    p_graph.add_argument("state", help="path to book_state.json")
    p_graph.add_argument("-c", "--chapter", type=int, default=1, help="chapter to render at")
    p_graph.add_argument("-o", "--output", help="write JSON here instead of stdout")
    p_graph.set_defaults(func=cmd_graph)

    p_show = sub.add_parser("show", help="summarize a state file")
    p_show.add_argument("state", help="path to book_state.json")
    p_show.set_defaults(func=cmd_show)

    p_new = sub.add_parser("new", help="create a novel project under runs/")
    p_new.add_argument("premise", help="the premise (a sentence or a paragraph)")
    p_new.add_argument("--name", help="novel title (slugified for the folder); else book_XXX_DD_MM_YY")
    p_new.add_argument("--words", type=int, help="target word count (default ~130k)")
    p_new.add_argument("--runs", default="runs", help="parent directory for projects")
    p_new.set_defaults(func=cmd_new)

    p_stage = sub.add_parser("stage", help="run one pipeline stage (setup stages use real models; viz is offline)")
    p_stage.add_argument("project", help="path to the novel project folder")
    p_stage.add_argument("stage", help="normalize | world | cast | structure | outline | dossier | viz")
    p_stage.add_argument("--force", action="store_true", help="regenerate (invalidates downstream)")
    p_stage.add_argument(
        "--critique-mode", choices=[m.value for m in CritiqueMode], default=None,
        help="override the critique mode for this run (default: from params.toml)",
    )
    p_stage.add_argument("--no-critique", action="store_true", help="skip the dimensional critique")
    p_stage.add_argument(
        "-i", "--interactive", action="store_true",
        help="confirm/change this stage's params before running (writes params.toml)",
    )
    p_stage.set_defaults(func=cmd_stage)

    p_critique = sub.add_parser("critique", help="re-run the dimensional critique panel (advisory)")
    p_critique.add_argument("project", help="path to the novel project folder")
    p_critique.add_argument("stage", help="world | cast | structure | outline")
    p_critique.set_defaults(func=cmd_critique)

    p_render = sub.add_parser("render", help="re-render review markdown from book_state.json")
    p_render.add_argument("project", help="path to the novel project folder")
    p_render.set_defaults(func=cmd_render)

    p_status = sub.add_parser("status", help="show stage progress + review checks")
    p_status.add_argument("project", help="path to the novel project folder")
    p_status.set_defaults(func=cmd_status)

    p_viz = sub.add_parser("viz", help="build the interactive story-graph studio (viz/studio.html)")
    p_viz.add_argument("project", help="path to the novel project folder")
    p_viz.add_argument("--open", action="store_true", help="open studio.html in the browser")
    p_viz.set_defaults(func=cmd_viz)

    p_params = sub.add_parser("params", help="show resolved pipeline params (or seed the global file)")
    p_params.add_argument("project", nargs="?", help="path to the novel project folder")
    p_params.add_argument(
        "--init-global", action="store_true",
        help="write a commented template to ~/.config/ludllm/params.toml",
    )
    p_params.add_argument("--force", action="store_true", help="overwrite the global file if it exists")
    p_params.set_defaults(func=cmd_params)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
