# Agentic Novel Pipeline: System Primer

*A goal-driven, multi-agent system for generating a full-length novel end to end. The point of the experiment is to find out how far a generation-plus-judgment loop can be pushed over 80k+ words while staying coherent and not reading like a machine wrote it.*

---

## TL;DR

A novel is too long to fit in any context window, so the system keeps all state in files and works one chapter at a time. Each chapter goes through a loop: draft, extract what it established back into state, critique it with a fresh adversarial model, then revise. A human (you) approves the plan up front and spot-checks at act boundaries. Claude generates the prose; a different model family (Gemini or GPT) does the critique so it is not grading its own homework. The whole thing runs over one recoverable state file.

The thesis: word production is not the bottleneck. Coherence and taste are. The architecture exists to protect those two things.

---

## The core idea

Two failure modes sink a naive "give it the premise and let it run" loop:

**Coherence drift.** Left alone across chunks, the model contradicts itself: who knew what when, the timeline, planted details. For a thriller this is fatal, because a thriller *is* controlled information asymmetry. The reader learning a secret before the protagonist does, or a character's loyalty staying ambiguous, only holds if every chapter respects a tracked map of who knows what.

**Taste-free sag.** Models generate competent, generic prose that resolves tension too early, over-explains, and falls into repetitive tics over a long run. Novel-shaped text is easy. Prose worth reading needs judgment injected at the decision points.

Everything below is built to attack these two problems specifically.

---

## Architecture at a glance

```
  PREMISE
     |
     v
[ SETUP PHASE ]  run once, human-approved
  decompose -> classify -> world model -> characters (+belief states)
  -> knowledge inventory -> secrecy tiers -> reveal schedule -> structure
     |
     v
  >>> SHOWRUNNER CHECKPOINT 1: approve bible + beat sheet + reveal schedule <<<
     |
     v
[ CHAPTER LOOP ]  repeat per chapter until acceptance gate passes
     |
     |   +--> DRAFT (Claude, scoped context: global / reader / character)
     |   |
     |   +--> EXTRACT (read new chapter, write findings back to state)
     |   |
     |   +--> CRITIQUE (Gemini/GPT, adversarial, + mechanical QA)
     |   |
     |   +--> REVISE (feed flags back into a fix pass)
     |
     |   >>> SHOWRUNNER CHECKPOINT at each act boundary <<<
     v
  STATE FILE updated every chapter (single source of truth)
     |
     v
  FULL MANUSCRIPT
```

The orchestrator (Claude Code or a script) drives the phases and the loop, reading and rewriting the state file each chapter.

---

## 1. The state file (source of truth)

One artifact holds the entire project. It can be a single `book_state.json` or a set of markdown files in the vault; markdown is friendlier to read and hand-edit, JSON is friendlier to validate. Either way it must be recoverable from an interrupt and manually tweakable. It holds:

- **The bible.** Voice and style rules, the plot mechanism fully worked out, world rules, and tradecraft or domain detail.
- **The reveal ledger / knowledge inventory.** Every plot-critical fact as a discrete item, each tagged with a secrecy tier and a planned reveal point. Tiers: `public` (known freely), `hidden` (active secret), `delayed` (will surface on schedule), `never_explicit` (hinted, never stated outright). Reveals are multi-step, mapped to specific chapters.
- **Per-character epistemic state.** For each character: what they know, what they do not know, and what they *falsely believe*. The false-belief field matters more than it sounds. A character acting confidently on wrong intel is most of what drives a thriller.
- **The structural skeleton.** Acts, beats, POV assignment per scene, and the set of plot threads with advancement notes.
- **Rolling summaries.** Compressed memory of what has happened, so the drafter does not need every prior chapter in full.

This file is the thing that makes autonomy survivable. State lives on disk, not in the context window.

---

## 2. Setup phase (run once)

A sequence of steps that turns a one-line premise into the state file:

1. **Decomposition.** Premise into genre signals, constraints, world facts, characters, themes.
2. **Classification.** Primary genre, modifiers, and revelation mode (slow-burn mystery vs immediate action) which sets the pacing of reveals.
3. **World model.** Rules, entities, and causal constraints that keep the world consistent.
4. **Character initialization.** Characters created with their belief states (know / do not know / falsely believe).
5. **Knowledge inventory.** Catalog every plot-critical fact as an item.
6. **Secrecy and clues.** Sort items into tiers; generate ambiguous clues for the hidden and delayed ones.
7. **Reveal schedule.** Plan the multi-step reveals across chapters so tension builds without spoilers.
8. **Structural map.** Acts, beats, POVs, plot threads.

**Showrunner Checkpoint 1.** You approve the bible, beat sheet, and reveal schedule before a single line of prose is written. This is where your judgment matters most and should never be automated. Getting the plan right is cheaper than fixing 80k words later.

---

## 3. The chapter loop (the engine)

This is the heart of the system. It runs once per chapter and repeats internally until the chapter passes its acceptance gate.

**Draft.** Claude writes the chapter from a deliberately limited context: the relevant slice of the bible, this chapter's beat, the rolling summary, the previous chapter in full, and only the slice of the ledger this POV is allowed to see. The scoping is three layers: `global` (true facts of the world), `reader` (what the reader currently knows), and `character` (what this POV knows). The drafter physically cannot see what the character should not know, so leaks are prevented at generation time, not caught afterward. For information asymmetry this is the whole game.

**Extract.** A separate agent reads the freshly written chapter and writes back whatever it established: new facts into the ledger, updated character knowledge, and an appended summary. This keeps state current without you babysitting it.

**Critique.** A fresh, adversarial pass, and per your call this runs on a *different model family* (Gemini or GPT). It checks: did anything leak ahead of schedule, is tension sustained, is the plot logic airtight, is there repetition, is the prose carrying its weight. Self-critique in the same model is charitable to its own patterns; a different architecture catches what the generator is blind to.

**Revise.** The flagged issues feed back into a revision pass. This closes the loop that most builds leave open: they flag problems but never fix them. One or two revise iterations, then accept.

**Acceptance gate.** The chapter is done when the critique pass returns no blocking issues (leak, logic break, or hard repetition). The gate is per chapter. The loop's goal is never "finish the book."

**Showrunner checkpoints** fire at act boundaries. You read, you can intervene, you can rewrite the beat sheet for the next act. Full automation caps quality at "structurally sound." Your checkpoints are what lift it past that.

---

## 4. Anti-repetition arsenal

Repetition is a named adversary with its own toolkit. These are mostly model-independent and worth keeping even with a strong generator:

- **Prose consistency layer.** Each finished chapter is embedded and stored; every new chapter is compared against all prior content to flag repeated phrasing and structures.
- **Rotating opener templates.** Inject varying instructions so chapters do not all start the same way.
- **Entropy injection.** Analyze the previous chapter, generate two or three lines of anti-stagnation guidance for the next.
- **Motif cooldown.** Track recurring images (rain as metaphor, a tell, a gesture) and enforce a gap before reuse.
- **Ban filter.** Strip overused words.

Note: a chunk of this kind of machinery exists in weaker setups purely to compensate for weak models repeating themselves. On a strong generator you can thin it out, but motif cooldown and the leak guard stay useful regardless of model.

---

## 5. The multi-model eval layer

Your addition, and a strong one. The system is model-heterogeneous on purpose. You hand Claude the API keys for Gemini and GPT, kept in the environment and never in prompts, and the orchestrator routes by task:

| Task | Model | Why |
|---|---|---|
| Prose generation | Claude (primary) | Strongest writer in the stack |
| Adversarial critique | Gemini or GPT | Different family, orthogonal blind spots, not grading its own work |
| Mechanical QA (repetition scan, ban filter, continuity diff) | Cheapest capable model, possibly local | Deterministic-ish checks do not need a frontier model; saves cost |
| Tie-break / second opinion on a contested call | The third family | Breaks a deadlock between generator and critic |

**Why cross-family beats redundancy.** Two instances of the same model share the same blind spots, so a second opinion from the same family mostly confirms the first. A different training distribution disagrees in useful places. The value is orthogonality, not duplication.

**Ensemble gating to avoid thrash.** Revise loops can spin forever on subjective nitpicks. Cheap defense: only trigger an expensive revise when two critics agree something is actually wrong. Single-critic gripes get logged, not acted on. This keeps the loop converging.

---

## 6. /goal and /loop

The system is shaped to be driven by a goal-and-loop construct, so if you have `/goal` and `/loop` in your Claude Code setup they map cleanly. If you do not, this section is the spec for building them.

- **`/goal`** binds to the *acceptance criteria*, not the deliverable. The right goal is per chapter: "this chapter hits its beat and passes critique with no leak, no logic break, no hard repetition." The book-level objective lives in the approved beat sheet, not in the loop's goal.
- **`/loop`** binds to the per-chapter cycle: draft, extract, critique, revise, repeat until the goal's acceptance gate passes, then advance to the next chapter.

The trap, and the thing that kills naive versions: a `/goal` of "write the novel" with a `/loop` around it degenerates into exactly the runaway generator that drifts and sags. The discipline is to scope the goal narrow and put a real test at the gate. A loop without an acceptance test is just generation with extra steps.

(Heads up: in the chat interface where this was drafted, `/loop` and `/goal` were not registered commands. Confirm they exist in your project before wiring against them.)

---

## Why it works

- **State in files, not context** survives past the context window and recovers from interrupts.
- **Generator and critic split** is the core quality unlock; **cross-family critique** removes blind spots a single model keeps.
- **Scoped context** enforces information asymmetry at generation time instead of merely documenting it.
- **Secrecy tiers plus a reveal schedule** put reader and character knowledge under beat-by-beat control.
- **The anti-repetition arsenal** fights the sag directly.
- **Human checkpoints** inject taste where it matters and keep quality from plateauing.

---

## Open problems (be honest about these)

- **Character and relationship tracking at scale.** The hardest wall. The wrong fix is a bigger context window; the right fix is retrieval, inject only the relevant slice of state per chapter, plus tighter summaries. Buying context is the expensive way to paper over a state-management problem.
- **Cost vs latency.** Frontier APIs are fast but pricey; local models are cheap but slow (think tens of hours per book). Route mechanical work to cheap models, reserve the strong one for prose and critique.
- **Revise thrash.** Mitigated by ensemble gating, but watch for loops that polish forever. Cap iterations.
- **Taste is not a compute problem.** The most common category error is treating better output as something you buy with more hardware. Past a point, the lever is the showrunner, not the GPU.

---

## Lifted vs changed (from Book-Agent, the closest existing build)

**Lifted:** the single recoverable state file; the knowledge inventory with secrecy tiers including `never_explicit`; characters with explicit belief states including false beliefs; the triple-layer scoped context that enforces no-leak at draft time; the full anti-repetition arsenal.

**Changed:** that build flags problems in QA but does not clearly feed them back into a fix, so we close the loop with an explicit revise pass. It is fully automated with no human in the seat, so we add showrunner checkpoints. It answers context pressure with more VRAM, so we answer it with retrieval. And it runs a single model family, so we add cross-family critique using your Gemini and GPT keys.

---

## Tomorrow's first move

Start at the state file, not the prose. Decide JSON vs markdown, then define the schema for the four pieces that carry the whole system: the ledger item (fact + tier + reveal point), the character record (know / not-know / falsely-believe), the chapter beat, and the rolling summary. Get those four shapes right and the loop has something solid to read and write. Prose generation is the easy part and comes after.
