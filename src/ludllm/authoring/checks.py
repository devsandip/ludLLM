"""Deterministic pre-checks on a BookState. These catch the consistency errors a
human shouldn't have to hunt for, so review can focus on story judgment. Run
before rendering and print the results at the top of each stage's markdown.

These are SEMANTIC, cross-field checks Pydantic does not enforce (it validates a
single object, not references between them). A clean result is not approval; it
just means nothing is structurally broken.
"""

from __future__ import annotations

import re

from ludllm.state.schema import BookState, KnowledgeKind, SecrecyTier

# A 4-digit year in the plausible band for these stories, pulled from free-text
# story_time ("March 1991") to sanity-check it against the chapter's era.
_YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")


def _belief_scopes(c) -> list[tuple[str, list]]:
    """Every authored belief set on a character: the universal initial set (scope
    "") plus each per-era set. So the same checks cover single-era and braided
    timelines without duplication."""
    scopes: list[tuple[str, list]] = [("", c.initial_beliefs)]
    scopes += list(c.era_beliefs.items())
    return scopes


def check_state(state: BookState) -> list[str]:
    issues: list[str] = []
    a = state.authored
    fact_ids = {f.id for f in a.facts}
    char_ids = {c.id for c in a.characters}
    act_ids = {act.id for act in a.acts}
    thread_ids = {t.id for t in a.threads}
    era_ids = {e.id for e in a.world.eras}

    # Real-world grounding: once the world is generated, expect 3+ real anchors
    # and at least one real organization (Forsyth's false-document technique).
    w = a.world
    if w.premise:
        if len(w.real_anchors) < 3:
            issues.append(
                f"world anchors to {len(w.real_anchors)} real incident(s); aim for 3+ "
                "recognizable events (confirm if intended)"
            )
        if not w.real_organizations:
            issues.append("world names no real organizations; real names are preferred over invented ones")
        if not w.eras:
            issues.append(
                "world defines no eras; without an anchored period the anachronism guard "
                "is blind (set at least one era with a year and a capability baseline)"
            )

    # Temporal spine: each era needs an anchor year and a capability baseline, and
    # a braided timeline (2+ eras) should declare a braided narrative mode.
    for e in w.eras:
        if e.year_start is None:
            issues.append(f"era '{e.id}' has no anchor year; the anachronism guard cannot check it")
        if not e.capability_baseline:
            issues.append(f"era '{e.id}' has no capability baseline; period accuracy is unconstrained for it")
    mode = a.narrative.mode
    if len(w.eras) >= 2 and mode and mode not in ("dual_timeline", "parallel_tracks"):
        issues.append(
            f"{len(w.eras)} eras defined but narrative mode is '{mode}'; a braided "
            "timeline expects dual_timeline or parallel_tracks"
        )

    # Facts may name the era they belong to; if they do, it must be a real one.
    for f in a.facts:
        if f.era_id and f.era_id not in era_ids:
            issues.append(f"fact '{f.id}' era_id '{f.era_id}' is not a known era")

    # Beliefs (initial and per-era) must point at real facts and real eras; a false
    # belief must be about a secret.
    for c in a.characters:
        for scope, beliefs in _belief_scopes(c):
            where = f" (era {scope})" if scope else ""
            if scope and scope not in era_ids:
                issues.append(f"character '{c.id}' has beliefs for unknown era '{scope}'")
            for b in beliefs:
                if b.fact_id not in fact_ids:
                    issues.append(f"character '{c.id}' believes about unknown fact '{b.fact_id}'{where}")
                    continue
                if b.kind == KnowledgeKind.falsely_believes:
                    fact = state.fact(b.fact_id)
                    if fact and fact.tier == SecrecyTier.public:
                        issues.append(
                            f"character '{c.id}' falsely believes public fact '{b.fact_id}'{where}; "
                            "a false belief must be about a secret"
                        )

    # Once the outline exists, every false belief needs a scheduled correction (the
    # reveal of the fact it concerns) - otherwise it is a loose thread (the belief
    # never gets put right). This couples falsely_believes to the reveal schedule.
    if a.chapter_outline:
        for c in a.characters:
            for scope, beliefs in _belief_scopes(c):
                where = f" (era {scope})" if scope else ""
                for b in beliefs:
                    if b.kind != KnowledgeKind.falsely_believes:
                        continue
                    fact = state.fact(b.fact_id)
                    # never_explicit truths are circled, never stated, so they need
                    # no scheduled on-page correction - exempt them, like the
                    # reader-reveal check below does.
                    if fact and fact.tier not in (SecrecyTier.hidden, SecrecyTier.delayed):
                        continue
                    if fact and (fact.reveal is None or fact.reveal.character_reveal_chapter is None):
                        issues.append(
                            f"character '{c.id}' falsely believes '{b.fact_id}'{where} but it has no "
                            "scheduled correction (no character-reveal chapter) - a loose thread"
                        )

    # Reveal bindings.
    for f in a.facts:
        r = f.reveal
        if r is None:
            continue
        if r.act_anchor is not None and act_ids and r.act_anchor not in act_ids:
            issues.append(f"fact '{f.id}' reveal act_anchor '{r.act_anchor}' is not a known act")
        if r.reader_reveal_chapter is not None and r.character_reveal_chapter is not None:
            if r.reader_reveal_chapter > r.character_reveal_chapter:
                issues.append(
                    f"fact '{f.id}': reader learns (ch{r.reader_reveal_chapter}) AFTER the "
                    f"POV (ch{r.character_reveal_chapter}) — unusual, confirm intended"
                )

    # Once the outline exists, every secret should have a reader-reveal chapter,
    # and any scheduled reveal must point at a chapter that actually exists (an
    # out-of-range reveal silently never fires).
    if a.chapter_outline:
        chapter_ns = {cb.n for cb in a.chapter_outline}
        for f in a.facts:
            if f.tier in (SecrecyTier.hidden, SecrecyTier.delayed) and f.reveal:
                if f.reveal.reader_reveal_chapter is None:
                    issues.append(f"secret '{f.id}' ({f.tier.value}) has no reader-reveal chapter")
            if f.reveal:
                for label, ch in (
                    ("reader", f.reveal.reader_reveal_chapter),
                    ("character", f.reveal.character_reveal_chapter),
                ):
                    if ch is not None and ch not in chapter_ns:
                        issues.append(
                            f"fact '{f.id}' {label}-reveal chapter {ch} is not a chapter in the outline"
                        )

    # Outline integrity.
    seen: set[int] = set()
    for cb in a.chapter_outline:
        if cb.n in seen:
            issues.append(f"duplicate chapter number {cb.n} in outline")
        seen.add(cb.n)
        if cb.pov and cb.pov not in char_ids:
            issues.append(f"chapter {cb.n} pov '{cb.pov}' is not a known character")
        for cid in cb.present:
            if cid not in char_ids:
                issues.append(f"chapter {cb.n} present '{cid}' is not a known character")
        if cb.act_id and act_ids and cb.act_id not in act_ids:
            issues.append(f"chapter {cb.n} act_id '{cb.act_id}' is not a known act")
        for tid in cb.threads:
            if thread_ids and tid not in thread_ids:
                issues.append(f"chapter {cb.n} thread '{tid}' is not a known thread")
        for fid in cb.reader_reveals + cb.character_reveals:
            if fid not in fact_ids:
                issues.append(f"chapter {cb.n} reveals unknown fact '{fid}'")
        # Era assignment: a named era must be real; a braided timeline needs every
        # chapter placed in one (that placement is what orders knowledge in story time).
        if cb.era_id and cb.era_id not in era_ids:
            issues.append(f"chapter {cb.n} era_id '{cb.era_id}' is not a known era")
        elif len(w.eras) >= 2 and not cb.era_id:
            issues.append(f"chapter {cb.n} has no era in a braided timeline; assign one")
        # Best-effort: a 4-digit year in story_time must fall inside its era's window
        # (relative markers like "+3 days" carry no year and are skipped).
        era = state.era(cb.era_id)
        if era is not None and era.year_start is not None and cb.story_time:
            m = _YEAR_RE.search(cb.story_time)
            if m:
                yr = int(m.group(1))
                hi = era.year_end if era.year_end is not None else era.year_start
                if not (era.year_start <= yr <= hi):
                    issues.append(
                        f"chapter {cb.n} story_time '{cb.story_time}' ({yr}) is outside its era "
                        f"'{era.id}' window {era.year_start}-{hi}"
                    )

    # Age sanity: with a birth year and an anchored era, flag an implausible age
    # (a child in the field, a centenarian operative) so a cross-era contradiction
    # surfaces before it reaches the page.
    if a.chapter_outline:
        born = {c.id: c.born for c in a.characters if c.born is not None}
        flagged_age: set[tuple[str, str]] = set()
        for cb in a.chapter_outline:
            era = state.era(cb.era_id)
            if era is None or era.year_start is None:
                continue
            for cid in [cb.pov, *cb.present]:
                if cid in born and (cid, era.id) not in flagged_age:
                    age = era.year_start - born[cid]
                    if age < 12 or age > 100:
                        flagged_age.add((cid, era.id))
                        issues.append(
                            f"character '{cid}' is {age} in era '{era.id}' ({era.year_start}); "
                            "confirm intended"
                        )

    # Per-era beliefs authored for an era the character never appears in are dead
    # intent: effective_beliefs applies an era override only when a chapter sits in
    # that era, so flag the mismatch once the outline pins where people appear.
    if a.chapter_outline:
        appears_in: dict[str, set[str]] = {}
        for cb in a.chapter_outline:
            if not cb.era_id:
                continue
            for cid in [cb.pov, *cb.present]:
                if cid:
                    appears_in.setdefault(cid, set()).add(cb.era_id)
        for c in a.characters:
            for era_id in c.era_beliefs:
                if era_id in era_ids and era_id not in appears_in.get(c.id, set()):
                    issues.append(
                        f"character '{c.id}' has era_beliefs for era '{era_id}' but never appears "
                        "in a chapter placed there - dead intent that is never applied"
                    )

    return issues
