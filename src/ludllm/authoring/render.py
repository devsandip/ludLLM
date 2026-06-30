"""Render book_state.json into per-stage markdown for human review.

The JSON is canonical; this produces the readable surface. Each file opens with
a "Review checks" banner (from checks.py) so structural problems surface before
you read the content. You review the markdown, then push edits back through any
channel (chat, edit the markdown, edit the JSON); re-render to reconverge.
"""

from __future__ import annotations

from ludllm.authoring.checks import check_state
from ludllm.authoring.project import NovelProject
from ludllm.pipeline.stages import (
    STAGE_CAST,
    STAGE_DOSSIER,
    STAGE_NORMALIZE,
    STAGE_OUTLINE,
    STAGE_STRUCTURE,
    STAGE_WORLD,
)
from ludllm.state.schema import BookState


def _checks_banner(state: BookState) -> str:
    issues = check_state(state)
    if not issues:
        return "## Review checks\n\nNo structural issues found.\n"
    lines = ["## Review checks", "", f"{len(issues)} issue(s) to confirm or fix:", ""]
    lines += [f"- {i}" for i in issues]
    return "\n".join(lines) + "\n"


_VERDICT_MARK = {"ship": "ship", "tighten": "tighten", "regenerate": "REGENERATE"}


def _critique_banner(state: BookState, key: str) -> str:
    """The dimensional critique scorecard for a stage (advisory; informs the gate).
    Empty if the stage has not been critiqued yet."""
    crit = state.reviews.get(key)
    if crit is None:
        return ""
    revised = " (after one auto-revise)" if crit.revised else ""
    lines = [
        "## Critique panel",
        "",
        f"Verdict: **{_VERDICT_MARK.get(crit.verdict, crit.verdict)}**{revised}  "
        f"(lowest dimension {crit.min_score}/5)",
        "",
        "| dimension | score | reading | fix |",
        "|---|---|---|---|",
    ]
    for s in crit.scores:
        ev = (s.evidence or "").replace("|", "\\|")
        fx = (s.fix or "").replace("|", "\\|")
        lines.append(f"| {s.dimension} | {s.score}/5 | {ev} | {fx} |")
    if crit.top_fix:
        lines += ["", f"Highest-leverage fix: {crit.top_fix}"]
    return "\n".join(lines) + "\n"


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items) if items else "- (none)"


def _belief_line(b) -> str:
    fv = f' -> believes: "{b.false_value}"' if b.false_value else ""
    return f"- {b.kind.value} `{b.fact_id}`{fv}"


def _era_span(e) -> str:
    if e.year_start is None:
        return "year unset"
    if e.year_end and e.year_end != e.year_start:
        return f"{e.year_start}-{e.year_end}"
    return str(e.year_start)


def _eras_block(eras: list) -> str:
    if not eras:
        return "- (none defined)"
    lines: list[str] = []
    for e in eras:
        place = f", {e.place}" if e.place else ""
        lines.append(f"- **{e.label or e.id}** `{e.id}` ({_era_span(e)}{place})")
        for b in e.capability_baseline:
            lines.append(f"  - {b}")
        if not e.capability_baseline:
            lines.append("  - (no capability baseline set)")
    return "\n".join(lines)


def render_brief(state: BookState) -> str:
    parts = [f"# Brief — {state.meta.title}", "", _checks_banner(state), "## Premise", "",
             state.brief.raw_input or "(none)", "", "## Elements", ""]
    if state.brief.elements:
        for e in state.brief.elements:
            parts.append(f"- **{e.kind}** ({e.provenance.value}): {e.text}")
    else:
        parts.append("(not yet normalized)")
    return "\n".join(parts) + "\n"


def render_world(state: BookState) -> str:
    w = state.authored.world
    anchors = [f"{a.incident}" + (f" ({a.era})" if a.era else "")
               + (f" - {a.relevance}" if a.relevance else "") for a in w.real_anchors]
    units = [f"{u.name} (in {u.parent_org})" + (f" - {u.justification}" if u.justification else "")
             for u in w.invented_units]
    return "\n".join(
        [
            f"# World — {state.meta.title}", "", _checks_banner(state),
            _critique_banner(state, "world"),
            "## Premise", "", w.premise or "(none)", "",
            "## Setting", "", w.setting or "(none)", "",
            "## Plot mechanism", "", w.plot_mechanism or "(none)", "",
            "## Real-world grounding", "",
            "Real organizations used:", _bullets(w.real_organizations), "",
            "Anchored real incidents:", _bullets(anchors), "",
            "Invented units (inside real orgs):", _bullets(units), "",
            "## Timeline / eras", "",
            _eras_block(w.eras), "",
            "## Rules", "", _bullets(w.rules), "",
            "## Factions", "", _bullets(w.factions), "",
            "## Tradecraft", "", _bullets(w.tradecraft), "",
            "## Themes", "", _bullets(w.themes), "",
        ]
    ) + "\n"


def render_cast(state: BookState) -> str:
    parts = [f"# Cast — {state.meta.title}", "", _checks_banner(state),
             _critique_banner(state, "cast")]
    for c in state.authored.characters:
        parts += [f"## {c.name}  `{c.id}`", "", f"- role: {c.role}", f"- provenance: {c.provenance.value}"]
        if c.born is not None:
            parts.append(f"- born: {c.born}")
        if c.backstory:
            parts.append(f"- backstory: {c.backstory}")
        if c.worldview:
            parts.append(f"- worldview: {c.worldview}")
        parts += ["", "Belief states:"]
        parts += [_belief_line(b) for b in c.initial_beliefs] if c.initial_beliefs else ["- (none)"]
        # Per-era belief states (braided timeline): the same person's knowledge by era.
        for era_id, beliefs in c.era_beliefs.items():
            parts += ["", f"Belief states in era `{era_id}`:"]
            parts += [_belief_line(b) for b in beliefs] if beliefs else ["- (none)"]
        parts.append("")
    if not state.authored.characters:
        parts.append("(not yet generated)")
    return "\n".join(parts) + "\n"


def render_ledger(state: BookState) -> str:
    parts = [f"# Ledger — {state.meta.title}", "", _checks_banner(state),
             "Every plot-critical fact, its secrecy tier, and its reveal binding.", "",
             "| id | tier | reader@ | char@ | act | text |",
             "|---|---|---|---|---|---|"]
    for f in state.authored.facts:
        r = f.reveal
        reader = r.reader_reveal_chapter if r and r.reader_reveal_chapter is not None else "-"
        char = r.character_reveal_chapter if r and r.character_reveal_chapter is not None else "-"
        act = r.act_anchor if r and r.act_anchor else "-"
        text = f.text.replace("|", "\\|")
        parts.append(f"| {f.id} | {f.tier.value} | {reader} | {char} | {act} | {text} |")
    if not state.authored.facts:
        parts.append("| (not yet generated) | | | | | |")
    return "\n".join(parts) + "\n"


def render_structure(state: BookState) -> str:
    n = state.authored.narrative
    parts = [f"# Structure — {state.meta.title}", "", _checks_banner(state),
             _critique_banner(state, "structure")]
    # How the story is told.
    parts += ["## Narrative design", ""]
    if n.mode or n.pov_strategy:
        pov = n.pov_strategy + (f" ({n.pov_count} POV)" if n.pov_count else "")
        parts += [f"- mode: {n.mode or '-'}", f"- POV: {pov or '-'}"]
        if n.rationale:
            parts.append(f"- rationale: {n.rationale}")
    else:
        parts.append("(not yet decided)")
    # Tropes in play.
    parts += ["", "## Tropes in play", ""]
    if state.authored.tropes:
        for t in state.authored.tropes:
            tag = " (subverted)" if t.subverted else ""
            parts.append(f"- **{t.name}**{tag}: {t.how_used}")
    else:
        parts.append("- (none selected)")
    parts += ["", f"## Acts ({len(state.authored.acts)})", ""]
    for act in state.authored.acts:
        parts += [f"## Act {act.n}: {act.name}  `{act.id}`", "", act.summary or "(no summary)", ""]
        if act.beat_anchors:
            parts += ["Beats:", _bullets(act.beat_anchors), ""]
    parts += ["## Reveal -> act bindings", ""]
    bound = [f for f in state.authored.facts if f.reveal and f.reveal.act_anchor]
    if bound:
        for f in bound:
            parts.append(f"- `{f.id}` ({f.tier.value}) -> act `{f.reveal.act_anchor}`")
    else:
        parts.append("- (not yet bound)")
    return "\n".join(parts) + "\n"


def render_outline(state: BookState) -> str:
    parts = [f"# Outline — {state.meta.title}", "", _checks_banner(state),
             _critique_banner(state, "outline"),
             "| ch | act | era | when | pov | reader reveals | char reveals | beat | hook |",
             "|---|---|---|---|---|---|---|---|---|"]
    for cb in sorted(state.authored.chapter_outline, key=lambda c: c.n):
        rr = ",".join(cb.reader_reveals) or "-"
        cr = ",".join(cb.character_reveals) or "-"
        beat = (cb.beat or cb.intent).replace("|", "\\|")
        hook = (cb.hook or "-").replace("|", "\\|")
        when = (cb.story_time or "-").replace("|", "\\|")
        parts.append(
            f"| {cb.n} | {cb.act_id or '-'} | {cb.era_id or '-'} | {when} | {cb.pov or '-'} "
            f"| {rr} | {cr} | {beat} | {hook} |"
        )
    if not state.authored.chapter_outline:
        parts.append("| (not yet generated) | | | | | |")
    # The asymmetry, spelled out.
    parts += ["", "## Information asymmetry (reader vs POV)", ""]
    gaps = [f for f in state.authored.facts
            if f.reveal and f.reveal.reader_reveal_chapter is not None
            and f.reveal.character_reveal_chapter is not None]
    if gaps:
        for f in gaps:
            r = f.reveal
            gap = r.character_reveal_chapter - r.reader_reveal_chapter
            parts.append(
                f"- `{f.id}`: reader at ch{r.reader_reveal_chapter}, "
                f"POV at ch{r.character_reveal_chapter} (gap {gap})"
            )
    else:
        parts.append("- (no scheduled reveals yet)")
    return "\n".join(parts) + "\n"


def render_timeline(state: BookState) -> str:
    """The two clocks side by side: chapters in STORY order (grouped by era) and
    in READING order. For a braided timeline this is the artifact that shows the
    interleave at a glance and surfaces a thread that jumps around incoherently."""
    parts = [f"# Timeline — {state.meta.title}", "", _checks_banner(state)]
    eras = state.authored.world.eras
    outline = state.authored.chapter_outline
    if not eras:
        parts.append("(no eras defined; single-period story or not yet generated)")
        return "\n".join(parts) + "\n"

    parts += ["## Eras", "", _eras_block(eras), ""]
    if not outline:
        parts.append("(no chapter outline yet)")
        return "\n".join(parts) + "\n"

    def era_year(cb) -> int:
        e = state.era(cb.era_id)
        return e.year_start if e and e.year_start is not None else 0

    parts += ["## Chapters in story order", "",
              "| era | when | ch (printed at) | beat |", "|---|---|---|---|"]
    for cb in sorted(outline, key=lambda c: (era_year(c), c.n)):
        beat = (cb.beat or cb.intent).replace("|", "\\|")
        when = (cb.story_time or "-").replace("|", "\\|")
        parts.append(f"| {cb.era_id or '-'} | {when} | {cb.n} | {beat} |")

    parts += ["", "## Chapters in reading order", "",
              "| ch | era | when | beat |", "|---|---|---|---|"]
    for cb in sorted(outline, key=lambda c: c.n):
        beat = (cb.beat or cb.intent).replace("|", "\\|")
        when = (cb.story_time or "-").replace("|", "\\|")
        parts.append(f"| {cb.n} | {cb.era_id or '-'} | {when} | {beat} |")
    return "\n".join(parts) + "\n"


def render_dossier(state: BookState) -> str:
    """Index of the character dossiers, with each file's redactions shown against
    the ledger fact they seal (the reveal each black bar hides)."""
    fact = {f.id: f for f in state.authored.facts}
    parts = [f"# Dossiers — {state.meta.title}", "", _checks_banner(state),
             "One classified file per principal. The `sealed` redactions are bound to the "
             "secret ledger: each black bar hides a real reveal.", ""]
    if not state.authored.dossiers:
        parts.append("(not yet generated)")
        return "\n".join(parts) + "\n"
    for d in state.authored.dossiers:
        parts += [f"## {d.name}  ·  `{d.codename}`  ·  stamp: {d.stamp}", "",
                  f"- file: {d.fileno}  ·  subject: `{d.character_id}`"]
        if d.appearance:
            parts.append(f"- appearance: {d.appearance}")
        if d.pdf_path:
            parts.append(f"- pdf: {d.pdf_path}")
        if d.spread_path:
            parts.append(f"- spread: {d.spread_path}")
        parts += ["", "Redactions (sealed → the reveal it hides):"]
        if d.sealed:
            for lab, fid in d.sealed:
                f = fact.get(fid)
                tier = f.tier.value if f else "?"
                rc = f.reveal.reader_reveal_chapter if f and f.reveal else None
                cc = f.reveal.character_reveal_chapter if f and f.reveal else None
                when = f" (reader ch{rc} / subject ch{cc})" if rc or cc else ""
                txt = (f.text if f else "(unknown fact)").replace("\n", " ")
                parts.append(f"- **{lab}** [`{fid}` · {tier}]{when} → {txt}")
        else:
            parts.append("- (none)")
        parts.append("")
    return "\n".join(parts) + "\n"


# stage -> list of (filename, render fn)
_STAGE_FILES = {
    STAGE_NORMALIZE: [("brief.md", render_brief)],
    STAGE_WORLD: [("world.md", render_world), ("ledger.md", render_ledger)],
    STAGE_CAST: [("cast.md", render_cast)],
    STAGE_STRUCTURE: [("structure.md", render_structure)],
    STAGE_OUTLINE: [("outline.md", render_outline), ("timeline.md", render_timeline)],
    STAGE_DOSSIER: [("dossiers.md", render_dossier)],
}


def render_stage(project: NovelProject, state: BookState, stage: str) -> list[str]:
    """Write the markdown file(s) for one stage. Returns the paths written."""
    out_dir = project.stage_dir(stage)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, fn in _STAGE_FILES[stage]:
        path = out_dir / filename
        path.write_text(fn(state), encoding="utf-8")
        written.append(str(path))
    return written


def render_all(project: NovelProject, state: BookState | None = None) -> list[str]:
    """Re-render every stage's markdown from the current state. Call after any
    edit (chat, markdown, or JSON) to reconverge the review surface with the JSON."""
    state = state or project.load()
    written = []
    for stage in _STAGE_FILES:
        written += render_stage(project, state, stage)
    return written
