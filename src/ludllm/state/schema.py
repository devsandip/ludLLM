"""The book state: one recoverable object that is the single source of truth.

The load-bearing design decision is the split between AUTHORED INTENT (produced
by the setup stages, gate-frozen once approved) and EXTRACTED RUNNING STATE
(mutated by the Stage 5 extract step every chapter, never re-triggers a gate).
See docs/architecture.md.

Relationship of belief state to the split: a character carries `initial_beliefs`
(authored intent). The chapter loop appends `BeliefUpdate`s to the running state.
Effective knowledge at chapter N is the initial set overlaid with every update up
to N. That is what lets extract run without invalidating a frozen gate.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #

class Provenance(str, Enum):
    """Where an element came from. The normalizer (Stage 0) tags every element."""

    user_locked = "user_locked"  # user supplied; never overwrite
    user_seed = "user_seed"      # user supplied; may elaborate
    invented = "invented"        # system-generated


class SecrecyTier(str, Enum):
    """How a plot-critical fact is held. From the primer's knowledge inventory."""

    public = "public"                    # known freely
    hidden = "hidden"                    # active secret
    delayed = "delayed"                  # will surface on schedule
    never_explicit = "never_explicit"    # hinted, never stated outright


class KnowledgeKind(str, Enum):
    """A character's epistemic relation to a fact."""

    knows = "knows"
    does_not_know = "does_not_know"
    falsely_believes = "falsely_believes"


class RevelationMode(str, Enum):
    slow_burn = "slow_burn"          # mystery, reveals paced out
    immediate_action = "immediate_action"
    mixed = "mixed"


class CritiqueMode(str, Enum):
    """How a stage's dimensional critique acts on its verdict.

    The critique is a coverage panel (one cross-family critic per rubric
    dimension) that informs the human gate. The mode decides what happens after:
    """

    advisory_only = "advisory_only"  # score + render; the human decides
    auto_revise = "auto_revise"      # if not 'ship', regenerate once with the notes, then re-critique
    blocking = "blocking"            # a 'regenerate' verdict blocks the freeze until resolved


# --------------------------------------------------------------------------- #
# Genre profile (pluggable config the plot-agnostic stages consume)
# --------------------------------------------------------------------------- #

class GenreProfile(BaseModel):
    genre: str = "spy_thriller"
    revelation_mode: RevelationMode = RevelationMode.slow_burn
    default_acts: int = 4
    target_words: int = 130_000
    words_per_chapter: int = 3_000
    cliffhanger_rate: float = 0.5  # fraction of chapters ending on a turn

    @property
    def estimated_chapters(self) -> int:
        return max(1, round(self.target_words / self.words_per_chapter))


# --------------------------------------------------------------------------- #
# Reveal: authored once as intent, bound progressively across stages
# --------------------------------------------------------------------------- #

class RevealPlan(BaseModel):
    """A reveal's binding, filled in over the stages. Never re-invented downstream.

    Stage 1 authors `order` as intent. Stage 3 (structure) sets `act_anchor`.
    Stage 4 (outline) sets the chapter fields. The reader-reveal and
    character-reveal chapters differ on purpose: that gap is the information
    asymmetry the whole system exists to control.
    """

    order: int | None = None                     # Stage 1: relative ordering (intent)
    act_anchor: str | None = None                # Stage 3: act/beat id
    reader_reveal_chapter: int | None = None     # Stage 4: when the reader learns
    character_reveal_chapter: int | None = None  # Stage 4: when the protagonist learns
    clue_ids: list[str] = Field(default_factory=list)  # ambiguous clues planted before


# --------------------------------------------------------------------------- #
# AUTHORED INTENT shapes
# --------------------------------------------------------------------------- #

class Fact(BaseModel):
    """A ledger item: one plot-critical fact + its tier + its reveal plan.

    Authored intent. The *truth* of the world. `public` facts carry no reveal.
    """

    id: str
    text: str                                    # the true statement
    tier: SecrecyTier
    provenance: Provenance = Provenance.invented
    reveal: RevealPlan | None = None             # None iff public
    era_id: str | None = None                    # which timeline it belongs to (None = spans/timeless)
    notes: str = ""

    @model_validator(mode="after")
    def _reveal_consistency(self) -> Fact:
        if self.tier == SecrecyTier.public and self.reveal is not None:
            raise ValueError(f"public fact {self.id!r} must not carry a reveal plan")
        if self.tier != SecrecyTier.public and self.reveal is None:
            self.reveal = RevealPlan()  # secret facts always have a (possibly empty) plan
        return self


class Belief(BaseModel):
    """One edge of the knowledge graph: a character's relation to a fact.

    The canonical home for knowledge edges is the character (not the fact), so
    there is exactly one writer per edge. `who_knows` derives the reverse by scan.
    """

    fact_id: str
    kind: KnowledgeKind
    false_value: str | None = None  # required iff kind == falsely_believes

    @model_validator(mode="after")
    def _false_value_consistency(self) -> Belief:
        if self.kind == KnowledgeKind.falsely_believes and not self.false_value:
            raise ValueError(f"falsely_believes about {self.fact_id!r} needs a false_value")
        if self.kind != KnowledgeKind.falsely_believes and self.false_value is not None:
            raise ValueError(f"false_value only valid with falsely_believes ({self.fact_id!r})")
        return self


class Character(BaseModel):
    id: str
    name: str
    provenance: Provenance = Provenance.invented
    role: str = ""
    backstory: str = ""
    worldview: str = ""
    born: int | None = None                                      # birth year, for age sanity across eras
    initial_beliefs: list[Belief] = Field(default_factory=list)  # authored starting state (earliest appearance)
    # Per-era authored knowledge for a braided timeline: the character's belief
    # state at the START of each era, keyed by era id. Overlays initial_beliefs.
    # Empty for a single-era book. This is how the same person knows different
    # things in 1961 and 1991 without one bleeding into the other.
    era_beliefs: dict[str, list[Belief]] = Field(default_factory=dict)


class Thread(BaseModel):
    id: str
    name: str
    description: str = ""


class Act(BaseModel):
    id: str
    n: int
    name: str = ""
    summary: str = ""
    beat_anchors: list[str] = Field(default_factory=list)  # the finer 15-beat layer


class RealAnchor(BaseModel):
    """A real historical or contemporary event the story is anchored to, so the
    fiction sits in a world the reader recognizes (Forsyth's false-document
    technique). The rule is to anchor to EVENTS; never put invented words, crimes,
    or conspiracies in the mouths of real, identifiable living people."""

    incident: str            # e.g. "the 1991 assassination of Rajiv Gandhi"
    era: str = ""            # when it happened / the story's relation to it
    relevance: str = ""      # how it touches the plot


class InventedUnit(BaseModel):
    """A fictional clandestine unit/desk placed inside a REAL organization. Allowed
    only when no real unit closely matches; otherwise the real one must be used."""

    name: str
    parent_org: str          # a real organization (CIA, RAW, MI6, Mossad, ISI, ...)
    justification: str = ""  # why this is invented rather than a real unit


class Era(BaseModel):
    """A time period the book operates in. A single-period book has one era; a
    dual-timeline book has two or more, braided across chapters.

    Each era carries a CAPABILITY BASELINE: the dated technological, forensic,
    communications, and geopolitical facts that bound what can plausibly happen in
    it. LLMs have a weak grip on chronology (nukes before the test, DNA testing
    before it existed, mobile phones in the 1960s), so the year alone is not
    enough. The baseline is stated once here, reviewed at the gate, and fed into
    every chapter set in this era, which turns anachronism from a per-chapter
    recall problem (unreliable) into a grounding problem (the system's specialty):
    prevented at generation time, then double-checked deterministically and by a
    cross-family critic.
    """

    id: str                                    # e_snake
    label: str = ""                            # human label, e.g. "present, Vienna 1991"
    year_start: int | None = None              # absolute anchor; None only if deliberately vague
    year_end: int | None = None                # for a span; None means a single year (== year_start)
    place: str = ""                            # primary locale(s) for the era
    # What IS available and true in this era (comms, forensics, computing, weapons,
    # surveillance, geopolitics, and period naming), stated positively, plus the
    # hard nos. This is the anti-anachronism payload.
    capability_baseline: list[str] = Field(default_factory=list)
    notes: str = ""

    @property
    def year(self) -> int | None:
        return self.year_start

    @model_validator(mode="after")
    def _span_ok(self) -> Era:
        if (
            self.year_start is not None
            and self.year_end is not None
            and self.year_end < self.year_start
        ):
            raise ValueError(f"era {self.id!r}: year_end {self.year_end} precedes year_start {self.year_start}")
        return self


class World(BaseModel):
    premise: str = ""
    setting: str = ""
    rules: list[str] = Field(default_factory=list)
    factions: list[str] = Field(default_factory=list)
    tradecraft: list[str] = Field(default_factory=list)
    plot_mechanism: str = ""  # the fully-worked-out engine, authored in Stage 1
    themes: list[str] = Field(default_factory=list)
    # Real-world grounding (Forsyth's false-document technique). Authored in Stage 1.
    real_anchors: list[RealAnchor] = Field(default_factory=list)
    real_organizations: list[str] = Field(default_factory=list)   # real names used verbatim
    invented_units: list[InventedUnit] = Field(default_factory=list)
    # The time period(s) the book operates in, each with a capability baseline.
    # One era for a single-period book; two or more braided for a dual timeline.
    eras: list[Era] = Field(default_factory=list)

    @model_validator(mode="after")
    def _eras_orderable(self) -> World:
        # A braided timeline orders knowledge by era year, so every era must be
        # anchored or a deliberately-vague era would sort to year 0 and invert the
        # timeline. A single era may stay year-less (it reduces to chapter order).
        if len(self.eras) >= 2:
            missing = [e.id for e in self.eras if e.year_start is None]
            if missing:
                raise ValueError(
                    "a braided timeline (2+ eras) needs an anchored year_start on every era "
                    f"so knowledge orders in story time; missing on: {missing}"
                )
        return self


class NarrativeDesign(BaseModel):
    """How the story is TOLD, decided explicitly at the structure stage and
    reviewed. Distinct from the acts (what happens): POV count and time-handling
    change which scenes are even possible, so they are an authored, gated choice
    rather than an accident of drafting."""

    mode: str = ""          # linear | in_medias_res | framed_retrospective | dual_timeline | parallel_tracks
    pov_strategy: str = ""  # single | dual | ensemble
    pov_count: int | None = None
    rationale: str = ""     # why this serves THIS story's secret and asymmetry
    era_ids: list[str] = Field(default_factory=list)  # the eras this design braids (>=2 for a dual timeline)
    interleave: str = ""    # how the eras are braided across chapters (when multi-era)


class TropeUse(BaseModel):
    """A spy-genre trope deliberately put in play, and whether it is used straight
    or subverted. Chosen to serve the secret, never pulled at random; the craft is
    in the intentional selection and the inversion."""

    name: str
    how_used: str = ""
    subverted: bool = False


class ChapterBeat(BaseModel):
    """A chapter's authored outline (Stage 4). What *should* happen, pre-draft."""

    n: int
    act_id: str | None = None
    era_id: str | None = None                    # which timeline this chapter sits in (multi-era books)
    story_time: str = ""                         # in-story date or relative marker ("March 1991", "+3 days")
    pov: str | None = None                       # character id
    present: list[str] = Field(default_factory=list)   # character ids on stage
    threads: list[str] = Field(default_factory=list)   # thread ids advanced
    beat: str = ""                               # the turning point / change delivered
    intent: str = ""                             # prose-free summary of the chapter
    hook: str = ""                               # the final pull into the next chapter (turn/reversal/threat/question/clock)
    reader_reveals: list[str] = Field(default_factory=list)     # fact ids surfaced to reader
    character_reveals: list[str] = Field(default_factory=list)  # fact ids the POV learns


class Dossier(BaseModel):
    """A character's intelligence dossier (the stage between outline and the
    writer). Derived from the cast and the secret ledger so its redactions
    coincide with the novel's reveals: each `sealed` entry blacks out a real fact
    the file is not cleared to show. This holds the authored content; the
    image/PDF artifacts are composed from it by the dossier stage."""

    character_id: str
    name: str = ""
    codename: str = ""
    fileno: str = ""
    stamp: str = "CLASSIFIED"                                   # the big diagonal status stamp
    appearance: str = ""                                        # photographic look fed to the portrait generator
    photocap: str = "SURVEILLANCE"
    cover_rows: list[list[str]] = Field(default_factory=list)   # [label, value] identity fields
    redacted_cover: list[str] = Field(default_factory=list)     # cover labels whose value is blacked out
    sections: list[list[str]] = Field(default_factory=list)     # [title, body] background / assessment
    sealed: list[list[str]] = Field(default_factory=list)       # [label, fact_id] redactions bound to the ledger
    associates: list[str] = Field(default_factory=list)
    training: str = ""
    capabilities: str = ""
    oplog: list[str] = Field(default_factory=list)
    oplog_sealed_label: str = ""
    threat: str = ""
    threat_detail: str = ""
    standing_orders: str = ""
    authoriser: str = ""
    pdf_path: str = ""                                          # artifact paths, filled when composed
    spread_path: str = ""


class Authored(BaseModel):
    """Gate-frozen intent. Produced by the setup stages (world, cast, structure,
    outline) and frozen on approval."""

    world: World = Field(default_factory=World)               # Stage 1 (world)
    facts: list[Fact] = Field(default_factory=list)          # Stage 1: the reveal ledger
    threads: list[Thread] = Field(default_factory=list)      # Stage 1
    characters: list[Character] = Field(default_factory=list)  # Stage 2 (cast): roster + belief states
    narrative: NarrativeDesign = Field(default_factory=NarrativeDesign)  # Stage 3 (structure)
    tropes: list[TropeUse] = Field(default_factory=list)     # Stage 3 (structure)
    acts: list[Act] = Field(default_factory=list)            # Stage 3 (structure)
    dossiers: list[Dossier] = Field(default_factory=list)    # dossier stage (between outline and the writer)
    chapter_outline: list[ChapterBeat] = Field(default_factory=list)  # Stage 4 (outline)


# --------------------------------------------------------------------------- #
# EXTRACTED RUNNING STATE shapes (mutated by the Stage 5 loop)
# --------------------------------------------------------------------------- #

class BeliefUpdate(BaseModel):
    """Appended by extract when the prose changes what a character knows."""

    chapter: int
    character_id: str
    fact_id: str
    kind: KnowledgeKind
    false_value: str | None = None


class ChapterStatus(str, Enum):
    planned = "planned"
    drafted = "drafted"
    critiqued = "critiqued"
    accepted = "accepted"


class ChapterState(BaseModel):
    """The running record of one chapter as it moves through the loop."""

    n: int
    status: ChapterStatus = ChapterStatus.planned
    draft_path: str | None = None                # prose lives on disk, not in state
    rolling_summary: str = ""                     # appended/updated by extract
    established_fact_ids: list[str] = Field(default_factory=list)
    word_count: int | None = None
    critique_flags: list[str] = Field(default_factory=list)
    anachronism_flags: list[str] = Field(default_factory=list)  # period terms the scan caught (advisory)
    revise_iterations: int = 0


class Running(BaseModel):
    """Mutable extracted state. Never re-triggers a setup gate."""

    chapters: list[ChapterState] = Field(default_factory=list)
    belief_updates: list[BeliefUpdate] = Field(default_factory=list)
    rolling_summary: str = ""


# --------------------------------------------------------------------------- #
# Creative brief (Stage 0 output) and project meta
# --------------------------------------------------------------------------- #

class BriefElement(BaseModel):
    """A normalized input element with provenance, so the writer never
    overwrites something the user locked."""

    kind: str            # "character" | "secret" | "setting" | "premise" | ...
    text: str
    provenance: Provenance


class CreativeBrief(BaseModel):
    raw_input: str = ""
    elements: list[BriefElement] = Field(default_factory=list)


class ProjectMeta(BaseModel):
    title: str = "Untitled"
    schema_version: int = 1
    frozen_stages: list[str] = Field(default_factory=list)  # gate tracking


# --------------------------------------------------------------------------- #
# Critique: the dimensional coverage panel (advisory, informs the human gate)
# --------------------------------------------------------------------------- #

class DimensionScore(BaseModel):
    """One critic's verdict on one dimension. The number is the least important
    field; the evidence and the concrete fix are the value."""

    dimension: str
    score: int                       # 1 broken, 2 weak, 3 competent, 4 strong, 5 exceptional
    evidence: str = ""               # the specific element/line that earned the score
    fix: str = ""                    # one concrete, actionable change


class StageCritique(BaseModel):
    """A stage's coverage report: one DimensionScore per rubric dimension, plus a
    deterministically-derived verdict and the single highest-leverage fix."""

    stage: str
    mode: CritiqueMode = CritiqueMode.advisory_only
    scores: list[DimensionScore] = Field(default_factory=list)
    verdict: str = "ship"            # ship | tighten | regenerate (derived from the lowest score)
    top_fix: str = ""                # the weakest dimension's fix
    revised: bool = False            # True if an auto_revise pass regenerated the stage
    revise_passes: int = 0           # how many auto_revise regenerations actually ran

    @property
    def min_score(self) -> int:
        return min((s.score for s in self.scores), default=5)


# --------------------------------------------------------------------------- #
# BookState: the single source of truth
# --------------------------------------------------------------------------- #

class BookState(BaseModel):
    meta: ProjectMeta = Field(default_factory=ProjectMeta)
    genre: GenreProfile = Field(default_factory=GenreProfile)
    brief: CreativeBrief = Field(default_factory=CreativeBrief)
    authored: Authored = Field(default_factory=Authored)
    running: Running = Field(default_factory=Running)
    # Latest dimensional critique per stage (and per chapter, keyed "chapter_<n>").
    # Advisory: it informs the human gate, it does not freeze or mutate authored intent.
    reviews: dict[str, StageCritique] = Field(default_factory=dict)

    # ----- lookups ----- #

    def character(self, character_id: str) -> Character | None:
        return next((c for c in self.authored.characters if c.id == character_id), None)

    def fact(self, fact_id: str) -> Fact | None:
        return next((f for f in self.authored.facts if f.id == fact_id), None)

    def era(self, era_id: str | None) -> Era | None:
        if not era_id:
            return None
        return next((e for e in self.authored.world.eras if e.id == era_id), None)

    def chapter_beat(self, n: int) -> ChapterBeat:
        beat = next((cb for cb in self.authored.chapter_outline if cb.n == n), None)
        if beat is None:
            raise ValueError(f"no chapter outline for chapter {n}")
        return beat

    def chapter_era(self, n: int) -> Era | None:
        """The era a chapter is set in, via its outline beat (None for single-era
        or unbound chapters)."""
        beat = next((cb for cb in self.authored.chapter_outline if cb.n == n), None)
        return self.era(beat.era_id) if beat else None

    # ----- story time vs narrative time ----- #

    def _resolve_era_id(self, n: int) -> str | None:
        """The era id governing chapter `n`: its own beat's era_id when set and
        valid; otherwise (a query point past the outline, or an unbound chapter)
        the era of the nearest preceding outlined chapter that resolves to a real
        era. Used by BOTH the ordering and the per-era belief base so they cannot
        disagree about which era a chapter belongs to."""
        beat = next((cb for cb in self.authored.chapter_outline if cb.n == n), None)
        if beat and beat.era_id and self.era(beat.era_id) is not None:
            return beat.era_id
        prior = [
            cb for cb in self.authored.chapter_outline
            if cb.n <= n and cb.era_id and self.era(cb.era_id) is not None
        ]
        if prior:
            return max(prior, key=lambda cb: cb.n).era_id
        return None

    def _era_ordinal(self, era_id: str | None) -> int:
        """A stable index of an era within world.eras, the tiebreak that keeps two
        same-year eras (parallel tracks) from collapsing to print order."""
        for i, e in enumerate(self.authored.world.eras):
            if e.id == era_id:
                return i
        return 0

    def _chapter_era_year(self, n: int) -> int | None:
        """The era year governing chapter `n`, for story-time ordering. None when
        the book has no eras (legacy chapter-order behavior). A single era is
        unambiguous for every chapter; with several eras (all anchored, enforced
        by World) an unresolved query point inherits the nearest preceding era."""
        eras = self.authored.world.eras
        if not eras:
            return None
        if len(eras) == 1:
            return eras[0].year_start
        era = self.era(self._resolve_era_id(n))
        return era.year_start if era and era.year_start is not None else 0

    def _story_rank(self, n: int) -> tuple[int, int, int]:
        """A sortable (era_year, era_ordinal, chapter_index) key that orders events
        in STORY time rather than narrative (reading) order.

        Knowledge accrues in story time, not in the order chapters are printed.
        For a single-era or no-era book every chapter shares the year and ordinal,
        so this reduces to chapter order = the legacy behavior. For a braided
        timeline it orders by era first (year, then a stable ordinal so same-year
        parallel tracks stay isolated), so a past-thread chapter never sees what a
        later-narrated present-thread chapter revealed.
        """
        year = self._chapter_era_year(n)
        era_id = self._resolve_era_id(n) if self.authored.world.eras else None
        return (year if year is not None else 0, self._era_ordinal(era_id), n)

    # ----- the knowledge graph, computed (intent + running overlay) ----- #

    def effective_beliefs(self, character_id: str, chapter: int) -> dict[str, Belief]:
        """A character's knowledge at the START of `chapter`.

        The authored base (initial_beliefs, then any era-specific override for the
        chapter's era) overlaid with every belief update that happened EARLIER in
        story time. Story time, not narrative order: in a braided timeline a
        1961 chapter must not inherit what the same character learned in a 1991
        chapter that was printed earlier. For a single-era book story rank reduces
        to chapter order, so this matches the original chapter-index behavior.
        """
        char = self.character(character_id)
        beliefs: dict[str, Belief] = {}
        if char:
            for b in char.initial_beliefs:
                beliefs[b.fact_id] = b
            # Per-era authored override: the character's knowledge at the start of
            # the era this chapter sits in (braided timelines only). Resolved the
            # same way as the ordering, so a post-outline query keeps the base.
            era_id = self._resolve_era_id(chapter)
            if era_id and era_id in char.era_beliefs:
                for b in char.era_beliefs[era_id]:
                    beliefs[b.fact_id] = b
        cur_rank = self._story_rank(chapter)
        updates = sorted(
            (u for u in self.running.belief_updates
             if u.character_id == character_id and self._story_rank(u.chapter) < cur_rank),
            key=lambda u: self._story_rank(u.chapter),
        )
        for u in updates:
            beliefs[u.fact_id] = Belief(
                fact_id=u.fact_id, kind=u.kind, false_value=u.false_value
            )
        return beliefs

    def character_known_facts(self, character_id: str, chapter: int) -> list[Fact]:
        """Facts this character actually knows (kind == knows) entering `chapter`."""
        beliefs = self.effective_beliefs(character_id, chapter)
        known = [fid for fid, b in beliefs.items() if b.kind == KnowledgeKind.knows]
        return [f for f in self.authored.facts if f.id in known]

    def who_knows(self, fact_id: str, chapter: int) -> list[str]:
        """Reverse edge, derived by scan: character ids that know `fact_id`."""
        out = []
        for c in self.authored.characters:
            b = self.effective_beliefs(c.id, chapter).get(fact_id)
            if b and b.kind == KnowledgeKind.knows:
                out.append(c.id)
        return out

    def reader_known_facts(self, chapter: int) -> list[Fact]:
        """Facts the READER has learned by the start of `chapter`.

        Public facts are always known. A secret is reader-known once its
        reader_reveal_chapter has passed.
        """
        out = []
        for f in self.authored.facts:
            if f.tier == SecrecyTier.public:
                out.append(f)
            elif f.reveal and f.reveal.reader_reveal_chapter is not None:
                if f.reveal.reader_reveal_chapter < chapter:
                    out.append(f)
        return out

    def revealed_in_chapter(self, chapter: int) -> list[Fact]:
        """Facts whose scheduled reveal (to reader or to the POV) lands IN this
        chapter. The drafter must be allowed these: you cannot write the discovery
        scene without the fact being discovered.
        """
        out = []
        for f in self.authored.facts:
            if f.reveal and chapter in (
                f.reveal.reader_reveal_chapter,
                f.reveal.character_reveal_chapter,
            ):
                out.append(f)
        return out

    def drafter_allowed_facts(self, pov_id: str, chapter: int) -> list[Fact]:
        """The facts the Stage 5 drafter is permitted to see for a POV scene:
        what the POV knows, plus what the reader already knows, plus whatever is
        being revealed in this very chapter."""
        ids = {f.id for f in self.character_known_facts(pov_id, chapter)}
        ids |= {f.id for f in self.reader_known_facts(chapter)}
        ids |= {f.id for f in self.revealed_in_chapter(chapter)}
        return [f for f in self.authored.facts if f.id in ids]

    def forbidden_for_drafter(self, pov_id: str, chapter: int) -> list[Fact]:
        """Facts the Stage 5 drafter must be PHYSICALLY denied for a POV scene:
        the complement of `drafter_allowed_facts`.

        This is the data behind the triple-layer scoped context. The drafter is
        fed only the allowed set, so a leak is prevented at generation time
        rather than caught afterward.
        """
        allowed_ids = {f.id for f in self.drafter_allowed_facts(pov_id, chapter)}
        return [f for f in self.authored.facts if f.id not in allowed_ids]
