# LudLLM Architecture

LudLLM is an agentic pipeline that writes a full-length spy novel end to end. A
human approves the plan stage by stage; the models generate. This document is the
current-state architecture: the state graph, the stages and their inputs and
outputs, the loops, the eval stack, and the model routing. For the why behind the
design read [novel-pipeline-primer.md](novel-pipeline-primer.md) (the idea); for
how to drive it conversationally read the repo-root `CLAUDE.md`.

The core bet: word production is not the bottleneck, coherence and taste are. The
whole architecture exists to protect those two over 80k-150k words, where any
single context window is far too small to hold the book.

## Overview: from a premise to a finished book

You hand the system a little: a premise paragraph, and ideally the secret or
betrayal spine (who hides what, and when the reader versus the protagonist should
learn it), maybe a few locked characters, a tone and a length. From that, it builds
the whole book by progressive elaboration. Each step expands the previous one into
more structure, the human approves it, and the next step builds on the approved
result. No single prompt ever writes the book; the book is the fixed point of a
chain of small, reviewed expansions.

**How the plot gets filled in.** The premise is thin; the **world** stage thickens
it. From the premise it invents the worked-out plot mechanism (a real operation with
a method and a fatal vulnerability), then decomposes the story's secrets into a
tiered ledger of discrete facts, grounds the fiction in real organizations and
anchored real incidents, and pins the era(s) with their capability baselines. So
"a spy hides that his mother faked her death" becomes a concrete operation, a set of
named facts each with a secrecy tier, and a reveal order. The **structure** and
**outline** stages then turn that into acts and a chapter-by-chapter plan, binding
each secret's reveal to a specific chapter (and splitting the reader's reveal from
the protagonist's, which is where the irony lives). Plot points are not improvised
during writing; they are planned here and only rendered into prose later.

**Where the extra characters come from.** You rarely supply a full cast, so the
**cast** stage derives the institutional ecosystem the world implies (the services,
desks, and roles such a plot needs), over-generates a role-keyed roster to fill
those slots, then winnows it to a small load-bearing cast. Every invented character
is given a backstory, a worldview, and a belief state bound to the ledger (what they
know, do not know, or falsely believe), so a new character exists to carry a
specific piece of the secret, not as set dressing.

**How your input is preserved while the gaps are filled.** The first stage,
**normalize**, tags every element you provided with a provenance: `user_locked`
(never overwrite), `user_seed` (may elaborate), or `invented`. Everything the model
adds downstream is `invented` and fills a gap; anything you locked is carried through
untouched. That tagging is what lets the same pipeline accept "here is a plot, invent
the people" and "here is a cast, invent the plot," and it is why the expansion never
overwrites your intent. The human gate at every stage is the steering wheel: you see
the elaboration rendered as markdown (with a critique scorecard), edit or regenerate
it, and only then advance. The model fills the gaps; you decide whether the fill is
right.

The rest of this document is the machinery that makes that safe and coherent: one
validated state object, a no-leak contract so a secret cannot reach the page early,
a temporal spine so chronology holds, and a cross-family critic so no model grades
its own work.

---

## 1. The two planes

The system separates a control plane from a data plane.

- **Control plane** (`pipeline/stages.py`, `authoring/run.py`): sequential,
  human-gated, artifact-producing. It runs one stage, critiques it, renders it for
  review, and stops. It never auto-advances the real book.
- **Data plane** (`state/schema.py`): one recoverable `BookState` object that
  every stage reads and writes slices of. Stages are producers and refiners of
  slices of one state, not a relay race of frozen documents.

`book_state.json` is the single source of truth. It is Pydantic-validated. The
rendered markdown (`world.md`, `cast.md`, ...) is a generated view for human
review. Every edit channel (chat, markdown, JSON) reconciles back into the JSON,
then re-renders. Markdown is never treated as truth.

```
  control plane            data plane (one BookState)             view
  -----------              --------------------------             ----
  normalize   ── writes ─► brief.elements                  ─► brief.md
  world       ── writes ─► authored.world / facts / threads ─► world.md, ledger.md
  cast        ── writes ─► authored.characters             ─► cast.md
  structure   ── writes ─► authored.narrative/acts/tropes  ─► structure.md
  outline     ── writes ─► authored.chapter_outline        ─► outline.md, timeline.md
  dossier     ── writes ─► authored.dossiers (+ PDFs)      ─► dossiers.md
  writer loop ── writes ─► running.* (per chapter)         ─► 05_manuscript/*.md
       ▲                          │
       └──── reads every slice ───┘
```

---

## 2. The state graph: `BookState`

The single most important schema decision is the split between **authored intent**
and **extracted running state**. They must not be conflated, because one is
gate-frozen and the other mutates every chapter.

```
BookState
├── meta:    ProjectMeta      (title, schema_version, frozen_stages[])
├── genre:   GenreProfile     (acts, target_words, words_per_chapter, ...)
├── brief:   CreativeBrief    (Stage 0 output: raw_input + elements[] w/ provenance)
├── authored: Authored        ← GATE-FROZEN INTENT (the setup stages produce this)
│   ├── world:           World            (Stage 1)
│   ├── facts:           list[Fact]       (Stage 1: the tiered secret ledger)
│   ├── threads:         list[Thread]     (Stage 1)
│   ├── characters:      list[Character]  (Stage 2: roster + belief states)
│   ├── narrative:       NarrativeDesign  (Stage 3)
│   ├── tropes:          list[TropeUse]   (Stage 3)
│   ├── acts:            list[Act]        (Stage 3)
│   ├── dossiers:        list[Dossier]    (dossier stage)
│   └── chapter_outline: list[ChapterBeat](Stage 4)
├── running:  Running          ← EXTRACTED RUNNING STATE (the writer loop mutates this)
│   ├── chapters:        list[ChapterState]
│   ├── belief_updates:  list[BeliefUpdate]
│   └── rolling_summary: str
└── reviews:  dict[str, StageCritique]   ← ADVISORY critique scorecards (per stage, per chapter)
```

**Why the split is load-bearing.** A character carries `initial_beliefs` (authored
intent). The writer loop appends `BeliefUpdate`s to `running`. Effective knowledge
at chapter N is the authored base overlaid with every update up to N. That is what
lets the extract step run every chapter without invalidating a frozen setup gate:
extract only ever writes to `running`, never to `authored`.

### Key authored shapes

- **`Fact`** is one plot-critical fact: `id`, `text` (the true statement), `tier`
  (`SecrecyTier`), `provenance`, an optional `era_id`, and a `reveal: RevealPlan`.
  A validator enforces the contract: a `public` fact carries no reveal; any
  non-public fact always carries a (possibly empty) reveal plan.

- **`SecrecyTier`**: `public` (known freely) / `hidden` (active secret) / `delayed`
  (will surface on schedule) / `never_explicit` (hinted, never stated outright).
  The tier decides whether a reveal object exists at all and how the eval and
  drafter treat the fact.

- **`RevealPlan`** is authored once as intent in Stage 1 and **bound progressively**
  over later stages, never re-invented:
  - `order` set in Stage 1 (relative intent),
  - `act_anchor` set in Stage 3,
  - `reader_reveal_chapter` and `character_reveal_chapter` set in Stage 4.
  The reader-reveal and character-reveal chapters differ on purpose. That gap is
  the information asymmetry the whole system exists to control.

- **`Character`** carries `role`, `backstory`, `worldview`, a `born` year, an
  `initial_beliefs: list[Belief]`, and (for braided timelines) `era_beliefs:
  dict[era_id, list[Belief]]`, the belief state at the start of each era.

- **`Belief`** is one edge of the knowledge graph: `fact_id`, `kind`
  (`KnowledgeKind`: `knows` / `does_not_know` / `falsely_believes`), and a
  `false_value` required iff the kind is `falsely_believes`. The canonical home for
  a knowledge edge is the character, so there is exactly one writer per edge;
  `who_knows` derives the reverse by scan.

- **`Era`** (the temporal spine, see section 8) anchors a time period to a year and
  carries a `capability_baseline`: the dated tech, forensics, comms, weapons, and
  geopolitics that bound what can happen in it.

### Running shapes

- **`ChapterState`**: `status` (`planned` / `drafted` / `critiqued` / `accepted`),
  `draft_path` (prose lives on disk, not in state), `rolling_summary`,
  `established_fact_ids`, `word_count`, `critique_flags`, `anachronism_flags`,
  `revise_iterations`.
- **`BeliefUpdate`**: appended by extract when prose changes what a character
  knows (`chapter`, `character_id`, `fact_id`, `kind`, `false_value`).

### The computed knowledge graph

The knowledge graph is a **computed view**, not a stored one. There is no graph DB.
`BookState` exposes the traversal as methods over authored intent plus the running
overlay:

- `effective_beliefs(character_id, chapter)` returns a character's knowledge at the
  start of `chapter`: the authored base (`initial_beliefs`, then any `era_beliefs`
  override for the chapter's era), overlaid with every `BeliefUpdate` that happened
  earlier **in story time** (see section 8).
- `character_known_facts`, `who_knows`, `reader_known_facts`, `revealed_in_chapter`
  derive from it.
- `drafter_allowed_facts(pov, chapter)` = facts the POV knows, plus facts the
  reader already knows, plus whatever is being revealed in this very chapter.
- `forbidden_for_drafter(pov, chapter)` = the complement. This is the data behind
  the no-leak guarantee (section 7).

### Why a graph, and what the nodes and edges are

The book's central problem is a relationship problem: who knows what, and when. A
secret is not a property of a fact or of a character alone; it is a property of the
pair, at a point in time. "Does Arjun know his mother faked her death?" has a
different answer in chapter 3 than in chapter 20, and a different answer for Arjun
than for the reader. That is a graph: entities connected by typed, time-varying
relations. Modeling it as a graph is what makes the load-bearing query of the whole
system, "what is this POV allowed to see in this chapter," a cheap traversal instead
of a bespoke lookup scattered through the writer.

The graph is **bipartite and computed**. `state_to_graph(state, chapter)`
(`viz/export.py`, the versioned `GRAPH_SCHEMA_VERSION = 2` contract) materializes it
for any chapter:

- **Nodes are two kinds:**
  - **character** nodes (`id`, `label`, `role`, `born`).
  - **fact** nodes (`id`, `label`, `tier`, `era_id`, and the reveal markers
    `reader_known`, `reader_reveal_chapter`, `character_reveal_chapter`).
  - The **reader** is a distinguished knower handled separately (`reader_known_facts`)
    rather than a character node, because the reader's knowledge advances in reading
    order while characters' advances in story time (section 8).
- **Edges are beliefs, character -> fact**, one per character's effective belief
  about each fact, typed by `kind`: `knows` / `does_not_know` / `falsely_believes`
  (a false edge carries its `false_value`). There are no character-character or
  fact-fact edges; every relation in the model is a belief, and a belief is always
  someone's relation to a fact.

Three properties make the graph the right structure and not just a diagram:

1. **One writer per edge.** The canonical home of a knowledge edge is the character
   (`Character.initial_beliefs`), so there is exactly one place that sets it. The
   reverse direction (`who_knows`) is derived by scan, never stored, so the two can
   never disagree.
2. **The edges are time-varying, and recomputed, not mutated.** Dragging the chapter
   re-resolves every edge through `effective_beliefs` (authored base + story-time
   overlay). The graph at chapter N is a snapshot; nothing in the graph is persisted,
   so there is no stale edge to go wrong.
3. **The same traversal feeds three consumers.** The drafter scoping
   (`drafter_allowed_facts`), the deterministic checks (orphan beliefs, reveal
   inversions), and the `viz` studio all read the same computed graph. The studio
   only renders it; it never re-derives epistemic logic, which is what keeps the
   no-leak contract in one place (Python core).

### `book_state.json`: the file on disk

`book_state.json` is the on-disk serialization of the `BookState` model above, one
file per project at `runs/<slug>/book_state.json`. It is the single source of truth.
Everything else in the project folder (the rendered markdown, the manuscript, the
dossier PDFs, the viz studio) is derived from it and can be regenerated; the JSON
cannot be regenerated from them.

**It is literally the model, serialized.** `save_state` writes
`state.model_dump_json(indent=2)`; `load_state` reads it back through
`BookState.model_validate_json` (`state/store.py`). So the file's structure is
exactly the tree in section 2: top-level `meta` / `genre` / `brief` / `authored` /
`running` / `reviews`, with the authored slice filling in stage by stage.

```jsonc
{
  "meta":   { "title": "...", "schema_version": 1, "frozen_stages": ["normalize", "world", ...] },
  "genre":  { "default_acts": 4, "target_words": 130000, "words_per_chapter": 3000, ... },
  "brief":  { "raw_input": "...", "elements": [ { "kind": "secret", "text": "...", "provenance": "user_locked" } ] },
  "authored": {
    "world": { "premise": "...", "eras": [ ... ], "real_anchors": [ ... ], ... },
    "facts": [ { "id": "f_mother_alive", "text": "...", "tier": "hidden", "reveal": { "reader_reveal_chapter": 18, ... } } ],
    "characters": [ { "id": "c_arjun", "initial_beliefs": [ { "fact_id": "f_mother_alive", "kind": "does_not_know" } ], ... } ],
    "narrative": { ... }, "acts": [ ... ], "tropes": [ ... ], "dossiers": [ ... ], "chapter_outline": [ ... ]
  },
  "running":  { "chapters": [ { "n": 1, "status": "accepted", "draft_path": "05_manuscript/chapter_001.md", ... } ],
                "belief_updates": [ { "chapter": 20, "character_id": "c_arjun", "fact_id": "f_mother_alive", "kind": "knows" } ],
                "rolling_summary": "..." },
  "reviews":  { "world": { "scores": [ ... ], "verdict": "ship", ... }, "chapter_1": { ... } }
}
```

Four properties make it trustworthy as the source of truth:

1. **Validated on every load.** `model_validate_json` runs the full Pydantic schema,
   including the cross-field validators (a public fact may not carry a reveal; a
   `falsely_believes` belief must carry a `false_value`; a braided timeline needs an
   anchored year per era). An illegal hand-edit fails loudly at load instead of
   silently corrupting a run. This is what makes direct JSON editing a safe channel.
2. **Written atomically.** `save_state` writes to a temp file in the same directory,
   `fsync`s, and `os.replace`s it onto the target (atomic on POSIX). A write
   interrupted mid-flush leaves the previous good file intact; the single source of
   truth never ends up half-written.
3. **Recoverable.** A run is resumable from this file alone. `frozen_stages` records
   which gates are approved, so reopening a project knows exactly where it is; the
   running slice records per-chapter status and the belief updates, so the writer
   loop can resume mid-book.
4. **Prose and binaries are referenced, not embedded.** Chapter text lives on disk
   at `draft_path` (`05_manuscript/chapter_NNN.md`); dossier PDFs and portraits live
   under the dossier folder, recorded as `pdf_path` / `spread_path`. The JSON holds
   structured state and pointers, so it stays small and diffable even for a
   150k-word book.

**The three edit channels all reconcile into this file**, then re-render:

- Chat ("move the reveal to chapter 8"): read the JSON, edit it, `ludllm render`.
- A hand-edited markdown file: read it, reconcile the change back into the JSON,
  re-render. Markdown is never the truth.
- A hand-edited `book_state.json`: `ludllm render`; Pydantic catches an illegal edit
  on the next load.

The rule is read-before-write on every channel, so a hand edit is never clobbered.
`schema_version` on `meta` is the forward-compat hook for migrating older files if
the schema changes. The file lives under `runs/`, which is gitignored, so a book in
progress is never committed.

---

## 3. The pipeline at a glance

Six setup stages, then the writer loop, then two off-spine finishing stages (dossier
and viz). Each setup stage produces a slice of authored intent and stops for human
review; the finishing stages run last, after the manuscript exists.

```
 Stage 0  NORMALIZE      any input ─────────► brief.elements[] (with provenance)
 Stage 1  WORLD          brief ─────────────► world + facts (ledger) + threads
 Stage 2  CAST           world + ledger ────► characters + belief states
 Stage 3  STRUCTURE      world + cast ──────► narrative design + acts + tropes + reveal act-anchors
 Stage 4  OUTLINE        structure ─────────► chapter_outline + reveal chapter-binding
 Stage 5  WRITER LOOP    everything ────────► manuscript (per chapter), running state
 ── dossier (finishing)  FINAL state ───────► dossiers + PDF/PNG artifacts
 ── viz     (finishing)  FINAL state ───────► viz/studio.html (interactive view, no state authored)

 SETUP_STAGES     = [normalize, world, cast, structure, outline]   (the linear JSON-authoring spine)
 RUNNABLE_STAGES  = SETUP_STAGES + [dossier, viz]                  (everything you can invoke)
 FINISHING_STAGES = [dossier, viz]                                 (off-spine, mandatory, run last)
```

The setup spine is `[normalize, world, cast, structure, outline]`. Two stages are
deliberately **off** the spine because they produce artifacts from finished state
rather than feeding it: **dossier** (image and PDF files) and **viz** (the
story-graph studio, section 14). Neither has a dimensional rubric; neither is walked
by the critique panel or the downstream-invalidation logic.

They run **last, after the writer**, not before it. The chapter loop mutates state as
it goes (belief updates from extract, plus any mid-write authored edits), so the
dossiers and the knowledge-graph studio must be built from the FINAL book; a
pre-write build would be a snapshot the writing then invalidates. Off-spine does not
mean optional: both are **mandatory finishing stages** (`FINISHING_STAGES`). The
full-book runner runs them once the manuscript is complete; `ludllm status` reports
them as pending until then; `pending_finishing_stages` is the check. Mandatory means
required-to-finish, not auto-run.

Every setup generator is a pure function `(state, models, notes="") -> None` that
fills one slice. They are model-driven: the value is the model's output; the code
is the scaffolding (prompt build, lenient JSON parse, schema validation). Each
accepts a revision `notes` block, so a human edit or an auto-revise critique
regenerates a stage through one code path.

### Spine vs off-spine, and why the distinction matters

The **spine** is the linear chain of JSON-authoring stages: `SETUP_STAGES =
[normalize, world, cast, structure, outline]`. A spine stage produces **authored
intent** that later spine stages build on (world's ledger feeds cast's belief
states, which feed the outline's reveals). **Off-spine** stages (dossier, viz)
consume that finished intent and emit **artifacts** (files, a PDF, an HTML view)
that nothing downstream reads.

The distinction is not cosmetic. Three machineries key off it:

1. **What the critique panel grades.** The dimensional critic (section 10) runs only
   on spine stages, because the rubric judges authored craft (plausibility,
   reveal-craft, voice). There is nothing to score on a rasterized dossier or an
   interactive graph, so off-spine stages have no rubric and the panel skips them.
2. **What downstream-invalidation touches.** Regenerating a spine stage with
   `--force` cascades: `_invalidate_from` unfreezes that stage and everything after
   it on the spine, because their intent depended on it (re-do the world, you must
   re-do the cast). Off-spine stages are **not** cascade-invalidated, because nothing
   on the spine depends on them; you rebuild them deliberately (viz always rebuilds,
   dossier is a cheap re-run).
3. **Where a stage attaches in time.** Spine stages are strictly ordered front to
   back and gated one at a time. An off-spine stage attaches wherever its inputs are
   ready. dossier and viz attach at the **end**, after the writer, because their
   correct input is the finished, written book (the writer mutates state, so an
   earlier build is stale).

Off-spine is orthogonal to **mandatory**. dossier and viz are off-spine and also
required: the book is not finished without its dossiers and its studio
(`FINISHING_STAGES`, section 11). Off-spine describes a stage's relationship to the
critique-and-invalidation machinery; mandatory describes whether the pipeline is
allowed to finish without it. The two answer different questions, which is why a
stage can be both off-spine and required.

---

## 4. The setup stages in detail

For each stage: what it reads, the model and token budget, what it writes, and the
rendered view. All setup generators run on the `author_model` (Sonnet by default,
or the Claude Code subscription, see section 9).

### Stage 0 - normalize (`generate.normalize`)

- **Reads:** `brief.raw_input` (the user's premise, in any shape: a one-line
  logline, or a full cast with no plot).
- **Writes:** `brief.elements: list[BriefElement]`, each tagged with `Provenance`
  (`user_locked` never overwrite / `user_seed` may elaborate / `invented`).
- **Why:** provenance tagging is what lets the same framework accept
  plot-in-characters-out and characters-in-plot-out, and what stops a downstream
  stage from overwriting something the user locked.
- **Output budget:** adapter default. No rubric, no critique panel.
- **View:** `brief.md`.

### Stage 1 - world (`generate.generate_world`)

- **Reads:** `GENRE`, the normalized `BRIEF`, `RAW_INPUT`.
- **Writes:** `authored.world` (premise, setting, rules, factions, tradecraft, the
  worked-out `plot_mechanism`, themes, the real-world grounding, and the era
  timeline), `authored.facts` (the tiered secret ledger), `authored.threads`.
- **Real-world grounding** (Forsyth's false-document technique): `real_organizations`
  used by their real names, `real_anchors` (3+ anchored real incidents the plot
  touches), and any `invented_units` placed inside a real org with a justification.
- **The ledger:** every plot-critical fact as a discrete `Fact` with a `tier`. The
  reveal schedule is authored as INTENT only here (`reveal.order`), no chapter
  numbers yet.
- **The era timeline:** one `Era` for a single-period book, two or more for a
  braided timeline, each anchored to a year with a `capability_baseline`. A `World`
  validator requires an anchored `year_start` on every era once there are two or
  more, because story-time ordering depends on it.
- **Output budget:** 16k tokens. Has a dimensional rubric (plausibility, grounding,
  coherence, originality, stakes_theme, period_authenticity).
- **View:** `world.md` and `ledger.md`.

### Stage 2 - cast (`generate.generate_cast`)

- **Reads:** `GENRE`, the full `WORLD`, the `FACTS` (id/text/tier/era), the `BRIEF`.
- **Writes:** `authored.characters`. Derives the institutional ecosystem the world
  implies, over-generates a role-keyed roster, winnows to a small load-bearing cast,
  and sets each character's belief state (including false beliefs and per-era
  beliefs) against the real Stage 1 fact ids.
- **Why after world:** belief edges must point at real fact ids, so the asymmetry
  is built on the ledger rather than invented in a vacuum.
- A `_clean_character` pass drops a stray empty `false_value` on a non-false
  belief, so a model that mirrors the JSON shape too literally does not hard-fail
  the gated stage.
- **Output budget:** 16k tokens. Rubric: character, plausibility, grounding,
  originality, coherence.
- **View:** `cast.md`.

### Stage 3 - structure (`generate.generate_structure`)

- **Reads:** `GENRE`, `WORLD`, the `CHARACTERS` (id/name/role), the `FACTS`
  (id/tier/era), and the curated `TROPES` catalogue (`reference/tropes.py`).
- **Writes:** `authored.narrative` (`NarrativeDesign`: time `mode`,
  `pov_strategy`/`pov_count`, the eras it braids, the interleave, and a rationale),
  `authored.acts` (with a finer `beat_anchors` layer), `authored.tropes`
  (`TropeUse`, used straight or subverted), and each reveal's `act_anchor` /`order`
  via `reveal_bindings`.
- **Act count** is proposed by the model with a rationale and ratified by the human
  at the gate; it is not hard-coded. Default 4 (see section 11).
- **Output budget:** 12k tokens. Rubric: momentum, reveal_craft, coherence,
  originality, stakes_theme.
- **View:** `structure.md`.

### Stage 4 - outline (`generate.generate_outline`)

- **Reads:** `TARGET_CHAPTERS` (`genre.estimated_chapters`), the `NARRATIVE`, the
  `ERAS` (with baselines), the `ACTS`, `CHARACTERS`, `THREADS`, and the `FACTS`
  with their act anchors.
- **Writes:** `authored.chapter_outline: list[ChapterBeat]`. Each chapter gets a
  `beat` (its turn), a `hook` (its pull into the next), a `pov`, the characters
  `present`, `threads` advanced, and (in a braided timeline) its `era_id` and
  `story_time`. Binds each reveal to a chapter via `reveal_bindings`, splitting
  `reader_reveal_chapter` from `character_reveal_chapter`.
- **Output budget:** 32k tokens, the largest, because it is one beat block per
  chapter across the whole book (~43 chapters at the default target). Rubric:
  momentum, reveal_craft, coherence, grounding, period_authenticity.
- **View:** `outline.md` and `timeline.md` (chapters in story order vs reading
  order, so a braided interleave is reviewable at a glance).

### Dossier stage (`pipeline/dossier.py`, off-spine, mandatory, finishing)

A finishing stage: off-spine but mandatory (in `FINISHING_STAGES`), run **after** the
writer so its content reflects the completed book. Two halves:

1. `generate_dossiers` (model-driven, pure): for each principal it writes the
   file's text and, crucially, the `sealed` redactions **bound to the ledger**.
   `principals` selects the load-bearing roster (every named character except pure
   functionaries, plus any functionary who is a POV or is written into a fact).
   `character_secrets` picks the secrets to redact: secrets ABOUT the subject (a
   fact names them) and secrets KEPT FROM them (they `does_not_know` or
   `falsely_believe` a hidden/delayed fact). So an un-redacted dossier reads as the
   novel's reveals. The build forces every handed-in secret into a sealed redaction
   even if the model dropped one, and retries the generate+parse up to 3 times
   before falling back to a minimal valid file, so one character's bad JSON cannot
   sink the batch.
2. `build_dossier_artifacts` (side-effecting): generates a region/class/profession
   matched surveillance portrait per subject (never defaulting to a Western look),
   composes a three-page classified document with the real text over aged paper,
   and rasterizes a PDF plus a side-by-side spread. Degrades gracefully: no image
   backend draws a placeholder photo; no `rsvg-convert` leaves the data in state
   and writes nothing. Image generation is the only paid, non-deterministic part
   and is guarded by `LUDLLM_NO_IMAGES`. Portraits and the paper are cached so a
   re-run is cheap.

The orchestration persists the model-generated content FIRST, then builds the
(paid, fallible) artifacts, so an image-backend failure cannot discard the
expensive text. **View:** `dossiers.md`.

---

## 5. Stage 5 - the writer loop

This is the entire engine from the primer, not a single "write" call. It is scoped
to one chapter; the loop's goal is never "finish the book." `run_chapter` in
`pipeline/writer/loop.py`:

```
run_chapter(state, n, models, config):
  assert_cross_family_critique()                  # the critic must differ from the drafter
  prose = draft(state, n)                          # scoped, no-leak context (section 7)

  for attempt in range(max_revise + 1):            # default max_revise = 2  -> up to 3 critique passes
      flags = critique(state, n, prose)            # cross-family model flags + the leak guard
      if not flags: accepted = True; break         # converged
      if attempt == max_revise: break              # out of passes, stop with flags
      prose = revise(state, n, prose, flags)       # feed flags back into the scoped context

  leaks        = find_leaks(prose, forbidden)      # advisory record on the chapter state
  anachronisms = scan_anachronisms(prose, era_year)# deterministic period backstop (advisory)
  record word_count, revise_iterations, flags, anachronism_flags

  if accepted:
      result = extract(state, n, prose)            # write established facts + belief updates to RUNNING
      append belief_updates; update rolling_summary; status = accepted
      if advisory: reviews["chapter_n"] = critique_chapter(...)   # voice/momentum/realism note
      if output_dir: write 05_manuscript/chapter_NNN.md
  else:
      status = critiqued                            # left for the human; not accepted
```

Key points:

- **Ordering.** The primer sketched draft -> extract -> critique -> revise. LudLLM
  runs **extract on the ACCEPTED prose only**, so it never writes established facts
  back to state from a draft it is about to throw away.
- **The blocking critic drives convergence.** `critique` (`writer/critique.py`)
  returns a list of must-fix flags. An empty list means accept. The leak guard runs
  regardless of what the critic model says; it is the model-independent floor. If
  the critic refuses to return JSON, it simply cannot block, and the leak guard
  still runs.
- **extract** (`writer/extract.py`) reads the accepted chapter, returns
  `established_fact_ids` and a `summary`, and appends a `BeliefUpdate(kind=knows)`
  for each fact the POV learned. A misformatted extract falls back to the authored
  `character_reveals` plan rather than crashing the run.
- **The advisory chapter note** (`critique_chapter`) is a separate per-chapter
  coverage read (voice_fit, momentum, plausibility, period_authenticity), prepended
  with the chapter's own era so the period critic judges the scene against its
  period, not the latest one. It is advisory; the blocking critic above stays the
  convergence driver.

For a full book, a runner loops `run_chapter` over the outline and pauses at each
act boundary for a human checkpoint. Prose goes to `runs/<proj>/05_manuscript/`.
Once every chapter is accepted, the runner runs the finishing stages
(`run_finishing_stages`: dossier then viz) on the final state, so the dossiers and
the studio reflect the completed book.

---

## 6. The loops, enumerated

The pipeline has five distinct loops, each separately bounded so nothing thrashes:

| Loop | Where | Bound | Tunable |
|------|-------|-------|---------|
| Per-chapter revise | `writer/loop.py` | `max_revise` passes (default 2 -> 3 critiques) | `writer.max_revise` |
| Setup auto-revise | `authoring/run.py` | `auto_revise_passes` (default 1) | `critique.auto_revise_passes` |
| Per-chapter transient retries | full-book runner | `retries` (default 3) | `writer.retries` |
| Dossier generate retry | `pipeline/dossier.py` | 3 attempts, then fallback | (fixed) |
| Full-book chapter loop | runner | one pass over the outline, act-boundary stops | (gated by human) |

The setup auto-revise loop (section 10) regenerates a stage with the critique fed
back as notes and re-critiques, stopping as soon as the verdict reaches `ship` or
the pass budget runs out. Cross-stage amendment (re-running an upstream stage with
`force`) is the human-triggered analogue and is bounded the same way.

---

## 7. The no-leak machinery

The crown jewel. A secret is physically denied to the drafter until its scheduled
reveal, so the reader-vs-character information asymmetry is enforced at generation
time, not patched afterward. All the who-knows-what logic lives in Python; the
drafter only ever sees an allowed set.

`build_drafter_context` (`writer/context.py`) turns `BookState` + chapter into the
drafter's prompt:

```
allowed   = drafter_allowed_facts(pov, chapter)   # POV-known + reader-known + revealed-this-chapter
forbidden = forbidden_for_drafter(pov, chapter)   # the complement

prompt blocks: CHAPTER, POV, ERA, BEAT, INTENT, ROLLING_SUMMARY,
               PREVIOUS_CHAPTER_SUMMARY, ALLOWED_FACTS, TARGET_LENGTH
               (only the allowed facts are ever serialized into the prompt)

leaked = find_leaks(prompt, forbidden)
if leaked: raise LeakError    # belt-and-braces: a forbidden fact must never reach the prompt
```

- The drafter is fed ONLY the allowed facts. A leak is structurally impossible at
  generation time, and `LeakError` is an assertion that the scoping actually did
  its job (it should never fire).
- `find_leaks` (`pipeline/guards.py`) is a model-independent guard. v1 is exact
  substring match against a forbidden fact's text. Real prose leaks are
  paraphrased, so the production guard will need a semantic (NLI) layer on top of
  this exact-match floor; the exact layer stays as the cheap first line. It runs in
  three places: pre-prompt (raises), post-draft critique (adds blocking flags), and
  the advisory chapter record.
- The acceptance test for the whole mechanism is the blind-reader leak eval: hand a
  non-Claude model chapters 1..N and ask it to name the mole; if it can before the
  scheduled reveal, the build failed. (A standalone harness for this is still an
  open follow-up.)

`TARGET_LENGTH` is the other thing the context injects: the drafter is otherwise
given no word goal and chapters come in short, so the per-chapter target is fed as
a soft goal (0.85x-1.2x) with explicit anti-padding guidance.

### Denial by omission, then defense in depth

The prevention is **denial by omission, not instruction.** The drafter is never told
"do not reveal that the mother is alive." It is simply never shown that fact. The
`ALLOWED_FACTS` block is the only fact list in the prompt, and it is built from the
allowed set; the forbidden set is computed only so the system can prove it stayed
out. A model cannot leak a fact it was never given, and it cannot be social-
engineered or confused into revealing one, because the information is not in its
context at all. This is the difference between a lock and a sign that says do not
enter.

Worked example. Suppose fact `f_mother_alive` (tier `hidden`) has
`character_reveal_chapter = 20`, `reader_reveal_chapter = 18`, and at chapter 6 the
POV is Arjun, who `does_not_know` it.

```
chapter 6, POV = Arjun:
  character_known_facts(Arjun, 6)  -> does NOT include f_mother_alive (he doesn't know it)
  reader_known_facts(6)            -> does NOT include it (reader learns at 18)
  revealed_in_chapter(6)           -> does NOT include it (revealed at 18/20)
  => drafter_allowed_facts         -> f_mother_alive absent
  => forbidden_for_drafter         -> f_mother_alive present
  => the prompt's ALLOWED_FACTS never contains its text; build raises LeakError if it somehow did
```

At chapter 20 the same fact moves into `revealed_in_chapter`, so the drafter is
finally allowed it, because you cannot write the discovery scene without the thing
being discovered.

The omission is the floor; three more layers sit on top so a failure is caught:

1. **Pre-prompt assertion.** `build_drafter_context` runs `find_leaks` over the
   assembled prompt and raises `LeakError` if any forbidden fact text is present. It
   should never fire; it is the proof the scoping worked, on the first draft and on
   every revision (both go through the same scoped context).
2. **Post-draft critique guard.** The blocking critic is handed
   `FORBIDDEN_FACT_IDS`, and `find_leaks` runs on the output independently of what
   the critic model says, adding a `LEAK:` flag that forces a revise pass.
3. **Advisory record.** Any post-draft leak hits are recorded on the chapter state
   for the human, and the end-to-end acceptance test is the blind-reader eval
   (section 7 intro): a non-Claude model is asked to name the mole from chapters
   1..N; naming it before the scheduled reveal is a build failure.

**Known hole.** `find_leaks` is exact substring match (`guards.py`). It catches a
verbatim restatement of a fact's text but not a paraphrase ("she had never died" vs
the ledger's wording). The structural omission still holds (the drafter never had
the fact), so a paraphrased leak can only arise if the model independently invents
the secret, which is what the cross-family critic and the blind-reader eval are
there to catch. A semantic (NLI) leak layer on top of the exact-match floor is the
planned hardening.

---

## 8. The temporal spine

LLMs have a weak grip on chronology (a nuke before the test, DNA testing before it
existed, a mobile phone in the 1960s). The fix mirrors the no-leak design: pin time
as a frozen, reviewed constraint and enforce it, rather than trust per-chapter
recall. Four layers:

1. **Eras with capability baselines** (`World.eras`, Stage 1). Each `Era` anchors
   to a `year_start` (and optional `year_end`) and carries a `capability_baseline`:
   the dated tech, forensics, comms, weapons, geopolitics, and period place names
   that bound the period. A single-period book has one era; a braided timeline has
   two or more, and the `World` validator requires an anchored year on every era so
   the ordering below cannot invert.

2. **Story-time, not reading-time, knowledge.** Chapters carry `era_id` +
   `story_time`; facts carry an optional `era_id`. The math:

   ```
   _story_rank(n) = (era_year, era_ordinal, chapter_index)
   ```

   `effective_beliefs` orders belief updates by this story rank instead of raw
   chapter index, so a past-thread chapter never inherits what a later-printed
   present-thread chapter revealed, while a past discovery still flows forward into
   the present thread. The `era_ordinal` tiebreak keeps two same-year parallel
   tracks from collapsing to print order. Characters carry per-era authored
   knowledge (`era_beliefs`) so the same person knows different things in 1961 and
   1991 without bleeding between them. A shared `_resolve_era_id` keeps the ordering
   era and the base-selection era in agreement, including at query points past the
   outline. A single-era or no-era book reduces exactly to legacy chapter-index
   behavior. Reader reveals stay narrative-ordered (the reader experiences print
   order); only character knowledge is story-ordered.

3. **Prevention at draft time.** The drafter is fed an `ERA` block (year, place,
   story time, baseline) for its chapter and told to write strictly inside it, the
   time analogue of feeding it only its allowed facts.

4. **Two backstops.** A deterministic term scan (`reference/anachronisms.py`,
   advisory) flags period-wrong prose in both directions (tech ahead of its time;
   defunct states or superseded place names too late), high-precision and honestly
   partial. And a `period_authenticity` critic dimension (cross-family, on world /
   outline / prose) catches the semantic anachronisms no word list can, each scene
   judged against its OWN era.

The braiding pattern itself (which eras, how they interleave) is a `NarrativeDesign`
choice at Stage 3; `timeline.md` renders chapters in story order vs reading order.

### The deterministic scan, concretely

`scan_anachronisms(text, year)` (`reference/anachronisms.py`) is the cheap
mechanical backstop, the time analogue of `find_leaks`. It is two word-boundary
term dictionaries, checked in both directions:

- `EARLIEST`: `term -> (earliest_year, reason)`, flagged when the scene's year is
  *before* the term could exist ("mobile phone" before 1983, "DNA testing" before
  1986, "Mumbai" before 1995, "GPS" before 1990).
- `LATEST`: `term -> (last_valid_year, reason)`, flagged when the scene's year is
  *after* the term stopped being current ("the Soviet Union" after 1991,
  "Leningrad" after 1991, "Bombay" after 1995).

It returns one advisory line per hit, recorded on the chapter state. It is empty when
the era has no anchored year (nothing to check against). It is intentionally partial
and high-precision: every entry is unambiguous enough to scan prose without drowning
the human in false positives.

### Where the logic can still fail

The anachronism defense is layered precisely because no single layer is sound. The
honest failure modes:

1. **The word list is partial by construction.** It catches lexical howlers
   (named devices, defunct states, renamed cities) and nothing else. A semantic
   anachronism with no flagged term, a character behaving as if a war has already
   happened, reasoning from a doctrine not yet written, using slang from the wrong
   decade, slips straight through the scan. That class is delegated to the
   `period_authenticity` critic, which is probabilistic, not a guarantee.
2. **The capability baseline is authored, so a wrong baseline propagates.** Eras and
   their baselines are model output approved at the world gate. If the baseline is
   itself wrong (a date off by a decade), every downstream check inherits the error:
   the drafter writes inside a bad contract and the critic judges against it. The
   only catch is the human at the world gate. Garbage in, consistent garbage out.
3. **The scan needs an anchored year.** A deliberately vague single-era book (no
   `year_start`) gets no scan at all. A braided timeline cannot be vague (the `World`
   validator forces a year on every era for ordering), so this hole is single-era
   only, but there it is silent: `scan_anachronisms` returns empty, not an error.
4. **The story_time year check is shallow.** The deterministic check
   (`checks.py`) only validates a 4-digit year that literally appears in a chapter's
   `story_time` against its era window. A relative marker ("+3 days") carries no year
   and is skipped, and a chapter mis-assigned to the wrong era passes as long as its
   stated year sits inside that wrong era's span.
5. **Everything here is advisory.** The scan and the critic both inform the human
   gate; neither blocks. A real anachronism that the scan misses and the critic does
   not flag reaches the page unless the showrunner catches it. The system narrows
   the surface and surfaces the obvious cases; it does not certify a chapter
   period-clean.

The design accepts this. The bet is the same as the no-leak bet: prevent at
generation time (the baseline in the drafter's contract), then catch with cheap
deterministic + cross-family layers, and keep the human as the final gate, rather
than pretend any one check is complete.

---

## 9. Model routing

The pipeline is written against a provider-agnostic `ChatModel` protocol
(`generate(system, prompt, task, max_tokens) -> str`). A `ModelBundle`
(`models/base.py`) holds the four roles the pipeline routes to:

| Role | Default model | Family | Used by |
|------|---------------|--------|---------|
| `drafter` | claude-sonnet-4-6 | anthropic | the writer loop (draft/revise) |
| `author` | claude-sonnet-4-6 | anthropic | the setup generators + dossier |
| `extractor` | claude-haiku-4-5 | anthropic | the writer extract step |
| `critic` | gemini-2.5-flash | google | the prose critic + the dimensional panel |

- **The critic must be a different family from the author.** This is the core
  quality unlock: no model grades its own homework. `assert_cross_family_critique`
  (the writer) and `_assert_cross_family` (the eval panel) both enforce it. The
  critic can swap to OpenAI (`gpt-5.1`) with `LUDLLM_CRITIC_PROVIDER=openai`; either
  is still cross-family from the Anthropic drafter.
- **Subscription by default.** `default_bundle` routes the Anthropic-family roles
  through the local Claude Code CLI (`claude -p`, the `ClaudeCodeModel` adapter), so
  calls run on the user's Claude Code subscription instead of the metered API. It
  forces subscription auth by stripping `ANTHROPIC_API_KEY` from the subprocess
  env, and benefits from the CLI's 64k output cap (the large setup JSON does not
  truncate the way an 8k API budget can). The cost is per-call harness overhead and
  subscription rate limits. Opt back to the metered API with
  `LUDLLM_USE_CLAUDE_CLI=0` (needed in CI or any environment without `claude` on
  PATH).
- **Metered path.** `AnthropicModel` streams and accumulates (the SDK refuses a
  non-streaming request whose estimated runtime exceeds 10 minutes, which a large
  `max_tokens` trips) and caches the stable system prompt (the bible and ledger are
  re-read on every pass across ~43 chapters, which is exactly what caching is for).
- Every model id is env-overridable (`ANTHROPIC_MODEL`, `LUDLLM_DRAFTER_MODEL`,
  `LUDLLM_AUTHOR_MODEL`, `LUDLLM_EXTRACTOR_MODEL`, `GEMINI_MODEL`, `OPENAI_MODEL`).
  Point the drafter at Opus for hero chapters when you want.

The provider SDKs import lazily inside each adapter, so the core stays lean and
key-free; constructing an adapter is what pulls the SDK in. With `MockModel`s the
entire pipeline runs deterministically and free (`ludllm demo`).

---

## 10. The eval stack

Quality control is three deliberately distinct layers. None of them replaces the
human gate; they inform it.

1. **Deterministic checks** (`authoring/checks.py`). The structural floor, run
   before every render and printed at the top of each stage's markdown. These are
   the semantic cross-field errors Pydantic cannot catch (it validates one object,
   not references between them): orphan beliefs, unknown act/thread/character/fact/
   era references, false beliefs about public facts, false beliefs with no
   scheduled correction, reveal inversions, reveals pointing at non-existent
   chapters, secrets with no reader-reveal chapter, too few real anchors, eras with
   no year or baseline, a `story_time` year outside its era window, implausible
   ages across eras, and per-era beliefs for an era the character never appears in.
   A clean result is not approval; it just means nothing is structurally broken.

2. **The dimensional critique panel** (`eval/`). An advisory coverage report on
   each setup stage. One cross-family critic call PER rubric dimension returns a 1-5
   score with specific evidence and one concrete fix. The rubric is per-stage, not a
   flat list:

   ```
   world     -> plausibility, grounding, coherence, originality, stakes_theme, period_authenticity
   cast      -> character, plausibility, grounding, originality, coherence
   structure -> momentum, reveal_craft, coherence, originality, stakes_theme
   outline   -> momentum, reveal_craft, coherence, grounding, period_authenticity
   prose     -> voice_fit, momentum, plausibility, period_authenticity
   ```

   The verdict is derived **deterministically from the LOWEST dimension**, never a
   composite average that hides the weak spot: lowest <= 1 -> `regenerate`, == 2 ->
   `tighten`, else `ship`. It renders as a scorecard on top of the stage markdown.
   Every critic gets the same shared `grounding_context` (the ledger, real orgs,
   real anchors, eras) so any dimension can check grounding and period accuracy.

3. **The prose blocking critic + leak guard** (`writer/critique.py`). Must-fix
   faults only (leak / logic / grounding / repetition), so the draft -> revise loop
   converges instead of thrashing on taste.

### Critique modes (how the panel acts on its verdict)

`authoring/run.py` orchestrates the panel. The mode (default `auto_revise`) decides
what happens to the verdict before the human sees it:

- **`advisory_only`**: score and render; the human decides.
- **`auto_revise`**: if the verdict is not `ship`, invalidate the stage, regenerate
  it with `critique_notes` fed back as the revision notes, and re-critique, up to
  `auto_revise_passes` times (default 1), stopping as soon as the verdict reaches
  `ship`. Records `revised` and `revise_passes` on the scorecard.
- **`blocking`**: a `regenerate` verdict unfreezes the stage (holds the freeze) so
  it cannot advance until the human resolves it.

The scorecards live on `state.reviews` (keyed by stage, and `chapter_<n>` for the
prose note). They are advisory metadata: regenerated freely, never gate-frozen,
never mutate authored intent. Even in `blocking` mode the human resolves the stage;
the panel only holds the freeze, it never rewrites the book on its own.

---

## 11. The gate framework

`pipeline/stages.run_stage` is the low-level control primitive. A stage in
`meta.frozen_stages` is not re-run. That is what protects approved authored intent
while the writer's extract step keeps mutating the running state underneath it.

Two gate dispositions:

- **Programmatic gate** (`gated=True` + a `Reviewer` callback): the reviewer
  approves before the stage freezes. Used by automated runners and tests.
- **Out-of-band human gate** (the file/conversational workflow): `authoring/run.py`
  runs a stage with `gated=False`, so it auto-freezes on a successful run, then
  renders the markdown and STOPS. The human reviews the rendered files plus the
  critique scorecard and decides whether to run the next stage or to regenerate
  this one. The freeze prevents an accidental re-run; the human advancing to the
  next stage is the real gate.

**Cross-stage amendment.** Stages are not a pure forward waterfall. When a
downstream stage exposes an upstream defect, re-running the upstream stage with
`force` regenerates it AND invalidates every downstream stage (`_invalidate_from`
unfreezes the stage and everything after it on the spine), so edits ripple forward
instead of leaving stale artifacts. `stale_stages` reports downstream artifacts
that ran before an unfrozen upstream stage. Note the off-spine stages (dossier,
viz) are not cascade-invalidated this way; after regenerating an upstream stage,
re-run them to refresh.

**The mandatory finishing stages.** The off-spine dossier and viz stages are
required, but they run **last**, after the manuscript, not before it.
`FINISHING_STAGES = [dossier, viz]`; `run_finishing_stages(project, models)` builds
them in order (dossier on the models, viz model-free) from the final state, and the
full-book runner calls it once every chapter is accepted, so the dossiers and the
studio reflect the completed book rather than a pre-write snapshot the writing would
invalidate. `pending_finishing_stages` and the `ludllm status` "Finishing stages"
line surface what is still owed. Mandatory means required-to-finish; the human still
runs each stage (nothing auto-advances the book).

**Two kinds of redo**, distinct in cost:

- "Apply my edits" = edit `book_state.json` directly, then `ludllm render`. No model
  call, cheap. Pydantic catches an illegal edit on load.
- "Regenerate with my notes" = `ludllm stage <proj> <stage> --force`, which re-runs
  the stage on the model (costs tokens) and invalidates downstream. The generators
  accept a NOTES block; auto-revise uses the same path.

---

## 12. Tunable parameters

The loop and revision counts are user-editable in `params.toml`, not code
constants (`params.py`). Layered, lowest wins to highest:

```
package defaults  <  global (~/.config/ludllm/params.toml)  <  per-project (runs/<proj>/params.toml)
```

A stage reads ONLY the params relevant to it (`STAGE_PARAMS`):

- **setup stages** (world/cast/structure/outline): `critique.mode`,
  `critique.enabled`, `critique.auto_revise_passes`.
- **writer stage**: `writer.max_revise`, `writer.retries`, `writer.advisory`.
- **normalize and dossier** have no loop/revision knobs.

Defaults: `critique.mode = auto_revise`, `critique.enabled = true`,
`critique.auto_revise_passes = 1`, `writer.max_revise = 2`, `writer.retries = 3`,
`writer.advisory = true`. A new project is seeded with an all-commented template
that overrides nothing until a line is uncommented. `ludllm params <proj>` shows
the resolved values and their source layer; a change is a read-modify-write of the
per-project file, validated by round-tripping the whole file through the `Params`
model before persisting.

---

## 13. The file workflow and CLI

A project is a directory under `runs/`:

```
runs/<proj>/
├── book_state.json          ← the canonical, validated source of truth
├── params.toml              ← seeded, all-commented tunables
├── 00_brief/   brief.md
├── 01_world/   world.md, ledger.md
├── 02_cast/    cast.md
├── 03_structure/ structure.md
├── 04_outline/ outline.md, timeline.md
├── 05_manuscript/ chapter_NNN.md     ← the prose
├── 04b_dossiers/ dossiers.md + per-character PDFs/spreads
└── viz/        studio.html           ← the story-graph studio (the viz stage; section 14)
```

The render map (`authoring/render.py`) is one or two markdown files per stage,
regenerated from the JSON on every stage run so earlier files that later stages
fill in (the ledger's reveal columns) stay in sync.

CLI surface (`cli.py`):

- **Offline, no keys:** `demo` (run the bundled example end to end on mocks),
  `graph` (export the story graph at a chapter), `show` (summarize a state file),
  `new` (scaffold a project), `render` (re-render markdown from JSON), `status`
  (stage progress + checks), `viz` (build the studio; the quick-refresh alias for
  the viz stage, section 14), `params`.
- **Real models** (`uv sync --extra models`, keys in `.env`): `stage <proj> <stage>`
  runs a stage, with `--force`, `-i/--interactive`, `--critique-mode`, and
  `--no-critique`; `critique <proj> <stage>` re-runs the dimensional panel
  advisory-only. The setup stages and dossier use the models; `stage <proj> viz`
  runs the model-free viz stage (no keys needed).

The writer stage is driven by `run_chapter` (and a thin full-book runner), not a
dedicated subcommand, because a long unattended write wants act-boundary
checkpoints.

---

## 14. The story-graph studio (the viz stage)

`ludllm viz` builds a self-contained, interactive view of one book's knowledge
graph into `runs/<proj>/viz/studio.html`: open it in any browser, no server. It is
the visual front end to the computed knowledge graph (section 2), and the place the
showrunner inspects the information asymmetry before committing to a 40-chapter
write.

### It is an off-spine, mandatory finishing stage (and a standalone command)

`viz` is a runnable pipeline stage (`STAGE_VIZ`, in `RUNNABLE_STAGES`) but
deliberately **off the authoring spine** (`SETUP_STAGES`), the same shape as the
dossier stage. What that means concretely:

- **It authors no state and needs no models.** `run_stage` short-circuits it before
  any model, critique, or markdown-render machinery (`authoring/run.py`); the writer
  passes `models=None`. So `ludllm stage <proj> viz` runs offline, with no keys.
- **It always rebuilds.** A view should never go stale, so unlike an authoring
  stage it re-renders every run rather than skipping when frozen. It records itself
  in `frozen_stages` once, only so `ludllm status` shows it done.
- **It is never invalidated by an upstream `--force`.** Downstream invalidation only
  walks the spine, so regenerating the outline does not unfreeze viz. Re-run it (or
  the `ludllm viz` alias) to refresh after an edit.
- **It runs last, and it is mandatory.** Off-spine does not mean optional: `viz` is in
  `FINISHING_STAGES`, run after the writer so the graph reflects the final book
  (the chapter loop writes belief updates as it goes). The full-book runner builds it
  once the manuscript is complete; the book is not finished without it. See
  section 11 / `run_finishing_stages`.
- **Run it after the dossier stage** (both are finishing stages) so the Dossiers tab
  is populated; the Story Graph tab needs only the outline, so it also renders
  mid-write if you run the `ludllm viz` alias to peek.

The standalone `ludllm viz <proj>` command (`cmd_viz`) does the same render without
touching the freeze, for an ad-hoc refresh. Both call `build_viz` (`viz/studio.py`),
which precomputes a graph blob in Python (`build_studio_data` / `state_to_graph`)
and writes the HTML with the data inlined. All epistemic logic stays in the core;
the page only renders precomputed data, never re-deriving who-knows-what. The output
is derived and gitignored.

### Two top-level tabs

The studio opens on two tabs:

- **Story Graph** (default): the knowledge graph over chapters, with a chapter
  slider, three views (below), a revealed-only secrets panel, and click-to-open
  detail panels for any secret or character.
- **Dossiers**: a card grid of the cast (portrait, name, role, a backstory line),
  each opening an inline paginated viewer of that character's classified file
  (pages rasterized from the dossier PDF). Empty if the dossier stage has not run.

A chapter slider drives the whole Story Graph tab. Dragging it moves "chapter N";
character knowledge resolves by **story time** and the reader by **reading order**
(section 8), so on a braided timeline a flashback chapter correctly shows a
character knowing less than a later-printed present-day chapter.

### The three Story-Graph views

The same underlying belief graph, shown three ways:

1. **Knowledge** (the default). A swimlane per character plus a Reader lane. At
   chapter N, each secret a character holds is a dot, anchored at the chapter they
   first learned it (so static characters cluster their knowledge at chapter 1 and a
   protagonist's dots march across the timeline). Green = knows, red = holds a false
   belief, dot size = secrecy tier; the Reader lane shows what the reader has been
   told. A playhead marks chapter N. This is the "who knows what, and since when"
   view.
2. **3-chapter window.** A combined mesh of chapters N-1, N, N+1 with a single
   shared character column on the left and three tinted fact bands (one per
   chapter). Edges run character -> fact, colored by belief (green knows, red dashed
   for a lie); a secret square carries a blue outline when the reader knows it. This
   is the close-up "state right around here" view, for reading the asymmetry at a
   specific beat.
3. **Propagation.** A cascade of acquisition events: when a character learns or is
   corrected on a fact, plotted at that chapter, with an inferred-source arrow from a
   character who was on stage and already knew. Green = acquisition, orange =
   corrected, dashed = inferred transfer. This is the "how knowledge spreads through
   the cast over time" view.

Below the graph, the **secrets panel** has two sub-tabs ("Reveals near chapter N"
and "What each character knows"), and clicking any secret or character opens a
**detail panel** (tier and meaning, who holds it, the reveal schedule, or a
character's full belief set, with a jump to that character's dossier).

The split is the same one the rest of the system enforces: precompute in Python,
render only in JS. `state_to_graph` is the versioned contract (`GRAPH_SCHEMA_VERSION
= 2`); the renderers consume it and never recompute knowledge, which is what keeps
the no-leak logic in exactly one place.

---

## 15. The trope catalogue

`reference/tropes.py` is a curated catalogue of spy-genre tropes, drawn from le
Carre, Forsyth, and Littell. It is **reference data, not model output**: a fixed
palette the structure stage consults, so the model is choosing from a researched set
rather than free-associating genre cliches.

**Shape.** `SPY_TROPES` is a list of ~31 entries grouped into six families: moles /
doubles / sleepers; deception tradecraft; the institution; people; and structure /
set-piece / ending. Each entry has four fields:

- `name` (e.g. "The mole at the top"),
- `what` (one line on the mechanism),
- `example` (a real scene from a named novel, e.g. Tinker Tailor's Bill Haydon),
- `fresh` (how to use it well or play it against the grain).

The `fresh` field is the point. A trope played straight reads as cliche; the field
pre-loads the inversion ("skip the whodunit-among-five shape; let the reader know
early and mine the cost of silence"), so the catalogue pushes toward subversion
rather than imitation. The `example` is calibration, not plot to copy (the
non-negotiable against using a real film's plot still holds).

**How it is used.**

1. `tropes_digest()` flattens the catalogue into a compact text block.
2. `generate_structure` injects that block as the `TROPES` prompt block (section 4,
   Stage 3) under a guiding rule: pick only the tropes that serve THIS story's
   secret, never at random, and use at least one against the grain.
3. The model's selection is written back to state as `authored.tropes:
   list[TropeUse]`, each recording `name`, `how_used`, and a `subverted` flag, so
   the choice is auditable and reviewable at the structure gate rather than buried
   in prose.
4. The `originality` critic dimension on the structure stage scores exactly this:
   whether cliches are examined or subverted rather than used straight.

So the catalogue is a curated input (the palette), the selection is gated authored
intent (`TropeUse`), and the critique panel checks that the selection took a swing.
The model never invents the menu; it commits to dishes from a known one and records
which it bent.

## 16. Prompts and the rest of the reference data

- **All system prompts live in one registry** (`prompts.py`): the prompts for
  normalize, world, cast, structure, outline, drafter, critique, extract,
  stage-critic, and dossier. Calibrate there; do not scatter prompt edits into the
  pipeline modules.
- `reference/anachronisms.py` is the deterministic period term scan (section 8).

---

## 17. Act-count and genre policy

No single standard exists for spy novels. Three-act is the generic default;
**four-act is the default for this system specifically**, because the whole thing
pivots on a midpoint information-asymmetry reversal (the mole turn, the false-belief
collapse), and four-act is three-act with Act 2 split at exactly that midpoint,
giving the pivot its own structural home instead of a baggy Act 2 sagging over 130k
words. The model proposes N with a rationale tied to strand count and revelation
mode; the human ratifies at the structure gate. Default 4, overridable to 3
(single-strand slow-burn) or 5.

Genre arrives with the plot, so it is a pluggable `GenreProfile` the plot-agnostic
stages consume: `default_acts` (4), `revelation_mode` (slow_burn), `target_words`
(130k), `words_per_chapter` (3k, so `estimated_chapters` is ~43), `cliffhanger_rate`
(0.5).

---

## 18. Cost

A full setup (normalize through outline, five stages) is roughly $0.25-0.45 on
Opus. A full book (the writer stage, ~43 chapters) is roughly $10-40. The critique
panel adds cheap Gemini calls (one per rubric dimension per stage; auto-revise can
double a stage's cost when it triggers). On the subscription path the metered spend
is near zero (only the Gemini critic and the dossier images bill), at the cost of
subscription usage. Prompt caching is on in the Anthropic adapter. Real stages spend
tokens, so only run them when the user intends to.

---

## Appendix: build order and why this shape

Built engine-first, against fixtures, hardest part first: the state schema, then
the writer loop with scoped-context no-leak enforcement over hand-authored fixture
artifacts, then cross-family critique routing, then the upstream generators and the
normalizer, then the file workflow and the dimensional critique panel on top. The
no-leak chapter engine is the only genuinely hard part; building pretty setup
stages first and bolting them onto an unproven writer is the failure mode (beautiful
setup, naive writer). The engine and all setup stages were proven on mocks, then
validated end to end on real Opus before the critique layer went on.

The decomposition is the Snowflake Method as a gated pipeline, putting the human
gate where reversal is cheapest. It was evaluated against the primer through four
independent lenses (narrative craft, agentic systems, spec fidelity,
alternative-design) plus an adversarial critic. The consensus risk was that a stage
decomposition regresses on the primer's controls unless the crown jewels are
explicitly preserved: the intent/fact split made structural, the writer stage
treated as the full engine rather than a single writer, generation-time no-leak
enforcement, the closed draft-critique-revise-extract loop, per-character belief
states with the false-belief field, cross-family adversarial critique, real-world
grounding, the temporal spine, and prompt caching. Those are the load-bearing
elements this architecture is built around. The later split of cast into its own
stage, the real-world grounding, the narrative-design and trope layers, the temporal
spine, the dossier stage, and the critique panel are calibration improvements made
once the engine was proven.
