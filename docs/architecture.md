# LudLLM Build Architecture

This is the canonical build plan. It refines the design in [novel-pipeline-primer.md](novel-pipeline-primer.md) into the concrete pipeline and data model we implement. Where the primer describes the idea, this describes how we build it.

Decided 2026-06-20 after a multi-lens evaluation of the staged decomposition against the primer. The evaluation and its reasoning are summarized at the end. Revised 2026-06-20 after building: the cast became its own gated stage (so the pipeline is now six stages), the world stage gained real-world grounding, the structure stage gained an explicit narrative design and a curated trope palette, and a dimensional critique panel was added across the setup stages.

## The pipeline: 6 stages, 5 gates

The primer's monolithic "setup phase" is unbundled into separately-review-gated generators, plus the chapter loop. A human calibrates at each gate. Each gate can be toggled off for unattended pipeline-tuning runs and on for the hero run.

```
Stage 0  NORMALIZE          (automatic, no gate)
  Any input (a logline, OR a full cast with no plot) -> one canonical creative
  brief. Tags every supplied element with provenance: user_locked (never
  overwrite), user_seed (may elaborate), or invented. Surfaces what is implied
  (the secret, the tone, any real-world anchors the writer named). This is what
  lets the same framework accept plot-in-characters-out AND characters-in-plot-out.

Stage 1  WORLD + SECRETS + GROUNDING    (gate)
  World rules, factions, tradecraft. The fully-worked-out plot mechanism (a real
  operation with a method and a fatal vulnerability). The knowledge inventory:
  every plot-critical fact as a discrete item with a secrecy tier (public /
  hidden / delayed / never_explicit). The reveal schedule authored as INTENT
  only: ordering and which-party-learns-when, no chapter numbers yet. Plus the
  real-world grounding (Forsyth's false-document technique): real organizations
  by their real names, 3+ anchored real incidents the plot touches, and any
  invented clandestine unit placed inside a real org with a justification. Plus
  the era timeline: one or more time periods (one for a single-period book, two+
  braided for a dual timeline), each anchored to a year and carrying a CAPABILITY
  BASELINE (the dated tech / forensics / comms / geopolitics that bound what can
  happen in it). The cast is NOT built here.

Stage 2  CAST                (gate)
  The people, as their own gated stage so the roster can be reviewed and
  regenerated independently. Derives the institutional ecosystem the world
  implies, over-generates a role-keyed roster, then winnows to a small
  load-bearing cast. Each character carries backstory, worldview, and an INITIAL
  belief state (knows / does-not-know / falsely-believes) bound to the Stage 1
  facts. Runs after world so the belief edges point at real fact ids.

Stage 3  STRUCTURE           (gate)
  First the narrative design: how the story is TOLD (POV strategy and time mode:
  linear / in_medias_res / framed_retrospective / dual_timeline / parallel_tracks),
  an explicit, reviewable choice because it decides which scenes are possible.
  Then N acts with a finer beat-anchor layer, the tropes deliberately put in play
  (chosen from a curated catalogue under a principled-use + subvert-at-least-one
  rule), and the binding of each reveal to an act anchor. Act count is proposed by
  the model with a rationale and ratified by the human; it is not hard-coded.

Stage 4  CHAPTER OUTLINE      (gate)
  The chapter manifest, honoring the narrative design. Each chapter gets a beat
  (its turn), a hook (its pull into the next), and (in a braided timeline) its era
  and in-story time, so the interleave is explicit. Binds each reveal to a specific
  chapter, splitting the reader-reveal chapter from the character-reveal chapter
  (the asymmetry); in a dual timeline a secret seeded in a past-era chapter is
  revealed in a later-printed present-era chapter, and the gap carries the irony.

Stage 5  WRITER / CHAPTER LOOP    (gate at act boundaries)
  Per chapter: DRAFT (scoped context) -> CRITIQUE (cross-family, Gemini/GPT) ->
  REVISE -> per-chapter acceptance gate -> EXTRACT (write established facts back
  to state on the ACCEPTED prose). This is the entire engine from the primer, not
  a single "write" call.
```

## Two planes

The pipeline is a **control plane** (sequential, human-gated, artifact-producing). It sits on top of a **data plane**: one recoverable `book_state` object that every stage reads and writes slices of. The stages are producers and refiners of slices of one state, never a relay race of frozen documents. This preserves the primer's single-source-of-truth and recoverability.

The crown jewels live in the data/machinery plane and cut across stages. They are named here so the artifact-shaped stage list does not let them fall into a seam:

- **Generation-time no-leak enforcement** (triple-layer scoped context: global / reader / character). The drafter is physically denied forbidden ledger items at draft time. Acceptance check: the blind-reader leak test (hand a non-Claude model chapters 1..N, ask it to name the mole; if it can before the scheduled reveal, the build failed). Lives in Stage 5 drafter input.
- **The closed draft -> critique -> revise -> extract loop with a per-chapter acceptance gate.** Scoped to one chapter, never "finish the book." Lives entirely in Stage 5.
- **The extract step** as a live, continuous write-back to state. Keeps the ledger and belief states current during writing.
- **Per-character belief states including the false-belief field.** Created in Stage 2 (cast), carried through 3 and 4, updated by extract in Stage 5.
- **Cross-family adversarial critique.** Two kinds: the Stage 5 prose critic that flags only blocking faults (leak / logic / grounding / repetition) to drive the revise loop, and the dimensional critique panel over the setup stages (see below). Both must run on a different model family from the author.
- **Real-world grounding.** Real organizations and anchored real incidents authored in Stage 1, kept consistent through the outline and the prose. Anchor to events, never invented words or crimes in the mouths of real, identifiable living people.
- **The temporal spine** (see below). Eras with capability baselines authored in Stage 1, story-time-ordered belief evolution, and a deterministic + cross-family anachronism guard. Keeps chronology fixed instead of re-guessed per chapter.
- **Anti-repetition arsenal**, at minimum motif cooldown and the leak guard.
- **Prompt caching** as non-negotiable infrastructure (the stable bible and ledger are re-read on every pass across ~43 chapters).

## The critique panel: the eval stack

Quality control is three layers, deliberately distinct:

1. **Deterministic checks** (`authoring/checks.py`). Structural and referential errors Pydantic cannot catch across objects: orphan beliefs, unknown act/thread/character/fact/era references, reveal inversions, reveals pointing at non-existent chapters, secrets with no reader-reveal chapter, false beliefs with no scheduled correction, too few real anchors, eras with no year or baseline, implausible ages across eras, a story_time that contradicts its era, dead per-era beliefs. Cheap, exact. The floor that runs before every render.
2. **The dimensional critique panel** (`eval/`). An advisory coverage report on each setup stage. One cross-family critic call PER rubric dimension returns a 1-5 score with specific evidence and one concrete fix. The rubric is per-stage, not a flat list (world is scored on plausibility / grounding / coherence / originality / stakes-theme / period-authenticity; cast on character / plausibility / grounding / originality / coherence; structure on momentum / reveal-craft / coherence / originality / stakes-theme; outline on momentum / reveal-craft / coherence / grounding / period-authenticity; prose on voice-fit / momentum / plausibility / period-authenticity). The verdict (ship / tighten / regenerate) is derived deterministically from the LOWEST dimension, never a composite average that hides the weak spot. It renders as a scorecard on top of the stage markdown.
3. **The Stage 5 prose blocking critic + leak guard.** Must-fix faults only, so the draft -> revise loop converges instead of thrashing on taste.

The panel is **advisory: it informs the human gate, it never replaces it.** "Artistic taste" is decomposed into the parts a model can judge (originality, voice-fit, cliche-detection); the holistic taste verdict stays with the showrunner. Three modes decide what happens to the verdict (the human is asked per stage; default is auto-revise):

- **advisory_only** - score and render; the human decides.
- **auto_revise** - if the verdict is not 'ship', regenerate the stage once with the critique fed back as notes, then re-critique, before the human sees it. Best-effort one pass, then advance.
- **blocking** - a 'regenerate' verdict holds the stage open (it is left unfrozen, not approved), so it will not advance until the human resolves it.

The critique scorecards are stored on `book_state.reviews` (keyed by stage, and by `chapter_<n>` for the prose advisory note). They are advisory metadata: regenerated freely, never gate-frozen, never mutate authored intent.

## State model: authored intent vs running state

The single most important schema decision. The state holds two kinds of content that must not be conflated:

- **Authored intent** (the world + grounding + secret ledger, the cast and their initial belief states, the narrative design + tropes + acts, the chapter outline, the reveal schedule). Produced by the setup stages. Gate-frozen once approved.
- **Extracted running state** (facts the prose actually establishes, belief updates, rolling summaries, chapter status). Mutated by the Stage 5 extract step every chapter. Must NOT re-trigger a gate.

So `BookState` is split into `authored` and `running` (plus `reviews` for the advisory critiques). Belief evolution is modeled as running state: a character carries an `initial_beliefs` set (authored); the loop appends `belief_updates` (running). Effective knowledge at chapter N is the initial set plus updates up to N. This is what lets the extract step run without invalidating a frozen gate.

The reveal schedule is **authored once as intent, then bound progressively**: a single reveal object whose fields fill in over the stages (order -> act_anchor -> reader_reveal_chapter / character_reveal_chapter). The fact's secrecy tier is set at Stage 1 and gates whether a reveal object exists at all (public facts carry none); it is not a phase of the reveal's fill-in. Never re-invented downstream. The setup generators each accept revision `notes`, so a human edit or an auto-revise critique can regenerate a stage with feedback through one path.

## The temporal spine

LLMs have a weak grip on chronology (a nuke before the test, DNA testing before it existed, a mobile phone in the 1960s). The fix mirrors the no-leak design: pin time as a frozen, reviewed constraint and enforce it, rather than trust per-chapter recall. Four layers:

- **Eras with capability baselines** (`World.eras`, authored at Stage 1). Each era anchors to a year (or span) and carries a `capability_baseline`: the dated tech, forensics, comms, weapons, and geopolitics that bound the period, plus its place names. A single-period book has one era; a dual timeline has two or more. A `World` validator requires an anchored year on every era once there are two or more, because the ordering below depends on it.
- **Story-time, not reading-time, knowledge.** Chapters carry `era_id` + `story_time`; facts carry an optional `era_id`. `effective_beliefs` orders belief updates by a story rank `(era_year, era_ordinal, chapter)` instead of raw chapter index, so a past-thread chapter never inherits what a later-printed present-thread chapter revealed, while a past discovery still flows forward into the present thread. Reader reveals stay narrative-ordered (the reader experiences print order); only character knowledge is story-ordered. A single-era or no-era book reduces exactly to the legacy chapter-index behavior. Characters carry per-era authored knowledge (`era_beliefs`) so the same person can know different things in 1961 and 1991 without one bleeding into the other; a shared `_resolve_era_id` keeps the ordering era and the base-selection era in agreement (including for query points past the outline).
- **Prevention at draft time.** The drafter is fed an `ERA` block (year, place, story time, baseline) for its chapter and told to write strictly inside it - the time analogue of feeding it only its allowed facts.
- **Two backstops.** A deterministic term scan (`reference/anachronisms.py`) flags period-wrong prose in both directions (tech ahead of its time; defunct states / superseded place names too late) - high-precision and honestly partial. And a `period_authenticity` critic dimension (cross-family, on world / outline / prose) catches the semantic anachronisms no word list can, each chapter judged against its OWN era.

The braiding pattern itself (which eras, how they interleave) is a `NarrativeDesign` choice at Stage 3; a `timeline.md` render shows chapters in story order vs reading order so the interleave is reviewable at a glance.

## Build order: engine-first (done)

Built against fixtures, hardest part first, in this order:

1. The state schema (the load-bearing piece).
2. The Stage 5 chapter loop with scoped-context no-leak enforcement and the per-chapter acceptance gate, run over hand-authored fixture artifacts.
3. Cross-family critique routing.
4. The upstream generators (the setup stages) and the Stage 0 normalizer.
5. The file-based authoring workflow and the dimensional critique panel on top.

Rationale: the no-leak chapter engine is the only genuinely hard part. Building the pretty setup stages first and bolting them onto an unproven writer is exactly Book-Agent's mistake (beautiful setup, naive writer). The engine and all setup stages were proven on mocks, then validated end to end on real Opus before the critique layer went on.

## Act-count policy

No single standard for spy novels. Three-act is the generic default; **four-act is the default for this system specifically**, because the whole thing pivots on a midpoint information-asymmetry reversal (the mole turn, the false-belief collapse), and four-act is three-act with Act 2 split at exactly that midpoint, giving the pivot its own structural home instead of a baggy Act 2 that sags over 130k words. Forsyth's Day of the Jackal (closest scale exemplar) is in four parts. The midpoint differs by tradition: le Carre's is internal (doubt crystallizes into a name), Forsyth's is external (the tracks intersect, the clock appears); the strongest delivers both at once.

Discipline: the model proposes N with a rationale tied to strand count and revelation mode; the human ratifies at the Stage 3 (structure) gate. Default 4, overridable to 3 (single-strand slow-burn) or 5. A finer beat-anchor layer sits under the human-legible acts, and every chapter ends on a typed hook, so pacing has structural hooks the prose stage can honor.

## Genre profile

Because the framework is built plot-agnostic but genre arrives with the plot, genre is an unbound parameter validated against a fixture spy-thriller profile. It is a pluggable config object (default act count, revelation mode, target length, words per chapter, cadence knobs) that the plot-agnostic stages consume.

## Cross-stage amendments

Stages are not a pure forward waterfall. When a downstream stage discovers an upstream defect (an outline exposing a world-logic hole, a reveal that cannot be paced), re-running an upstream stage with `force` regenerates it and invalidates every downstream stage so edits ripple forward instead of leaving stale artifacts. Revision is human-triggered (or one best-effort auto-revise pass from the critique); amendment thrash is bounded the same way the revise-iteration cap bounds the prose loop.

## Resolved items

- **JSON vs markdown for the canonical state.** Resolved: JSON/Pydantic is the validated source of truth; rendered markdown is a generated view for human review at gates. All three edit channels (chat, markdown, JSON) reconcile into the JSON, then re-render.
- **One combined gate vs two for the old Stage 1.** Resolved by splitting: world and cast are now separate stages with separate gates, so the cast can be regenerated without re-deriving the world.
- **The acceptance signal for the setup gates.** Resolved into three layers: the deterministic checks (structural floor), the dimensional critique panel (advisory coverage), and the human taste call (the gate itself).

## Why this shape (evaluation summary)

Four independent lenses (narrative craft, agentic-systems, spec-fidelity, alternative-design) plus an adversarial critic evaluated the staged decomposition against the primer. Consensus: the decomposition is a real improvement on the primer's organization (it is the Snowflake Method as a gated pipeline, putting the human gate where reversal is cheapest), but a regression on the primer's controls unless the crown jewels above are explicitly preserved, the intent/fact split is made structural, and the writer stage is treated as the full engine rather than a single writer. The alterations in this doc are those fixes. The later split of cast into its own stage, the real-world grounding, the narrative-design and trope layers, and the critique panel are calibration improvements made once the engine was proven.
